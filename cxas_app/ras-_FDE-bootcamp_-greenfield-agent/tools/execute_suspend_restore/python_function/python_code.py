# // Mismo extracto de cuenta que consulta verify_payment_posted. La plataforma no permite
# // modulos Python compartidos entre tools, asi que cada tool hace su propia "llamada al
# // backend" (en produccion, cada una llamaria al mismo Billing API).
MOCK_BILLING_LEDGER = {
    "4155550101": {"past_due_balance": 45.00},
    "4155550102": {"past_due_balance": 45.00},
    "4155550103": {"past_due_balance": 0.00},
}
UNKNOWN_ACCOUNT = {"past_due_balance": 45.00}

# // Tipos de retencion. Una suspension por impago la dispara el sistema de cobros; el resto
# // son retenciones voluntarias pedidas por el cliente (perdida/robo/vacaciones).
# // "" = motivo desconocido -> se trata como impago (fail-closed).
COLLECTIONS_HOLDS = ("", "non_payment")


def execute_suspend_restore(action: str, reason: str = "", cirn: str = "") -> dict:
    """Suspend or restore service (M7, CUJ-6) and send SMS confirmation.

    Restoration is gated by the past-due balance reported by the billing backend, never by
    what the caller claims. The balance can only be settled in-call by process_payment (a real
    payment) or verify_payment_posted (a payment already posted in the ledger).
    """
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

    act = (action or "").lower().strip()
    if act == "restore":
        ledger = MOCK_BILLING_LEDGER.get(str(context.state.get("clid", "")), UNKNOWN_ACCOUNT)
        # // Lo unico que puede haber saldado la deuda durante la llamada es process_payment o
        # // verify_payment_posted; ambos dejan flag_val == "balance_cleared".
        settled_in_call = context.state.get("flag_val") == "balance_cleared"
        past_due = 0.0 if settled_in_call else float(ledger.get("past_due_balance", 0.0))
        hold = str(context.state.get("suspension_reason", ""))

        if hold in COLLECTIONS_HOLDS and past_due > 0:
            context.state["suspension_reason"] = "non_payment"
            context.state["flag_val"] = "balance_owed_redirect"
            context.state["route"] = "M3"
            return {
                "status": "error",
                "error": "BALANCE_OWED",
                "balance_due": f"{past_due:.2f}",
                "agent_action": (
                    f"CRITICAL: Service CANNOT be restored until the ${past_due:.2f} past-due balance is paid "
                    "or a payment arrangement is set up. If the caller claims they have already paid, call "
                    "verify_payment_posted instead of believing them. Otherwise, in ONE turn and in the caller's "
                    f"active language ({{language}}), say the ${past_due:.2f} past-due balance must be settled first "
                    "and ASK: pay it now with the card on file, or set up a payment arrangement? Do NOT say you are "
                    "transferring them, do NOT mention a representative, department or specialist, and do NOT ask "
                    "them to hold: the system routes their answer to billing automatically."
                ),
            }

        context.state["suspension_reason"] = "none"
        context.state["flag_val"] = "service_restored"
        return {
            "status": "success",
            "new_state": "active",
            "effective_iso": "2026-09-22T16:30:00Z",
            "sms_confirmation_sent": True,
            "message": "Service has been restored to active and an SMS confirmation has been sent.",
            "agent_instruction": "Confirm to the caller in their active language ({language}) that their service is now restored to active and an SMS confirmation has been sent.",
        }

    # // Suspension pedida por el cliente: por definicion es voluntaria (las de impago las
    # // dispara el sistema de cobros, no el agente), asi que no bloqueara la restauracion.
    reason_recorded = (reason or "customer_request").strip().lower().replace(" ", "_")
    context.state["suspension_reason"] = "voluntary_hold"
    return {
        "status": "success",
        "new_state": "suspended",
        "hold_type": "voluntary_hold",
        "reason_recorded": reason_recorded,
        "effective_iso": "2026-09-22T16:30:00Z",
        "sms_confirmation_sent": True,
        "message": "Service has been immediately suspended and an SMS confirmation has been sent.",
        "agent_instruction": "Confirm to the caller in their active language ({language}) that their service has been suspended and an SMS confirmation was sent.",
    }
