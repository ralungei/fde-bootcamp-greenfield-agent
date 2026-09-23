# // Mismo catalogo que lookup_active_appointments (la plataforma no permite modulos compartidos
# // entre tools, asi que cada tool consulta su propia copia del "backend" de agenda).
SLOT_CATALOG = {
    "SLT-4821": {
        "start_iso": "2026-09-23T14:00:00-04:00",
        "label_en": "Wednesday, September 23, 2:00 PM to 4:00 PM",
        "label_fr": "le mercredi 23 septembre, de 14 h a 16 h",
    },
    "SLT-9137": {
        "start_iso": "2026-09-26T10:00:00-04:00",
        "label_en": "Saturday, September 26, 10:00 AM to 12:00 PM",
        "label_fr": "le samedi 26 septembre, de 10 h a 12 h",
    },
    "SLT-2605": {
        "start_iso": "2026-09-29T09:00:00-04:00",
        "label_en": "Tuesday, September 29, 9:00 AM to 12:00 PM",
        "label_fr": "le mardi 29 septembre, de 9 h a 12 h",
    },
}


def commit_appointment_reschedule(appt_id: str = "APT-5012", slot_id: str = "", service_type: str = "", action: str = "reschedule") -> dict:
    """Commit an appointment booking, reschedule, or cancellation and send SMS confirmation (CUJ-4)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller with OTP or PIN before committing an appointment change.",
        }

    slot = SLOT_CATALOG.get((slot_id or "").strip().upper())
    if not slot:
        return {
            "status": "error",
            "error": "SLOT_NOT_FOUND",
            "valid_slot_ids": list(SLOT_CATALOG.keys()),
            "agent_action": "Call lookup_active_appointments first and pass one of the slot_id values returned in available_slots.",
        }

    lang = context.state.get("language", "primary")
    label = slot["label_fr"] if lang == "secondary" else slot["label_en"]
    service = (service_type or "").strip()
    context.state["date_val"] = label

    if lang == "secondary":
        subject = f"Votre rendez-vous pour {service}" if service else "Votre rendez-vous avec le technicien"
        msg = f"{subject} a bien ete reporte a {label}. Un SMS de confirmation vous a ete envoye."
    else:
        subject = f"Your {service} appointment" if service else "Your technician appointment"
        msg = f"{subject} has been rescheduled to {label}, and an SMS confirmation has been sent."

    context.state["sms_content"] = msg
    return {
        "status": "success",
        "confirmed": True,
        "appt_id": appt_id,
        "action": action,
        "slot_id": slot_id,
        "new_start_iso": slot["start_iso"],
        "new_slot_label": label,
        "sms_confirmation_sent": True,
        "confirmation_message": msg,
        "agent_instruction": f"State this confirmation to the caller verbatim in their active language ({lang}): '{msg}'",
    }
