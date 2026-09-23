def send_password_reset_sms(cirn: str = "") -> dict:
    """Send a 30-minute self-serve password reset SMS link (M7, CUJ-1)."""
    if context.state.get("identification_status") != "Pass" and context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "IDENTIFICATION_REQUIRED",
            "agent_action": "Identify the caller using fetch_customer_profile before calling send_password_reset_sms.",
        }
    return {
        "status": "success",
        "sent": True,
        "delivery_channel": "SMS",
        "valid_minutes": 30,
        "agent_instruction": "Confirm in the caller's active language ({language}) that the self-serve password reset SMS link has been sent to their mobile phone and is valid for 30 minutes. NEVER read or echo any URL.",
    }
