# Agent Handoff & Context Guide (`AGENT_HANDOFF_CONTEXT.md`)

Este documento sirve como contexto rápido para cualquier otro agente de IA que continúe ayudando con la preparación de la **Presentación de Certificación FDE (Day 3 — Certification Test 3)** para el proyecto **Telco Voice Central** (`ras-fde-bootcamp-greenfield-agent`).

---

## 1. Mapa de Documentos Clave (En qué debes fijarte)

| Archivo / Carpeta | Qué contiene y para qué sirve |
| :--- | :--- |
| **[`presentation/FDE_EVALUATION_GUIDE.md`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/presentation/FDE_EVALUATION_GUIDE.md)** | **La rúbrica oficial del examen de mañana.** Contiene los 5 bloques obligatorios (`2.1 Framing`, `2.2 Live Demo`, `2.3 Architecture`, `2.4 Expansion Roadmap`, `2.5 Quality Reports`), la estructura de 30 minutos y la lista de *Automatic Red Flags* (Sección 5). |
| **[`presentation/demo-deck.html`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/presentation/demo-deck.html)** | **La plantilla visual de referencia.** De aquí se toman los estilos exactos (`.bento.cols8`, `.tile`, colores `v-gemini`, `v-solid`, `v-deep`, `v-tint`, `v-cyan`, `v-indigo`, `v-spec`, animaciones `.blob` y cajón inferior `Presenter notes [N]`). |
| **[`presentation/master.html`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/presentation/master.html)** (y [`/master.html`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/master.html)) | **El deck final para presentar al cliente mañana.** Debe tener **cero lenguaje interno de bootcamp** en la parte visible (se presenta como un *Customer Readout* real para Telco Voice Central), baja carga cognitiva visual (tarjetas cortas y muy visuales) y **Speaker Notes (`[N]`) completas en español** con analogías sencillas + explicación técnica. |
| **[`todo.md`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/todo.md)** | **El diario de ingeniería y decisiones (`v1.0` → `v2.1`).** Documenta la evolución real del score (`63/90` → `71/90` con `18/20` en Secret Evals → `100% (9/9)` en la suite de simulación limpia) y los 5 bugs forenses de trazas que corregimos. **Úsalo siempre para aterrizar ejemplos reales que la usuaria ya conoce de memoria.** |
| **[`tdd.md`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/tdd.md)** | **Technical Design Document.** Documenta la arquitectura **Hub-and-Spoke** (`M1 Root_agent` como concentrador + 5 especialistas `M3`–`M7` con `childAgents: []`), las 32 tools en Python, las variables de estado (`context.state`) y el modelo de seguridad de 2 niveles (`auth_status` vs `step_up_status`). |
| **[`sources/telco-voice-central-spec.md`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/sources/telco-voice-central-spec.md)** | Especificación funcional original de 25 páginas (PRD) con todas las reglas de negocio (`BR-TV-001` aviso de grabación, topes de disputa de `$25.00`, ETF de cancelación, etc.). |
| **[`cxas_app/ras-_FDE-bootcamp_-greenfield-agent/`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/cxas_app/ras-_FDE-bootcamp_-greenfield-agent)** | Código declarativo real del agente desplegado en Google Cloud CES (`projects/fde-bootcamp/locations/us/apps/844c20f7-c058-424e-8ce2-6a66e4ef4ddb`). |

---

## 2. Resumen de los Casos Reales y Fixes que la Usuaria Domina al Dedillo

Cuando prepares explicaciones, guiones de demo o historias de *Hill-Climbing*, usa siempre estos casos reales que hemos implementado juntos:

1. **Caso Estrella de Autenticación (`and` vs `or` + `send_authentication_otp` en Ventas):**
   - **El problema:** Al vaciar `session_parameters: {}` en las simulaciones (para no hacer trampa pre-inyectando estado), vimos dos fallos:
     1. En ventas/upgrades (`sim__upgrade_internet_wfh` / `place_new_order`), el agente le pedía al usuario el código OTP por voz pero **se había olvidado de llamar primero a la tool `send_authentication_otp`**.
     2. En 7 tools sensibles (`manage_mfa`, `place_new_order`, `cancel_or_port_service`, `execute_suspend_restore`, etc.) la guarda tenía un bug booleano: `if auth_status != "Pass" and identification_status != "Pass":`. Como tenía `and`, en cuanto `fetch_customer_profile` identificaba el teléfono (`identification_status = "Pass"`), la condición daba `False` y dejaba ejecutar sin PIN ni OTP.
   - **La solución:** Cambiamos las 7 tools a `if context.state.get("auth_status") != "Pass": return {"status": "AUTH_REQUIRED", ...}` y añadimos la regla obligatoria en `global_instruction.txt`, `Root_agent/instruction.txt` y `place_new_order` para llamar siempre a `send_authentication_otp` antes de pedir el código.

2. **Caso Estrella de Voz en Vivo (`Barge-In` + Regla de Mínimo 3 Palabras de Idioma):**
   - **El problema:** Al interrumpir el saludo en el simulador de voz diciendo una sola palabra (ej. *"Excusez-moi"*), el agente cambiaba toda la llamada a francés por una simple interjección o se comía el aviso legal de grabación (`BR-TV-001`).
   - **La solución:** Activamos `"bargeInConfig": {"bargeInAwareness": true}` en `app.json` (para que CES sepa que la frase fue truncada y re-emita el aviso obligatorio *"This call may be recorded..."*) y añadimos la **regla de mínimo 3 palabras** en `global_instruction.txt` para que interjecciones de 1–2 palabras no cambien el idioma activo.

3. **Caso Estrella de Callbacks (`before_model_callback` + `after_model_callback` con `CLOSING_STATES`):**
   - **Por qué usamos ambos callbacks al cerrar llamadas (`handover_completed` / `malicious_terminated`):**
     - En el turno en que ocurre el insulto o la petición de agente humano, `before_model` aún no ve el flag activo porque la tool (`report_malicious_utterance` o `execute_live_agent_handover`) la ejecuta el LLM durante ese turno.
     - Al salir del LLM en ese mismo turno, el LLM a veces inventaba media frase (*"I've called a representative..."*). Ahí entra **`after_model_callback`** (el "portero de salida"): pisa la frase del LLM, inyecta la frase oficial verbatim (`handoff_str` o `malicious_str`) y añade `end_session`.
     - Y si el simulador envía un turno adicional después, entra **`before_model_callback`** (el "portero de entrada"): ve `CLOSING_STATES` activo y cortocircuita antes de llamar a Gemini.

4. **Caso Estrella Multi-Agente (`M7 → M1 → M3 → M1 → M7` Reactivar Línea Suspendida):**
   - Si un cliente pide en `M7 (account_management_specialist)` reactivar una línea suspendida por impago (`non_payment`), el código Python de `execute_suspend_restore` bloquea la reactivación gratuita (`BALANCE_OWED`, `flag_val = "balance_owed_redirect"`).
   - Las `transferRules` deterministas de `M1 (Root_agent)` lo envían a `M3 (billing_specialist)`, donde `process_payment` cobra la deuda (`flag_val = "balance_cleared"`), y lo devuelven automáticamente a `M7` para activar la línea conservando `auth_status = "Pass"`.

5. **Estado de Producción y Linter:**
   - `"goldenHallucinationMetricBehavior": "ENABLED"` en `app.json` (desplegado en CES y en GitHub).
   - `uv run cxas lint` = `0 errors, 0 warnings` en los 155 archivos.

---

## 3. Reglas de Estilo y Preferencias de la Usuaria (MUY IMPORTANTE)

1. **Pensado para alguien con TDAH (ADHD-friendly):**
   - **En las diapositivas (vista del cliente):** Baja carga cognitiva. Nada de párrafos largos ni muros de texto. Usa elementos visuales (diagramas SVG de Hub & Spoke, flujos de 3 pasos, números grandes, colores limpios de `demo-deck.html`).
   - **Cero referencias internas al Bootcamp en la diapositiva:** El cliente/evaluador nunca debe leer *"Sección 2.1"*, *"Hill-Climbing"* o *"todo.md"* en los títulos o chips de las tarjetas.
2. **En las Speaker Notes (`Presenter notes [N]`):**
   - Siempre en **español**.
   - Estructura visual muy clara con cajas diferenciadas:
     1. 💡 **Ejemplo cotidiano sencillo primero** (para entender el concepto al vuelo).
     2. 🔧 **Qué ruta seguir en la demo y por qué pasa cada cosa por debajo**.
     3. 🗣️ **Guion literal con palabras clave en negrita** para que la vista encuentre el punto exacto en 1 segundo.
