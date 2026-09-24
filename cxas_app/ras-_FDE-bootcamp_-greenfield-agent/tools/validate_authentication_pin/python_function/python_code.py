def validate_authentication_pin(pin: str, is_dtmf: bool = True) -> dict:
    """Validate 4-digit PIN for primary authentication (never grants step-up)."""
    try:
        # // No se puede autenticar a quien aun no se ha identificado: sin cuenta no hay a quien
        # // enviar el codigo ni contra que validar el PIN. Solo fetch_customer_profile identifica.
        if context.state.get("identification_status") != "Pass":
            return {
                "status": "error",
                "error": "IDENTIFICATION_REQUIRED",
                "next_step": "identify",
                "agent_action": "The caller is NOT identified yet, so this action cannot run. Step 1 of 2: ask for the phone number or 9-digit account number on their service and call fetch_customer_profile with it. Do NOT ask for a PIN or code yet. Once identified, come back to authentication.",
            }
        was_authenticated = context.state.get("auth_status") == "Pass"
        candidate = (context.state.get("dtmf_digits") or pin or "").strip()
        digits_only = "".join(ch for ch in candidate if ch.isdigit())

        if (
            digits_only in ("0000", "9999", "1111", "000000", "999999")
            or "wrong" in candidate.lower()
            or candidate == "FAIL"
        ):
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
                    f"Inform the caller in their active language ({{language}}) that the PIN was incorrect "
                    f"(never repeat the digits) and ask them to re-enter their 4-digit PIN ({remaining} attempts remaining). "
                    f"Only if attempts_remaining is 0, call execute_live_agent_handover(reason='auth_failure_handoff')."
                ),
            }

        context.state["auth_status"] = "Pass"
        context.state["misc_counter"] = "0"
        # // El PIN estatico SOLO sirve como autenticacion primaria. Si el cliente ya estaba
        # // autenticado y necesitamos step-up, no concedemos step_up_status y guiamos al
        # // modelo a enviar y validar el OTP de 6 digitos (que llega a SMS y backup email).
        if was_authenticated:
            return {
                "status": "success",
                "auth_status": "Pass",
                "step_up_status": "",
                "attempts_remaining": 3,
                "agent_instruction": (
                    "Primary PIN is already verified, but a static 4-digit PIN cannot be reused for step-up "
                    "verification. To complete step-up (e.g., to disable MFA), call send_authentication_otp "
                    "(which sends a 6-digit code starting with 48 to their phone and backup email) and then "
                    "validate_authentication_otp."
                ),
            }

        return {
            "status": "success",
            "auth_status": "Pass",
            "step_up_status": "",
            "attempts_remaining": 3,
            "agent_instruction": "PIN verified. NEVER echo the PIN back to the caller (BR-TV-009). Continue in the caller's language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Escalate to a representative with reason auth_failure_handoff.",
        }
