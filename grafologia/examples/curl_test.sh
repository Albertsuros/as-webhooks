#!/usr/bin/env bash
# Uso: bash curl_test.sh http://127.0.0.1:5000 /ruta/a/escritura.jpg
BASE="${1:-http://127.0.0.1:5000}"
IMG="${2:-sample.jpg}"

echo "== Health =="
curl -i "$BASE/grafologia/health" || exit 1

echo -e "\n== Analizar =="
curl -i -X POST -F "file=@${IMG}" "$BASE/grafologia/analizar"

echo -e "\n== Informe HTML =="
curl -i -X POST -F "file=@${IMG}" "$BASE/grafologia/informe"

echo -e "\n== Informe PDF (guardando grafo.pdf) =="
curl -L -o grafo.pdf -X POST -F "file=@${IMG}" "$BASE/grafologia/informe_pdf"
echo "PDF guardado como grafo.pdf"
