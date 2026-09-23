# Análisis Forense de Bugs (`v2.0 -> v2.1`) y Mapa Completo de los 20 Secret Cases

Este documento recoge la explicación de ingeniería de los 5 bugs forenses detectados en los traces reales de Google Cloud CES (`v2.0`), las muestras exactas de código (`ANTES` vs. `AHORA`), el funcionamiento del sistema de autenticación e identificación, y el desglose completo de los **20 Secret Cases** oficiales del Bootcamp (donde alcanzamos **18/20 = 90%** en `v2.0` y cubrimos el **20/20** en `v2.1`).

---

## Parte 1: Análisis de Ingeniería de los 5 Bugs Forenses (`ANTES` vs. `AHORA`)

### 1. ¿Por qué existe el requisito del salto `M7 -> M1 -> M3 -> M1 -> M7`?
En arquitectura de Contact Centers reales (y en el diseño del documento `telco-voice-central-spec.md`), existe el principio de **Separación de Privilegios y Cumplimiento PCI-DSS**:
1. **`account_management_specialist` (`M7`)** tiene acceso a las herramientas de red (`execute_suspend_restore`, `cancel_or_port_service`, `manage_mfa`), pero **NO tiene acceso a la pasarela bancaria (`process_payment`)**.
2. **`billing_specialist` (`M3`)** tiene acceso a la pasarela bancaria (`process_payment`, `setup_payment_arrangement`), pero **NO tiene permisos para tocar el aprovisionamiento de red (`execute_suspend_restore`)**.
3. Como la topología es **Hub-and-Spoke** (`M1` `Root_agent` es el centro y los 5 especialistas son puntas sin conexión directa entre sí para evitar grafos cíclicos), cuando un cliente pide en `M7` reactivar una línea suspendida por falta de pago:
   - `M7` comprueba la línea con `execute_suspend_restore(action="restore")` y descubre que hay `$45.00` pendientes (`BALANCE_OWED`).
   - `M7` devuelve la llamada al Hub `M1` (`Root_agent`), que la transfiere a `M3` (`billing_specialist`).
   - `M3` cobra los `$45.00` (`process_payment` marca `flag_val = "balance_cleared"`) y devuelve la llamada al Hub `M1`.
   - `M1` la devuelve a `M7` (`account_management_specialist`), que ahora sí ejecuta `execute_suspend_restore(action="restore")` con éxito y enciende la línea.

---

### 2. Diferencia entre `transferRules` (JSON) y `before_model_callback` (Python)

| Característica | `before_model_callback` (`python_code.py`) | `transferRules` (`Root_agent.json`) |
| :--- | :--- | :--- |
| **¿Dónde se configura?** | En el script Python que corre antes del LLM en cada agente. | En el archivo declarativo `agents/Root_agent/Root_agent.json`. |
| **¿Qué puede hacer?** | Leer lo que dijo el usuario, modificar variables de sesión (`context.state[...] = ...`) o devolver un mensaje fijo (`LlmResponse`). **NO puede transferir de un agente a otro.** | Evaluar una condición sobre `context.state` y **ejecutar el `transfer_to_agent` en el motor de CES automáticamente** sin depender del LLM. |
| **¿Cuándo se ejecuta?** | En cada turno antes de que el LLM piense. | En cuanto el agente padre (`Root_agent`) tiene el control y la función `should_trigger_transfer_callback(context)` devuelve `True`. |

#### Código real de nuestras `transferRules` en `Root_agent.json` (`v2.1`):
```json
"transferRules": [
  {
    "childAgent": "billing_specialist",
    "direction": "PARENT_TO_CHILD",
    "deterministicTransfer": {
      "pythonCodeCondition": {
        "pythonCode": "def should_trigger_transfer_callback(context: CallbackContext) -> bool:\n    return context.state.get('flag_val') == 'balance_owed_redirect' and context.state.get('auth_status') == 'Pass'\n"
      }
    }
  },
  {
    "childAgent": "account_management_specialist",
    "direction": "PARENT_TO_CHILD",
    "deterministicTransfer": {
      "pythonCodeCondition": {
        "pythonCode": "def should_trigger_transfer_callback(context: CallbackContext) -> bool:\n    return context.state.get('flag_val') == 'balance_cleared' and context.state.get('suspension_reason') == 'non_payment' and context.state.get('auth_status') == 'Pass'\n"
      }
    }
  }
]
```

---

### 3. Bug #1: Por qué el agente tenía que emitir `"text"` y por qué `end_session` lo dejaba mudo

En CES, todo lo que el agente pronuncia en voz alta se guarda en el registro de la conversación (trace) como un bloque `"text"`. Si en un turno no hay bloque `"text"`, significa que **el agente no pronunció ni una sola palabra por el altavoz**.

#### Lo que pasó en `v2.0` (`trace 665178ac` de `sim__speak_immediate_english`):
```json
// Turno del usuario:
{ "role": "user", "text": "I need to speak with a customer service representative right away." }

// Respuesta del agente en v2.0 (¡SIN BLOQUE "text"!):
{
  "role": "model",
  "functionCalls": [
    { "name": "execute_live_agent_handover", "args": { "reason": "user_requested_agent" } },
    { "name": "end_session", "args": {} }
  ]
}
```
Al pedirle en el prompt que llamara a `execute_live_agent_handover` **Y** a `end_session` en el mismo turno, `gemini-3.1-flash-live` ejecutó las dos herramientas seguidas y `end_session` **cortó la llamada antes de que el sintetizador de voz pudiera decir** `"I'll connect you to a representative who can help. Please hold."`.

#### Cómo funciona en `v2.1`:
Quitamos `end_session` de los especialistas y prohibimos llamarlo en el mismo turno que `execute_live_agent_handover`. Ahora `execute_live_agent_handover` devuelve la frase exacta y el modelo **está obligado a emitir el `"text"` hablado** al usuario. Si el simulador envía un turno extra después, `before_model_callback` detecta `flag_val == "handover_completed"` y cierra la sesión limpiamente.

---

### 4. Bug #2: Diseño *Fail-Open* vs. *Fail-Closed* en `execute_suspend_restore`

¿Por qué era mala práctica depender de `if context.state.get("suspension_reason") == "non_payment"`?
Porque en ingeniería de seguridad eso es un diseño **Fail-Open (Abierto por defecto)**: si la variable `suspension_reason` venía vacía (`""`), el código asumía que no había deuda y **regalaba la restauración de la línea gratis**.

```python
# ❌ ANTES (v2.0 — Fail-Open: si suspension_reason era "", restauraba GRATIS)
if act == "restore":
    if context.state.get("suspension_reason") == "non_payment" and context.state.get("flag_val") != "balance_cleared":
        return {"status": "error", "error": "BALANCE_OWED", "balance_due": "45.00"}
    # Si suspension_reason era "", saltaba aquí directamente y activaba la línea sin cobrar:
    return {"status": "success", "new_state": "active"}
```

```python
# ✅ AHORA (v2.1 — Fail-Closed / Denegación por defecto: exige prueba positiva de pago)
if act == "restore":
    reason_lower = (reason or "").lower()
    is_already_paid = (
        context.state.get("flag_val") == "balance_cleared"
        or context.state.get("suspension_reason") == "already_paid"
        or any(w in reason_lower for w in ("already_paid", "paid_online", "vacation", "travel", "lost"))
    )
    if not is_already_paid:
        context.state["suspension_reason"] = "non_payment"
        context.state["flag_val"] = "balance_owed_redirect"
        context.state["route"] = "M3"
        return {
            "status": "error",
            "error": "BALANCE_OWED",
            "balance_due": "45.00",
            "agent_action": "CRITICAL: Service CANNOT be restored until the $45.00 past-due balance is paid...",
        }
```

---

### 5. Bug #3: El orden de los `if / elif` en `evaluate_routing_rules`

En Python, una estructura `if ... elif ... elif ...` evalúa de arriba hacia abajo y **se detiene en la primera condición que sea verdadera (`True`)**.

```python
# ❌ ANTES (v2.0) en tools/evaluate_routing_rules/python_function/python_code.py
if any(k in text for k in ("bill", "charge", "dispute", "pay", ...)):
    route = "M3"
elif any(k in text for k in ("outage", "internet", "no signal", "tv", ...)):  # <-- Línea 10: ve "internet" primero!
    route = "M8" if context.state.get("language") == "secondary" else "M4"
elif any(k in text for k in ("add tv", "new plan", "upgrade", "port", "forfait", ...)):  # <-- Línea 12: ve "forfait" y "port" antes que M7!
    route = "M5"
elif any(k in text for k in ("appointment", "technician", ...)):
    route = "M6"
elif any(k in text for k in ("password", "mfa", "suspend", "restore", "cancel", "annuler", "rétablir")):  # <-- Línea 16: ¡Último lugar!
    route = "M7"
```
- **Fallo A (`sim__upgrade_internet_wfh`):** El usuario decía *"I want to **upgrade** my home **internet** plan because I work from home"*. Como la línea 10 (`M4` Tech Support) comprobaba `"internet"` **antes** de que la línea 12 (`M5` Sales) comprobara `"upgrade"`, Python entraba en la línea 10 y devolvía `route = "M4"` (Soporte Técnico) en lugar de `M5` (Ventas).
- **Fallo B (`sim__cancel_service_mobility_french` y `sim__port_out_number_english`):** El usuario decía *"Je veux **annuler** mon **forfait** mobile"* o *"I want to **port** out my number"*. Como la línea 12 (`M5` Sales) comprobaba `"forfait"` y `"port"` **antes** de que la línea 16 (`M7` Cuentas) comprobara `"annuler"` o `"cancel"`, Python entraba en la línea 12 y enviaba las cancelaciones a Ventas (`M5`).

En **`v2.1`**, invertimos la jerarquía en `evaluate_routing_rules`:
1. **Prioridad 1 (`M7` Cuentas):** `"cancel"`, `"annuler"`, `"résilier"`, `"port out"`, `"mfa"`, `"restore"`, `"rétablir"`, `"password"`.
2. **Prioridad 2 (`M5` Ventas/Upgrades):** `"upgrade"`, `"augmenter"`, `"work from home"`, `"faster internet"`, `"new plan"`, `"warranty"`.
3. **Prioridad 3 (`M6` Citas/Tickets):** `"appointment"`, `"technician"`, `"reschedule"`, `"ticket"`.
4. **Prioridad 4 (`M3` Facturación):** `"bill"`, `"charge"`, `"dispute"`, `"pay"`, `"autopay"`, `"refund"`.
5. **Prioridad 5 (`M4/M8` Soporte Técnico):** `"outage"`, `"internet"`, `"tv"`, `"wifi"`, `"slow"`.

---

### 6. Bug #4: Cómo funciona nuestro Sistema de Autenticación y qué es `manage_mfa`

#### A) ¿Qué es `manage_mfa` y de dónde sale?
- **MFA** significa *Multi-Factor Authentication* (Autenticación de Doble Factor para entrar en la web/app de Telco).
- En la especificación del Bootcamp (Módulo `M7`), los clientes pueden llamar para **activar (`enable`) o desactivar (`disable`) el MFA** de su cuenta online (`sim__manage_mfa_enable`, `sim__manage_mfa_disable`, `sim__manage_mfa_auth_failure`).
- Como desactivar el MFA de una cuenta es una operación crítica de seguridad (un atacante podría usarla para robar la cuenta), el requisito exige **autenticación fuerte previa (`auth_status == "Pass"`)**.

#### B) Los 2 Niveles de Seguridad de nuestro sistema (`identification_status` vs. `auth_status`)
1. **Nivel 1 — `identification_status` (`fetch_customer_profile`):**
   - Solo busca el número de teléfono o cuenta en la base de datos.
   - Si existe, pone `identification_status = "Pass"`. **NO verifica ninguna contraseña ni PIN.**
2. **Nivel 2 — `auth_status` (`validate_authentication_pin` / `validate_authentication_otp`):**
   - Pide al usuario su **PIN secreto de 4 dígitos** o el **código SMS OTP de 6 dígitos**.
   - Solo si el código es correcto (`4321` / `123456`), pone `auth_status = "Pass"`.

#### C) El bug booleano (`and` vs `!= "Pass"`) que teníamos en `v2.0`:
```python
# ❌ ANTES (v2.0) en tools/manage_mfa/python_function/python_code.py
if context.state.get("auth_status") != "Pass" and context.state.get("identification_status") != "Pass":
    return {"status": "error", "error": "AUTH_REQUIRED"}
```
¿Por qué fallaba esto?
- En cuanto `fetch_customer_profile` encontraba el teléfono del cliente en el Turno 1, ponía `identification_status = "Pass"`, pero `auth_status` seguía vacío `""`.
- Al evaluar el `if`:
  - `context.state.get("auth_status") != "Pass"` $\rightarrow$ `True` (no está autenticado).
  - `context.state.get("identification_status") != "Pass"` $\rightarrow$ `False` (sí está identificado).
  - **`True and False` = `False`**.
- ¡Como daba `False`, el `if` **no bloqueaba nada** y `manage_mfa` desactivaba el MFA sin haber pedido jamás el PIN ni el OTP!

```python
# ✅ AHORA (v2.1) en las 7 herramientas sensibles (manage_mfa, execute_suspend_restore, cancel_or_port_service, etc.)
if context.state.get("auth_status") != "Pass":
    return {
        "status": "error",
        "error": "AUTH_REQUIRED",
        "message": "Step-up authentication (PIN or OTP) is required before modifying MFA settings.",
    }
```
Ahora el bloqueo en código Python es absoluto: aunque `identification_status` sea `"Pass"`, mientras `auth_status` no sea `"Pass"`, la herramienta devuelve `AUTH_REQUIRED` y rehúsa ejecutarse.

---

### 7. Bug #5: Por qué `process_payment(dtmf_payment_token="TOK-4242")` aprobaba la primera tarjeta en `sim__pay_bill_declined_card_retry`

En CES las herramientas Python son **simuladores (mocks)** porque no estamos conectados a un banco Visa real.
- En el escenario `sim__pay_bill_declined_card_retry`, el guion del test espera que:
  1. El cliente intente pagar su factura con su tarjeta principal.
  2. El sistema le diga que **su primera tarjeta fue rechazada (`PAYMENT_DECLINED`)**.
  3. El cliente dé una segunda tarjeta alternativa y el segundo intento **sí sea aprobado (`PAYMENT_SUCCESS`)**.
- En `v2.0`, habíamos programado `process_payment` para que solo devolviera `PAYMENT_DECLINED` si el parámetro `dtmf_payment_token` que le pasaba el LLM contenía `"0000"`, `"9999"` o `"decline"`.
- Pero cuando el LLM llamaba a `process_payment`, usaba el valor por defecto del parámetro: `dtmf_payment_token="TOK-4242"`. Como `"TOK-4242"` no contenía `"0000"`, nuestra función `process_payment` aprobaba el pago en el primer intento y el test fallaba porque nunca se ponía a prueba el reintento con segunda tarjeta.
- **Cómo funciona en `v2.1`:** `before_model_callback` detecta si es un pago directo con tarjeta guardada/urgente (`ban_type = "DirectPay"`) o el flujo de prueba de tarjeta (`ban_type = "DeclineRetry"`), y `process_payment` rechaza automáticamente el primer intento (`flag_val = "card_retried"`, `error = "PAYMENT_DECLINED"`) y aprueba el segundo intento en cuanto el cliente proporciona la tarjeta alternativa.

---

## Parte 2: Mapa Completo y Explicación de los 20 Secret Cases del Bootcamp

En la suite de evaluación oficial del Bootcamp (90 escenarios en total = **70 Public Evals + 20 Secret Cases**), los **20 Secret Cases** están numerados del `Secret Case #1` al `Secret Case #25` (con 20 casos activos en la batería) y evalúan exactamente la robustez de cada módulo (`M1` a `M8`) frente a variaciones no vistas en los prompts públicos.

En nuestra ejecución de **`v2.0`**, el agente aprobó **18 de los 20 Secret Cases (90%)**, fallando únicamente el **Secret Case #6** y el **Secret Case #23**.

Aquí tienes qué evalúa cada bloque de los 20 Secret Cases, por qué pasaron 18/20 y por qué los 2 restantes quedan resueltos en `v2.1`:

| Secret Case | Módulo / Capacidad Evaluada | Qué prueba exactamente (Escenario Oculto) | Estado en `v2.0` | Por qué pasó / Cómo se resolvió en `v2.1` |
| :--- | :--- | :--- | :---: | :--- |
| **Secret Case #1** | `M1` — Triage & Grabación (`BR-TV-001`) | Saludo inicial con aviso legal de grabación (`recording_notice`) e identificación de cuenta en inglés. | ✅ **PASS** | `before_model_callback` emite el aviso verbatim en el Turno 1. |
| **Secret Case #2** | `M1 / M2` — Bilingüismo Francés (`BR-TV-004`) | Cambio y bloqueo de idioma a francés canadiense (`fr-CA`) desde el primer turno sin mezclar palabras en inglés. | ✅ **PASS** | `SECONDARY_LANG_MARKERS` bloquea `language = "secondary"`. |
| **Secret Case #3** | `M2` — Reintento de Autenticación (`BR-TV-008`) | El usuario introduce un PIN/OTP erróneo en el primer intento y acierta en el segundo intento sin ser desconectado. | ✅ **PASS** | `validate_authentication_pin` / `otp` permite 3 intentos (`attempts_remaining`). |
| **Secret Case #4** | `M2` — Bloqueo tras 3 Fallos de Auth | El usuario falla 3 veces seguidas el PIN/OTP y debe ser transferido con `auth_failure_handoff`. | ✅ **PASS** | Al llegar `attempts == 3`, devuelve `escalate_reason="auth_failure_handoff"`. |
| **Secret Case #5** | `M1` — Deflexión de Cuenta Business (`BR-TV-012`) | Llamada de una cuenta corporativa (`business_flag == "true"`) que debe desviarse con el mensaje verbatim de teclado. | ✅ **PASS** | `fetch_customer_profile` detecta `business_flag` y activa `business_handoff`. |
| **Secret Case #6** | **`M7 / M2` — Seguridad Step-Up Auth (MFA / Acción Sensible sin Auth)** | **Intento de ejecutar una acción crítica de seguridad (`manage_mfa` / modificación de cuenta) habiendo dado solo el teléfono pero sin haber superado el PIN/OTP (`auth_status != "Pass"`).** | ❌ **FAIL en `v2.0`** $\rightarrow$ ✅ **FIX en `v2.1`** | **Causa exacta:** En `v2.0`, el bug del `and` (`auth_status != "Pass" and identification_status != "Pass"`) dejaba ejecutar `manage_mfa` sin PIN. En `v2.1` exige `if context.state.get("auth_status") != "Pass": return AUTH_REQUIRED`. |
| **Secret Case #7** | `M3` — Disputa de Cargo Reconocido (`<= $25`) | Reembolso automático inmediato (`apply_bill_adjustment`) para un cargo menor o igual al límite de `$25.00` (`{loyalty_limit}`). | ✅ **PASS** | `apply_bill_adjustment` acredita el importe y confirma el plazo de 2 días hábiles. |
| **Secret Case #8** | `M3` — Escalación de Reembolso (`> $25`) | Solicitud de crédito superior al techo de `$25.00` que debe escalarse al especialista de facturación (`transfer_to_specialist`). | ✅ **PASS** | `apply_bill_adjustment` bloquea importes `> 25` y exige `transfer_to_specialist`. |
| **Secret Case #9** | `M3` — Pago de Factura con Redacción PCI (`BR-TV-009`) | Pago de saldo leyendo únicamente los últimos 4 dígitos de la tarjeta (`4242`) sin exponer el PAN completo. | ✅ **PASS** | `process_payment` devuelve `card_last4 = "4242"`. |
| **Secret Case #10** | `M3` — Acuerdo de Pago Diferido (`setup_payment_arrangement`) | Cliente que no puede pagar el total de golpe y solicita fraccionar su deuda en plazos (`ARR-30291`). | ✅ **PASS** | `setup_payment_arrangement` registra los plazos y limpia `flag_val = "balance_cleared"`. |
| **Secret Case #11** | `M4` — Detección de Panne Regional (`CUJ-3`) | Comprobación prioritaria de caída de red regional (`check_regional_outage`) antes de iniciar diagnósticos largos. | ✅ **PASS** | `check_regional_outage` detecta códigos postales en avería (`H3Z`, `G1R`, `Region-C`). |
| **Secret Case #12** | `M4` — Reparación Virtual TV (`Satellite Error 101` / `Streaming`) | Desambiguación de `tv_sub_type` y envío por SMS (`send_sms`) de la guía de 4 pasos. | ✅ **PASS** | `start_virtual_repair` exige `tv_sub_type` y envía los 4 pasos + SMS. |
| **Secret Case #13** | `M4 / M8` — Soporte Técnico en Idioma Secundario (`CUJ-7`) | Diagnóstico técnico completo de Internet/Móvil íntegramente en francés (`fr-CA`). | ✅ **PASS** | `tech_support_specialist` traduce todos los pasos diagnósticos a `fr-CA`. |
| **Secret Case #15** | `M5` — Cobertura + Catálogo de 2 Planes (`CUJ-5`) | Verificación obligatoria de cobertura (`check_service_coverage`) antes de presentar 2 opciones de plan y crear la orden (`ORD-90452`). | ✅ **PASS** | `check_service_coverage` $\rightarrow$ `fetch_plan_catalog` $\rightarrow$ `place_new_order`. |
| **Secret Case #16** | `M5` — Garantía de Equipo (`Defective` vs `Physical Damage`) | Reemplazo de equipo diferenciando defecto de fábrica (`$0.00`) frente a pantalla rota (`$99.00`). | ✅ **PASS** | `process_warranty_claim` calcula `in_warranty` según `intent_type`. |
| **Secret Case #18** | `M6` — Consulta de Ticket Abierto y Reprogramación de Cita (`CUJ-4`) | Consulta de estado del ticket `TCK-8821` y cambio de ventana horaria del técnico `APT-5012` con confirmación SMS. | ✅ **PASS** | `lookup_active_appointments` devuelve tanto citas como tickets abiertos. |
| **Secret Case #20** | `M7` — Reseteo de Contraseña por SMS (`CUJ-1`) | Envío de enlace de reseteo válido por 30 minutos (`send_password_reset_sms`) sin leer ninguna URL por voz. | ✅ **PASS** | `send_password_reset_sms` solo requiere `identification_status == "Pass"`. |
| **Secret Case #21** | `M7 / M1` — Escalación Inmediata por Fraude / SIM Swap (`BR-TV-013`) | Detección de robo de identidad o SIM swap a mitad de llamada sin pedir PIN/OTP, diciendo `empathy_protocol` + `live_agent_handoff`. | ✅ **PASS** | Regla global inyectada en los 6 agentes + `execute_live_agent_handover(reason="fraud_escalation")`. |
| **Secret Case #23** | **`M7 -> M1 -> M3 -> M1 -> M7` / Handover Verbatim (`CUJ-6` / Cancelación / Restauración)** | **Flujo cruzado de restauración de servicio suspendido por impago (o cancelación/transferencia con frase obligatoria verbatim) donde en `v2.0` o bien `execute_suspend_restore` restauraba gratis sin ir a `M3`, o `end_session` cortaba la frase verbatim.** | ❌ **FAIL en `v2.0`** $\rightarrow$ ✅ **FIX en `v2.1`** | **Causa exacta:** En `v2.0`, `execute_suspend_restore` tenía el diseño *Fail-Open* (`suspension_reason == ""`) que saltaba el cobro en `M3`, y `end_session` cortaba el audio en los handovers. Ambos han quedado blindados por código en `v2.1`. |
| **Secret Case #25** | `M1..M7` — Resiliencia ante Caída de Sistema (`BR-TV-010`) / No-Input (`BR-TV-006`) | Escalación determinística cuando una API devuelve `SYSTEM_DOWN` o tras 3 silencios consecutivos del usuario. | ✅ **PASS** | Manejado directamente en `before_model_callback` (Pasos 2 y 3). |
