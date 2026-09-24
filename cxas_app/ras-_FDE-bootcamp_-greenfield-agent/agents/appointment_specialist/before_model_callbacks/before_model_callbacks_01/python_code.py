# Copyright 2026 Google LLC
# ==========================================================================================
# WHAT THIS CALLBACK DOES (before_model_callback)
# ------------------------------------------------------------------------------------------
# Runs BEFORE every call to the model. It handles the things that must be deterministic
# (decided by code, not by the LLM). It can answer on its own and skip the model entirely.
#
# We use this to:
#   * Record the digits the caller actually said or typed (caller_said_digits), so
#     fetch_customer_profile can only identify with a number the caller gave, never the caller ID.
#   * Normalise keypad (DTMF) input so PINs and numbers reach the model in a clean format.
#   * Pick the language on turn 1 from the caller's area code.
#   * Count silences: after 3 no-inputs, transfer to a human and end the call.
#   * Escalate when a backend tool is down, and end the call after repeated invalid input.
#   * Block restricted / anonymous callers with a fixed line.
#   * Speak the opening greeting (regional outage notice + recording notice + welcome) word
#     for word from the copy_* variables in app.json.
#   * Close the call if a closing state was left pending (handover or malicious caller).
#
# If we did not have this:
#   * The model could identify someone silently with the caller ID and send an OTP to them.
#   * The legally required recording notice and greeting could be paraphrased or skipped.
#   * Silent or abusive calls could stay open forever, and tool outages would leave the
#     caller stuck instead of reaching a human.
# ==========================================================================================
"""
before_model_callback — Telco Voice Central Per-Turn Preprocessing Pipeline (Section 6).

SCOPE
-----
This callback handles ONLY platform protocol signals and deterministic state:
DTMF transport normalization, No-Input accounting (BR-TV-006), tool-error escalation
(BR-TV-010), the Turn-1 language bootstrap from telephony data (BR-TV-004), the restricted
caller block, the opening greeting, and the fallback session close.

Anything that requires UNDERSTANDING the caller is detected generatively by the LLM and
enforced through a tool:
  * language switches (BR-TV-020)      -> update_language
  * prior-payment claims               -> verify_payment_posted
  * malicious utterances (BR-TV-016)   -> report_malicious_utterance
  * recording-notice re-emission        -> the agent instruction

All spoken copy lives in app.json (`copy_*` variables), never in this file, so adding a
language is a data change.
"""

import re
from typing import Optional

# Telephony data (not caller intent): area codes served in the secondary language.
SECONDARY_CLID_PREFIXES = ("514", "418", "438", "305")

# Session states that must close the call once the caller has heard the verbatim line.
CLOSING_STATES = {
    "handover_completed": "handover_completed",
    "malicious_terminated": "malicious_caller_terminated",
}


def _copy(state, key: str) -> str:
    # // Los textos verbatim viven en app.json (variables copy_*). Si faltara la copia del
    # // idioma activo se cae al principal, para no dejar la llamada en silencio.
    lang = state.get("language") or "primary"
    return state.get(f"copy_{key}_{lang}") or state.get(f"copy_{key}_primary") or ""


def _extract_last_user_text(callback_context: CallbackContext, llm_request: LlmRequest) -> str:
    texts = []
    try:
        for part in callback_context.get_last_user_input():
            if getattr(part, "text", None):
                texts.append(part.text)
    except Exception:
        pass
    if not texts and getattr(llm_request, "contents", None):
        last_content = llm_request.contents[-1]
        if getattr(last_content, "role", "") == "user":
            for part in getattr(last_content, "parts", []):
                if getattr(part, "text", None):
                    texts.append(part.text)
    return " ".join(texts).strip()


_NUM_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "zéro": "0", "un": "1", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5",
    "sept": "7", "huit": "8", "neuf": "9",
}


def _spoken_digits(text: str) -> str:
    # // Pasa a cifras lo que el cliente dice o teclea ("four one five" -> "415").
    out = []
    for tok in re.findall(r"\d+|[a-zà-ÿ]+", (text or "").lower()):
        if tok.isdigit():
            out.append(tok)
        elif tok in _NUM_WORDS:
            out.append(_NUM_WORDS[tok])
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _is_no_input(user_text: str) -> bool:
    if not user_text:
        return False
    # Platform protocol signals ONLY (never user intent):
    #   - documented CES marker: "<context>no user activity detected for N seconds.</context>"
    #   - simulator variants: "<event>no-input</event>" / "no_input"
    # Deliberately NOT matching words like "silence", which a caller may legitimately say
    # ("there is silence on the line when I call").
    return bool(
        re.search(r"no user activity detected|no[-_]input|<event>\s*no-input\s*</event>", user_text, re.IGNORECASE)
    )


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    state = callback_context.state
    user_text = _extract_last_user_text(callback_context, llm_request)
    # // Registro determinista de los numeros que el cliente ha dicho o tecleado en la llamada.
    # // fetch_customer_profile solo identifica con un numero que aparezca aqui (nunca el caller ID).
    said = _spoken_digits(user_text)
    if said and said not in (state.get("caller_said_digits") or ""):
        state["caller_said_digits"] = ((state.get("caller_said_digits") or "") + " " + said).strip()[-400:]
    lower_text = user_text.lower()

    # STEP 1: DTMF NORMALIZATION (spec Section 6.1)
    # This is transport-level normalization, NOT intent detection. Only three sources:
    #   1) native CES DTMF payload:  <dtmf>1234</dtmf>  /  "dtmf: 1234"
    #   2) the wording named in the spec: "user pressed 1234"
    #   3) a digits-only utterance:  "1234" / "1 2 3 4"
    # Everything else (what the caller MEANS) is left to the LLM.
    native_dtmf = str(state.get("dtmf") or "").strip()
    if native_dtmf:
        state["dtmf_digits"] = re.sub(r"[^0-9]", "", native_dtmf)
    else:
        dtmf_match = re.search(
            r"(?:<dtmf>|dtmf[\s:=]+|(?:user|caller)?\s*pressed\s+|card\s+number\s+is\s+|^)\s*([0-9][0-9\s\-]{3,19})\s*(?:on\s+keypad|</dtmf>|</context>|[,\.\s]|$)",
            lower_text,
        )
        state["dtmf_digits"] = re.sub(r"[^0-9]", "", dtmf_match.group(1)) if dtmf_match else ""

    # STEP 2: TURN-1 LANGUAGE BOOTSTRAP (BR-TV-004)
    # Only telephony data is used here, because the greeting is emitted before the caller has
    # said a single word. A mid-call switch (BR-TV-020) is detected by the LLM and applied
    # deterministically through the update_language tool.
    clid = str(state.get("clid", ""))
    if str(state.get("language_locked", "")).lower() != "true":
        if clid.startswith(SECONDARY_CLID_PREFIXES):
            state["language"] = "secondary"
        else:
            state["language"] = state.get("language") or "primary"
        state["language_locked"] = "True"

    # Fallback close: the same-turn close is done by after_model_callback. If a further turn
    # still arrives after the call was supposed to end, close here using the EXACT line the
    # tool produced (business/fraud/refund/malicious wording all differ).
    closing_reason = CLOSING_STATES.get(state.get("flag_val"))
    if closing_reason:
        state["flag_val"] = ""
        return LlmResponse.from_parts(
            parts=[
                Part.from_text(text=state.get("handover_message") or _copy(state, "live_agent_handoff")),
                Part.from_function_call(name="end_session", args={"reason": closing_reason}),
            ]
        )

    # Clear one-shot redirect trigger once the turn has already landed in M3 (billing_specialist)
    # so if the caller changes topic mid-flow, Root_agent will not force them back into M3.
    if state.get("flag_val") == "balance_owed_redirect":
        state["flag_val"] = ""

    # Suspension state and the past-due balance are backend facts, not caller claims: they are
    # owned by execute_suspend_restore and verify_payment_posted. Card authorization is owned by
    # process_payment. The LLM decides WHEN to call them; the tools decide the answer.

    # STEP 3: NO-INPUT ACCOUNTING (BR-TV-006)
    if _is_no_input(user_text):
        counter = int(state.get("local_noinput_counter") or 0) + 1
        state["local_noinput_counter"] = str(counter)
        if counter >= 3:
            return LlmResponse.from_parts(
                parts=[
                    Part.from_text(text=_copy(state, "live_agent_handoff")),
                    Part.from_function_call(
                        name="end_session",
                        args={"reason": "no_input_escalation"},
                    ),
                ]
            )
        return LlmResponse.from_parts(parts=[Part.from_text(text=_copy(state, "noinput_reprompt"))])
    elif user_text and user_text != "<event>session start</event>":
        state["local_noinput_counter"] = "0"
        state["utterance"] = user_text

    # STEP 4: TOOL-ERROR CLASSIFICATION (BR-TV-010)
    api_resp = str(state.get("api_resp", ""))
    if any(code in api_resp for code in ("SYSTEM_DOWN", "INTERNAL_ERROR", "AUTH_SERVICE_UNAVAILABLE")):
        state["api_resp"] = ""
        return LlmResponse.from_parts(
            parts=[
                Part.from_text(text=_copy(state, "live_agent_handoff")),
                Part.from_function_call(
                    name="end_session",
                    args={"reason": "system_unavailable"},
                ),
            ]
        )
    if any(code in api_resp for code in ("INVALID_INPUT", "MALFORMED_REQUEST")):
        state["api_resp"] = ""
        err_count = int(state.get("global_err_count") or 0) + 1
        state["global_err_count"] = str(err_count)
        if err_count >= 3:
            return LlmResponse.from_parts(
                parts=[
                    Part.from_text(text=_copy(state, "live_agent_handoff")),
                    Part.from_function_call(
                        name="end_session",
                        args={"reason": "too_many_errors"},
                    ),
                ]
            )

    # STEP 5: RESTRICTED CALLER & SESSION START GREETING
    if clid.startswith("999") or state.get("restricted_caller") == "true":
        return LlmResponse.from_parts(
            parts=[
                Part.from_text(
                    text="We are unable to complete your call from this number. Goodbye."
                ),
                Part.from_function_call(
                    name="end_session",
                    args={"reason": "restricted_caller_blocked"},
                ),
            ]
        )

    if user_text == "<event>session start</event>":
        advisory = _copy(state, "regional_advisory") if state.get("regional_alert_active") == "true" else ""
        opening = f"{advisory}{_copy(state, 'recording_notice')} {_copy(state, 'greeting_main')}"
        state["greeting_emitted"] = "True"
        return LlmResponse.from_parts(parts=[Part.from_text(text=opening)])

    return None
