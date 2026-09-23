def manage_mfa(action: str = "enable") -> dict:
    """Enable or disable MFA. Disabling additionally requires a fresh 6-digit OTP step-up verification."""
    # // (1) Autenticacion base: obligatoria para cualquier cambio de MFA.
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "message": "The caller must be authenticated (PIN or OTP) before modifying MFA settings.",
            "agent_action": (
                "Call send_authentication_otp and validate_authentication_otp (or validate_authentication_pin "
                "if the caller prefers or lost their phone), then call manage_mfa again."
            ),
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
