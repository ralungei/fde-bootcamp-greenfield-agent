# Checklist de Certificación FDE (Día 3) — Estado del Agente y Artefactos

Este documento lista **todos los requisitos técnicos y artefactos** que exige la guía oficial (`FDE Presentation Guide — Certification Test 3`), explica **qué es cada uno**, y confirma su estado **100% completado** en nuestro repositorio (`ras-fde-bootcamp-greenfield-agent`).

---

## 1. Resumen Ejecutivo de Estado (`11 / 11 COMPLETADOS`)

| # | Requisito de la Guía (Sección) | ¿Qué es exactamente? | Estado | Archivo / Ubicación |
| :-: | :--- | :--- | :---: | :--- |
| **1** | **`goldenHallucinationMetricBehavior: ENABLED`** (`2.5` & `Red Flag`) | Activa el juez de alucinaciones de CES para que verifique que el agente no inventa saldos, citas ni políticas. | ✅ **HECHO** | `cxas_app/.../app.json` (Línea 94) |
| **2** | **Umbrales de Evaluación en `app.json`** (`2.5` & `6`) | `overallToolInvocationCorrectnessThreshold: 1` (1.0 en llamadas críticas) y `semanticSimilaritySuccessThreshold: 3`. | ✅ **HECHO** | `cxas_app/.../app.json` (Líneas 84–93) |
| **3** | **Callback Syntax (`llm_response.content.parts`)** (`Red Flag`) | Usar `llm_response.content.parts` en lugar de `llm_response.parts` en los 6 `after_model_callbacks` para evitar `AttributeError` en voz. | ✅ **HECHO** | `agents/*/after_model_callbacks/` |
| **4** | **`tdd.md` alineado 1:1 con el agente real** (`2.3` & `Red Flag`) | Documento de diseño técnico con topología Hub-and-Spoke (6 agentes), 32 tools, 18 callbacks y separación `auth_status` vs `step_up_status`. | ✅ **HECHO** | `tdd.md` |
| **5** | **Linter Estructural (`cxas lint`) limpio** (`6`) | Validación estática determinista de 60+ reglas de esquema CES, callbacks, guardrails y variables (`0 errors, 0 warnings`). | ✅ **HECHO** | Verificado vía `uv run cxas lint` |
| **6** | **Suite de Simulaciones (`70 Public + 30 Secret`)** (`2.5`) | 100 escenarios multi-turno ejecutados con `session_parameters: {}` (`91/100 PASS` global, `63/70` públicos = `90.0%`, `28/30` ocultos = `93.3%`, sin rastro de los ocultos en el repo). | ✅ **HECHO** | `eval-reports/sim_report_2026-09-24_0006.html` |
| **7** | **Guardrails Nativos y Redacción PII en `app.json` / `guardrails/`** (`2.5` & `6`) | Declaración explícita en `app.json` (`guardrails` + `redactionConfig.enableRedaction: true`) y carpeta `guardrails/` (`prompt_injection_shield` y `model_toxicity_safety`), complementando a `report_malicious_utterance`. | ✅ **HECHO** | `cxas_app/.../app.json` + `cxas_app/.../guardrails/` |
| **8** | **Reporte `gate-check-*.json` con Gate 6 en `PASS`** (`2.5` & `Red Flag`) | Script oficial de verificación pre-vuelo de 6 puertas (`Gate 1` Pull/Lint, `Gate 2` Jerarquía, `Gate 3` Tools, `Gate 4` Callbacks, `Gate 5` Single-turn, y `Gate 6` Multi-turn smoke test: **`6 passed, 0 failed, 0 skipped`**). | ✅ **HECHO** | `eval-reports/gate-check-20260924-010430.json` |
| **9** | **Configuración `environment.json` y Snapshot de Versión CES** (`2.3`) | Configuración declarativa por entorno (`dev`/`staging`/`prod`) y snapshot inmutable **`v1.0-cert-test3-ready`** (`67c09d08-3e09-46c9-b825-3166072cb137`) creado en Google Cloud CES. | ✅ **HECHO** | `environment.json` + CES Version `v1.0-cert-test3-ready` |
| **10** | **Golden Dataset Determinista (`evals/goldens/`)** (`2.5`) | 5 casos P0 deterministas turno a turno (`goldens.yaml`) y su reporte (`golden_report_2026-09-24.json` con `5/5 PASS`, Tool Invocation `1.0`, Similitud `4.72/5.0`). | ✅ **HECHO** | `evals/goldens/goldens.yaml` + `eval-reports/golden_report_2026-09-24.json` |
| **11** | **Observabilidad / CCAI Insights Scorecards** (`2.5`) | Reglas declarativas CEL (`autolabel_rules.yaml`) y cuadros de mando Vega-Lite + SQL (`dashboards.yaml`) para *Containment*, *Caller Sentiment* y *Tool P50/P95 Latency*. | ✅ **HECHO** | `autolabel_rules.yaml` + `dashboards.yaml` |

---

## 2. Resumen Rápido de Qué Hace Cada Artefacto Nuevo

### 1. `cxas_app/ras-_FDE-bootcamp_-greenfield-agent/guardrails/` y `app.json`
- **`prompt_injection_shield`**: Guardrail nativo de CES (`contentFilter` con `WORD_BOUNDARY_STRING_MATCH`) que protege frente a exfiltración de prompt interno sin interferir con turnos legítimos de OTP/teléfono, trabajando en conjunto con nuestra tool determinista `report_malicious_utterance`.
- **`model_toxicity_safety`**: Guardrail nativo de `modelSafety` activo sobre las 4 categorías (`HATE_SPEECH`, `HARASSMENT`, `DANGEROUS_CONTENT`, `SEXUALLY_EXPLICIT`).
- **`loggingSettings.redactionConfig.enableRedaction: true`**: Activa la redacción de PII en logs a nivel de plataforma, sumada a nuestra redacción a 4 dígitos en Python (`cirn`, `billing_account`, `card_last4`).

### 2. `eval-reports/gate-check-20260924-010430.json`
- Ejecutado en vivo contra `projects/fde-bootcamp/locations/us/apps/844c20f7-c058-424e-8ce2-6a66e4ef4ddb` con `--multi-turn`.
- Resultado: **`Summary: 6 passed, 0 failed, 0 skipped` (`Result: ALL PASS`)**.
- En **Gate 6**, verifica una conversación completa de 4 turnos (`Root_agent` → identificación `415-555-0101` → validación OTP `481234` → transferencia a `billing_specialist` → desglose de factura de `$45.00`).

### 3. `evals/goldens/goldens.yaml` y `eval-reports/golden_report_2026-09-24.json`
- Incluye 5 evaluaciones Golden deterministas turno a turno:
  1. `golden__welcome_and_otp_auth_dispatch` (`BR-TV-001`, `BR-TV-009`)
  2. `golden__business_account_immediate_deflection` (`BR-TV-012`)
  3. `golden__prompt_injection_safety_termination` (`BR-TV-016`)
  4. `golden__human_escalation_immediate_request` (`BR-TV-014`)
  5. `golden__bilingual_french_greeting_and_switch` (`BR-TV-004`, `BR-TV-020`)

### 4. `autolabel_rules.yaml`, `dashboards.yaml` y `environment.json`
- **`autolabel_rules.yaml`**: 4 reglas CEL con fallback obligatorio (`condition: ""`) para clasificar contención (`resolution_status`), dominio especialista (`agent_domain`), causa de no-contención (`containment_failure_reason`) y nivel de autenticación/MFA (`security_verification_tier`).
- **`dashboards.yaml`**: Scorecard ejecutivo de CCAI Insights con 3 pestañas (*1. Containment & Resolution Overview*, *2. Sentiment & Safety Guardrails*, *3. Tool & API Performance P50/P95*).
- **`environment.json`**: Configuración declarativa separada para `development`, `staging` y `production`.
