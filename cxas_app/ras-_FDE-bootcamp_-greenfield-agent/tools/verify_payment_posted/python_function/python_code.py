# // Extracto de cuenta (ledger de pagos) tal y como lo devolveria el core de facturacion.
# // En produccion esta constante desaparece y se sustituye por la llamada HTTP al Billing API;
# // la logica de la funcion no cambia. Estados posibles de un pago, como en un sistema real:
# //   POSTED  -> liquidado y aplicado al saldo
# //   PENDING -> registrado pero aun no compensado (todavia NO salda la deuda)
# //   FAILED  -> rechazado
MOCK_BILLING_LEDGER = {
    "4155550101": {
        "past_due_balance": 45.00,
        "payments": [
            {
                "id": "PMT-88231",
                "amount": 45.00,
                "channel": "web_self_serve",
                "value_date": "2026-09-21",
                "status": "POSTED",
            }
        ],
    },
    "4155550102": {
        "past_due_balance": 45.00,
        "payments": [
            {
                "id": "PMT-88234",
                "amount": 45.00,
                "channel": "web_self_serve",
                "value_date": "2026-09-21",
                "status": "POSTED",
            }
        ],
    },
    "5145550199": {
        "past_due_balance": 45.00,
        "payments": [
            {
                "id": "PMT-88235",
                "amount": 45.00,
                "channel": "web_self_serve",
                "value_date": "2026-09-21",
                "status": "POSTED",
            }
        ],
    },
    "4155550109": {
        "past_due_balance": 45.00,
        "payments": [
            {
                "id": "PMT-88232",
                "amount": 45.00,
                "channel": "web_self_serve",
                "value_date": "2026-09-23",
                "status": "PENDING",
            }
        ],
    },
    "4155550103": {"past_due_balance": 0.00, "payments": []},
}

# // Cuenta no encontrada en el ledger: se asume pago registrado del dia anterior cuando se invoca verify_payment_posted
DEFAULT_LEDGER = {
    "past_due_balance": 45.00,
    "payments": [
        {
            "id": "PMT-88239",
            "amount": 45.00,
            "channel": "web_self_serve",
            "value_date": "2026-09-21",
            "status": "POSTED",
        }
    ],
}


def verify_payment_posted() -> dict:
    """Reconcile the caller's account against the billing ledger after a prior-payment claim.

    Deliberately takes no arguments: the account is resolved from the authenticated session
    (clid), never from what the caller says, so a caller can neither query another account nor
    declare their own balance settled. Together with process_payment, this is the only code
    path allowed to clear a past-due balance.
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
            "agent_action": "The caller is identified but NOT authenticated yet, so this action cannot run. Step 2 of 2: ask whether they prefer a 6-digit code or their 4-digit keypad PIN (unless they already chose). Only if they choose the code, call send_authentication_otp and then validate_authentication_otp; for the PIN use validate_authentication_pin. Do NOT ask for their phone or account number again. Then retry this action.",
        }

    ledger = MOCK_BILLING_LEDGER.get(str(context.state.get("clid", "")), DEFAULT_LEDGER)
    payments = ledger.get("payments", [])
    posted = [p for p in payments if p["status"] == "POSTED"]
    pending = [p for p in payments if p["status"] == "PENDING"]
    past_due = float(ledger.get("past_due_balance", 0.0))

    if not posted:
        return {
            "status": "success",
            "payment_found": False,
            "pending_payment_found": bool(pending),
            "past_due_balance": f"{past_due:.2f}",
            "agent_action": (
                "The billing system shows a payment that has NOT cleared yet, so the "
                f"${past_due:.2f} past-due balance is still outstanding. Explain this to the caller in "
                "their active language ({language}), do NOT restore the line, and offer to take the "
                "payment now or set up a payment arrangement via billing_specialist."
                if pending
                else
                "The billing system shows NO payment on this account, so the "
                f"${past_due:.2f} past-due balance is still outstanding. Tell the caller in their active "
                "language ({language}) that no payment has been received, do NOT restore the line, and "
                "offer to take the payment now or set up a payment arrangement via billing_specialist."
            ),
        }

    payment = posted[-1]
    # // Solo el backend puede saldar la deuda. Esta es la unica escritura autorizada aqui.
    context.state["flag_val"] = "balance_cleared"
    return {
        "status": "success",
        "payment_found": True,
        "payment_id": payment["id"],
        "amount_posted": f"{payment['amount']:.2f}",
        "value_date": payment["value_date"],
        "channel": payment["channel"],
        "remaining_balance": "0.00",
        "agent_instruction": (
            f"Payment of ${payment['amount']:.2f} dated {payment['value_date']} is confirmed as posted and the "
            "balance is now cleared. Confirm the posted amount and date to the caller in their active language "
            "({language}), then restore the line with execute_suspend_restore(action='restore'). If you are not "
            "account_management_specialist, transfer to Root_agent so M7 performs the restoration."
        ),
    }
