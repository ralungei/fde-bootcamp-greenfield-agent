# fde-bootcamp-greenfield-agent

Agente conversacional de voz para telecomunicaciones (**Telco Voice Central**) construido sobre **Google Customer Engagement Suite (CES)** con arquitectura híbrida (orquestación generativa + guardas deterministas en Python).

## Estructura del repositorio

- `cxas_app/ras-_FDE-bootcamp_-greenfield-agent/`: Aplicación declarativa de CES (`app.json`, 6 agentes especialistas en `agents/`, 32 herramientas Python en `tools/`, y *callbacks* deterministas).
- `evals/`: Escenarios y simulaciones de evaluación (`simulations/simulations.yaml` y `scenarios/`).
- `sources/`: Especificación de requisitos del sistema (`telco-voice-central-spec.md`).
- `CHARLA_DECISIONES_Y_APRENDIZAJES.md`: Documento de arquitectura, decisiones de diseño, seguridad (`auth_status` vs `step_up_status`) y lecciones aprendidas.
- `GUIA_TELCO_VOICE_CENTRAL.md`: Guía detallada de flujos, herramientas y variables de estado.
