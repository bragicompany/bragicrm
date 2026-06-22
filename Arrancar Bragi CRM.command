#!/bin/bash
# Lanzador de doble clic para el CRM de Bragi (uso local).
# Haz doble clic en este archivo desde Finder para abrir la app.
# Para apagarla: cierra esta ventana o pulsa Ctrl+C.

# Ir a la carpeta del proyecto (donde está este archivo).
cd "$(dirname "$0")" || exit 1

# Activar el entorno de Python si existe.
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

echo "==============================================="
echo "   BRAGI CRM — arrancando en tu computadora"
echo "==============================================="

# 1) Respaldo automático de la base (red de seguridad antes de trabajar).
python3 -c "import database; database.respaldar()" 2>/dev/null

# 2) Abrir el navegador en la página correcta (tras un par de segundos).
( sleep 2 ; open "http://localhost:5001" ) &

echo ""
echo "Abriendo http://localhost:5001 en tu navegador..."
echo "(Deja esta ventana abierta mientras uses la app. Para apagar: Ctrl+C)"
echo ""

# 3) Arrancar la app.
python3 app.py
