#!/usr/bin/env bash

# ============================================================
# Auto start script for qr_tx_display3in7g.py
# ============================================================

sleep 60

PROJECT_DIR="/home/yamalog-8/Desktop/QRe-paper"
API_DIR="${PROJECT_DIR}/api"
VENV_PY="${PROJECT_DIR}/venv/bin/python3"
SCRIPT="${API_DIR}/qr_tx_display3in7g.py"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/qr_tx_display3in7g_startup.log"

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GPIOZERO_PIN_FACTORY=lgpio
export EPAPER_BASE_DIR="/home/yamalog-8/Desktop/QRe-paper/e-Paper/waveshare-e-Paper-latest/E-paper_Separate_Program/3in7_e-Paper_G/RaspberryPi_JetsonNano/python"
export NODE_BIN="/usr/bin/node"
export NODE_ID="node-s-3in7g"
export CSV_FILENAME="qr_tx_log_yamalog_epaper_3in7g.csv"
export DISPLAY_HOLD_SEC="180"
export N_TRIALS="0"
export SEND_JS="send_set_value.js"

mkdir -p "${LOG_DIR}"

{
  echo "=================================================="
  echo "[START] $(date '+%Y-%m-%d %H:%M:%S')"
  echo "USER=$(whoami)"
  echo "PROJECT_DIR=${PROJECT_DIR}"
  echo "API_DIR=${API_DIR}"
  echo "SCRIPT=${SCRIPT}"
  echo "PYTHON=${VENV_PY}"
  echo "NODE_BIN=${NODE_BIN}"
  echo "EPAPER_BASE_DIR=${EPAPER_BASE_DIR}"
  echo "spidev:"
  ls -l /dev/spidev* 2>&1 || true
  echo "gpiochip:"
  ls -l /dev/gpiochip* 2>&1 || true
} >> "${LOG_FILE}" 2>&1

cd "${API_DIR}" || {
  echo "[ERROR] cd failed: ${API_DIR}" >> "${LOG_FILE}" 2>&1
  exit 1
}

exec "${VENV_PY}" "${SCRIPT}" >> "${LOG_FILE}" 2>&1
