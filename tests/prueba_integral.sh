#!/usr/bin/env bash
# Prueba integral con datos SINTÉTICOS (no corresponde a un municipio real).
set -euo pipefail
cd "$(dirname "$0")/.."
TMP="${1:-/tmp/ladm_pot_prueba}"
rm -rf "$TMP"; mkdir -p "$TMP"
python tests/generar_datos_prueba.py "$TMP/insumos"
echo "== Pasada 1 (sin decisiones) =="
python -m ladm_pot.pipeline --insumos "$TMP/insumos" --salida "$TMP/salida_1" --proyecto tests/proyecto_prueba.json --prueba > "$TMP/pasada1.log" 2>&1
echo "== Pasada 2 (con decisiones simuladas) =="
python -m ladm_pot.pipeline --insumos "$TMP/insumos" --salida "$TMP/salida_2" --proyecto tests/proyecto_prueba.json --decisiones tests/decisiones_prueba.json --prueba > "$TMP/pasada2.log" 2>&1
python tests/verificar_salida.py "$TMP/salida_1" "$TMP/salida_2"
