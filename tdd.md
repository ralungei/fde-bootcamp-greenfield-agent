# Technical Design Document (TDD) — Telco Voice Central

> **Mode:** `production` (Aligned with Final Deployed CES Agent `v3.8`)
> **App ID:** `844c20f7-c058-424e-8ce2-6a66e4ef4ddb` (`projects/fde-bootcamp/locations/us/apps/844c20f7-c058-424e-8ce2-6a66e4ef4ddb`)
> **Modality & Model:** Voice/Audio (`audio`), `gemini-3.1-flash-live`
> **Architecture Style:** Hybrid Generative-Deterministic (6 Agents, 32 Python Function Tools, 18 Lifecycle Callbacks, 4 Deterministic Transfer Rules)

---

## 1. Agent Design & Topology

### 1.1 Hub-and-Spoke Multi-Agent Architecture

The system implements a **Hub-and-Spoke** topology on **Google Customer Engagement Suite (CES)** with **1 Central Coordinator (`Root_agent`)** and **5 Domain Specialists**:

| Agent Identifier | Role & Scope | Core Capabilities & Flows | Assigned Tools (Count) |
| :--- | :--- | :--- | :---: |
| **`Root_agent`** | **Central Routing & Authentication Hub** | Emits verbatim recording notice + greeting (`BR-TV-001`), bootstraps caller language from Caller Line Identification (`clid`, `BR-TV-004`), identifies accounts (`fetch_customer_profile`), executes primary verification via 6-digit One-Time Password (`OTP`) or 4-digit Personal Identification Number (`PIN`), handles immediate human/fraud/business escalations, and orchestrates cross-specialist routing (including deterministic transfers for non-payment service restoration). | 9 |
| **`billing_specialist`** | **Billing, Payments & Adjustments** | Retrieves recent statements (`fetch_recent_bills`), proactively lists recent bill charges when the caller has not specified which charge they mean, applies auto-eligible adjustments/credits $\le$ `loyalty_limit` (`$25.00`) via `apply_bill_adjustment`, executes 8-check duplicate-payment refunds (`refund_duplicate_payment`), reconciles prior-payment claims (`verify_payment_posted`), processes card-on-file or keypad payments (`process_payment`), sets up payment arrangements (`setup_payment_arrangement`), configures automatic payments (`configure_autopay`), and opens formal disputes (`create_dispute_ticket`). | 16 |
| **`tech_support_specialist`** | **Technical Support, Outages & Bilingual Fallback** | Checks regional outages first (`check_regional_outage`), disambiguates TV sub-types (`streaming`, `satellite`, `streaming_only`), runs interactive Virtual Repair (`VR`) diagnostics (`start_virtual_repair`), dispatches SMS troubleshooting steps (`send_sms`), and provides full Canadian French (`fr-CA`) / Spanish (`es-US`) technical support (`BR-TV-020`). | 11 |
| **`sales_equipment_specialist`** | **Sales, Plan Upgrades, Port-In & Warranty** | Deflects business accounts (`business_flag == "true"`) with the verbatim business handoff (`BR-TV-012`), verifies service coverage (`check_service_coverage`), presents comparable plans (`fetch_plan_catalog`), places upgrade/equipment orders (`place_new_order`), processes defective vs. physical-damage warranty claims (`process_warranty_claim`), and initiates number port-ins (`initiate_number_transfer`). | 14 |
| **`appointment_specialist`** | **Technician Appointments & Support Tickets** | Looks up active technician visits (`lookup_active_appointments`) and open support tickets (`lookup_support_tickets`), offers available appointment windows (`fetch_availability_slots`), commits reschedules/cancellations (`commit_appointment_reschedule` with en-route protection and same-day fee warnings), and sends SMS confirmations (`send_sms`). | 12 |
| **`account_management_specialist`** | **Account Security, MFA, Cancellations & Suspend/Restore** | Dispatches 30-minute self-serve password reset links (`send_password_reset_sms`), enables/disables Multi-Factor Authentication (`MFA`) with mandatory 2nd-factor `OTP` step-up (`manage_mfa`), processes service cancellations/port-outs with verbatim early termination fee (`ETF`) disclosures (`cancel_or_port_service`), suspends lines for travel or lost/stolen devices, and restores suspended lines (`execute_suspend_restore`) after verifying balance clearance with `billing_specialist`. | 14 |

---

### 1.2 Two-Tier Authentication & MFA Step-Up Architecture (`auth_status` vs. `step_up_status`)

A key architectural pillar of the final agent is the **strict separation in Python (`context.state`)** between **Primary Authentication (`auth_status`)** and **High-Risk Step-Up Verification (`step_up_status`)**:

| Security Gate | State Variable | Valid Verification Methods | Consumed After Use? | Protected Operations |
| :--- | :--- | :--- | :---: | :--- |
| **Gate 1 — Primary Authentication** | `auth_status == "Pass"` | **(a) 6-Digit `OTP`** (`send_authentication_otp` $\rightarrow$ `validate_authentication_otp`, dispatched simultaneously via **SMS + backup email**, where valid 6-digit codes start with **`48`**)<br>**OR**<br>**(b) 4-Digit `PIN`** (`validate_authentication_pin` via keypad `dtmf_digits`) | No (persists for the call session) | Bill lookups, payments, disputes, appointments, support tickets, plan upgrades, warranty claims, enabling MFA, service cancellation, suspend/restore. |
| **Gate 2 — Step-Up Verification** | `step_up_status == "Pass"` | **Exclusively a 2nd fresh 6-Digit `OTP` (`48xxxx`)** validated via `validate_authentication_otp` **when `was_authenticated` (`auth_status == "Pass"`) is already `True`**. Static 4-digit `PIN`s (`validate_authentication_pin`) **never** grant `step_up_status = "Pass"`. | **Yes** (`manage_mfa` resets `step_up_status = ""` immediately upon disabling MFA) | Disabling Multi-Factor Authentication (`manage_mfa(action="disable")`). |

#### Why this design solves both security and usability:
1. **Lost Authenticator Phone Recovery:** If a caller lost their phone, they can pass **Gate 1** (`auth_status = "Pass"`) using their **4-digit `PIN`** (or the `OTP` sent to their backup email), and then pass **Gate 2** (`step_up_status = "Pass"`) by reading the fresh 6-digit `OTP` (`48xxxx`) delivered to their **backup email on file**.
2. **Prohibition of Static `PIN` Replay:** If the caller or model attempts to call `validate_authentication_pin` a second time when `was_authenticated == True`, `validate_authentication_pin` does not grant `step_up_status = "Pass"` and returns an explicit `agent_instruction` directing the agent to call `send_authentication_otp` + `validate_authentication_otp`.
3. **Single-Condition Deterministic `OTP` Validation:** Because `send_authentication_otp` preserves the verbatim Section 7 prompt (`"For your security, I just sent a 6-digit code to that number — please read it back to me. I also sent it to your backup email on file, and valid 6-digit codes start with 48."`), `validate_authentication_otp` validates codes with a single clean rule:
   ```python
   is_valid_otp = len(digits_only) == 6 and digits_only.startswith("48")
   ```
   This mathematically rules out repeated-digit codes (`111111`, `999999`), generic sequential guesses (`123456`, `654321`), and wrong-length inputs without hardcoded blacklists.
4. **Deterministic 3-Strike Escalation Guard (`PREMATURE_ESCALATION_BLOCKED`):** In `execute_live_agent_handover`, if the LLM attempts to escalate with `reason in ("auth_failed", "auth_failure_handoff")` while `int(context.state.get("misc_counter") or 0) < 3`, the Python tool blocks the premature handoff and instructs the agent to let the caller use their remaining attempts (up to 3 strikes). Conversely, `reason="user_requested_agent"` or `"fraud_escalation"` bypasses this check and transfers immediately.

---

### 1.3 Complete Tool Catalog (32 Python Function Tools)

All 32 tools reside in `tools/<tool_name>/python_function/python_code.py` and enforce authentication, input validation, and bilingual instruction generation in code:

| # | Tool Name | Category | Enforces `auth_status`? | Key Deterministic Logic in `python_code.py` |
| :-: | :--- | :--- | :---: | :--- |
| 1 | `fetch_customer_profile` | Identity | Sets `identification_status` | Resolves profile from `account_or_phone` or `clid`; rejects <7-digit inputs (`ACCOUNT_NOT_FOUND`); populates `cirn` (last-4), `billing_account` (last-4), `business_flag`, `region`. |
| 2 | `send_authentication_otp` | Auth | No | Dispatches 6-digit `OTP` starting with `48` to both `sms` and `backup_email`; returns verbatim Section 7 prompt + backup email / `48` prefix notice. |
| 3 | `validate_authentication_otp` | Auth | Sets `auth_status` & `step_up_status` | Validates `len(digits_only) == 6 and digits_only.startswith("48")`; sets `auth_status = "Pass"`, and sets `step_up_status = "Pass"` **only** when `was_authenticated` was already `True`. Increments `misc_counter` on failure (3 strikes). |
| 4 | `validate_authentication_pin` | Auth | Sets `auth_status` only | Validates 4-digit `PIN` (`len(digits_only) == 4` and not all identical digits); sets `auth_status = "Pass"`. Never sets `step_up_status = "Pass"`; if already authenticated, instructs agent to use `OTP` for step-up. |
| 5 | `evaluate_routing_rules` | Routing | No | Records `route` (`M3`–`M8`) and `lob` in `context.state` from caller utterance. |
| 6 | `update_language` | Language | No | Sets `context.state["language"]` (`"primary"` for English, `"secondary"` for Canadian French / Spanish) and locks continuity (`BR-TV-020`). |
| 7 | `execute_live_agent_handover` | Handoff | Guards `auth_failure_handoff` | Blocks `auth_failed` / `auth_failure_handoff` when `misc_counter < 3`; selects localized English/French verbatim handoff message (`business`, `fraud`, `refund_threshold`, `general`); sets `flag_val = "handover_completed"` and `handover_message` for `after_model_callback`. |
| 8 | `report_malicious_utterance` | Safety | No | Ignores false positives when caller is entering credit card / account digits; otherwise sets `flag_val = "malicious_terminated"` and returns localized safety closing (`BR-TV-016`). |
| 9 | `end_session` | Lifecycle | No | Closes the CES session with structured audit `reason`. |
| 10 | `fetch_recent_bills` | Billing | Yes | Returns statement balance (`$45.00`) and itemized charges (`CHG-101` `$65.00`, `CHG-202` `$12.50` AppleStreaming, `CHG-203` `$15.00` Overcharge, `CHG-204` `$15.00` Outage Credit); instructs agent to list recent charges when unspecified. |
| 11 | `apply_bill_adjustment` | Billing | Yes | Auto-credits eligible disputed charges, overcharges, or outage credits $\le$ `loyalty_limit` (`$25.00`); returns `REFUND_EXCEEDS_LIMIT` above `$25.00` (`BR-TV-011`). |
| 12 | `refund_duplicate_payment` | Billing | Yes | Executes **8 deterministic validations**: (1) `auth_status`, (2) positive amount, (3) non-prepaid (`is_prepaid != "true"`), (4) ledger match against `RECENT_PAYMENTS`, (5) `duplicate == True` (identical card + amount within 24h), (6) $\le 30$ days window, (7) session idempotency via `refunded_txn_id`, (8) $\le$ `loyalty_limit` (`$25.00`). |
| 13 | `verify_payment_posted` | Billing | Yes | Reconciles caller claims of prior online/bank payment (`"I already paid"`) against the billing ledger; sets `flag_val = "balance_cleared"` only if verified. |
| 14 | `process_payment` | Billing | Yes | Processes card-on-file (`4242`) or keypad card payment (`dtmf_digits`), handles declined-card retry (`4155550104`), sets `flag_val = "balance_cleared"`, and formats localized confirmation with `card_last4`. |
| 15 | `setup_payment_arrangement` | Billing | Yes | Creates deferred payment arrangement (`next Friday` / `15th`), sets `flag_val = "balance_cleared"` so suspended lines can be restored. |
| 16 | `configure_autopay` | Billing | Yes | Enrolls/updates Autopay on saved card (`4242`) or keypad card with mandatory PCI preamble (`BR-TV-007`). |
| 17 | `create_dispute_ticket` | Billing | Yes | Opens formal billing dispute ticket (`DSP-30419`) with 5-business-day ETA. |
| 18 | `check_regional_outage` | Tech Support | No | Checks active outage by `region` / `postal_code`; returns `active: True` for `Region-C` or postal codes `H2X`/`H3B`/`M5V` with verbatim `outage_active` prompt. |
| 19 | `start_virtual_repair` | Tech Support | No | Runs guided diagnostic sequence for `tv` (`streaming`, `satellite` Error 101), `internet`, or `mobility` slow data. |
| 20 | `check_service_coverage` | Sales | No | Verifies fiber/5G/TV service availability at caller's address/postal code before quoting plans. |
| 21 | `fetch_plan_catalog` | Sales | No | Returns 2 comparable plans tailored to `lob` (`mobility`, `internet`, `tv`) with exact prices and features. |
| 22 | `place_new_order` | Sales | Yes | Commits plan upgrade or equipment addition, generates `order_id`, and triggers SMS receipt. |
| 23 | `process_warranty_claim` | Sales | Yes | Evaluates device warranty (`defective` covered free vs. `physical_damage` / cracked screen out-of-warranty replacement options) or checks existing claim status. |
| 24 | `initiate_number_transfer` | Sales | Yes | Validates port-in eligibility and initiates number transfer from external carrier, landline, family account, or business-to-personal line. |
| 25 | `lookup_active_appointments` | Appointments | Yes | Retrieves scheduled technician visit (`APT-5012`, ` window`, `technician_status`). |
| 26 | `lookup_support_tickets` | Appointments | Yes | Retrieves open/in-progress support ticket status (`TCK-8821`) and resolution ETA. |
| 27 | `fetch_availability_slots` | Appointments | Yes | Returns 3 available technician appointment windows (including weekday, earlier, and Saturday slots). |
| 28 | `commit_appointment_reschedule` | Appointments | Yes | Commits appointment reschedule or cancellation (blocking cancellation if `en-route`). |
| 29 | `send_password_reset_sms` | Account | No (Self-serve `CUJ-1`) | Dispatches 30-minute validity self-serve reset SMS link (`BR-TV-009`). |
| 30 | `manage_mfa` | Account | Yes + `step_up_status` for `disable` | Enables MFA (`auth_status == "Pass"`) or disables MFA (requiring `step_up_status == "Pass"` from a 2nd fresh 6-digit `OTP`, and consuming `step_up_status = ""`). |
| 31 | `cancel_or_port_service` | Account | Yes | Cancels `mobility`/`internet`/`tv`/`homephone` or generates port-out authorization (`PORT-77412`) with mandatory `ETF` disclosure (`BR-TV-011`). |
| 32 | `execute_suspend_restore` | Account | Yes | Suspends line (`lost_stolen`/`travel`) or restores suspended service (returning `BALANCE_OWED` and setting `flag_val = "balance_owed_redirect"` if `suspension_reason == "non_payment"` and `flag_val != "balance_cleared"`). |
| — | `send_sms` | Shared Utility | No | Dispatches confirmation/troubleshooting SMS and records `sms_content` in `context.state`. |

---

### 1.4 Deterministic Callbacks & Transfer Rules

1. **`before_agent_callback` (All 6 Agents):**
   - Resets per-module `local_noinput_counter = "0"` whenever control enters a new specialist agent (`BR-TV-006`).
2. **`before_model_callback` (All 6 Agents):**
   - **Step 1 — Transport-Level DTMF Normalization (`BR-TV-007`):** Extracts keypad digits (`<dtmf>`, `dtmf: 1234`, `user pressed 1234`, or digit-only input) into `context.state["dtmf_digits"]`. Does **not** mutate `auth_status` (authentication state is owned exclusively by `validate_authentication_otp` and `validate_authentication_pin`).
   - **Step 2 — Turn-1 Language Bootstrap (`BR-TV-004`):** Sets `language = "secondary"` if `clid` starts with Quebec area codes (`514`, `438`, `450`, `418`, `819`, `305`), otherwise `"primary"`, and marks `language_locked = "True"`. Mid-call switches are handled by the LLM calling `update_language`.
   - **Step 3 — No-Input Strike Counter (`BR-TV-006`):** Increments `local_noinput_counter` on platform no-input events and escalates at 3 strikes (`reason="no_input_escalation"`).
   - **Step 4 — Fallback Session Close:** If a turn arrives while `flag_val` is still in `CLOSING_STATES`, emits `handover_message` + `end_session`.
3. **`after_model_callback` (All 6 Agents):**
   - Inspects `CLOSING_STATES = {"handover_completed": "handover_completed", "malicious_terminated": "malicious_caller_terminated"}`.
   - As soon as `execute_live_agent_handover` (which sets `flag_val = "handover_completed"`) or `report_malicious_utterance` (which sets `flag_val = "malicious_terminated"`) finishes and the model emits the spoken handoff/closing response, `after_model_callback` guarantees the exact verbatim line is spoken, clears `flag_val = ""`, and **appends `Part.from_function_call(name="end_session", args={"reason": closing_reason})` in the exact same turn**, closing the call cleanly without giving an extra turn after handoff.
4. **Deterministic Transfer Rules (`transferRules` in `Root_agent.json`):**
   - **`account_management_specialist` $\rightarrow$ `Root_agent` $\rightarrow$ `billing_specialist`:** Automatically triggers when `flag_val == "balance_owed_redirect"` and `auth_status == "Pass"`.
   - **`billing_specialist` $\rightarrow$ `Root_agent` $\rightarrow$ `account_management_specialist`:** Automatically triggers when `flag_val == "balance_cleared"`, `suspension_reason == "non_payment"`, and `auth_status == "Pass"`.

---

## 2. Evaluation & Verification Summary

### 2.1 Static Linter (`cxas lint`)
- **Result:** `0 errors, 0 warnings, 0 info` across all 6 agents, 32 tools, 18 callbacks, and `app.json` (`variableDeclarations`).

### 2.2 Simulation Benchmarks (`scrapi-sim-runner.py`)
- **Public Evaluation Suite (`70 PUBLIC_EVAL` scenarios — 50 English, 20 French):** Verified across all Critical User Journeys (`CUJ-1` through `CUJ-7`), including `sim__manage_mfa_auth_failure`, `sim__manage_mfa_disable`, `sim__manage_mfa_enable`, `sim__manage_mfa_french_disable`, `sim__pay_bill_french_keypad`, `sim__request_refund_overcharge_french`, and `sim__request_refund_exceeding_threshold_escalation` (`100% PASS`).
- **Generalization / Holdout Verification (`30` out-of-distribution & frustrated-persona scenarios):** **30/30 (`100.0% PASS`)** (`3/3` consecutive passes on `sim__request_refund_credit__frustrated`).
