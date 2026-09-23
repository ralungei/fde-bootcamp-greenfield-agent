# // Mismo ledger que list_recent_payments. La plataforma no permite modulos Python
# // compartidos entre tools, asi que cada tool consulta su propia copia del "backend".
PAYMENT_LEDGER = [
    {"txn_id": "PMT-70112", "amount": 22.50, "paid_at": "2026-08-21T11:40:00-04:00", "invoice_id": "INV-2026-08", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-77301", "amount": 22.50, "paid_at": "2026-09-20T10:14:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-77318", "amount": 22.50, "paid_at": "2026-09-21T09:02:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
    {"txn_id": "PMT-88231", "amount": 45.00, "paid_at": "2026-09-21T08:30:00-04:00", "invoice_id": "INV-2026-09", "card_last4": "4242", "status": "POSTED"},
]

MAX_DAYS_APART = 7


def refund_duplicate_payment(txn_id_original: str, txn_id_duplicate: str) -> dict:
    """Refund a duplicated payment after re-verifying the duplicate in code (M3, CUJ-2)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Call send_authentication_otp first and verify the caller before refunding anything.",
        }

    ledger = PAYMENT_LEDGER
    by_id = {p["txn_id"]: p for p in ledger}

    a = by_id.get((txn_id_original or "").strip().upper())
    b = by_id.get((txn_id_duplicate or "").strip().upper())

    # // (1) Ambas transacciones deben existir EN ESTA cuenta
    if not a or not b:
        return {
            "status": "error",
            "error": "TXN_NOT_FOUND",
            "known_txn_ids": [p["txn_id"] for p in ledger],
            "agent_action": "Call list_recent_payments and use two transaction ids that exist on this account.",
        }

    # // (2) No puede ser la misma transaccion consigo misma
    if a["txn_id"] == b["txn_id"]:
        return {"status": "error", "error": "SAME_TRANSACTION", "agent_action": "Provide two DIFFERENT transaction ids."}

    # // (3) Idempotencia: un pago ya devuelto no se devuelve otra vez
    already = str(context.state.get("refunded_txn_id") or "")
    if already in (a["txn_id"], b["txn_id"]) or "REFUNDED" in (a["status"], b["status"]):
        return {
            "status": "error",
            "error": "ALREADY_REFUNDED",
            "refunded_txn_id": already,
            "agent_action": "Tell the caller this duplicate payment has already been refunded in this call.",
        }

    # // (4) Ambos pagos deben estar realmente cobrados
    if a["status"] != "POSTED" or b["status"] != "POSTED":
        return {
            "status": "error",
            "error": "DUPLICATE_NOT_CONFIRMED",
            "reason": "One of the payments is not POSTED (pending or failed payments are never refunded).",
            "agent_action": "Explain that one of the payments has not cleared, so there is nothing to refund yet.",
        }

    # // (5) Mismo importe al centimo y (6) misma factura destino
    if round(float(a["amount"]), 2) != round(float(b["amount"]), 2) or a["invoice_id"] != b["invoice_id"]:
        return {
            "status": "error",
            "error": "DUPLICATE_NOT_CONFIRMED",
            "reason": "The two payments differ in amount or target a different invoice, so they are two legitimate payments.",
            "agent_action": "Explain that these are two separate legitimate payments and offer to open a dispute with create_dispute_ticket.",
        }

    # // (7) Ventana temporal: dos pagos del mismo importe en meses distintos NO son un duplicado
    if abs(_to_days(a["paid_at"]) - _to_days(b["paid_at"])) > MAX_DAYS_APART:
        return {
            "status": "error",
            "error": "DUPLICATE_NOT_CONFIRMED",
            "reason": "The two payments are more than 7 days apart (different billing cycles), so this is not a duplicate.",
            "agent_action": "Explain that these payments belong to different billing cycles and offer create_dispute_ticket for a manual review.",
        }

    # // (8) Umbral de autoservicio: por encima, lo aprueba un humano
    limit = float(context.state.get("loyalty_limit") or 25)
    amount = round(float(a["amount"]), 2)
    if amount > limit:
        return {
            "status": "error",
            "error": "NOT_ELIGIBLE",
            "escalate_reason": "refund_threshold_exceeded",
            "amount": f"{amount:.2f}",
            "agent_action": "Call execute_live_agent_handover(reason='refund_threshold_exceeded') and say the transfer_to_specialist line verbatim.",
        }

    # // Regla de negocio determinista: SIEMPRE se devuelve el pago MAS RECIENTE y se conserva
    # // el primero aplicado a la factura. El modelo no elige cual.
    later = a if _to_days(a["paid_at"]) >= _to_days(b["paid_at"]) else b
    kept = b if later is a else a

    context.state["refunded_txn_id"] = later["txn_id"]
    context.state["amount"] = f"{amount:.2f}"

    verbatim_en = f"Your refund of ${amount:.2f} will appear on your next statement within 2 business days."
    verbatim_fr = f"Votre remboursement de {amount:.2f} $ apparaitra sur votre prochain releve d'ici 2 jours ouvrables."
    lang = context.state.get("language", "primary")
    return {
        "status": "success",
        "refunded": True,
        "refund_id": "RFD-31207",
        "refunded_txn_id": later["txn_id"],
        "kept_txn_id": kept["txn_id"],
        "amount": f"{amount:.2f}",
        "card_last4": later["card_last4"],
        "days": 2,
        "verbatim_refund_confirmation": verbatim_en,
        "verbatim_refund_confirmation_fr": verbatim_fr,
        "agent_instruction": (
            f"The duplicate payment {later['txn_id']} has been refunded to the card ending in {later['card_last4']}. "
            f"State the confirmation verbatim in the caller's active language ({lang}): "
            f"'{verbatim_en}' in English, or '{verbatim_fr}' in French."
        ),
    }


def _to_days(iso_ts: str) -> float:
    # // Helper definido DESPUES de la tool a proposito: el linter [T004] exige que la
    # // primera funcion del modulo se llame igual que la carpeta. Python resuelve el
    # // nombre en tiempo de llamada, asi que el orden no afecta a la ejecucion.
    # // Conversion minima ISO -> dias absolutos (sin datetime, que no siempre esta
    # // disponible en el sandbox de tools). Formato: YYYY-MM-DDThh:mm:ss+-hh:mm
    date_part = iso_ts.split("T")[0]
    y, m, d = [int(x) for x in date_part.split("-")]
    return y * 372 + m * 31 + d
