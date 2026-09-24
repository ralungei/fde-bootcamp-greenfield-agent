# We use this to force the exact closing line and end_session; without it the model could paraphrase the transfer line and the call might not end.

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
