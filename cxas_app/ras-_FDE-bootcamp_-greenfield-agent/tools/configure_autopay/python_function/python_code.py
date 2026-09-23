def configure_autopay(billing_account: str = "", enabled: bool = True) -> dict:
    """Configure autopay enrollment for the authenticated billing account."""
    if context.state.get("auth_status") != "Pass":
        return {
            "status": "error",
            "error": "AUTH_REQUIRED",
            "agent_action": "Authenticate the caller before configuring autopay.",
        }
    card_last4 = context.state.get("card_last4") or "4242"
    return {
        "status": "success",
        "autopay_enabled": enabled,
        "card_last4": card_last4,
        "billing_account_last4": (billing_account or context.state.get("billing_account", "5678"))[-4:],
        "verbatim_preamble_required": "For your security, please do not speak your card number aloud. Use your keypad when prompted.",
        "agent_instruction": f"Confirm that Autopay is enabled using the card ending in {card_last4} in the caller's active language ({{language}}).",
    }
