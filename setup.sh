#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

echo "--- Raspberry Piの環境設定開始 ---"

# raspi-configによるSPIの有効化
echo -e "--- raspi-configをインストールし、SPIを有効化 ---"
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y raspi-config

echo "SPIを有効中..."

# raspi-configでSPIを有効化(0)
sudo raspi-config noint do spi 0
echo "SPIを有効にしました。デバイスファイルを確認します"
ls -l /dev/spidev* || echo "SPIデバイスが見つかりません。再起動後に再度確認してください"

# 必要なパッケージのインストール
echo "--- 必要なシステムパッケージをインストールします ---"
# venv を作成するために python3-venv を追加
sudo apt-get install -y git python3-pip python3-venv python3-pil python3-numpy

echo "--- Python仮想環境 (venv) を作成します ---"
VENV_DIR='venv'
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" --system-site-packages
    echo "仮想環境'$VENV_DIR'を作成しました"
else
    echo "仮想環境'$VENV_DIR'はすでに存在します"
fi

echo "--- 仮想環境にPythonライブラリを requirements.txt からインストールします ---"
# venv内のpipを直接使用し、sudoは付けない
./venv/bin/pip install -r requirements.txt

echo "--- Waveshare e-Paper ドライバを仮想環境にインストールします ---"
E_PAPER_DIR='e-Paper'
if [ ! -d "$E_PAPER_DIR" ]; then
    git clone https://github.com/waveshare/e-Paper.git
fi

echo "path:$PWD"
cd "$E_PAPER_DIR"/RaspberryPi_JetsonNano/python/
echo "path:$PWD"
# venv内のpythonを使用してインストール
../../../"$VENV_DIR"/bin/pip install .
#../../../"$VENV_DIR"/bin/python3 setup.py install
echo "path:$PWD"
cd ../../../ # 元のディレクトリに戻る
echo "path:$PWD"

echo "--- セットアップスクリプトが完了しました ---"
echo "✅ 次のステップ: 'source venv/bin/activate' を実行して仮想環境を有効化し、プログラムを実行してください。"
