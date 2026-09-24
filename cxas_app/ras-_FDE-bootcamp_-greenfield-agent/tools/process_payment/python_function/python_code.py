# // Boveda de tarjetas guardadas por cuenta (MOCK_PAYMENT_VAULT).
# // En produccion esta consulta va al Payment Gateway: la cuenta 4155550104 tiene su tarjeta
# // principal caducada (rechaza el primer intento y aprueba cuando el cliente da otra tarjeta).
MOCK_PAYMENT_VAULT = {
    "4155550104": {"primary_card_status": "DECLINED", "saved_last4": "4242"},
}


# Charges a payment to the card on file (requires authentication).
def process_payment(billing_account: str, amount: float = 45.0, dtmf_payment_token: str = "", payment_method: str = "card_on_file") -> dict:
    """Process one-time bill payment via saved card or DTMF card entry (M3, CUJ-1)."""
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

    attempts = int(context.state.get("payment_attempts") or 0) + 1
    context.state["payment_attempts"] = attempts

    clid = str(context.state.get("clid") or "4155550101")
    vault = MOCK_PAYMENT_VAULT.get(clid, {"primary_card_status": "ACTIVE", "saved_last4": "4242"})
    raw_digits = str(dtmf_payment_token or context.state.get("dtmf_digits") or "")
    digits_only = "".join(c for c in raw_digits if c.isdigit())

    should_decline_first = (
        vault["primary_card_status"] == "DECLINED"
        or digits_only.endswith("0000")
        or (
            context.state.get("language") != "secondary"
            and context.state.get("suspension_reason") != "non_payment"
            and context.state.get("lob") != "direct_pay"
        )
    )
    if attempts == 1 and should_decline_first:
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
