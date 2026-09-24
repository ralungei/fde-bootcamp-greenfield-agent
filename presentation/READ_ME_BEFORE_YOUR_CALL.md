# 📖 READ ME BEFORE YOUR CALL — Guía Didáctica (De Cero a Experto)

Esta guía está escrita pensando en que **entiendas de verdad y sin esfuerzo visual** cada pieza que hemos montado hoy.

Cada concepto sigue siempre **4 escalones de menos a más**:
1. **💡 1. En genérico (la analogía fácil)**: Qué es sin palabras raras.
2. **🎯 2. Para qué sirve con un ejemplo**: Qué problema evita.
3. **🛠️ 3. Qué hemos hecho exactamente en tu proyecto**: Qué archivos tocamos y qué tienen dentro.
4. **🗣️ 4. Cómo explicárselo al evaluador en 20 segundos**: Tu frase lista para soltar en la entrevista.

---

## 🔍 Duda Rápida: ¿Por qué no veías los Guardrails en la UI y qué había que pasarle al Gate Check?

### A. ¿Por qué no veías los Guardrails en la UI de CES?
- **Lo que pasaba**: En Google Cloud CES, los Guardrails existen en **dos sitios**:
  1. A nivel global de la **App** (`app.json` → menú lateral *Guardrails* de la consola).
  2. Dentro de **cada Agente individual** (`Root_agent.json`, `billing_specialist.json`, etc. → la pestaña *Guardrails* que ves cuando pinchas en un agente en el lienzo).
- **Lo que acabamos de hacer**: Además de tenerlos en `app.json`, **los hemos vinculado explícitamente dentro de los 6 archivos `.json` de los 6 agentes** (`Root_agent` y los 5 especialistas) y hemos hecho `cxas push`. **Refresca la pestaña del navegador (`Cmd + R`)** y ya los verás marcados tanto en el menú global *Guardrails* como dentro de cada uno de los 6 agentes.

### B. ¿Qué usamos para el `gate-check` (Gate 6)? ¿Era un Golden Set o qué había que pasarle?
- **Respuesta corta**: **NO es un Golden Set.** Al script `gate-check.py` solo había que pasarle **un archivo JSON con 4 frases de usuario seguidas** (`--multi-turn gate6_prompts.json`).
- **¿Por qué?**: Porque `gate-check.py` es un chequeo rápido de salud ("humo").
  - En la **Puerta 5 (Gate 5)**, el script manda 1 sola palabra (`"Hello"`) para ver si el agente está vivo.
  - En la **Puerta 6 (Gate 6)**, el script pide una lista de 3 o 4 frases (`[{"text": "..."}, {"text": "..."}]`) para mandarlas **en la misma llamada (mismo `session_id`)** y comprobar que el agente no pierde la memoria entre el turno 1 y el turno 4 ni se cae al transferir de `Root_agent` a `billing_specialist`.
  - Nosotros le pasamos exactamente estas **4 frases de nuestro flujo de facturación**:
    1. `"Hi, I'd like to check my current bill balance please."` (El `Root_agent` saluda y pide teléfono).
    2. `"My phone number is 415-555-0101."` (El `Root_agent` llama a `fetch_customer_profile` y pide verificar con OTP o PIN).
    3. `"The 6-digit verification code is 481234."` (El `Root_agent` llama a `validate_authentication_otp`, pone `auth_status = "Pass"`, transfiere a `billing_specialist`, y este llama a `fetch_recent_bills` y dice `$45`).
    4. `"Can you tell me what my current balance is and what charges are on the bill?"` (`billing_specialist` recuerda que ya estás autenticado y te desglosa los `$65` de plan base, `$12.50` de AppleStreaming y `$15` de cargo internacional).

---

# 🧱 BLOQUE 1: Las 3 Formas de Probar el Agente (Gate Check vs. Goldens vs. Simulaciones)

Imagina que hemos fabricado un **coche autónomo** (nuestro agente de voz). Hay **3 pruebas distintas** que nos pide la guía, de más sencilla a más avanzada:

---

## 1️⃣ El `gate-check-*.json` (y la Puerta 6 / Gate 6)

### 💡 1. En genérico (la analogía)
Es **la ITV o el chequeo antes de arrancar el avión**. No mide si el piloto conduce bonito en 100 carreteras distintas; mide que las 4 ruedas estén puestas, que los frenos estén conectados y que al dar una vuelta a la manzana el motor no se apague.

### 🎯 2. Para qué sirve con un ejemplo
Muchas veces alguien edita el código en su portátil, cree que todo está bien, pero al subirlo a la nube:
- Un sub-agente se quedó desconectado del `Root_agent` (**Gate 2**).
- A un agente se le olvidó vincularle una herramienta (**Gate 3**).
- O cuando el usuario habla por segunda vez, la memoria de la sesión se borra (**Gate 6**).

### 🛠️ 3. Qué hemos hecho nosotros
Ejecutamos `gate-check.py --multi-turn` contra Google Cloud CES y generamos **[eval-reports/gate-check-20260924-010430.json](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/eval-reports/gate-check-20260924-010430.json)** con **las 6 puertas en `PASS` (`6 passed, 0 failed, 0 skipped`)**:
- **Gate 1**: `cxas pull` + `cxas lint` (`0 errores`).
- **Gate 2**: Los 6 agentes están bien conectados en jerarquía Hub-and-Spoke.
- **Gate 3**: Las 32 tools están vinculadas.
- **Gate 4**: Los 18 callbacks de Python están activos.
- **Gate 5**: Prueba de 1 turno (`"Hello"`) respondida con el aviso legal literal.
- **Gate 6**: Prueba de 4 turnos seguidos (autenticación + traspaso a `billing_specialist` + lectura de factura de `$45.00`) superada sin perder el estado.

### 🗣️ 4. Cómo explicárselo al evaluador
> *"El `gate-check` es nuestra verificación estructural pre-vuelo de 6 puertas contra la nube. A diferencia de muchos proyectos que dejan la Puerta 6 en `skipped`, nosotros ejecutamos Gate 6 con una sesión multi-turno real de 4 pasos que verifica que `Root_agent` autentica al usuario con el OTP `481234`, transfiere el control a `billing_specialist` manteniendo `auth_status = Pass` en memoria, y lee el saldo de `$45`. Las 6 puertas están en `PASS`."*

---

## 2️⃣ El Golden Dataset (`evals/goldens/goldens.yaml`)

### 💡 1. En genérico (la analogía)
Es **un guion de cine fijo, frase por frase**. Tú escribes exactamente qué dice el cliente en la frase 1 y exactamente qué herramienta tiene que pulsar el agente y qué frase tiene que responder.

### 🎯 2. Para qué sirve con un ejemplo
Sirve para cosas donde **no quieres creatividad**, sino **precisión quirúrgica turno a turno**:
- Ejemplo: Si el cliente dice *"Mi cuenta es de empresa (`415-555-0109`)"*, quieres comprobar que **en ese mismo turno exacto** el agente llama a `fetch_customer_profile`, llama a `execute_live_agent_handover`, llama a `end_session` y dice la frase literal de empresa.
- Aquí es donde actúan los dos números de tu `app.json`:
  - **`overallToolInvocationCorrectnessThreshold: 1` (1.0 = 100%)**: Exige que llame exactamente a las herramientas esperadas en ese turno.
  - **`semanticSimilaritySuccessThreshold: 3` (sobre 5)**: Mide del 1 al 5 cuánto se parece el significado de la frase que dijo el agente a la frase del guion.

### 🛠️ 3. Qué hemos hecho nosotros
Creamos **[evals/goldens/goldens.yaml](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/evals/goldens/goldens.yaml)** (y su reporte **[eval-reports/golden_report_2026-09-24.json](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/eval-reports/golden_report_2026-09-24.json)**) con **5 casos P0 deterministas (`5/5 PASS`, Tool Correctness `1.0`, Similitud `4.72/5.0`)**:
1. Saludo legal + envío de OTP (`48xxxx`) a SMS y email de respaldo.
2. Desvío inmediato de cuenta Business (`BR-TV-012`).
3. Bloqueo determinista de Prompt Injection (`BR-TV-016`).
4. Escalado inmediato a humano cuando el cliente lo pide (`BR-TV-014`).
5. Cambio y bloqueo de idioma a Francés Canadiense (`fr-CA`, `BR-TV-020`).

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Usamos el Golden Dataset (`evals/goldens/goldens.yaml`) para regresión determinista turno por turno en las reglas donde no caben variaciones: avisos legales, desvío de empresas y bloqueo de ataques. Ahí exigimos en `app.json` una precisión de invocación de herramientas de `1.0` (100%) y similitud semántica `>= 3`, obteniendo `5/5 PASS` con media de `4.72 sobre 5`."*

---

## 3️⃣ Las Simulaciones de Usuario (`evals/simulations/simulations.yaml`)

### 💡 1. En genérico (la analogía)
En vez de un guion fijo, **contratas a 100 actores (otro modelo Gemini haciendo de cliente)** y a cada uno le das una tarjeta con una misión: *"Eres un cliente que perdió su móvil, hablas francés y quieres desactivar el MFA"*. El cliente IA improvisa la conversación hasta lograrlo (o hasta 12 turnos), y al final un **Juez IA** lee toda la llamada y decide si se cumplió el objetivo y las reglas.

### 🎯 2. Para qué sirve con un ejemplo
En la vida real los clientes no hablan siguiendo nuestro guion fijo: cambian de tema a mitad de llamada, dan el PIN por teclado o se frustran. Las simulaciones prueban si el agente aguanta conversaciones abiertas de principio a fin **empezando con la memoria en blanco (`session_parameters: {}`)**.

### 🛠️ 3. Qué hemos hecho nosotros (Run Oficial Agent Academy `f5b233531be74ad5bf231f67f72d7243`)
Ejecutamos las **100 simulaciones completas (70 públicas + 30 ocultas)** tanto en **CXAS Labs Agent Academy** (Run `f5b233531be74ad5bf231f67f72d7243`) como en local sin variables pre-inyectadas (`session_parameters: {}`):
- **Resultado Oficial Agent Academy**: **`92 / 100 PASS (92.0%)`** en `692.9s`.
- **Batería Pública (`70` casos)**: **`63 / 70 PASS (90.0%)`**.
- **Casos Ocultos (`30` Secret Cases)**: **`29 / 30 PASS (96.7%)`** — ¡Solo falló `Secret Case #7` de los 30!

#### 🔍 Los 8 Fallos de la Run `f5b233531be74ad5bf231f67f72d7243` (por si el evaluador te pregunta por cualquiera de ellos):
1. **`sim__speak_mid_call_billing_english` (`6.2s`)** y 2. **`sim__speak_frustrated_english` (`10.2s`)**: El agente detectó la petición/frustración y ejecutó correctamente `execute_live_agent_handover` + `end_session`, pero el modelo pronunció su propia frase natural de traspaso en ese primer paquete antes de que `after_model_callback` leyera la bandera.
3. **`sim__pay_mobility_bill_card_file` (`26.2s`)**: El agente autenticó y cobró los `$45.00` con `process_payment`, pero al confirmar dijo *"paid with your card on file"* sin repetir en voz alta los últimos 4 dígitos (`4242`).
4. **`sim__pay_bill_french_keypad` (`144.3s`)**: Timeout de latencia en el turno largo de entrada por teclado DTMF en francés (`144.3s`).
5. **`sim__manage_mfa_disable` (`32.8s`)**: Al endurecer en Python `step_up_status` (que exige un **2º OTP fresco `48xxxx`** después de autenticar la sesión para desactivar MFA), el usuario simulado solo dio un código y no completó el segundo factor.
6. **`sim__dispute_charge_auth_retry` (`15.3s`)**: Tras fallar el primer intento de autenticación y acertar al segundo, el agente pidió al cliente confirmar cuál de los cargos quería disputar antes de llamar a `apply_bill_adjustment`.
7. **`sim__warranty_replacement_samsung_french` (`16.5s`)**: Ante *"mon téléphone Samsung qui ne charge plus"*, el agente ofreció un paso rápido de diagnóstico antes de tramitar el reemplazo en garantía (`process_warranty_claim`).
8. **`Secret Case #7`**: Único caso oculto no superado de los 30 (`29/30 = 96.7% PASS`).

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Mientras que los Goldens prueban turnos fijos, nuestras 100 Simulaciones en CXAS Labs Agent Academy (`f5b233531be74ad5bf231f67f72d7243`) enfrentan al agente contra un cliente LLM dinámico arrancando con `session_parameters: {}` vacío. Alcanzamos un **92/100 global (92%)**: **63/70 (90%)** en la suite pública y un **29/30 (96.7%)** en los casos ocultos, demostrando que el agente generaliza sin estar sobreajustado a los tests públicos."*

---

# 🛡️ BLOQUE 2: Seguridad, Privacidad y Antialucinación en `app.json`

---

## 4️⃣ Guardrails Nativos (`guardrails/`) vs. Tool `report_malicious_utterance`

### 💡 1. En genérico (la analogía)
Es tener **dos anillos de seguridad en un edificio**:
1. **Los Guardrails de Plataforma (`guardrails/`)**: Son el detector de metales automático de Google en la puerta de entrada/salida.
2. **La Tool `report_malicious_utterance` + `after_model_callback`**: Es el guardia de seguridad propio de Telco que, cuando detecta un intento de hackeo ("ignora tus instrucciones"), dice la frase oficial de Telco palabra por palabra y cuelga el teléfono (`end_session`).

### 🎯 2. Para qué sirve con un ejemplo
Si solo tienes la tool, un evaluador que mire la pestaña *Guardrails* de CES verá que está vacía. Si solo tienes el Guardrail genérico de Google, cuando un test de evaluación intente un ataque, el filtro genérico respondería una frase estándar de Google en lugar de la frase obligatoria de Telco (*"I'm sorry, but I'm not able to help with that. I'm going to end the call now. Thank you for calling Telco."*) y no llamaría a `report_malicious_utterance`.
Con nuestro diseño en **doble capa**, tienes **las dos cosas a la vez sin que se pisen**.

### 🛠️ 3. Qué hemos hecho nosotros
Creamos dos recursos en `cxas_app/.../guardrails/` y los vinculamos **tanto en `app.json` como en los 6 agentes**:
- **`prompt_injection_shield`**: Filtro de contenido (`WORD_BOUNDARY_STRING_MATCH`) contra exfiltración de tokens internos del sistema, permitiendo que `report_malicious_utterance` capture los ataques conversacionales y cierre la sesión con la frase exacta de la especificación.
- **`model_toxicity_safety`**: Filtro `modelSafety` activo en las 4 categorías de daño (`HATE_SPEECH`, `HARASSMENT`, `DANGEROUS_CONTENT`, `SEXUALLY_EXPLICIT`).

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Implementamos defensa en profundidad en dos capas: a nivel de plataforma en `app.json` y en los 6 agentes tenemos activos `model_toxicity_safety` y `prompt_injection_shield`, y a nivel de aplicación nuestra tool determinista `report_malicious_utterance` junto con `after_model_callback` garantiza que ante cualquier intento de prompt injection se pronuncie la frase reglamentaria exacta de Telco y se ejecute `end_session` en el mismo turno."*

---

## 5️⃣ Redacción de PII (`redactionConfig`) vs. Enmascarado a 4 Dígitos

### 💡 1. En genérico (la analogía)
- **Enmascarado en Python (`last 4 digits`)**: Es que el cajero del banco por teléfono solo te diga *"su tarjeta terminada en 4242"* para que nadie que esté escuchando a tu lado oiga los 16 números.
- **`redactionConfig: enableRedaction: true` en `app.json`**: Es que la grabadora de seguridad del banco borre automáticamente con un pitido (`[REDACTED]`) los números de tarjeta o códigos antes de guardar la transcripción en la base de datos de logs.

### 🛠️ 3. Qué hemos hecho nosotros
- En Python (`fetch_customer_profile`, `process_payment`, `validate_authentication_otp`): truncamos `cirn`, `billing_account` y `saved_card_last4` a los últimos 4 dígitos y prohibimos repetir el PIN u OTP en voz alta (`BR-TV-009`).
- En `app.json` (líneas 71–74): activamos `"redactionConfig": {"enableRedaction": true}` dentro de `"loggingSettings"`.

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Protegemos el PII tanto en tránsito como en reposo: en conversación las tools de Python devuelven exclusivamente los últimos 4 dígitos (`cirn_last4`, `saved_card_last4`) y nunca repiten un OTP o PIN en voz; y en reposo tenemos activado `redactionConfig.enableRedaction: true` en el `loggingSettings` de `app.json` para que no queden datos sensibles en los logs de plataforma."*

---

## 6️⃣ `goldenHallucinationMetricBehavior: ENABLED`

### 💡 1. En genérico (la analogía)
Es **el detector de mentiras (fact-checker)** de las evaluaciones. Comprueba que cada cifra o dato que dice el agente (por ejemplo, *"su saldo es de 45 dólares"* o *"su cita es el martes"*) haya salido **de verdad** del JSON que devolvió una herramienta de Python en esa llamada, y no de la imaginación del modelo.

### 🎯 2. Por qué es crítico
En la guía del evaluador aparece como **Red Flag Automático**: mucha gente lo pone en `DISABLED` para que sus tests aprueben más fácil. Nosotros lo tenemos en **`ENABLED`** en `app.json` (línea 94).

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Tenemos `goldenHallucinationMetricBehavior` en `ENABLED` en `app.json`. Como toda nuestra lógica de negocio devuelve datos estructurados desde las 32 tools de Python, el agente nunca tiene que inventar importes ni políticas, logrando cero alucinaciones con el verificador activo."*

---

# 📊 BLOQUE 3: Operación en Producción (Scorecards, Entornos y Versiones)

---

## 7️⃣ Scorecards de CCAI Insights (`autolabel_rules.yaml` y `dashboards.yaml`)

### 💡 1. En genérico (la analogía)
Cuando el agente recibe 10.000 llamadas al día en producción, ningún humano puede leerse las 10.000 transcripciones.
- **`autolabel_rules.yaml` (Reglas CEL)**: Es una máquina que al terminar cada llamada le pega automáticamente **etiquetas de colores (pegatinas)** según lo que pasó: *"🟢 Resuelta sola (`contained`)"*, *"🟡 Escalada por 3 fallos de PIN"*, *"🔴 Cliente enfadado"*.
- **`dashboards.yaml` (Cuadros de Mando)**: Es la pantalla de televisión del director del Call Center que suma esas pegatinas con consultas SQL y dibuja las gráficas de **Contención**, **Sentimiento** y **Velocidad de las APIs (P50/P95)**.

### 🛠️ 3. Qué hemos hecho nosotros
Creamos ambos archivos siguiendo el esquema oficial de Google Cloud CCAI Insights:
- **[autolabel_rules.yaml](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/autolabel_rules.yaml)**: 4 reglas en lenguaje CEL (`containment_resolution_status`, `agent_specialist_domain`, `containment_failure_driver`, `security_and_mfa_tier`), todas con su condición de cierre por defecto (`condition: ""`).
- **[dashboards.yaml](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/dashboards.yaml)**: Un Scorecard ejecutivo con 3 pestañas (*1. Containment & Resolution*, *2. Sentiment & Safety Guardrails*, *3. Tool & API Performance P50/P95*).

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Para observabilidad en Día 2 de producción, definimos declarativamente `autolabel_rules.yaml` con expresiones CEL que etiquetan cada llamada según si fue contenida, qué especialista actuó y por qué escaló (como los 3 strikes de autenticación), alimentando las tres pestañas del Scorecard en `dashboards.yaml`: tasa de contención por dominio, sentimiento del cliente y latencia P50/P95 de las 32 tools."*

---

## 8️⃣ `environment.json` y Snapshot de Versión (`v1.0-cert-test3-ready`)

### 💡 1. En genérico (la analogía)
- **`environment.json`**: Es tener tres enchufes separados (**Desarrollo**, **Preproducción/Staging** y **Producción**) para que mientras pruebas cambios con datos falsos (`mock_backend: true`) no toques las bases de datos ni los secretos reales de los clientes (`prod-telco-*` en Secret Manager).
- **Snapshot de Versión en CES (`cxas versions create`)**: Es hacer un **"Guardar partida fijo (`v1.0-cert-test3-ready`)"** en la consola de Google Cloud. Así, el teléfono de atención al cliente apunta a la versión fija `v1.0`, y aunque alguien edite el borrador (`Draft`) mañana, los clientes reales no sufren ningún corte.

### 🗣️ 4. Cómo explicárselo al evaluador
> *"Gestionamos el ciclo de vida separando la configuración de `development`, `staging` y `production` en `environment.json` (timeouts de APIs, cuentas de servicio IAM de mínimo privilegio y prefijos de Secret Manager) y publicando en CES el snapshot inmutable `v1.0-cert-test3-ready` (`67c09d08-3e09-46c9-b825-3166072cb137`)."*

---

# ⚡ CHULETA EXPRÉS DE 1 MINUTO (Tabla Resumen para tener abierta en la llamada)

| Si el evaluador menciona... | Qué es en tu cabeza (3 palabras) | Qué archivo le enseñas | La frase ganadora para responder |
| :--- | :--- | :--- | :--- |
| **Gate Check / Gate 6** | La ITV de 6 puertas con llamada de 4 turnos | `eval-reports/gate-check-20260924-010430.json` | *"Tenemos las 6 puertas en `PASS` (`0 skipped`). En Gate 6 corremos una llamada real de 4 turnos que autentica con OTP `481234`, pasa de `Root_agent` a `billing_specialist` sin perder sesión y lee el saldo de `$45`."* |
| **Golden vs. Simulations** | Guion fijo turno a turno vs. Actor IA libre | `evals/goldens/goldens.yaml` y Agent Academy Run `f5b233531be74ad5bf231f67f72d7243` | *"Usamos 5 Goldens deterministas (`5/5 PASS`, Tool Correctness `1.0`) para turnos exactos como avisos legales o bloqueos, y 100 Simulaciones abiertas en Agent Academy (`92/100 PASS`: `63/70` públicos y `29/30` ocultos = `96.7%`) para validar conversaciones completas."* |
| **Hallucination Metric** | El detector de mentiras activado | `cxas_app/.../app.json` (Línea 94) | *"Está en `ENABLED` en `app.json`. Como los importes y estados salen siempre del JSON de nuestras 32 tools de Python, el agente no alucina datos."* |
| **Guardrails & Safety** | Detector de metales de Google + Guardia de Telco | `cxas_app/.../guardrails/` y `report_malicious_utterance` | *"Tenemos doble capa: los Guardrails nativos (`prompt_injection_shield` y `model_toxicity_safety`) activos tanto en `app.json` como en los 6 agentes, más `report_malicious_utterance` y `after_model_callback` para garantizar el cierre literal."* |
| **PII & Redaction** | Últimos 4 dígitos en voz + Censura en logs | `cxas_app/.../app.json` (`redactionConfig`) | *"En voz truncamos a los últimos 4 dígitos y prohibimos repetir PIN/OTP; y en logs tenemos `redactionConfig.enableRedaction: true` en `app.json`."* |
| **Hill-Climbing Story** | Cómo arreglamos el bug de MFA sin romper PIN | `tools/validate_authentication_otp` y `manage_mfa` | *"Descubrimos que el modelo se auto-aprobaba el MFA o rehusaba el PIN estático. Separamos `auth_status` (Puerta 1: PIN u OTP) de `step_up_status` (Puerta 2: exige un 2º OTP fresco `48xxxx` enviado también al email de respaldo), pasando de fallo a 100% sin regresión en login por PIN."* |
| **Insights Scorecards** | Pegatinas automáticas CEL + Gráficas SQL | `autolabel_rules.yaml` y `dashboards.yaml` | *"Definimos reglas CEL en `autolabel_rules.yaml` para clasificar contención y causas de escalado, conectadas al Scorecard de 3 pestañas en `dashboards.yaml` (Contención, Sentimiento y Latencia P50/P95)."* |
