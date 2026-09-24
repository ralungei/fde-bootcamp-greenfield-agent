#!/bin/bash
# Abre la presentación en modo app de Chrome: ventana limpia, sin pestañas ni barra de direcciones, redimensionable.
# Uso: doble clic en Finder, o ./abrir_presentacion.command desde la terminal.
DIR="$(cd "$(dirname "$0")" && pwd)"
open -na "Google Chrome" --args --app="file://$DIR/master.html" --window-size=1600,900
