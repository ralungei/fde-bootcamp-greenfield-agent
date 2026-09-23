def evaluate_routing_rules(utterance: str, lob: str = "") -> dict:
    """Evaluate caller utterance to determine target capability module and auth requirement."""
    try:
        text = (utterance or context.state.get("utterance", "")).lower()
        if lob:
            context.state["lob"] = lob

        # Priority 1: M7 Account Management (Cancel, Port-Out, Suspend/Restore, MFA, Password Reset)
        if any(
            k in text
            for k in (
                "cancel",
                "annuler",
                "résilier",
                "port out",
                "port my number",
                "keep my number",
                "mfa",
                "two-factor",
                "2fa",
                "double facteur",
                "password",
                "mot de passe",
                "login",
                "suspend",
                "restore",
                "rétablir",
                "stolen",
                "volé",
            )
        ):
            route = "M7"
        # Priority 2: M5 Sales, Upgrades, Equipment & Port-In (before M4 so 'upgrade internet' goes to M5)
        elif any(
            k in text
            for k in (
                "upgrade",
                "augmenter",
                "work from home",
                "télétravail",
                "faster internet",
                "add tv",
                "new plan",
                "nouveau forfait",
                "defective",
                "défectueux",
                "warranty",
                "garantie",
                "transfer my number",
                "port in",
                "transférer mon numéro",
                "sports package",
            )
        ):
            route = "M5"
        # Priority 3: M6 Technician Appointments & Open Support Tickets
        elif any(
            k in text
            for k in (
                "appointment",
                "technician",
                "reschedule",
                "ticket",
                "book",
                "rendez-vous",
                "billet",
                "technicien",
            )
        ):
            route = "M6"
        # Priority 4: M3 Billing, Payments, Disputes & Autopay
        elif any(
            k in text
            for k in (
                "bill",
                "charge",
                "dispute",
                "pay",
                "autopay",
                "refund",
                "credit",
                "balance",
                "facture",
                "frais",
                "remboursement",
                "payer",
                "arrangement",
            )
        ):
            route = "M3"
        # Priority 5: M4/M8 Technical Support & Outages
        elif any(
            k in text
            for k in (
                "outage",
                "internet",
                "no signal",
                "tv",
                "sim",
                "slow",
                "wifi",
                "repair",
                "panne",
                "télé",
                "données",
                "cellulaire",
                "error 101",
                "freezing",
            )
        ):
            route = "M8" if context.state.get("language") == "secondary" else "M4"
        else:
            route = "M4"

        context.state["route"] = route
        no_auth_needed = route in ("M4", "M8") or any(
            w in text
            for w in ("outage", "panne", "password", "mot de passe", "coverage", "plans", "hours")
        )
        return {
            "status": "success",
            "route": route,
            "confidence": 0.96,
            "requires_auth": not no_auth_needed,
            "auth_status": context.state.get("auth_status", "Fail"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Ask a single targeted clarifying question to disambiguate the caller's intent.",
        }
