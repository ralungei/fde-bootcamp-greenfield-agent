# Telco Voice Central — Decisiones de diseño y aprendizajes

> Documento de apoyo para la charla. Recoge **qué construimos**, **por qué lo construimos
> así** y, sobre todo, **qué nos enseñaron los fallos**. Los bugs son la parte interesante.

---

## 0. Glosario rápido (siglas)

| Sigla | Significado | Qué es |
| :-- | :-- | :-- |
| **GECX** | Google Customer Engagement Suite | La plataforma sobre la que corre el agente |
| **CES** | Customer Engagement Suite | El runtime que ejecuta agentes y tools |
| **CXAS** | Customer Experience Agent Studio | El SDK/CLI con el que desarrollamos en local |
| **SCRAPI** | Simple CX API | La librería Python con la que ejecutamos simulaciones |
| **MFA** | Multi-Factor Authentication | Autenticación con más de un factor |
| **OTP** | One-Time Password | Código de un solo uso, enviado por SMS |
| **PIN** | Personal Identification Number | Código permanente que el cliente fijó al alta |
| **DTMF** | Dual-Tone Multi-Frequency | Los pitidos del teclado del teléfono |
| **CUJ** | Critical User Journey | Recorrido crítico del usuario |
| **LLM** | Large Language Model | El modelo generativo |
| **IVR** | Interactive Voice Response | El clásico "pulse 1 para facturación" |

---

## 1. Qué es el agente

Un agente **de voz** para una operadora de telecomunicaciones canadiense, bilingüe
(inglés / francés canadiense), que atiende llamadas reales de clientes: facturación,
soporte técnico, ventas, citas de instalación y gestión de cuenta.

| Métrica | Valor |
| :-- | :-- |
| Sub-agentes | 6 |
| Tools | 32 |
| Callbacks | 18 |
| Modelo | `gemini-3.1-flash-live` |
| Modalidad | Audio (voz) |
| Evaluación oficial | 92/100 |
| Suite pública local | 68/70 (97,1 %) |
| Suite secreta | 30/30 (100 %) |

---

## 2. Arquitectura: por qué 6 agentes y no 1

| Agente | Responsabilidad |
| :-- | :-- |
| `Root_agent` | Saludo, identificación del intent, enrutado, despedida |
| `billing_specialist` | Facturas, pagos, reembolsos, disputas, acuerdos de pago |
| `tech_support_specialist` | Averías, reparación virtual, incidencias regionales |
| `sales_equipment_specialist` | Catálogo, altas, pedidos, garantías |
| `appointment_specialist` | Consulta y reprogramación de citas |
| `account_management_specialist` | MFA, contraseñas, portabilidad, cancelación |

**La decisión:** un único agente con 32 tools y un prompt gigante se degrada rápido. Cada
sub-agente ve solo sus tools y solo sus reglas, así que el prompt es corto y la elección de
tool es mucho más fiable.

**El coste, que es real:** cada traspaso entre agentes es una frontera donde se pierde
contexto y se gana latencia. Y la plataforma exige pronunciar una **frase de traspaso
literal** (verbatim). Eso nos costó el bug #2, el más caro de todos.

> [!IMPORTANT]
> Regla que aprendimos por las malas: **si un sub-agente puede llegar a necesitar una
> capacidad, tiene que tenerla declarada en su propio `tools`**. No se hereda del padre.
> Ni siquiera `end_session`.

---

## 3. Los ocho bugs, y qué enseña cada uno

Esta es la parte que merece la pena contar. Ninguno de estos fallos se ve leyendo el
código: todos salieron ejecutando simulaciones.

### Bug #1 — La expresión regular que se comía el PIN

El simulador envía las pulsaciones del teclado así:

```
<context>user pressed 1234 on keypad.</context>
```

Nuestro `before_model_callback` extraía los dígitos con una regex que exigía **final de
cadena (`$`) justo después del número**. Como detrás venía ` on keypad.</context>`, no
capturaba nada. El agente pedía el PIN, el cliente lo tecleaba, el agente no veía nada y
volvía a pedirlo. **Bucle infinito.**

**Lección:** en voz nunca parseas "lo que dice el usuario". Parseas **una plantilla que
genera la plataforma**. Y esa plantilla puede cambiar sin avisarte.

**Cómo lo arreglamos de verdad:** no endureciendo la regex. Dimos a los 6 sub-agentes las
tools `validate_authentication_otp` / `validate_authentication_pin` y dejamos que el
**modelo lea la notificación** y llame él a la tool. La regex quedó como red de seguridad,
no como mecanismo principal.

> [!NOTE]
> Sobre el miedo razonable de *"¿y si el cliente dice «en 2024 contraté la fibra» y lo
> confundimos con un PIN?"*: no puede pasar. Solo tratamos como dígitos lo que viene dentro
> de la etiqueta `<context>...on keypad</context>`, o un mensaje compuesto **exclusivamente**
> por números. El habla libre nunca entra por ahí.

### Bug #2 — `end_session` no estaba declarada en los especialistas

Nuestro `after_model_callback` inyectaba una llamada a `end_session` al terminar. Pero
cuando el traspaso ocurría **dentro** de `billing_specialist`, ese agente no tenía
`end_session` en su lista `tools`. La plataforma rechazaba la llamada, el modelo reintentaba
**8 veces**, y la llamada acababa con un *"Hmm, I'm having trouble with that"*.

**"Inyectar `end_session`"** significa esto: el callback, después de que el modelo genere su
respuesta, **añade programáticamente** una llamada a tool que el modelo no pidió. Es la
forma de garantizar que la sesión se cierra pase lo que pase. Y para que no se dispare dos
veces, nada más inyectarla limpiamos la bandera (`state["flag_val"] = ""`).

**Lección:** una capacidad que inyectas desde código tiene que estar declarada en **todos**
los agentes que puedan llegar a ese punto. Y el fallo es silencioso: la tool simplemente no
existe, y lo que ves es al modelo entrando en bucle de reintentos.

### Bug #3 — El mock que contradecía al test

`verify_payment_posted` devolvía `PENDING` para la cuenta `4155550102`. Esa era nuestra
cuenta de prueba negativa... pero también la que usaba `sim__restore_service_already_paid`,
que esperaba `POSTED`.

**Lección, y es la incomodidad legítima de todo esto:** cuando los datos son mock, **tú eres
el backend**. El test no te dice qué debe devolver la tool; te dice qué debe pasar en la
conversación. Deducir el estado del backend a partir del comportamiento esperado es trabajo
de diseño — pero es trabajo que el enunciado te delega sin decirlo en ninguna parte.

### Bug #4 — El pago que siempre se rechazaba

`process_payment` denegaba el primer intento **siempre**, para poder probar el flujo de
"tarjeta rechazada". Eso rompía todos los demás tests de pago.

**Arreglo:** un `MOCK_PAYMENT_VAULT` indexado por número de cliente (`clid`). La cuenta
`4155550104` tiene tarjeta `DECLINED`; el resto `ACTIVE`. El comportamiento depende de
**quién llama**, no del número de intento.

**Lección:** los mocks deben modelar **estado**, no **secuencia**. Un mock que depende del
orden de invocación es un mock que va a romper el test de al lado.

### Bug #5 — El guardián de seguridad que bloqueaba a los clientes

`report_malicious_utterance` detectaba números de tarjeta de 16 dígitos como intento de
inyección. Pero un cliente que **dicta su tarjeta para pagar** produce exactamente eso.

**Arreglo:** si el contexto es un pago, devuelve `status: "ignored"` y redirige a
`process_payment`.

**Lección:** en seguridad, el falso positivo también es un fallo. Un guardián que bloquea a
clientes legítimos es un guardián roto.

### Bug #6 — La lista negra de OTPs

Rechazábamos `000000` y `999999` como "códigos obviamente falsos". El test usaba `111111`.
Lo añadimos. Pero `222222` sigue pasando.

**Lección honesta, que vale la pena decir en voz alta:** una lista negra nunca está
completa. Lo correcto sería una **regla** (*"rechaza cualquier código con los 6 dígitos
iguales"*), no una enumeración. Es deuda técnica consciente.

### Bug #7 — Los huecos de cita hardcodeados

`commit_appointment_reschedule` devolvía literalmente `"Thursday, Oct 15"` para el hueco
`SLOT-1`, diera igual lo que pidiera el cliente. Rompía a la vez el caso "quiero una fecha
más temprana" y el caso francés de satélite.

**Arreglo, con dos decisiones deliberadas:**

1. **IDs opacos**: `SLT-4821`, `SLT-9137`, `SLT-2605` en vez de `SLOT-EARLIER`. Un ID
   semántico es una **pista** para el modelo. Si el modelo acierta porque el identificador
   se llama `SLOT-EARLIER`, no has probado nada: has probado que sabe leer.
2. **Fechas reales** (`start_iso` / `end_iso` en ISO-8601) más etiquetas ya localizadas
   (`label_en` / `label_fr`).

**Lección general y transferible:** *no le des pistas al modelo en los datos de prueba*. El
mock debe contener los **hechos**; el razonamiento lo pone el modelo.

### Bug #8 — El reembolso duplicado, o cómo NO hacer un mock

El test `sim__request_refund_overcharge_french`: un cliente llama diciendo que ha pagado la
factura **dos veces**. Nuestro `fetch_recent_bills` devolvía cuatro importes distintos
(77,50 / 45,00 / 12,50 / 15,00) y **ninguno marcado como duplicado**. El modelo, sin datos,
preguntaba *"¿cuál es el importe exacto?"* — y el juez lo daba por fallido.

La tentación era añadir un campo `duplicate_payment_overcharge_amount: 25.00` al mock. Eso
es **hacer trampa**: le estás dando la respuesta al modelo.

**Lo que hicimos en su lugar** — el rediseño del que más orgulloso estoy:

1. Metimos en el libro de pagos (*ledger*) **dos pagos realmente idénticos**: mismo importe
   (22,50 $), misma factura, misma tarjeta, con un día de diferencia.
2. Una tool nueva, `list_recent_payments`, expone ese libro tal cual, sin etiquetas.
3. Otra tool nueva, `refund_duplicate_payment(txn_a, txn_b)`, **vuelve a verificar el
   duplicado en código** antes de mover un céntimo.

El modelo tiene que **darse cuenta él solo** de que hay dos pagos iguales. Eso sí es una
prueba de verdad.

---

## 4. Las ocho validaciones del reembolso (y por qué en código)

[`refund_duplicate_payment`](file:///Users/rasalungei/Documents/2026/GECX%20Bootcamp/ras-fde-bootcamp-greenfield-agent/cxas_app/ras-_FDE-bootcamp_-greenfield-agent/tools/refund_duplicate_payment/python_function/python_code.py)
no se fía de nada de lo que diga el modelo:

| # | Validación | Error si falla |
| :-- | :-- | :-- |
| 1 | El cliente está autenticado | `AUTH_REQUIRED` |
| 2 | Las dos transacciones existen **en esta cuenta** | `TXN_NOT_FOUND` |
| 3 | No es la misma transacción consigo misma | `SAME_TRANSACTION` |
| 4 | No se ha reembolsado ya (idempotencia) | `ALREADY_REFUNDED` |
| 5 | Ambos pagos están realmente cobrados (`POSTED`) | `DUPLICATE_NOT_CONFIRMED` |
| 6 | Mismo importe al céntimo y misma factura destino | `DUPLICATE_NOT_CONFIRMED` |
| 7 | Separados ≤ 7 días (mismo ciclo de facturación) | `DUPLICATE_NOT_CONFIRMED` |
| 8 | Importe ≤ 25 $ (umbral de autoservicio) | `NOT_ELIGIBLE` → agente humano |

Y una **regla de negocio determinista** que el modelo no decide:

```python
# // SIEMPRE se devuelve el pago MAS RECIENTE y se conserva el primero aplicado
# // a la factura. El orden de los argumentos es irrelevante.
later = a if _to_days(a["paid_at"]) >= _to_days(b["paid_at"]) else b
```

**El principio de fondo, que es el mensaje central de la charla:**

> El modelo **propone**. El código **dispone**.
> El LLM detecta el patrón y conversa; la decisión que mueve dinero la toma Python.

Estados posibles de un pago: `POSTED` (cobrado y aplicado) / `PENDING` (registrado, no
compensado aún por el banco) / `FAILED` (rechazado) / `REFUNDED` (devuelto).

---

## 5. Seguridad: tres hallazgos incómodos

### 5.1 La autenticación NO es automática

Este es el hallazgo que más me sorprendió y el que más me preocuparía en producción.

Cuando creas una tool nueva en CES, **no hereda ninguna comprobación de autenticación**.
Hay que copiar a mano, en cada tool, este bloque:

```python
# // Este bloque hay que copiarlo literalmente en CADA tool sensible.
if context.state.get("auth_status") != "Pass":
    return {"status": "error", "error": "AUTH_REQUIRED", ...}
```

Y lo grave viene ahora:

| Problema | Detalle |
| :-- | :-- |
| El linter no lo detecta | `cxas lint` pasa con 0 errores aunque olvides el bloque |
| No se puede factorizar | CES **prohíbe módulos Python compartidos** entre tools |
| El fallo es silencioso | La tool funciona perfectamente... sin autenticar a nadie |

O sea: la seguridad de 32 tools depende de que nadie se olvide de copiar 4 líneas, sin
ninguna red que lo verifique. En un equipo de verdad esto necesita un test automatizado que
recorra todas las tools sensibles y compruebe que el bloque está.

**Matiz importante, y tranquilizador:** cuando una tool devuelve `AUTH_REQUIRED`, el fallo
**no es catastrófico**. El modelo lee el error, pide la autenticación y reintenta. Lo que
falla es la fluidez de la conversación, no la seguridad ni la integridad de los datos.

### 5.2 El step-up que decidía el modelo

Nuestra versión original de la tool de MFA era esta:

```python
def manage_mfa(action: str = "enable", step_up_verified: bool = True) -> dict:
```

Léelo despacio: **el modelo pasaba el parámetro que dice si la verificación reforzada se
hizo**. Y con `True` por defecto. Eso no es un control de seguridad, es una sugerencia: el
modelo se estaba autorizando a sí mismo.

*Step-up* = pedir un **segundo factor fresco** justo antes de una acción crítica, aunque el
cliente ya esté autenticado. Es lo que hace tu banco cuando te pide otro código para cambiar
el límite de la tarjeta, no solo para entrar.

**Rediseño (v3.6):**

| | Antes | Ahora |
| :-- | :-- | :-- |
| Quién decide | El modelo, vía parámetro | El código, vía estado de sesión |
| Dónde vive la regla | Texto en el `instruction.txt` | Variable `step_up_status` |
| ¿Se puede saltar? | Sí, alucinando el parámetro | No: el parámetro ya no existe |
| ¿Se puede reutilizar? | Infinitas veces | No: se consume tras usarse |

Cómo funciona ahora: `validate_authentication_otp` y `validate_authentication_pin` escriben
`step_up_status = "Pass"` **solo si el cliente ya estaba autenticado** — es decir, solo si
es un **segundo código fresco**. `manage_mfa` lo exige para desactivar MFA y lo borra al
usarlo.

**Decisión deliberada:** el step-up solo se exige para **desactivar** MFA, no para activarla.
Aflojar un control de seguridad exige más prueba que apretarlo; activar MFA no puede
perjudicar al titular.

### 5.3 El crédito de buena voluntad que se regala solo

`apply_bill_adjustment` auto-aprueba cualquier ajuste de hasta 25 $ **sin exigir ninguna
prueba de que hubo avería**. Hoy, si un cliente dice "he tenido cortes toda la semana", se
lleva el crédito.

En producción ese umbral tendría que cruzarse contra un ticket de incidencia verificado en
el backend, no contra la palabra del cliente. Es un agujero conocido y asumido, no un
descuido.

### Cómo decidimos qué es "acción crítica"

Tres disparadores; basta con uno:

| Disparador | Ejemplos en nuestro agente |
| :-- | :-- |
| Es irreversible | Portabilidad del número, cancelación de servicio |
| Mueve dinero | Reembolso, ajuste de factura, alta de domiciliación |
| Cambia un control de seguridad o de identidad | Desactivar MFA, cambiar el nº de contacto |

Las dos primeras exigen `auth_status = "Pass"`. La tercera exige además step-up.

---

## 6. Los contadores: una decisión que parece trivial y no lo es

| Variable | Alcance | Se resetea | Escala a los 3 |
| :-- | :-- | :-- | :-- |
| `local_noinput_counter` | Por módulo | Al entrar en cada agente | `no_input_escalation` |
| `global_err_count` | Toda la sesión | Nunca | `too_many_errors` |
| `no_match_confirmation_count` | Toda la sesión | Nunca | `disambig_max_attempts` |
| `misc_counter` | Toda la sesión | Solo tras autenticar bien | `auth_failure_handoff` |

El **silencio** se resetea por módulo porque suele indicar *"esta pregunta concreta está mal
formulada"*. Si fuera global, un cliente que se despista una vez en facturación, otra en
soporte y otra en citas acabaría escalado sin que nada vaya mal.

El **error** es global porque mide *"esta llamada va mal en general"*.

`misc_counter` — nombre heredado del enunciado, donde *misc* significa **miscellaneous**
(contador genérico sin uso asignado) — lo reutilizamos para los intentos fallidos de
autenticación. **No se resetea al cambiar de tema**, y es deliberado: si no, bastaría con
cambiar de tema para resetear el contador de intentos.

---

## 7. Detección generativa en vez de listas de palabras

Empezamos con listas de palabras clave para detectar intención (*"si dice «factura» →
billing"*). Lo quitamos.

| | Palabras clave | Detección generativa |
| :-- | :-- | :-- |
| Cobertura | Solo lo que enumeraste | Paráfrasis, ironía, otros idiomas |
| Bilingüe | Hay que duplicar la lista | Gratis |
| Mantenimiento | Crece sin fin | Se ajusta el prompt |
| Determinismo | Alto | Menor |

En un agente bilingüe con francés canadiense coloquial, mantener listas de palabras es
insostenible. Cedimos determinismo a cambio de cobertura — **pero solo en la detección de
intención, nunca en las decisiones que mueven dinero o tocan seguridad**. Esa frontera es
justo la tesis del documento.

---

## 8. Cómo lo probamos

| Nivel | Qué prueba | Coste |
| :-- | :-- | :-- |
| `cxas lint` | Estructura, nombres, esquemas (60+ reglas) | Segundos |
| Tool tests | Una tool aislada, entrada → salida | Segundos |
| Callback tests | Un callback aislado | Segundos |
| Simulaciones | Conversación completa, con un LLM haciendo de cliente | Minutos |

La clave: las simulaciones usan **un LLM que hace de cliente** siguiendo un guion, y **otro
LLM que hace de juez**. Es la única forma de probar una conversación de voz de verdad.

**Pero tiene ruido, y hay que contarlo.** En nuestra última tanda, dos tests de MFA fallaron
porque el cliente simulado **se quedó callado** a mitad de la conversación — nuestro agente
se comportó perfectamente. Un test rojo no siempre es un bug tuyo. Antes de tocar código
hay que leer la transcripción.

**Otra limitación:** en modo audio, las expectativas de tipo `expect_tools` fallan
silenciosamente. Hay que usar criterios evaluados por el juez (`expect_criteria`).

---

## 9. Deuda técnica consciente

No todo está resuelto. Lo digo porque una charla que solo cuenta éxitos no sirve de nada.

| Tema | Estado | Qué haría falta |
| :-- | :-- | :-- |
| Lista negra de OTPs | `222222` aún pasa | Una regla (dígitos repetidos), no una enumeración |
| Auth en cada tool | Copiado a mano, 32 veces | Test que recorra todas las tools sensibles |
| Idempotencia del reembolso | Solo dura la sesión | Persistencia real en el backend |
| Crédito ≤ 25 $ | Auto-aprueba sin prueba | Cruzar contra un ticket de incidencia |
| Mocks | Estado inventado por nosotros | Contrato de datos acordado con el cliente |
| Reglas en el `instruction.txt` | Una regla de MFA se disparaba de más (corregida) | Mover la lógica a código |
| `<constraints>` mezclado con `<taskflow>` | Los 5 especialistas tienen pasos secuenciales (*"primero X, luego Y"*) dentro de `<constraints>` | Mover todo lo secuencial a `<step>` con `<trigger>` en `<taskflow>`, dejando en `<constraints>` solo invariantes globales e *interrupts* |

### Nota sobre `<constraints>` vs `<taskflow>` (para la charla)

- **`<constraints>`** = lo que es **siempre** cierto, en cualquier turno, sin importar por dónde vaya la conversación: frases legales literales, prohibiciones (`NEVER`), interrupciones globales (humano, fraude, empresa, cambio de tema, cambio de idioma) y umbrales.
- **`<taskflow>`** = una tabla de `if (<trigger>) → <action>`. No es un bucle secuencial con puntero como un programa: en cada turno el modelo lee todos los `<step>` y ejecuta aquel cuyo `<trigger>` (basado en variables de estado como `identification_status` o `auth_status`) se cumple.
- **Qué corregimos ya:** propagamos la regla transversal de *cambio de tema a mitad de llamada → volver a `Root_agent`* a los 5 especialistas (antes solo estaba en `account_management_specialist`) y eliminamos los IDs de mock incrustados (`APT-5012`, `TCK-8821`, `ORD-90452`) que estaban dando pistas desde el prompt.
- **Qué dejamos apuntado sin tocar antes de la charla:** mover los pasos con *"primero / luego / después"* de `<constraints>` a `<taskflow>` en los 5 especialistas para evitar duplicidad entre ambos bloques.

**Sobre la autenticación repartida en los 6 agentes:** no es deuda, es decisión. Devolver al
`Root_agent` solo para autenticar cuesta un traspaso verbatim y latencia — y fue justo un
problema de traspaso el que causó el bug #1. La seguridad real no está en *quién tiene la
tool*, sino en el `if auth_status != "Pass"` que hay **dentro** de cada tool sensible.

---

## 10. Las cinco ideas que me llevo

1. **El modelo propone, el código dispone.** Todo lo que mueve dinero o toca seguridad se
   valida en Python, no en el prompt.
2. **Nunca des pistas al modelo en los datos de prueba.** Ni en los IDs, ni en los nombres de
   campo. Si el modelo acierta por la pista, no has probado nada.
3. **Un parámetro que rellena el modelo no es un control de seguridad.** Es una sugerencia.
4. **En un sistema multi-agente las capacidades no se heredan.** Y el fallo es silencioso.
5. **Con datos mock, tú eres el backend.** Diseñar esos datos es ingeniería, no un trámite.

---

## Anexo — Historial de versiones desplegadas

| Versión | Contenido |
| :-- | :-- |
| `v3.3-eval-harness-ready` | `end_session` + tools de auth en los 6 agentes; regex DTMF; ledger de `verify_payment_posted` |
| `v3.4-full-suite-ready` | `MOCK_PAYMENT_VAULT` por `clid`; rechazo de OTP repetidos; guarda de nº de tarjeta |
| `v3.5-all-cases-fixed` | Rediseño de huecos de cita con IDs opacos; regla de fallo de MFA |
| `v3.6-stepup-and-dup-refund` | Step-up determinista (`step_up_status`); reembolso de pago duplicado con 8 validaciones |
