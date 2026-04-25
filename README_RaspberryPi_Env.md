# Raspberry Pi Environment Setup for QRe-paper

このREADMEは、Raspberry Pi 上で QRe-paper / Waveshare e-Paper / QR表示プログラムを動かすために、`git clone` する前までに必要な環境設定をまとめたものです。

対象環境の例：

- Raspberry Pi OS Bookworm 系
- Python 3.11 以降
- Waveshare e-Paper HAT
- SPI 使用
- GPIO backend: `gpiozero + lgpio`
- Python virtual environment 使用

---

## 1. 目的

この手順では、以下を準備します。

- OSパッケージ更新
- Git / curl / jq などの基本ツール
- Python venv 関連パッケージ
- Pythonビルド関連パッケージ
- `lgpio` / `gpiozero` / `spidev` に必要な依存関係
- Waveshare e-Paper 用の SPI 有効化
- GPIO確認ツール
- 再起動前後の確認コマンド

---

## 2. env.sh の実行

```bash
chmod +x env.sh
./env.sh
3. SPI の有効化確認

env.sh は可能な範囲で SPI を有効化します。
反映には再起動が必要な場合があります。

sudo reboot

再起動後、以下を確認します。

ls /dev/spidev*

期待される表示例：

/dev/spidev0.0  /dev/spidev0.1
4. git clone 前の最終確認

以下が通れば、clone 前の基本環境は整っています。

git --version
python3 --version
python3 -m venv --help | head
ls /dev/spidev*
gpioinfo | head
5. git clone

ここまで完了した後、リポジトリを clone します。

cd ~/Desktop
git clone <YOUR_REPOSITORY_URL>

例：

cd ~/Desktop
git clone https://github.com/yourname/QRe-paper.git
6. clone 後の venv 作成例
cd ~/Desktop/QRe-paper

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip setuptools wheel

requirements.txt がある場合：

python -m pip install -r requirements.txt

Waveshare e-Paper / QR表示で最低限必要な Python パッケージ例：

python -m pip install gpiozero lgpio spidev qrcode pillow
7. Waveshare e-Paper ドライバのインストール
cd ~/Desktop/QRe-paper/e-Paper/RaspberryPi_JetsonNano/python
python setup.py install

または、venv の Python を直接指定します。

~/Desktop/QRe-paper/venv/bin/python setup.py install
8. import 確認

2.15inch b の場合：

~/Desktop/QRe-paper/venv/bin/python - <<'PY'
from waveshare_epd import epd2in15b

print("epd2in15b OK")
epd = epd2in15b.EPD()
print("width =", epd.width)
print("height =", epd.height)
PY

3.7inch の場合：

~/Desktop/QRe-paper/venv/bin/python - <<'PY'
from waveshare_epd import epd3in7

print("epd3in7 OK")
epd = epd3in7.EPD()
print("width =", epd.width)
print("height =", epd.height)
PY
9. 公式サンプル実行例

2.15inch b：

cd ~/Desktop/QRe-paper/e-Paper/RaspberryPi_JetsonNano/python/examples

GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python epd_2in15b_test.py

sudo が必要な場合：

sudo env GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python epd_2in15b_test.py

3.7inch：

cd ~/Desktop/QRe-paper/e-Paper/RaspberryPi_JetsonNano/python/examples

sudo env GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python epd_3in7_test.py
10. QR表示プログラム実行例

2.15inch b 固定版：

cd ~/Desktop/QRe-paper/api

GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python qr_code_display215b.py

sudo が必要な場合：

sudo env GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python qr_code_display215b.py
11. よくあるエラー
externally-managed-environment

system Python に直接 pip install しようとすると発生します。

対策：

python3 -m venv venv
source venv/bin/activate
python -m pip install ...
No module named qrcode / gpiozero / lgpio

venv ではない Python で実行している可能性があります。

確認：

which python
python -m pip --version

venv を直接指定する場合：

~/Desktop/QRe-paper/venv/bin/python your_script.py
error: command 'swig' failed

lgpio のビルドに swig が必要です。

対策：

sudo apt install -y swig python3-dev build-essential liblgpio-dev
/dev/spidev* がない

SPI が無効です。

sudo raspi-config nonint do_spi 0
sudo reboot

再起動後：

ls /dev/spidev*
e-Paper busy で止まる

主な原因：

BUSY ピンの接続不良
FPC ケーブルの向き違い
HAT の向き違い
e-Paper 型番とドライバ不一致
PWR_PIN / BUSY_PIN の不一致
SPI / GPIO 権限問題

まず公式サンプルで確認します。

cd ~/Desktop/QRe-paper/e-Paper/RaspberryPi_JetsonNano/python/examples

sudo env GPIOZERO_PIN_FACTORY=lgpio \
~/Desktop/QRe-paper/venv/bin/python epd_2in15b_test.py
12. 推奨実行スタイル

このプロジェクトでは、常に venv の Python を使うことを推奨します。

~/Desktop/QRe-paper/venv/bin/python script.py

または：

cd ~/Desktop/QRe-paper
source venv/bin/activate
python script.py

