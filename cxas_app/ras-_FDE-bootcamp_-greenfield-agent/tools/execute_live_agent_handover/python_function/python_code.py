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
    context.state["flag_val"] = "handover_ready"
    lang = context.state.get("language", "primary")

    if "business" in r or context.state.get("business_flag") == "true":
        en = "To get you the best support for your business account, I'll transfer you to an agent. You'll need to use your phone keypad instead of talking to the virtual assistant. Just a moment while I connect you."
        fr = "Pour vous offrir le meilleur soutien pour votre compte d'entreprise, je vais vous transférer à un agent. Vous devrez utiliser le clavier de votre téléphone plutôt que de parler à l'assistant virtuel. Un instant pendant que je vous mets en relation."
    elif "fraud" in r:
        en = "I'm very sorry to hear that you are facing challenges. I will ensure we handle your request with the utmost care. I'll connect you to a representative who can help. Please hold."
        fr = "Je suis vraiment désolé d'apprendre que vous rencontrez ces difficultés. Je veillerai à ce que votre demande soit traitée avec le plus grand soin. Je vais vous transférer à un représentant qui pourra vous aider. Veuillez patienter."
    elif "refund" in r or "threshold" in r or "specialist" in r:
        en = "I'll connect you to a billing specialist now — they'll have everything we've already discussed."
        fr = "Je vais vous transférer à un spécialiste de la facturation maintenant — il aura tout ce dont nous avons déjà discuté."
    else:
        en = "I'll connect you to a representative who can help. Please hold."
        fr = "Je vais vous transférer à un représentant qui pourra vous aider. Veuillez patienter."

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
