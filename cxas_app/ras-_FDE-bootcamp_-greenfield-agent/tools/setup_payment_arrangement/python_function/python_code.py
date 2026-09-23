def setup_payment_arrangement(billing_account: str = "", installment_amount: float = 22.50, installments: int = 2) -> dict:
    """Set up a payment arrangement and mark flag_val='balance_cleared' so M7 can restore service."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller before setting up a payment arrangement.",
        }
    card_last4 = context.state.get("card_last4") or "4242"
    context.state["flag_val"] = "balance_cleared"
    return {
        "status": "success",
        "arrangement_id": "ARR-30291",
        "installment_amount": f"{installment_amount:.2f}",
        "installments": installments,
        "card_last4": card_last4,
        "balance_cleared": True,
        "agent_instruction": "Confirm the payment arrangement details in the caller's active language ({language}). Since the caller wants their suspended service restored, immediately transfer to Root_agent so account_management_specialist can call execute_suspend_restore(action='restore')!",
    }
