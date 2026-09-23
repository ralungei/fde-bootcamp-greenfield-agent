# Telco Voice Central — Agent Development Brief (Specification)

## Overview
Build a production voice agent (`audio` modality) that answers a consumer telco's main customer-service line and resolves the six most common contact reasons:
1. **Billing questions** (M3, ~25% volume)
2. **Technical support** (M4, ~30% volume)
3. **Sales & equipment** (M5, ~15% volume)
4. **Appointment management** (M6, ~10% volume)
5. **Account management** (M7, ~15% volume)
6. **Service changes** (M3 + M7, ~5% volume)
Plus M1 (Session Lifecycle & Routing), M2 (Authentication & Identity), and M8 (Secondary Language Fallback).

---

## Section 1 — Global Behavioral Requirements
- **Recording notice (BR-TV-001):** Regional privacy disclosure emitted verbatim on initial greeting; re-emitted verbatim if caller asks whether they are being recorded or interrupts it.
- **Language locking (BR-TV-004):** Determined at turn 1 from area-code prefix (`clid`) + first utterance (`primary` | `secondary`) and locked for the call unless explicit switch trigger ("primary language" / "secondary language").
- **PII redaction (BR-TV-009):** `cirn`, `billing_account`, and card digits are read back **only as the last 4 characters**. PINs and OTP codes are **never** spoken back.
- **Malicious utterance handling (BR-TV-016):** Per-turn classifier; on hit, emit polite closing line and end session with reason `malicious_input`.
- **Retry-strike escalation (BR-TV-006):** 3 consecutive no-input events (`no_input_escalation`) or 3 unresolved no-match events (`disambig_max_attempts`) on the same module trigger graceful escalation.
- **After-hours awareness (BR-TV-014):** Live-agent queues honored 24/7 for outage & fraud escalations. Sales, plan changes, and appointment booking route to next-business-day when closed.

---

## Section 2 — Capability Modules Overview
- **M1 · Session Lifecycle & Routing:** Greet, capture identity, detect language, disambiguate intent, hand off to specialist capability, wrap and close. Entry/exit for all CUJs.
- **M2 · Authentication & Identity:** Verify caller via OTP or PIN; manage auth ladder (`Guest` -> `Identified` -> `Authenticated`); escalate on failure (`auth_failure_handoff`).
- **M3 · Billing & Payment:** Bill lookup, dispute cases, autopay, refunds, arrangements, deposits (CUJ-2, part of CUJ-6).
- **M4 · Technical Support & Virtual Repair:** Outage lookup, `tv_sub_type` disambiguation (`streaming` | `satellite` | `streaming_only`), virtual-repair session, SMS-delivered troubleshooting (>2 steps), ticket creation (CUJ-3).
- **M5 · Sales & Equipment:** Plan catalog (present 2–3 options max), service coverage, order placement, warranty claims, returns, SIM requests, number-transfer-in. Business callers (`business_flag == true`) immediately receive verbatim `business_handoff` and end with `business_handoff` (CUJ-5).
- **M6 · Appointment & Ticket Management:** Active appointment lookup, offer 2–3 availability slots, reschedule/cancel commit + SMS confirmation, technician-visit status (CUJ-4).
- **M7 · Account Management:** Password reset SMS link (30-min validity, requires authenticated, never echo link), MFA enable/disable (step-up auth), fraud reporting (empathy_protocol + immediate escalate `fraud_escalation`, NO auth attempt), profile update, suspend/restore (lost/stolen suspends immediately; non-payment hands back to M1 -> M3 -> M7) (CUJ-1, CUJ-6).
- **M8 · Secondary Language Fallback:** Tech-support queries in secondary language when M4 primary content lacks coverage. If outside M8's supported set, emit verbatim `live_agent_handoff` in secondary language and end with `secondary_language_live_agent` (CUJ-7).

---

## Section 3 — Call Lifecycle Sequence (Before Caller Interaction)
1. **Restricted caller check (BR-TV-002):** If blocked -> play deflection + disconnect.
2. **Regional service alert active? (BR-TV-003):** If Yes -> prepend advisory banner to greeting.
3. **Standard greeting + Recording notice verbatim (BR-TV-001).**
4. **Language detect from CLID + first utterance (BR-TV-004).**
5. **Open-ended intent capture.**

---

## Section 5 — Canonical Session Data Model
### Identity
- `clid` (str): 10-digit caller ID from telephony
- `tfn` (str): Toll-free number dialed
- `cirn` (str, PII): Customer reference number (last-4 only)
- `billing_account` (str, PII): Billing account number (last-4 only)
- `customer_type` (`New` | `Existing`)
- `user_id` (str): Internal CRM record ID

### Auth state
- `auth_status` (`Pass` | `Fail`): NEVER mock or override in evals
- `identification_status` (`Pass` | `Fail`): NEVER mock or override in evals
- `business_flag` (bool-str): Triggers business-account handoff

### Routing
- `route` (enum-str): Disambiguation output
- `lob` (`mobility` | `internet` | `tv` | `homephone` | `smarthome`)
- `tv_sub_type` (`streaming` | `satellite` | `streaming_only` | `null`)
- `region` (str): `Region-A` / `Region-B` / `Region-C`

### Conversation state
- `language` (`primary` | `secondary`)
- `utterance` (str): Latest caller intent text
- `dtmf_digits` (str): Normalized DTMF captured during current turn

### Counters & flags
- `local_noinput_counter` (int): Per-module no-input retry count (escalates at 3 -> `no_input_escalation`)
- `global_err_count` (int): Cross-module error count (escalates at 3 -> `too_many_errors`)
- `no_match_confirmation_count` (int): No-match retry budget (escalates at 3 -> `disambig_max_attempts`)
- `misc_counter` (int): Generic per-flow counter
- `mock_mode` (str): `"True"` in eval harness to return deterministic synthetic success

### Payment / order
- `last_pmt_amt` (float-str), `amount` (float-str), `ban_type` (str), `is_prepaid` (bool-str), `loyalty_limit` (int)

### Virtual-repair & ticketing
- `vr_task_count` (int), `ticket_state` (str), `item_list` (str), `intent_type` (str), `api_resp` (str)

### SMS & misc
- `sms_type` (`Public` | `Private`), `sms_content` (str), `day_val`, `date_val`, `month_val`, `end_time`, `flag_val`

---

## Section 6 — Per-Turn Preprocessing (Strict Order)
1. **DTMF capture:** Normalize native DTMF or `"user pressed 1234"` into `dtmf_digits`.
2. **No-input accounting:** Increment `local_noinput_counter` on no user activity; escalate at 3 with `no_input_escalation`.
3. **Tool-error classification:**
   - System (`SYSTEM_DOWN`, `INTERNAL_ERROR`, `AUTH_SERVICE_UNAVAILABLE`) -> immediately end session with `system_unavailable`.
   - Business (`INSUFFICIENT_FUNDS`, `NOT_ELIGIBLE`, `ALREADY_APPLIED`) -> surface to model to apologize and offer alternative.
   - Validation (`INVALID_INPUT`, `MALFORMED_REQUEST`) -> increment `global_err_count` (escalate at 3 with `too_many_errors`) and ask caller to clarify.
4. **Module-specific pre-checks.**

---

## Section 7 — Verbatim Copy Library
- `greeting_main`: `"Welcome to Telco. I can help with billing, technical support, or managing your account. To get started, could you tell me the phone number or account number associated with your service?"`
- `recording_notice`: `"This call may be recorded for quality and training purposes."`
- `id_verification_otp`: `"For your security, I just sent a 6-digit code to that number — please read it back to me."`
- `id_verification_pin`: `"For your security, I'll need to verify your identity. Please enter the 4-digit PIN you set up."`
- `live_agent_handoff`: `"I'll connect you to a representative who can help. Please hold."`
- `business_handoff`: `"To get you the best support for your business account, I'll transfer you to an agent. You'll need to use your phone keypad instead of talking to the virtual assistant. Just a moment while I connect you."`
- `refund_confirmation_pattern`: `"Your refund of ${amount} will appear on your next statement within {days} business days."`
- `empathy_protocol`: `"I'm very sorry to hear that you are facing challenges. I will ensure we handle your request with the utmost care."`
- `outage_active`: `"I see there's an active outage in your area. We're working on it. Would you like me to text you when it's restored?"`
- `transfer_to_specialist`: `"I'll connect you to a billing specialist now — they'll have everything we've already discussed."`

---

## Section 17 — Representative Backend Tool Contracts
All tools must support `mock_mode == "True"` and return `{ "error": "<CODE>", "message": "<human>" }` on errors.
- `fetch_customer_profile({ clid })` -> `{ identification_status, customer_type, business_flag, is_prepaid, cirn, billing_account, region, user_id }`
- `send_authentication_otp({ clid })` -> `{ sent: bool, expires_in_sec: int }`
- `validate_authentication_otp({ code })` -> `{ auth_status: "Pass" | "Fail", attempts_remaining: int }`
- `validate_authentication_pin({ pin })` -> `{ auth_status: "Pass" | "Fail", attempts_remaining: int }`
- `evaluate_routing_rules({ utterance, entities })` -> `{ route, confidence, requires_auth }`
- `fetch_recent_bills({ billing_account })` -> `{ bills: [{ id, date, amount, line_items }] }`
- `create_dispute_ticket({ charge_id, reason, notes })` -> `{ ticket_id, eta_business_days }`
- `check_regional_outage({ region, lob })` -> `{ active: bool, restoration_eta_iso }`
- `start_virtual_repair({ cirn, lob, symptom })` -> `{ session_id, first_diagnostic_question }`
- `fetch_availability_slots({ zip, service_type })` -> `{ slots: [{ date, window, technician_id }] }`
- `commit_appointment_reschedule({ appt_id, new_slot })` -> `{ confirmed: bool, new_date }`
- `fetch_plan_catalog({ lob, customer_type })` -> `{ plans: [{ id, name, price, key_features }] }`
- `send_password_reset_sms({ cirn })` -> `{ sent: bool, valid_minutes: 30 }`
- `execute_suspend_restore({ cirn, action, reason })` -> `{ new_state, effective_iso }`
- `execute_live_agent_handover({ reason, session_context })` -> `{ handover_id, queue }`
