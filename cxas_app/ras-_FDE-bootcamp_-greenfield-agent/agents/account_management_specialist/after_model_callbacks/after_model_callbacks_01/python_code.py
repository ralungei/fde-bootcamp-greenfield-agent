# ==========================================================================================
# WHAT THIS CALLBACK DOES (after_model_callback)
# ------------------------------------------------------------------------------------------
# Runs AFTER the model has written its reply and BEFORE the caller hears it.
#
# We use this to guarantee the closing line of the call. When a tool has set a closing state
# (handover to a human, or a malicious caller), this callback:
#   * Checks that the model is saying the exact verbatim line (handover_message, from app.json).
#   * If the model paraphrased it, replaces the text with the exact line.
#   * Adds end_session so the call really ends right after the line, exactly once.
#   * If the model said the line exactly, keeps its original audio (sounds more natural).
#
# If we did not have this:
#   * The model could reword the legal / transfer line ("let me get someone for you..."),
#     which fails compliance and the golden tests.
#   * The call might not end after the transfer line, or end_session could be sent twice.
#   * The model could keep talking after saying goodbye to a malicious caller.
# ==========================================================================================

from typing import Optional

CLOSING_STATES = {
    "handover_completed": "handover_completed",
    "malicious_terminated": "malicious_caller_terminated",
}


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Guarantee the exact verbatim handover line is spoken (preserving native audio when matched), then end_session."""
    state = callback_context.state
    closing_reason = CLOSING_STATES.get(state.get("flag_val"))
    if not closing_reason:
        return None
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        return None

    for part in llm_response.content.parts:
        fc = getattr(part, "function_call", None)
        if fc and getattr(fc, "name", "") in ("execute_live_agent_handover", "report_malicious_utterance"):
            return None
        if fc and getattr(fc, "name", "") == "end_session":
            state["flag_val"] = ""
            return None

    # Consume closing state so end_session can never be injected more than once
    state["flag_val"] = ""

    expected_line = (
        state.get("handover_message")
        or state.get("copy_live_agent_handoff_primary")
        or "I'll connect you to a representative who can help. Please hold."
    )

    spoken_text = " ".join(
        p.text.strip() for p in llm_response.content.parts if getattr(p, "text", None)
    ).strip()

    def _norm(s: str) -> str:
        return " ".join(s.lower().replace("\u2019", "'").split())

    end_call_part = Part.from_function_call(
        name="end_session",
        args={"reason": closing_reason},
    )

    if _norm(spoken_text) == _norm(expected_line):
        new_parts = list(llm_response.content.parts)
        new_parts.append(end_call_part)
    else:
        new_parts = [
            Part.from_text(text=expected_line),
            end_call_part,
        ]

    return LlmResponse(content=Content(parts=new_parts, role="model"))
