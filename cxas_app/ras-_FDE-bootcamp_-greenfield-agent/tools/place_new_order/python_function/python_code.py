def place_new_order(plan_id: str, lob: str = "tv", cirn: str = "") -> dict:
    """Place a new service/upgrade order and send SMS confirmation receipt (CUJ-5)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Call send_authentication_otp immediately so the system sends the 6-digit OTP and returns verbatim_to_say (stating valid 6-digit codes start with 48) before asking the caller for the code.",
        }
    return {
        "status": "success",
        "order_id": "ORD-90452",
        "plan_id": plan_id,
        "lob": lob,
        "effective_status": "Plan upgrade active immediately; equipment delivery in 2 business days (Thursday by 5:00 PM)",
        "delivery_eta": "2 business days (Thursday by 5:00 PM)",
        "sms_receipt_sent": True,
        "agent_instruction": "State the order_id (ORD-90452), confirm the upgrade/order is complete, state the delivery/activation ETA, and confirm that an SMS receipt has been sent — all in the caller's active language ({language}).",
    }
