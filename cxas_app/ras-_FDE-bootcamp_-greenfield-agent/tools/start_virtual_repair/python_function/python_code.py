# Runs a guided remote repair / line test for the caller's service.
def start_virtual_repair(cirn: str = "", lob: str = "tv", symptom: str = "no signal", tv_sub_type: str = "") -> dict:
    """Start a virtual repair session with LOB-specific troubleshooting steps (mobility, internet, tv)."""
    try:
        lob_clean = (lob or context.state.get("lob") or "tv").lower().strip()
        sym_clean = (symptom or "").lower()
        if any(w in sym_clean for w in ("mobile", "cellular", "data", "sim", "cellulaire", "données", "5g", "lte")):
            lob_clean = "mobility"
        elif any(w in sym_clean for w in ("wifi", "wi-fi", "internet", "router", "modem")):
            lob_clean = "internet"

        sub_type = (tv_sub_type or context.state.get("tv_sub_type", "")).strip()
        if lob_clean == "tv" and not sub_type:
            if "satellite" in sym_clean or "101" in sym_clean:
                sub_type = "satellite"
            elif "app" in sym_clean or "freez" in sym_clean or "stream" in sym_clean:
                sub_type = "streaming"
            else:
                return {
                    "status": "error",
                    "error": "VALIDATION_REQUIRED",
                    "agent_action": "Ask the caller in their active language ({language}) whether their TV service is streaming, satellite, or streaming_only before calling start_virtual_repair.",
                }

        if sub_type:
            context.state["tv_sub_type"] = sub_type
        context.state["vr_task_count"] = "1"

        if lob_clean == "mobility":
            steps = [
                "Step 1: Turn Airplane Mode ON for 15 seconds and then turn it OFF to refresh your cellular tower connection.",
                "Step 2: Open Cellular Settings and verify that Mobile Data and 5G/LTE Data Mode are enabled.",
                "Step 3: Reset your network settings (Settings -> General -> Reset -> Reset Network Settings) to clear stale APN cache.",
                "Step 4: Restart your mobile phone to complete SIM re-registration on the network.",
            ]
            diag_q = "Are you seeing low signal bars, or does the 5G/LTE icon appear without pages loading?"
        elif lob_clean == "internet":
            steps = [
                "Step 1: Unplug the power cable from your Home Fiber Gateway router for 30 seconds.",
                "Step 2: Verify the white fiber optical cable is securely clicked into the PON port.",
                "Step 3: Plug the power cord back in and wait 2 minutes until the status light turns solid white.",
                "Step 4: Reconnect your device to the Wi-Fi network and test your connection.",
            ]
            diag_q = "Is the status light on your Home Fiber Gateway blinking red or solid white?"
        else:
            steps = [
                "Step 1: Power-cycle your TV receiver (or force-close and clear cache on the Fibe TV streaming app).",
                "Step 2: For Satellite Error 101 or no signal, check the coaxial/HDMI cable on Port 1 and press Info -> Reset on the receiver.",
                "Step 3: Wait 2 minutes for the receiver channel guide and DRM license to reload.",
                "Step 4: Press Input/Source on your remote and confirm HDMI 1 (or relaunch the Fibe TV app).",
            ]
            diag_q = "Is the status light on the front of your receiver blinking red, solid green, or are you using the Fibe TV app?"

        return {
            "status": "success",
            "session_id": "VR-77201",
            "lob": lob_clean,
            "tv_sub_type": sub_type or "n/a",
            "first_diagnostic_question": diag_q,
            "sequential_steps_count": 4,
            "troubleshooting_steps": steps,
            "agent_instruction": "Provide these LOB-specific troubleshooting steps clearly in the caller's active language ({language}) and also send them via SMS using send_sms so the caller has the 4-step guide on their phone.",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_action": "Send troubleshooting steps via send_sms or transfer to a representative.",
        }
