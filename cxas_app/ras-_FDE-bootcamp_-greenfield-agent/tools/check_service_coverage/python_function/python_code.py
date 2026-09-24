# Checks if a service is available at the caller's address; business accounts go to a human.
def check_service_coverage(address_or_zip: str = "94105", lob: str = "tv") -> dict:
    """Verify service coverage at caller's address before presenting plans (CUJ-5)."""
    if context.state.get("business_flag") == "true":
        return {
            "status": "error",
            "error": "BUSINESS_HANDOFF_REQUIRED",
            "verbatim_business_handoff": context.state.get("copy_handoff_business_secondary") if context.state.get("language") == "secondary" else context.state.get("copy_handoff_business_primary"),
            "escalate_reason": "business_handoff",
            "agent_action": "Emit the verbatim business_handoff line and escalate with reason business_handoff.",
        }
    return {
        "status": "success",
        "covered": True,
        "address_or_zip": address_or_zip,
        "lob": lob,
        "region": context.state.get("region", "Region-A"),
        "available_tiers": ["Essential Tier", "Premier High-Speed Tier"],
        "agent_instruction": "Coverage is confirmed. Now call fetch_plan_catalog with the matching lob ('mobility', 'internet', or 'tv') and present the 2 plans in the caller's active language ({language}).",
    }
