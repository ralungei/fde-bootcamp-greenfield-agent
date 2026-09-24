def execute_live_agent_handover(reason: str = "user_requested_agent", summary: str = "") -> dict:
    """Transfer the caller to a human representative and select the exact verbatim transfer sentence."""
    r = (reason or "user_requested_agent").strip().lower()

    # // Guarda determinista: prohibir por codigo que el modelo escale por fallo de
    # // autenticacion antes de haber agotado los 3 intentos reales (misc_counter >= 3).
    # // Si el cliente pide un agente humano (reason='user_requested_agent'), NO entra aqui
    # // y se transfiere inmediatamente.
    if r in ("auth_failed", "auth_failure_handoff") and int(context.state.get("misc_counter") or 0) < 3:
        used = int(context.state.get("misc_counter") or 0)
        remaining = max(1, 3 - used)
        return {
            "status": "error",
            "error": "PREMATURE_ESCALATION_BLOCKED",
            "attempts_used": used,
            "attempts_remaining": remaining,
            "agent_action": (
                f"Do NOT escalate yet — the caller has only failed {used} of 3 allowed verification attempts "
                f"({remaining} attempts remaining). Ask the caller in their active language ({{language}}) to "
                f"provide another code and call validate_authentication_otp or validate_authentication_pin."
            ),
        }

    context.state["api_resp"] = r
    context.state["flag_val"] = "handover_completed"
    lang = context.state.get("language", "primary")

    # // Las frases literales viven en app.json (variables copy_<frase>_<idioma>).
    # // Aqui solo se elige cual toca segun el motivo del traspaso.
    if "business" in r or context.state.get("business_flag") == "true":
        key = "handoff_business"
    elif "fraud" in r:
        key = "handoff_fraud"
    elif "refund" in r or "threshold" in r or "specialist" in r:
        key = "handoff_refund"
    else:
        key = "live_agent_handoff"
    en = context.state.get(f"copy_{key}_primary") or context.state.get("copy_live_agent_handoff_primary") or ""
    fr = context.state.get(f"copy_{key}_secondary") or en
    chosen = fr if lang == "secondary" else en
    context.state["handover_message"] = chosen
    return {
        "status": "success",
        "handover_initiated": True,
        "reason": r,
        "summary": summary,
        "verbatim_to_say": chosen,
        "verbatim_en": en,
        "verbatim_fr": fr,
        "agent_instruction": f"Respond ONLY with verbatim_to_say in the caller's active language ({lang}): '{chosen}'. Do NOT call end_session yourself.",
    }
