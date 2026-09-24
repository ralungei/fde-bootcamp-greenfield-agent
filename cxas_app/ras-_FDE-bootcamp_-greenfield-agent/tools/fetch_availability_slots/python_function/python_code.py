# Lists available technician appointment slots (requires authentication).
def fetch_availability_slots(zip_code: str = "94105", service_type: str = "TV & Fiber Installation") -> dict:
    """Return 2-3 available appointment windows (M6, CUJ-4)."""
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
    return {
        "status": "success",
        "slots": [
            {"slot_id": "SLOT-1", "date": "Thursday, Oct 15", "window": "9:00 AM - 12:00 PM", "technician_id": "TECH-21"},
            {"slot_id": "SLOT-2", "date": "Friday, Oct 16", "window": "1:00 PM - 4:00 PM", "technician_id": "TECH-44"},
            {"slot_id": "SLOT-3", "date": "Saturday, Oct 17", "window": "10:00 AM - 1:00 PM", "technician_id": "TECH-19"},
        ],
        "agent_instruction": "Present these 2-3 available appointment windows in the caller's active language ({language}).",
    }
