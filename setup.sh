#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

echo "--- システムのアップデートを開始します ---"
sudo apt update && sudo apt upgrade -y

echo "--- 必要なシステムパッケージをインストールします ---"
sudo apt install -y git python3 python3-pip

echo "--- Pythonライブラリを requirements.txt からインストールします ---"
sudo pip3 install -r requirements.txt

echo "--- Waveshare e-Paper ドライバをインストールします ---"
if [ ! -d "e-Paper" ]; then
    git clone https://github.com/waveshare/e-Paper.git
fi
cd e-Paper/RaspberryPi_JetsonNano/python/
sudo python3 setup.py install
cd ../../../ # 元のディレクトリに戻る

echo "--- セットアップスクリプトが完了しました ---"
echo "✅ 次のステップ: SPIを有効にするため、Raspberry Piを再起動してください。"