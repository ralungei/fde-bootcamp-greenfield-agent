def place_new_order(plan_id: str, lob: str = "tv", cirn: str = "") -> dict:
    """Place a new service/upgrade order and send SMS confirmation receipt (CUJ-5)."""
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
    return {
        "status": "success",
        "order_id": "ORD-90452",
        "plan_id": plan_id,
        "lob": lob,
        "effective_status": "Plan upgrade active immediately; equipment delivery in 2 business days (Thursday by 5:00 PM)",
        "delivery_eta": "2 business days (Thursday by 5:00 PM)",
        "sms_receipt_sent": True,
        "agent_instruction": "State the order_id (ORD-90452), confirm the upgrade/order is complete, state the delivery/activation ETA, and confirm that an SMS receipt has been sent — all in the caller's active language ({language}).",
    }
