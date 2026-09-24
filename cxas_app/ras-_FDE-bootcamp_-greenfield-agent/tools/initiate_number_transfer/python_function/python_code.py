# Starts porting a number in from another carrier.
def initiate_number_transfer(phone_number_to_port: str, previous_carrier: str = "Competitor", account_pin: str = "") -> dict:
    """Initiate a number transfer-in (port-in) request from a competitor or landline."""
    try:
        return {
            "status": "success",
            "port_request_id": "PRT-77410",
            "phone_number_last4": phone_number_to_port[-4:] if len(phone_number_to_port) >= 4 else "0199",
            "previous_carrier": previous_carrier,
            "estimated_completion": "2 to 4 hours for mobile, or up to 2 business days for landline",
            "sms_status_updates_enabled": True,
            "agent_instruction": "Confirm the port_request_id (PRT-77410) and estimated completion time in the caller's active language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Apologize and connect the caller to a porting specialist.",
        }
