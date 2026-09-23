# // Idiomas soportados por la maquina de estados de la conversacion. El modelo es quien
# // DETECTA el idioma (deteccion generativa); esta tool solo EJECUTA el cambio de forma
# // determinista, para que ninguna respuesta se emita en un idioma que el estado no refleja.
SUPPORTED_LANGUAGES = ("primary", "secondary")


def update_language(language: str) -> dict:
    """Lock the conversation to the language the caller is actually speaking (BR-TV-004 / BR-TV-020)."""
    normalized = (language or "").strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        return {
            "status": "error",
            "error": "UNSUPPORTED_LANGUAGE",
            "agent_action": (
                "Call update_language again with language='primary' for English, or "
                "language='secondary' for Canadian French or Spanish."
            ),
        }

    previous = context.state.get("language") or "primary"
    context.state["language"] = normalized
    context.state["language_locked"] = "True"
    return {
        "status": "success",
        "language": normalized,
        "previous_language": previous,
        "agent_instruction": (
            f"The conversation language is now '{normalized}'. Respond 100% in that language for the rest of "
            "the call, with zero words from any other language, and translate every tool message into it."
        ),
    }
