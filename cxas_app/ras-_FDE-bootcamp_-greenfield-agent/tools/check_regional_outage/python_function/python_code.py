def check_regional_outage(region: str = "Region-A", lob: str = "tv", postal_code: str = "") -> dict:
    """Check regional outage status by postal code or region before starting diagnostics (M4, CUJ-3)."""
    try:
        reg = (postal_code or region or context.state.get("region", "Region-A")).upper().strip()
        is_outage = (
            "H3Z" in reg
            or "G1R" in reg
            or reg == "REGION-C"
            or context.state.get("outage_override") == "true"
        )
        if "V6B" in reg or "NO_OUTAGE" in reg:
            is_outage = False
        return {
            "status": "success",
            "region": reg,
            "postal_code": postal_code or reg,
            "lob": lob,
            "active": is_outage,
            "restoration_eta_iso": "2026-09-22T20:00:00Z" if is_outage else "",
            "verbatim_if_active": "I see there's an active outage in your area. We're working on it. Would you like me to text you when it's restored?" if is_outage else "",
            "verbatim_if_active_fr": "Je vois qu'il y a une panne active dans votre secteur. Nous y travaillons. Voulez-vous que je vous envoie un texto lorsqu'elle sera rétablie?" if is_outage else "",
            "agent_instruction": "If active is True, state verbatim_if_active (or verbatim_if_active_fr if speaking French) in the caller's active language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Proceed with standard virtual repair troubleshooting or escalate to a representative.",
        }
