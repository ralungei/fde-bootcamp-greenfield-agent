def send_sms(sms_content: str, sms_type: str = "Public") -> dict:
    """Send SMS payload to the caller's phone number."""
    try:
        context.state["sms_type"] = sms_type
        context.state["sms_content"] = sms_content
        return {
            "status": "success",
            "sent": True,
            "sms_type": sms_type,
            "message_id": "SMS-66102",
            "agent_instruction": "Confirm SMS delivery in the caller's active language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Read the information verbally if SMS delivery fails.",
        }
