# Raspberry Pi 起動時に `qr_tx_display3in7g.py` を cron で自動実行する手順

この README は、Raspberry Pi 起動時に cron の `@reboot` を使って、3.7inch G e-Paper 用 QR/TX 表示スクリプトを自動実行するための手順をまとめたものです。

対象スクリプトは以下です。

```text
/home/yamalog-8/Desktop/QRe-paper/api/qr_tx_display3in7g.py

起動用シェルスクリプトは以下に作成します。

/home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh

cron 設定支援スクリプトは以下です。

/home/yamalog-8/Desktop/QRe-paper/setup_cron_qr_tx_display3in7g.sh
1. 前提ディレクトリ構成

この README では、以下の構成を前提とします。

/home/yamalog-8/Desktop/QRe-paper/
├── api/
│   ├── qr_tx_display3in7g.py
│   └── send_set_value.js
├── venv/
├── e-Paper/
│   └── waveshare-e-Paper-latest/
├── logs/
├── start_qr_tx_display3in7g.sh
└── setup_cron_qr_tx_display3in7g.sh

3.7inch G 用 Waveshare ライブラリは、以下の場所を使用します。

/home/yamalog-8/Desktop/QRe-paper/e-Paper/waveshare-e-Paper-latest/E-paper_Separate_Program/3in7_e-Paper_G/RaspberryPi_JetsonNano/python

この中に、次のファイルが存在している必要があります。

lib/waveshare_epd/epd3in7g.py

確認コマンド：

find /home/yamalog-8/Desktop/QRe-paper -iname "epd3in7g.py"
2. cron 自動起動の仕組み

cron の @reboot を使い、Raspberry Pi 起動時に次のシェルスクリプトを実行します。

/home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh

cron に直接 Python を書かず、シェルスクリプトを経由する理由は以下です。

起動直後の SPI/GPIO 初期化待ちを入れられる
venv の Python を明示できる
NODE_BIN, EPAPER_BASE_DIR, DISPLAY_HOLD_SEC などの環境変数を固定できる
ログを /home/yamalog-8/Desktop/QRe-paper/logs/ に保存できる
起動失敗時の原因を追跡しやすい
3. cron 設定支援スクリプトを実行する

以下を実行すると、起動用シェルスクリプトを作成し、cron の @reboot に登録します。

cd /home/yamalog-8/Desktop/QRe-paper

chmod +x setup_cron_qr_tx_display3in7g.sh
./setup_cron_qr_tx_display3in7g.sh
4. 作成される起動スクリプト

setup_cron_qr_tx_display3in7g.sh を実行すると、以下のファイルが作成されます。

/home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh

この起動スクリプトは、以下の処理を行います。

起動後 60 秒待機
必要な環境変数を設定
/home/yamalog-8/Desktop/QRe-paper/api に移動
venv/bin/python3 で qr_tx_display3in7g.py を実行
ログを以下に出力
/home/yamalog-8/Desktop/QRe-paper/logs/qr_tx_display3in7g_startup.log
5. cron 登録内容

登録される cron は以下です。

@reboot /home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh >> /home/yamalog-8/Desktop/QRe-paper/logs/cron_qr_tx_display3in7g.log 2>&1

確認コマンド：

crontab -l
6. 手動実行で確認する

cron に頼らず、まず手動で起動スクリプトを確認できます。

/home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh

このスクリプトは起動後に 60 秒待機します。

ログ確認：

tail -f /home/yamalog-8/Desktop/QRe-paper/logs/qr_tx_display3in7g_startup.log

正常な場合、次のようなログが出ます。

INFO:root:yamalog-epaper TX -> QR Display for epd3in7g
INFO:root:GPIOZERO_PIN_FACTORY=lgpio
INFO:root:EPAPER_BASE_DIR=...
INFO:root:width=240 height=416
INFO:root:DISPLAY_HOLD_SEC=180
INFO:root:SEND_JS=/home/yamalog-8/Desktop/QRe-paper/api/send_set_value.js
INFO:root:[1] ok=True ...
7. 再起動後の確認

Raspberry Pi を再起動します。

sudo reboot

再起動後、ログを確認します。

tail -n 150 /home/yamalog-8/Desktop/QRe-paper/logs/qr_tx_display3in7g_startup.log

新しい [START] が再起動後の時刻で出ていれば成功です。

cron の実行ログは以下で確認できます。

systemctl status cron --no-pager
grep CRON /var/log/syslog | tail -n 50
8. プロセス確認

起動後に qr_tx_display3in7g.py が動いているか確認します。

ps -ef | grep qr_tx_display3in7g.py | grep -v grep

1行だけ表示されれば正常です。

複数行ある場合は、同じスクリプトが重複起動している可能性があります。

停止する場合：

pkill -f qr_tx_display3in7g.py
9. 表示保持時間の変更

起動スクリプト内の以下を変更します。

export DISPLAY_HOLD_SEC="180"

例：30秒にする場合

export DISPLAY_HOLD_SEC="30"

変更後は、プロセスを再起動するか Raspberry Pi を再起動してください。

pkill -f qr_tx_display3in7g.py
/home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh
10. 自動起動を解除する

cron を編集します。

crontab -e

以下の行を削除またはコメントアウトします。

@reboot /home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh >> /home/yamalog-8/Desktop/QRe-paper/logs/cron_qr_tx_display3in7g.log 2>&1

コメントアウト例：

# @reboot /home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh >> /home/yamalog-8/Desktop/QRe-paper/logs/cron_qr_tx_display3in7g.log 2>&1
11. よくあるトラブル
cron は動いているが表示されない

cron の状態を確認します。

systemctl status cron --no-pager

cron の実行ログを確認します。

grep CRON /var/log/syslog | tail -n 50
起動スクリプトが存在しない

以下を確認します。

ls -l /home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh

存在しない場合は、再度セットアップします。

cd /home/yamalog-8/Desktop/QRe-paper
./setup_cron_qr_tx_display3in7g.sh
実行権限がない
chmod +x /home/yamalog-8/Desktop/QRe-paper/start_qr_tx_display3in7g.sh
chmod +x /home/yamalog-8/Desktop/QRe-paper/setup_cron_qr_tx_display3in7g.sh
epd3in7g.py が見つからない
find /home/yamalog-8/Desktop/QRe-paper -iname "epd3in7g.py"

想定パス：

/home/yamalog-8/Desktop/QRe-paper/e-Paper/waveshare-e-Paper-latest/E-paper_Separate_Program/3in7_e-Paper_G/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd3in7g.py
node が見つからない
which node

起動スクリプト内の以下を環境に合わせます。

export NODE_BIN="/usr/bin/node"
SPI が有効でない
ls /dev/spidev*

何も表示されない場合は、SPI を有効化します。

sudo raspi-config

以下を選択します。

Interface Options
→ SPI
→ Enable

その後、再起動します。

sudo reboot
12. git 管理するファイル

最低限、以下を git 管理対象にします。

git add README_CRON_QR_TX_DISPLAY3IN7G.md
git add setup_cron_qr_tx_display3in7g.sh
git add start_qr_tx_display3in7g.sh
git add api/qr_tx_display3in7g.py

Waveshare の e-Paper/ や waveshare-e-Paper-latest/ は容量が大きくなりやすいため、通常は .gitignore に入れ、README に取得方法を記載する方が安全です。
