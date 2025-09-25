プログラムのclone
git clone https://gitlab.com/keisho/trailregister.git

raspi-configのインストール
sudo apt install -y raspi-config

sudo raspi-configでSPIをEnableに変更
sudo raspi-config
Intefactorign Options
SPI -> Enable
SPI有効設定の確認方法
https://qiita.com/ekzemplaro/items/ae37876122b9dab53ae8

インストール (仮想環境でないとpipできない)
sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python3-pil
sudo apt-get install python3-numpy
sudo apt-get install python3-venv # venvがない場合

仮想環境構築
gpiozeroが仮想環境でも使用できるよう「--system-site-packages」オプションをつける
python3 -m venv venv --system-site-packages

pip install gpiozero
pip install lgpio
pip install spidev
pip install qrcode

e-paperの環境構築
git clone https://github.com/waveshare/e-Paper.git # setup.pyのためだけ
/e-Paper/RaspberryPi_JetsonNano/python$ pip install .

e-paper 2in7 か 2in7_v2で違う
# QRe-paper
# QRe-paper
