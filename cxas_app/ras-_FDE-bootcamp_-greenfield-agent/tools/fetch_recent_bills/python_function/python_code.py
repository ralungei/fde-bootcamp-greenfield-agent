def fetch_recent_bills(billing_account: str = "") -> dict:
    """Fetch recent bills, line items, and saved card_last4."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "message": "Caller is not authenticated (auth_status != Pass).",
            "agent_action": "Complete OTP or PIN verification before calling fetch_recent_bills.",
        }
    ban_last4 = (billing_account or context.state.get("billing_account", "5678"))[-4:]
    card_last4 = context.state.get("card_last4") or "4242"
    context.state["card_last4"] = card_last4
    context.state["last_pmt_amt"] = "65.00"
    context.state["amount"] = "12.50"
    return {
        "status": "success",
        "billing_account_last4": ban_last4,
        "saved_card_last4": card_last4,
        "bills": [
            {
                "id": "BILL-2026-09",
                "date": "2026-09-15",
                "amount": 77.50,
                "balance_due": 45.00,
                "saved_card_last4": card_last4,
                "line_items": [
                    {"charge_id": "CHG-101", "description": "Fiber Internet & Mobility Base Plan", "amount": 65.00, "auto_eligible": False},
                    {"charge_id": "CHG-202", "description": "AppleStreaming", "date": "last Tuesday", "amount": 12.50, "auto_eligible": True, "eta_days": 2},
                    {"charge_id": "CHG-203", "description": "International / Long Distance & Overcharge Fee", "date": "2026-09-10", "amount": 15.00, "auto_eligible": True, "eta_days": 2},
                    {"charge_id": "CHG-204", "description": "Service Outage Downtime Credit Eligibility", "date": "2026-09-12", "amount": 15.00, "auto_eligible": True, "eta_days": 2},
                ],
            }
        ],
        "agent_instruction": f"Saved card on file ends in {card_last4}. If the caller has not specified which charge they are referring to, briefly list the recent charges from the bill to help them identify it. For any disputed charge, overcharge, or outage credit <= $25.00, call apply_bill_adjustment immediately. Respond in the caller's language ({{language}}).",
    }
