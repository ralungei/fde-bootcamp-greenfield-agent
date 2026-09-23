# // Boveda de tarjetas guardadas por cuenta (MOCK_PAYMENT_VAULT).
# // En produccion esta consulta va al Payment Gateway: la cuenta 4155550104 tiene su tarjeta
# // principal caducada (rechaza el primer intento y aprueba cuando el cliente da otra tarjeta).
MOCK_PAYMENT_VAULT = {
    "4155550104": {"primary_card_status": "DECLINED", "saved_last4": "4242"},
}


def process_payment(billing_account: str, amount: float = 45.0, dtmf_payment_token: str = "", payment_method: str = "card_on_file") -> dict:
    """Process one-time bill payment via saved card or DTMF card entry (M3, CUJ-1)."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "message": "Caller is not authenticated (auth_status != Pass).",
            "agent_action": "Complete OTP or PIN verification before calling process_payment.",
        }

    attempts = int(context.state.get("payment_attempts") or 0) + 1
    context.state["payment_attempts"] = attempts

    clid = str(context.state.get("clid") or "4155550101")
    vault = MOCK_PAYMENT_VAULT.get(clid, {"primary_card_status": "ACTIVE", "saved_last4": "4242"})
    raw_digits = str(dtmf_payment_token or context.state.get("dtmf_digits") or "")
    digits_only = "".join(c for c in raw_digits if c.isdigit())

    # Decline on attempt 1 ONLY if the account's primary card in the vault is DECLINED (or token ends in 0000)
    if (attempts == 1 and vault["primary_card_status"] == "DECLINED") or digits_only.endswith("0000"):
        return {
            "status": "error",
            "error": "CARD_DECLINED",
            "attempt": attempts,
            "message": "The primary card on file ending in 4242 was declined by the issuer.",
            "agent_action": "Politely inform the caller in their active language ({language}) that the card ending in 4242 was declined, and ask them to enter or provide an alternative credit card number to complete the payment.",
        }

    last4 = digits_only[-4:] if len(digits_only) >= 4 else vault["saved_last4"]
    paid_amt = float(amount) if float(amount or 0) > 0 else 45.0
    context.state["flag_val"] = "balance_cleared"
    context.state["suspension_reason"] = "none"
    lang = context.state.get("language", "primary")
    msg = (
        f"Votre paiement de {paid_amt:.2f} $ sur la carte se terminant par {last4} a été accepté. Votre solde est maintenant de 0,00 $."
        if lang == "secondary"
        else f"Your payment of ${paid_amt:.2f} using the card ending in {last4} has been approved. Your remaining balance is $0.00."
    )
    return {
        "status": "success",
        "transaction_id": "TXN-90214",
        "amount_paid": f"{paid_amt:.2f}",
        "card_last4": last4,
        "remaining_balance": "0.00",
        "confirmation_message": msg,
        "agent_instruction": f"State clearly to the caller in their active language ({lang}): '{msg}'",
    }
