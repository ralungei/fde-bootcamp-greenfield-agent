def fetch_availability_slots(zip_code: str = "94105", service_type: str = "TV & Fiber Installation") -> dict:
    """Return 2-3 available appointment windows (M6, CUJ-4)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller with OTP or PIN before fetching availability slots.",
        }
    return {
        "status": "success",
        "slots": [
            {"slot_id": "SLOT-1", "date": "Thursday, Oct 15", "window": "9:00 AM - 12:00 PM", "technician_id": "TECH-21"},
            {"slot_id": "SLOT-2", "date": "Friday, Oct 16", "window": "1:00 PM - 4:00 PM", "technician_id": "TECH-44"},
            {"slot_id": "SLOT-3", "date": "Saturday, Oct 17", "window": "10:00 AM - 1:00 PM", "technician_id": "TECH-19"},
        ],
        "agent_instruction": "Present these 2-3 available appointment windows in the caller's active language ({language}).",
    }
