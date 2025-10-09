#!/bin/bash

#VENV_PATH="~/temp/QRe-paper/venv"
#LOG_FILE="~/temp/qr_log.txt"

VENV_PATH='/home/yama/tmp/QRe-paper/venv'
LOG_FILE='/home/yama/qr_log.txt'

echo "--- start.sh exe: $(date) ---" >> $LOG_FILE

sleep 10
echo "10 seconds waited" >> $LOG_FILE

cd /home/yama/tmp/QRe-paper/api
echo " change dir $(pwd)" >> $LOG_FILE

#. "${VENV_PATH}/bin/activate"
#echo "venv activate" >> $LOG_FILE

echo " try qr_code_display.py" >> $LOG_FILE
# sudo -u yama /usr/bin/python qr_code_display.py >> $LOG_FILE 2>&1 &
# tyokusetu venv no python wo yobu
sudo -u yama "${VENV_PATH}/bin/python" qr_code_display.py >> $LOG_FILE 2>&1 &

echo "--- complete start.sh ---" >> $LOG_FILE


