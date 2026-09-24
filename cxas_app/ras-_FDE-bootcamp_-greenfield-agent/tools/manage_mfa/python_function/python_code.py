def manage_mfa(action: str = "enable") -> dict:
    """Enable or disable MFA. Disabling additionally requires a fresh 6-digit OTP step-up verification."""
    # // (1) Autenticacion base: obligatoria para cualquier cambio de MFA.
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

    disabling = not action.lower().startswith("en")

    # // (2) Step-up SOLO para desactivar, y SIEMPRE mediante un OTP fresco de 6 digitos
    # // (enviado a movil y backup email). Un PIN fijo no concede step_up_status.
    if disabling and context.state.get("step_up_status") != "Pass":
        return {
            "status": "error",
            "error": "STEP_UP_REQUIRED",
            "message": "Disabling MFA is a critical security change and needs a second, fresh 6-digit OTP verification code.",
            "agent_action": (
                "1) IMMEDIATELY call send_authentication_otp RIGHT NOW in this same turn (before speaking to the caller) "
                "to dispatch a fresh 6-digit step-up code starting with 48 to the caller's phone and backup email on file. "
                "2) Then tell the caller in their active language ({language}) that disabling MFA requires this extra "
                "6-digit verification code starting with 48 and ask them to read it back. "
                "3) When they reply with the 6-digit code, call validate_authentication_otp and then manage_mfa(action='disable')."
            ),
        }

    # // (3) El step-up se CONSUME: un unico codigo no autoriza dos cambios criticos.
    if disabling:
        context.state["step_up_status"] = ""

    state_str = "disabled" if disabling else "enabled"
    return {
        "status": "success",
        "mfa_state": state_str,
        "step_up_verified": disabling,
        "sms_confirmation_sent": True,
        "agent_instruction": f"Confirm that multi-factor authentication (MFA) is now {state_str} strictly in the caller's active language ({{language}}).",
    }
