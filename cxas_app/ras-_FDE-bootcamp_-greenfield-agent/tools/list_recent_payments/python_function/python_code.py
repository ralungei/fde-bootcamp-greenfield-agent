# // Libro de movimientos (ledger) de pagos por cuenta, tal y como lo devolveria el core
# // de facturacion. Estados posibles de un apunte, como en un sistema real:
# //   POSTED   -> cobrado y aplicado a una factura
# //   PENDING  -> registrado pero aun no compensado por el banco
# //   FAILED   -> rechazado por el emisor
# //   REFUNDED -> ya devuelto al cliente (no se puede devolver dos veces)
# // OJO: el ledger NO marca que un pago sea "duplicado". Eso se deduce comparando
# // apuntes, y esa comparacion la hace codigo (refund_duplicate_payment), nunca el modelo.
PAYMENT_LEDGER = [
    {"txn_id": "PMT-70112", "amount": 22.50, "paid_at": "2026-08-21T11:40:00-04:00", "invoice_id": "INV-2026-08", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-77301", "amount": 22.50, "paid_at": "2026-09-20T10:14:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-77318", "amount": 22.50, "paid_at": "2026-09-21T09:02:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-88231", "amount": 45.00, "paid_at": "2026-09-21T08:30:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
]


# Lists recent payments so the model can spot duplicates by itself (no hint labels).
def list_recent_payments() -> dict:
    """Return the payment history (ledger) of the authenticated caller's account (M3, CUJ-2)."""
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

    payments = [dict(p) for p in PAYMENT_LEDGER]

    # // Un reembolso ya ejecutado en esta llamada se refleja en el historial (idempotencia).
    already = str(context.state.get("refunded_txn_id") or "")
    for p in payments:
        if p["txn_id"] == already:
            p["status"] = "REFUNDED"

    return {
        "status": "success",
        "payments": payments,
        "agent_instruction": (
            "Read the history yourself. If the caller claims a double payment, look for two POSTED payments with the "
            "SAME amount and the SAME invoice_id and close dates, tell the caller what you found (amount, both dates, "
            "card ending) in their active language ({language}), ask them to confirm, and then call "
            "refund_duplicate_payment with the two transaction ids. Never refund based on an amount the caller states."
        ),
    }
