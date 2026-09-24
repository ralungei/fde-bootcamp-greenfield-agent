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
    # // Puerta de identidad en dos pasos, en codigo y no en el prompt: primero IDENTIFICAR
    # // (que cuenta es, fetch_customer_profile) y despues AUTENTICAR (demostrar que es el titular,
    # // OTP o PIN). El error dice al modelo exactamente que paso falta para guiar al cliente.
    if context.state.get("identification_status") != "Pass":
        return {
            "status": "error",
            "error": "IDENTIFICATION_REQUIRED",
            "next_step": "identify",
            "agent_action": "The caller is NOT identified yet, so this action cannot run. Step 1 of 2: ask for the phone number or 9-digit account number on their service and call fetch_customer_profile with it. Do NOT ask for a PIN or code yet. Once identified, authenticate them (step 2), then retry this action.",
        }
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "next_step": "authenticate",
            "agent_action": "The caller is identified but NOT authenticated yet, so this action cannot run. Step 2 of 2: offer a 6-digit code (call send_authentication_otp, then validate_authentication_otp) or their 4-digit keypad PIN (validate_authentication_pin). Do NOT ask for their phone or account number again. Then retry this action.",
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
