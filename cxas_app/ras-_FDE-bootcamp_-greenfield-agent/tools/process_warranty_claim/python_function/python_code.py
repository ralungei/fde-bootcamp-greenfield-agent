def process_warranty_claim(device_id: str, intent_type: str = "Defective") -> dict:
    """Evaluate and process equipment warranty claim or check claim status."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller with OTP or PIN before processing a warranty claim.",
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
