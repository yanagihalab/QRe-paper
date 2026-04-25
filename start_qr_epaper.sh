#!/usr/bin/env bash

# ============================================================
# Auto start script for YamaLog QRe-paper
# Target: Waveshare 3.7inch G e-Paper
# ============================================================

# 起動直後は SPI/GPIO やネットワーク準備が完了していない場合があるため待機
sleep 20

PROJECT_DIR="/home/yamalog-8/Desktop/QRe-paper"
API_DIR="${PROJECT_DIR}/api"
VENV_PY="${PROJECT_DIR}/venv/bin/python3"
SCRIPT="${API_DIR}/qr_code_display3in7g.py"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/qr_epaper_startup.log"

mkdir -p "${LOG_DIR}"

echo "==================================================" >> "${LOG_FILE}"
echo "[START] $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_FILE}"
echo "PROJECT_DIR=${PROJECT_DIR}" >> "${LOG_FILE}"
echo "SCRIPT=${SCRIPT}" >> "${LOG_FILE}"

cd "${API_DIR}" || exit 1

# venv の Python で実行
"${VENV_PY}" "${SCRIPT}" >> "${LOG_FILE}" 2>&1
