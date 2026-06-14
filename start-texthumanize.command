#!/bin/zsh

set -e

cd "$(dirname "$0")"

PORT=8501
URL="http://127.0.0.1:${PORT}"

echo "TextHumanize wird gestartet..."
echo "Projektordner: $(pwd)"

EXISTING_PIDS=$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)
if [[ -n "$EXISTING_PIDS" ]]; then
  echo "Port ${PORT} ist belegt. Beende alten Streamlit-Prozess..."
  echo "$EXISTING_PIDS" | xargs kill
  sleep 1
fi

echo "Oeffne ${URL}"
open "$URL" >/dev/null 2>&1 || true

echo ""
echo "Streamlit laeuft jetzt unter:"
echo "  ${URL}"
echo ""
echo "Zum Beenden dieses Fenster aktivieren und Ctrl+C druecken."
echo ""

python3 -m streamlit run web/app.py \
  --server.address 127.0.0.1 \
  --server.port "${PORT}" \
  --server.headless true \
  --browser.gatherUsageStats false
