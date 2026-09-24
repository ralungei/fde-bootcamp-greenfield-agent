def process_warranty_claim(device_id: str, intent_type: str = "Defective") -> dict:
    """Evaluate and process equipment warranty claim or check claim status."""
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
    in_warranty = "damage" not in intent_type.lower() and "screen" not in intent_type.lower()
    context.state["intent_type"] = intent_type
    return {
        "status": "success",
        "claim_id": "WRN-33109",
        "claim_status": "Approved — Replacement shipped via Express Courier",
        "in_warranty": in_warranty,
        "replacement_fee": "0.00" if in_warranty else "99.00",
        "replacement_eta": "2 business days",
        "agent_instruction": "Confirm the warranty claim ID (WRN-33109), replacement fee, and 2-business-day delivery ETA in the caller's active language ({language}).",
    }
