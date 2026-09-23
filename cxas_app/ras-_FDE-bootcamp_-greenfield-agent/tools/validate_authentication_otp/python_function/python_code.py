def validate_authentication_otp(code: str) -> dict:
    """Validate the 6-digit OTP code entered or spoken by the caller (BR-TV-008, BR-TV-009)."""
    try:
        # // Se captura ANTES de sobrescribir: si el cliente ya estaba autenticado, este
        # // segundo codigo fresco cuenta como step-up (segundo factor para accion critica).
        was_authenticated = context.state.get("auth_status") == "Pass"
        candidate = (code or context.state.get("dtmf_digits", "")).strip()
        digits_only = "".join(ch for ch in candidate if ch.isdigit())

        # // Regla determinista simplificada de validacion OTP:
        # // Un OTP valido tiene exactamente 6 digitos y empieza por '48' (el prefijo anunciado
        # // por send_authentication_otp). Al exigir 6 digitos que empiecen por '48', quedan
        # // descartados automaticamente codigos de digitos repetidos (111111, 999999),
        # // secuencias genericas (123456, 654321) o longitudes distintas.
        is_valid_otp = len(digits_only) == 6 and digits_only.startswith("48")

        if not is_valid_otp:
            attempts = int(context.state.get("misc_counter") or 0) + 1
            context.state["misc_counter"] = str(attempts)
            context.state["auth_status"] = "Fail"
            remaining = max(0, 3 - attempts)
            return {
                "status": "error",
                "auth_status": "Fail",
                "attempts_remaining": remaining,
                "escalate_reason": "auth_failure_handoff" if remaining == 0 else "",
                "agent_action": (
                    f"Inform the caller in their active language ({{language}}) that the code '{digits_only}' "
                    f"was incorrect (valid 6-digit codes start with 48) and ask them to retry "
                    f"({remaining} attempts remaining). Only if attempts_remaining is 0, call "
                    f"execute_live_agent_handover(reason='auth_failure_handoff')."
                ),
            }

        context.state["auth_status"] = "Pass"
        context.state["identification_status"] = "Pass"
        context.state["misc_counter"] = "0"
        # // Step-up: solo un OTP valido sobre una sesion ya autenticada concede step_up_status.
        if was_authenticated:
            context.state["step_up_status"] = "Pass"
        return {
            "status": "success",
            "auth_status": "Pass",
            "step_up_status": "Pass" if was_authenticated else "",
            "attempts_remaining": 3,
            "agent_instruction": "Authentication succeeded. NEVER echo the OTP code back to the caller (BR-TV-009). Proceed in the caller's language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Escalate to a live representative with reason auth_failure_handoff.",
        }
