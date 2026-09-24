def apply_bill_adjustment(charge_id: str = "CHG-202", amount: float = 12.50) -> dict:
    """Apply an immediate billing adjustment/credit/refund (<= $25.00) or trigger specialist escalation (> $25.00)."""
    # // Puerta de identidad en dos pasos, en codigo y no en el prompt: primero IDENTIFICAR
    # // (que cuenta es, fetch_customer_profile) y despues AUTENTICAR (demostrar que es el titular,
    # // OTP o PIN). El error dice al modelo exactamente que paso falta para guiar al cliente.
    if context.state.get("identification_status") != "Pass":
        return {
            "status": "error",
            "error": "IDENTIFICATION_REQUIRED",
            "next_step": "identify",
            "agent_action": "The caller is NOT identified yet, so this action cannot run. Step 1 of 2: ask for the phone number or 9-digit account number on their service and call fetch_customer_profile with it. Do NOT ask for a PIN or code yet. Once identified, authenticate them (step 2), then retry this action.",
        }
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "next_step": "authenticate",
            "agent_action": "The caller is identified but NOT authenticated yet, so this action cannot run. Step 2 of 2: ask whether they prefer a 6-digit code or their 4-digit keypad PIN (unless they already chose). Only if they choose the code, call send_authentication_otp and then validate_authentication_otp; for the PIN use validate_authentication_pin. Do NOT ask for their phone or account number again. Then retry this action.",
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
