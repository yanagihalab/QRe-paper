#!/bin/bash

VENV_PATH="$HOME/QRe-paper/venv"
LOG_FILE="$HOME/qr_log.txt"

echo "--- start.sh exe: $(date) ---" >> $LOG_FILE

sleep 10
echo "10 seconds waited" >> $LOG_FILE

cd $HOME/QRe-paper/api
echo " change dir $(pwd)" >> $LOG_FILE

#. "${VENV_PATH}/bin/activate"
#echo "venv activate" >> $LOG_FILE

echo " try qr_code_display.py" >> $LOG_FILE
#sudo -u yama /usr/bin/python qr_code_display.py >> $LOG_FILE 2>&1 &
# venv経由でpythonを実行 
sudo -u yama "${VENV_PATH}/bin/python" qr_code_display.py >> $LOG_FILE 2>&1 &

echo "--- complete start.sh ---" >> $LOG_FILE
