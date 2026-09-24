def setup_payment_arrangement(billing_account: str = "", installment_amount: float = 22.50, installments: int = 2) -> dict:
    """Set up a payment arrangement and mark flag_val='balance_cleared' so M7 can restore service."""
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
            "agent_action": "The caller is identified but NOT authenticated yet, so this action cannot run. Step 2 of 2: offer a 6-digit code (call send_authentication_otp, then validate_authentication_otp) or their 4-digit keypad PIN (validate_authentication_pin). Do NOT ask for their phone or account number again. Then retry this action.",
        }
    card_last4 = context.state.get("card_last4") or "4242"
    context.state["flag_val"] = "balance_cleared"
    return {
        "status": "success",
        "arrangement_id": "ARR-30291",
        "installment_amount": f"{installment_amount:.2f}",
        "installments": installments,
        "card_last4": card_last4,
        "balance_cleared": True,
        "agent_instruction": "Confirm the payment arrangement details in the caller's active language ({language}). Since the caller wants their suspended service restored, immediately transfer to Root_agent so account_management_specialist can call execute_suspend_restore(action='restore')!",
    }
