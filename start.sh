#!/bin/sh

mkdir -p server
python3 -m http.server -d server &

if [ -n "$TOKEN" ] && [ -n "$BARER" ]; then
  echo "✅ Usando configuración con TOKEN y BARER"
fi

if [ -z "$TOKEN" ]; then
  echo "❌ Debes definir TOKEN en el entorno."
  exit 1
fi

if [ -z "$MASTER" ]; then
  echo "❌ Debes definir MASTER en el entorno (formato: @usuario,ID)."
  exit 1
fi

if [ -z "$REPO" ]; then
  echo "❌ Debes definir REPO en el entorno (formato: usuario/repo)."
  exit 1
fi

if [ -z "$BARER" ]; then
  echo "❌ Debes definir BARER en el entorno (token de GitHub)."
  exit 1
fi

START_MSG="${START_MSG:-}"

CMD="python3 bot.py \
  -t \"$TOKEN\" \
  -master \"$MASTER\""

[ -n "$START_MSG" ] && CMD="$CMD -msg \"$START_MSG\""
[ -n "$REPO" ] && CMD="$CMD -repo \"$REPO\""
[ -n "$BARER" ] && CMD="$CMD -barer \"$BARER\""

echo "🚀 Ejecutando: $CMD"
eval "$CMD"
