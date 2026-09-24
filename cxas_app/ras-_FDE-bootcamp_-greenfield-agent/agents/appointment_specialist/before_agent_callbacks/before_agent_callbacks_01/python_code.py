# Copyright 2026 Google LLC
# ==========================================================================================
# WHAT THIS CALLBACK DOES (before_agent_callback)
# ------------------------------------------------------------------------------------------
# Runs once every time the conversation ENTERS this agent (at call start or after a handoff
# from another agent).
#
# We use this to:
#   * Reset the per-agent no-input counter (BR-TV-006), so silences in the previous agent do
#     not count against the caller in this one.
#   * Mark the billing redirect as "handled" when we land in billing_specialist, so the
#     transfer rule that sent us here does not fire again and bounce the caller in a loop.
#   * Seed safe defaults (mock mode, refund limit of $25, card on file) if they are missing.
#
# If we did not have this:
#   * A caller could be hung up on too early, because silences from earlier agents would add up.
#   * After paying a past-due balance, the caller could be sent back to Billing over and over.
#   * Tools that read the refund limit or the card on file could get an empty value and fail.
# ==========================================================================================
"""before_agent_callback for appointment_specialist — resets local_noinput_counter on module entry (BR-TV-006)."""

from typing import Optional


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    state = callback_context.state
    current_agent = "appointment_specialist"

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
