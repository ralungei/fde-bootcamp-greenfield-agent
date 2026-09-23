def apply_bill_adjustment(charge_id: str = "CHG-202", amount: float = 12.50) -> dict:
    """Apply an immediate billing adjustment/credit/refund (<= $25.00) or trigger specialist escalation (> $25.00)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller first before applying a bill adjustment.",
        }

    limit = float(context.state.get("loyalty_limit") or 25)
    if amount > limit:
        return {
            "status": "error",
            "error": "NOT_ELIGIBLE",
            "escalate_reason": "refund_threshold_exceeded",
            "verbatim_transfer": "I'll connect you to a billing specialist now — they'll have everything we've already discussed.",
            "verbatim_transfer_fr": "Je vais vous transférer à un spécialiste de la facturation maintenant — il aura tout ce dont nous avons déjà discuté.",
            "agent_action": "Call execute_live_agent_handover(reason='refund_threshold_exceeded') and respond ONLY with verbatim_transfer (or verbatim_transfer_fr if {language} is 'secondary'). Do NOT call create_dispute_ticket.",
        }

    amt_str = f"{amount:.2f}"
    context.state["amount"] = amt_str
    verbatim_en = f"Your refund of ${amt_str} will appear on your next statement within 2 business days."
    verbatim_fr = f"Votre remboursement de {amt_str} $ apparaîtra sur votre prochain relevé d'ici 2 jours ouvrables."
    return {
        "status": "success",
        "adjusted": True,
        "charge_id": charge_id,
        "amount": amt_str,
        "days": 2,
        "verbatim_refund_confirmation": verbatim_en,
        "verbatim_refund_confirmation_fr": verbatim_fr,
        "agent_instruction": f"State the refund confirmation to the caller in their active language ({{language}}): '{verbatim_en}' (or '{verbatim_fr}' if speaking French).",
    }
