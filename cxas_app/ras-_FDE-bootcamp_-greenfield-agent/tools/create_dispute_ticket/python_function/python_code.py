def create_dispute_ticket(charge_id: str, reason: str, amount: float, notes: str = "") -> dict:
    """Open a billing dispute ticket (<= $25) or deterministically redirect to billing specialist if > $25."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller before creating a dispute ticket.",
        }

    if amount is None or float(amount) <= 0:
        return {
            "status": "error",
            "error": "MISSING_OR_INVALID_AMOUNT",
            "agent_action": "Re-invoke create_dispute_ticket with the exact positive dollar amount (e.g. amount=15.0 or amount=35.0).",
        }

    limit = float(context.state.get("loyalty_limit") or 25.0)
    if float(amount) > limit:
        context.state["flag_val"] = "handover_completed"
        return {
            "status": "error",
            "error": "THRESHOLD_EXCEEDED_HANDOVER_REQUIRED",
            "dispute_ticket_created": False,
            "requested_amount": f"{float(amount):.2f}",
            "loyalty_limit": f"{limit:.2f}",
            "escalate_reason": "refund_threshold_exceeded",
            "verbatim_transfer": "I'll connect you to a billing specialist now — they'll have everything we've already discussed.",
            "verbatim_transfer_fr": "Je vais vous transférer à un spécialiste de la facturation maintenant — il aura tout ce dont nous avons déjà discuté.",
            "agent_action": "CRITICAL: Do NOT mention any dispute ticket ID because no ticket was created (amount exceeds $25.00). Call execute_live_agent_handover(reason='refund_threshold_exceeded') and respond ONLY with verbatim_transfer (or verbatim_transfer_fr if speaking French).",
        }

    return {
        "status": "success",
        "ticket_id": "DSP-88412",
        "charge_id": charge_id,
        "amount": float(amount),
        "eta_business_days": 5,
        "reason": reason,
        "agent_instruction": "Confirm the dispute ticket ID (DSP-88412) and 5-business-day resolution window in the caller's active language ({language}).",
    }

