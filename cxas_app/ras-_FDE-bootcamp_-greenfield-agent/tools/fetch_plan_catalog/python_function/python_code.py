# Returns the plans and equipment the caller can buy.
def fetch_plan_catalog(lob: str = "tv", customer_type: str = "Existing") -> dict:
    """Return a curated shortlist of 2 comparable plans matching lob ('mobility', 'internet', or 'tv')."""
    try:
        lob_clean = (lob or context.state.get("lob") or "tv").lower().strip()
        if "mobil" in lob_clean or "phone" in lob_clean or "data" in lob_clean or "cell" in lob_clean:
            lob_clean = "mobility"
            plans = [
                {
                    "id": "PLAN-MOB-50GB",
                    "name": "Telco Mobility 50GB 5G",
                    "price": "45.00/month",
                    "key_features": "50GB high-speed 5G data, unlimited nationwide talk & text, under $60 budget",
                },
                {
                    "id": "PLAN-MOB-100GB",
                    "name": "Telco Mobility 100GB Unlimited 5G+",
                    "price": "55.00/month",
                    "key_features": "100GB high-speed 5G+ data, mobile hotspot & international texting included, under $60 budget",
                },
            ]
        elif "inter" in lob_clean or "wifi" in lob_clean or "fib" in lob_clean or "wfh" in lob_clean:
            lob_clean = "internet"
            plans = [
                {
                    "id": "PLAN-INT-500",
                    "name": "Telco Pure Fiber 500 Mbps (Home & WFH)",
                    "price": "50.00/month",
                    "key_features": "500 Mbps symmetrical download & upload speed, unlimited data, Wi-Fi 6E router included",
                },
                {
                    "id": "PLAN-INT-1500",
                    "name": "Telco Pure Fiber Gigabit 1.5 Gbps",
                    "price": "70.00/month",
                    "key_features": "1.5 Gbps download / 940 Mbps upload speed, ideal for 4K streaming & remote work, whole-home mesh Wi-Fi",
                },
            ]
        else:
            lob_clean = "tv"
            plans = [
                {
                    "id": "PLAN-TV-BASIC",
                    "name": "Telco TV Essential",
                    "price": "35.00/month",
                    "key_features": "85+ live HD channels, cloud DVR included, 4K streaming box",
                },
                {
                    "id": "PLAN-TV-PREMIER",
                    "name": "Telco TV Premier + Sports Package",
                    "price": "55.00/month",
                    "key_features": "160+ live HD channels, full Sports & Movie channel package included, 200-hour cloud DVR",
                },
            ]

        return {
            "status": "success",
            "lob": lob_clean,
            "customer_type": customer_type,
            "plans": plans,
            "agent_instruction": "Present these 2 plans clearly in the caller's active language ({language}). When the caller selects one, call place_new_order immediately.",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Inform the caller that plan catalog lookup failed and connect to a sales specialist.",
        }
