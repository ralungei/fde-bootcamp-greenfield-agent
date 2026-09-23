# // Catalogo de huecos del sistema de agenda del tecnico. Los identificadores son opacos
# // (como en un Field Service Management real) para no dar pistas semanticas al modelo:
# // el modelo debe razonar sobre start_iso / end_iso para saber cual es mas temprano,
# // cual cae en sabado y cual es la semana siguiente.
SLOT_CATALOG = [
    {
        "slot_id": "SLT-4821",
        "start_iso": "2026-09-23T14:00:00-04:00",
        "end_iso": "2026-09-23T16:00:00-04:00",
        "label_en": "Wednesday, September 23, 2:00 PM to 4:00 PM",
        "label_fr": "le mercredi 23 septembre, de 14 h a 16 h",
    },
    {
        "slot_id": "SLT-9137",
        "start_iso": "2026-09-26T10:00:00-04:00",
        "end_iso": "2026-09-26T12:00:00-04:00",
        "label_en": "Saturday, September 26, 10:00 AM to 12:00 PM",
        "label_fr": "le samedi 26 septembre, de 10 h a 12 h",
    },
    {
        "slot_id": "SLT-2605",
        "start_iso": "2026-09-29T09:00:00-04:00",
        "end_iso": "2026-09-29T12:00:00-04:00",
        "label_en": "Tuesday, September 29, 9:00 AM to 12:00 PM",
        "label_fr": "le mardi 29 septembre, de 9 h a 12 h",
    },
]


def lookup_active_appointments(cirn: str = "") -> dict:
    """Look up active technician appointments, bookable slots, and open support ticket status (M6, CUJ-4)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller with OTP or PIN before looking up active appointments or ticket status.",
        }
    context.state["ticket_state"] = "In Progress"
    return {
        "status": "success",
        "now_iso": "2026-09-23T09:00:00-04:00",
        "appointments": [
            {
                "appt_id": "APT-5012",
                "service_type": "Technician visit (installation / repair)",
                "start_iso": "2026-09-24T13:00:00-04:00",
                "end_iso": "2026-09-24T17:00:00-04:00",
                "label_en": "Thursday, September 24, 1:00 PM to 5:00 PM",
                "label_fr": "le jeudi 24 septembre, de 13 h a 17 h",
                "technician_status": "Scheduled and assigned (Technician Marc)",
            }
        ],
        "available_slots": SLOT_CATALOG,
        "open_tickets": [
            {
                "ticket_id": "TCK-8821",
                "ticket_state": "In Progress - Network technician assigned",
                "issue": "Line signal and connectivity repair",
                "estimated_resolution_iso": "2026-09-24T17:00:00-04:00",
            }
        ],
        "agent_instruction": (
            "Compare start_iso values against now_iso and against the caller's current appointment to pick the slots that "
            "actually match what the caller asked for (earlier date, weekend, next week, etc.), and offer them in the caller's "
            "active language ({language}) using label_en or label_fr. When the caller confirms one, call "
            "commit_appointment_reschedule with that slot_id and with service_type describing the service the caller named."
        ),
    }
