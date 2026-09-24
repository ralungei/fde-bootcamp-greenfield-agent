def fetch_customer_profile(account_or_phone: str = "") -> dict:
    """Identify the caller from the phone or account number THEY state on the call (never the telephony caller ID)."""
    try:
        # // Opcion A: se identifica SOLO con el numero que dice el cliente. El caller ID (clid)
        # // de telefonia se usa para el idioma, nunca para identificar en silencio.
        raw_input = (account_or_phone or "").strip()
        if not raw_input:
            return {
                "status": "error",
                "error": "NUMBER_REQUIRED",
                "identification_status": "",
                "agent_action": "Ask the caller for the phone number or 9-digit account number on their service, then call fetch_customer_profile with account_or_phone set to exactly what they said. Never use the caller ID.",
            }
        digits = "".join(c for c in raw_input if c.isdigit())

        # // Guarda determinista: el numero tiene que haberlo dicho o tecleado el cliente en esta
        # // llamada (lo registra before_model_callback en caller_said_digits). Si el modelo intenta
        # // usar el caller ID u otro numero que el cliente no ha dicho, no se identifica.
        said = (context.state.get("caller_said_digits") or "").replace(" ", "")
        if len(digits) >= 4 and digits not in said and digits[-9:] not in said:
            return {
                "status": "error",
                "error": "NUMBER_NOT_PROVIDED_BY_CALLER",
                "identification_status": "",
                "agent_action": "The caller has NOT said this number on the call. Do not use the caller ID or any number the caller did not say. Ask the caller for the phone number or 9-digit account number on their service, then call fetch_customer_profile with exactly what they said.",
            }

        if raw_input == "ERROR_SYSTEM":
            context.state["api_resp"] = "SYSTEM_DOWN"
            return {
                "status": "error",
                "error": "SYSTEM_DOWN",
                "message": "CRM profile service is down.",
                "agent_action": "Escalate immediately with reason system_unavailable.",
            }

        # Support wrong-number retry scenario (sim__reset_password_wrong_number_retry) without rejecting French 06 numbers
        already_failed_once = context.state.get("flag_val") == "id_retried"
        is_wrong_try = (
            not already_failed_once
            and (
                "wrong" in raw_input.lower()
                or digits.endswith(("0000", "9999", "1111"))
            )
        )
        if is_wrong_try:
            context.state["flag_val"] = "id_retried"
            context.state["identification_status"] = "Fail"
            return {
                "status": "error",
                "identification_status": "Fail",
                "error": "ACCOUNT_NOT_FOUND",
                "message": "No customer account was found matching that phone number.",
                "agent_action": "Inform the caller that no account was found with that number and ask them to provide their correct 9-digit account number or alternate phone number.",
            }

        is_business = "true" if raw_input.endswith("0103") or "business" in raw_input.lower() or context.state.get("business_flag") == "true" else "false"
        is_suspended = "non_payment" if raw_input.endswith("0102") or context.state.get("suspension_reason") == "non_payment" else context.state.get("suspension_reason", "")
        region = context.state.get("region") or ("Region-C" if raw_input.endswith("0104") else "Region-A")
        cirn_full = context.state.get("cirn") or "9988774321"
        ban_full = context.state.get("billing_account") or "1000205678"
        card_last4 = context.state.get("card_last4") or "4242"

        context.state["identification_status"] = "Pass"
        context.state["customer_type"] = context.state.get("customer_type") or "Existing"
        context.state["business_flag"] = is_business
        context.state["is_prepaid"] = context.state.get("is_prepaid") or "false"
        context.state["cirn"] = cirn_full[-4:]
        context.state["billing_account"] = ban_full[-4:]
        context.state["card_last4"] = card_last4
        context.state["region"] = region
        context.state["user_id"] = "USR-9001"
        if is_suspended:
            context.state["suspension_reason"] = is_suspended

        return {
            "status": "success",
            "identification_status": "Pass",
            "customer_type": context.state["customer_type"],
            "business_flag": is_business,
            "is_prepaid": context.state["is_prepaid"],
            "cirn_last4": cirn_full[-4:],
            "billing_account_last4": ban_full[-4:],
            "saved_card_last4": card_last4,
            "callback_number_masked": f"+1-NXX-555-{digits[-4:] if len(digits) >= 4 else '0101'}",
            "region": region,
            "user_id": "USR-9001",
            "agent_instruction": "If business_flag is 'true', immediately state business_handoff and call execute_live_agent_handover(reason='business_handoff'). Keep conversation in the caller's language ({language}).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Inform the caller that profile lookup is unavailable and connect to a specialist.",
        }
