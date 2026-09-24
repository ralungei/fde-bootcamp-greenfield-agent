# Copyright 2026 Google LLC
# We use this to reset per-agent counters and defaults on entry; without it silences add up across agents and Billing can loop.
"""before_agent_callback for Root_agent — resets local_noinput_counter on module entry (BR-TV-006)."""

from typing import Optional


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    state = callback_context.state
    current_agent = "Root_agent"

    # Only reset local_noinput_counter when landing on a new module/agent (BR-TV-006)
    if state.get("_active_agent") != current_agent:
        state["_active_agent"] = current_agent
        state["local_noinput_counter"] = "0"

    # Clear balance_owed_redirect once we land on billing_specialist so it doesn't re-trigger
    if current_agent == "billing_specialist" and state.get("flag_val") == "balance_owed_redirect":
        state["flag_val"] = "in_billing_for_restore"

    if not state.get("mock_mode"):
        state["mock_mode"] = "True"
    if not state.get("loyalty_limit"):
        state["loyalty_limit"] = "25"
    if not state.get("card_last4"):
        state["card_last4"] = "4242"

    return None
