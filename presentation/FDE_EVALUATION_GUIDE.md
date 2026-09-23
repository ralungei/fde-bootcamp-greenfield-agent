# FDE Presentation Guide — Certification Test 3
**CX Agent Studio (CXAS) Bootcamp · Day 3 · Graduation**

This is your guide to **Certification Test 3: Present your converted + greenfield agents**. It tells you exactly what you must show, how you will be judged, and how to prepare so nothing catches you off guard. Your evaluator is grading against this doc.

---

## 1. What this assessment is

On Day 3 you will deliver a live, timed presentation of the two agents you built during the bootcamp (pick your best of two):
1. **Your greenfield CXAS agent** (built in the Day 1 hands-on from a PRD), and
2. **Your converted agent** (migrated from DFCX to CXAS in the Day 2 hands-on).

Each evaluator reviews 5 presentations, so timing is strict. You are being certified as an FDE who can build production-grade virtual agents and communicate the engineering decisions behind them to a technical customer. The presentation is not a demo for its own sake — it is a proxy for the customer readout you will give on a real GECX delivery.

### Format & timing

| Item | Detail |
| :--- | :--- |
| **Total slot per FDE** | ~30 minutes presentation + ~10 minutes evaluator Q&A |
| **Delivery** | Live, screen-shared. Live demo strongly preferred over recorded video. |
| **Audience** | Your assigned trainer/evaluator |
| **Environment** | Make sure your agent is in [`go/fde-bootcamp-project`](http://goto.google.com/fde-bootcamp-project). Upload any `eval-reports/`, slides, and design docs into a new folder of your LDAP in [this Drive folder](https://drive.google.com/corp/drive/folders/0AEifp3BSv-FuUk9PVA). |

> **Note:** Time discipline is itself evaluated (see *Dimension 3: Execution Velocity*). Rehearse to land inside your slot. A crisp 12-minute story beats a rushed 20-minute one that gets cut off before your quality reports.

---

## 2. The five required components

Your presentation must cover **all five** of the following. Missing any one caps your score and can trigger a `CONDITIONAL PASS` or `FAIL`. These map directly to the evaluator's rubric.

### 2.1 Customer problem & business impact (Framing)
A brief introduction setting the context for your project.
**Show, at minimum:**
- The customer scenario (e.g., Telco, Retail, FSI) and the specific customer problem you are solving.
- The projected business impact of solving this problem (e.g., containment rate, customer satisfaction, cost reduction).
- Your project's **definition of done**.

### 2.2 Production agent demo
A live walkthrough of at least one agent (ideally both) handling real Core User Journeys (CUJs).
**Show, at minimum:**
- **One or two happy-path CUJs end-to-end** (e.g., billing inquiry, appointment booking, claim status).
- **At least one edge case / failure mode handled gracefully** — an API timeout, an out-of-scope request, an auth failure, or a multi-turn silence. *This is where scores are won or lost.*
- **State persistence across turns and sub-agent handoffs** (e.g., the agent remembers the authenticated user after routing).
- **If voice:** a clean spoken fallback and a graceful farewell on hangup/transfer.

**Best practices:**
- Use mock profiles / mock data so the demo runs without live DB dependencies — and say that you're doing so.
- Have a backup plan (screenshots or a short recording) in case live infra hiccups — but lead with live.
- Don't only show the golden path. Evaluators are specifically looking for how you handle friction.

### 2.3 Architecture & design docs
Walk through how the agent is built and why.
**Include:**
- **A topology diagram:** single-agent vs. multi-agent hierarchy, sub-agents, Steering Agent patterns, and `childAgent` relationships.
- **Your `tdd.md` (technical design doc)** — and the actual architecture must match it. Evaluators cross-check.
- **Agent-decomposition rationale:** why this became its own sub-agent vs. was grouped in. Show you understand instruction isolation / avoiding *"instruction rot."*
- **Tooling strategy:** API connectors vs. Python function tools, parallel execution where used, and your structured arg/return JSON schemas.
- **Deterministic workflows** (auth, transfers) handled via callbacks/tool calls rather than left to the model.
- **Security & privacy:** Principle of Least Privilege in IAM, secure secret handling, token gates on account details, PII encryption/redaction.
- **Directory structure** (`cxas_app/`, `tools/`, `agents/`), versioning (GIT / SCRAPI release), and `environment.json` configs.

### 2.4 Expansion roadmap
Show you think beyond the demo — how this agent grows into a real production deployment and expands scope.
**Include:**
- **Next CUJs / use cases** you'd add and why (prioritized by impact, not effort).
- **Integration roadmap:** additional backend systems, contact-center/telephony, downstream APIs, state layers.
- **Scaling & production-readiness:** quota requests (GCP), latency/cost targets, observability rollout.
- **Migration continuation (for the converted agent):** what's left to move off DFCX and how you'd re-design — not lift-and-shift — for a materially better CX.
- **Risks & sequencing:** what you'd tackle first, dependencies, and where customer sign-off is needed.

### 2.5 Quality reports
Prove the agent works with data, not vibes. This is the evidence base for certification.
**Include:**
- **Eval strategy & dataset:** how many test cases, category breakdown (SOP paths, adversarial/stress, out-of-domain), and how you generated them.
- **Golden Dataset vs. User Simulations:** deterministic matching plus open-ended interactions.
- **Current pass rate and the key metrics:** overall tool-invocation correctness (target `1.0` on critical calls), semantic similarity (threshold `≥ 3`), and groundedness against the golden dataset.
- **Gate checks:** your `gate-check-*.json` in `eval-reports/`, with **Gate 6** (multi-turn smoke test) passing, not skipped.
- **Safety config:** `goldenHallucinationMetricBehavior` set to `ENABLED`/`STRICT`, plus active PII, prompt-injection, and toxicity filters.
- **Hill-climbing story:** a concrete failure you found, how you fixed it in instructions (e.g., `<guidelines>`/`<constraints>` tags, not fragile script wrappers), and how you confirmed you didn't regress another flow.
- **Insights/observability:** scorecards configured (sentiment, containment failures, API performance).
- **Customer LGTM:** where you'd get (or got) sign-off on pass-rate and consistency targets.

---

## 3. Suggested presentation flow (~30 min)

| Time | Section | What to hit |
| :--- | :--- | :--- |
| **0:00–1:30** | **Framing** | The customer scenario (Telco/Retail/FSI), the problem, your "definition of done." |
| **1:30–6:30** | **Architecture & design** | Topology diagram, decomposition rationale, tooling & security decisions, `tdd.md`. |
| **6:30–11:00** | **Live demo** | 1–2 happy-path CUJs + at least one edge case handled gracefully; call out state persistence. |
| **11:00–17:00** | **Quality reports** | Eval dataset, pass rates, gate checks (incl. Gate 6), safety config, one hill-climbing story. |
| **17:00–21:00** | **Expansion roadmap** | Next CUJs, integrations, scaling, risks & sequencing. |
| **21:00–30:00** | **Wrap + Q&A setup** | 2–3 sentence summary of production-readiness; invite questions. |

> Adjust ratios to your strengths, but **never drop a required component to save time** — evaluators would rather see all five briefly than four deeply.

---

## 4. How you'll be scored (know the rubric)

You are graded on three dimensions, each `1–5`, drawn from the *CX Agent Studio Bootcamp Certification: Evaluator Framework*:
1. **Production-Grade Performance & Reliability** — resilience, accuracy & grounding, state management.
2. **Critical Thinking & System Design** — tooling strategy, workflow decomposition, security & privacy.
3. **Execution Velocity & Thoughtfulness** — speed to value, edge-case anticipation, maintainability.

See *Evaluator Grading Guide* for the full rubric and pass/fail thresholds. Your evaluator will also fill out *FDE Feedback Template* for you — expect written strengths, blind spots, scores, and one recommended action item.

---

## 5. Automatic red flags (avoid these)

These are called out in the evaluator framework as grounds for failure or major score hits:
- ❌ **Gate 6 skipped** — multi-turn state/routing left unverified.
- ❌ **Hallucination metrics disabled** to pass automated checks (`goldenHallucinationMetricBehavior` off).
- ❌ **PII leakage** in the demo, or hardcoded credentials in code.
- ❌ **Callback syntax bug:** using `for part in llm_response.parts` instead of `for part in llm_response.content.parts` (causes `AttributeError` on voice turns).
- ❌ **Architecture doesn't match `tdd.md`**.
- ❌ **Lift-and-shift conversion** with no CX redesign.
- ❌ **Over-engineered features** with no working core journey.
- ❌ **Fragile fixes:** patching failures with hardcoded script wrappers instead of instruction changes.

---

## 6. Pre-flight checklist

Run through this the night before:
- [x] Both agents deploy and run against mock profiles without manual intervention.
- [x] At least one edge case demo is rehearsed and reliable.
- [x] `tdd.md`, topology diagram, and directory structure are open and match the live agent.
- [x] `app.json` verified: safety filters active, thresholds set, hallucination metric `ENABLED`/`STRICT`.
- [x] `eval-reports/` shows current pass rates and Gate 6 passing.
- [x] One hill-climbing story (`failure → instruction fix → no regression`) ready to tell.
- [x] Expansion roadmap slide with prioritized next steps.
- [x] `cxas lint` run clean (`0 errors, 0 warnings`).
- [x] Deck + demo rehearsed inside the time slot.
- [x] Backup screenshots/recording ready if live infra fails.

*Good luck — build it like it's going to production tomorrow, because that's the bar.*
