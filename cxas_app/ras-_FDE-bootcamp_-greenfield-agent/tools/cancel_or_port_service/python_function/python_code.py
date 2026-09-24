# Cancels a service or ports the number out, only if the caller is authenticated.
def cancel_or_port_service(action: str = "cancel", lob: str = "mobility", fee_disclosed: bool = True) -> dict:
    """Cancel service or authorize port-out after mandatory contract fee disclosure."""
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
        "action": action,
        "lob": lob,
        "confirmation_id": "CNC-44821",
        "fee_disclosure_required_verbatim": "Please note that cancelling your service before the end of your contract term may result in an early termination fee on your final bill.",
        "fee_disclosure_required_verbatim_fr": "Veuillez noter que l'annulation de votre service avant la fin de votre contrat peut entraîner des frais de résiliation anticipée sur votre facture finale.",
        "sms_confirmation_sent": True,
        "agent_instruction": "You MUST state the contract cancellation fee disclosure verbatim in the caller's active language ({language}) (fee_disclosure_required_verbatim or fee_disclosure_required_verbatim_fr) AND confirm cancellation/port-out ID CNC-44821.",
    }
