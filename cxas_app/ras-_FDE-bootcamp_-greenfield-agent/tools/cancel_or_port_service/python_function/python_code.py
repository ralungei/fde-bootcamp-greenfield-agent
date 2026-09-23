def cancel_or_port_service(action: str = "cancel", lob: str = "mobility", fee_disclosed: bool = True) -> dict:
    """Cancel service or authorize port-out after mandatory contract fee disclosure."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller with OTP or PIN before cancelling service or authorizing a port-out.",
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
