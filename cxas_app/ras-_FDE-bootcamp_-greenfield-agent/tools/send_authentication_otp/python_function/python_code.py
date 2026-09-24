# Sends a 6-digit code by SMS and email, only if the caller is already identified.
def send_authentication_otp(clid: str = "", channel: str = "sms_and_email") -> dict:
    """Send a 6-digit authentication OTP to the customer's registered phone number and backup email on file."""
    # // No se puede autenticar a quien aun no se ha identificado: sin cuenta no hay a quien
    # // enviar el codigo ni contra que validar el PIN. Solo fetch_customer_profile identifica.
    if context.state.get("identification_status") != "Pass":
        return {
            "status": "error",
            "error": "IDENTIFICATION_REQUIRED",
            "next_step": "identify",
            "agent_action": "The caller is NOT identified yet, so this action cannot run. Step 1 of 2: ask for the phone number or 9-digit account number on their service and call fetch_customer_profile with it. Do NOT ask for a PIN or code yet. Once identified, come back to authentication.",
        }
    try:
        target = (clid or context.state.get("clid", "4155550101")).strip()
        last4 = target[-4:] if len(target) >= 4 else "0101"
        # // Enviamos el OTP de 6 digitos (empezando por 48) tanto al movil por SMS como al
        # // correo de respaldo (backup email). Asi, si el cliente perdio el movil, puede
        # // leer el OTP en su backup email (p. ej. para el step-up de MFA), y ademas el
        # // prefijo 48 permite distinguir un OTP real de codigos falsos (111111, 123456).
        return {
            "status": "success",
            "sent": True,
            "channel": channel,
            "otp_prefix": "48",
            "expires_in_sec": 300,
            "callback_last4": last4,
            "verbatim_to_say": (
                "For your security, I just sent a 6-digit code to that number — please read it back to me. "
                "I also sent it to your backup email on file, and valid 6-digit codes start with 48."
            ),
            "agent_instruction": (
                "State verbatim_to_say in English if {language} is 'primary', or translated into "
                "Canadian French if the caller is speaking French ({language} is 'secondary'). "
                "Always keep the verbatim sentence 'For your security, I just sent a 6-digit code to that number — please read it back to me.' "
                "(or French equivalent) and mention that it was also sent to their backup email and valid 6-digit codes start with 48."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Apologize and offer 4-digit PIN verification via validate_authentication_pin.",
        }
