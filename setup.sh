#!/bin/bash

# エラーが発生した場合にスクリプトを終了する
set -e

echo "--- システムのアップデートを開始します ---"
sudo apt update && sudo apt upgrade -y

echo "--- 必要なシステムパッケージをインストールします ---"
# venv を作成するために python3-venv を追加
sudo apt install -y git python3 python3-pip python3-venv

echo "--- Python仮想環境 (venv) を作成します ---"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "--- 仮想環境にPythonライブラリを requirements.txt からインストールします ---"
# venv内のpipを直接使用し、sudoは付けない
./venv/bin/pip install -r requirements.txt

echo "--- Waveshare e-Paper ドライバを仮想環境にインストールします ---"
if [ ! -d "e-Paper" ]; then
    git clone https://github.com/waveshare/e-Paper.git
fi
cd e-Paper/RaspberryPi_JetsonNano/python/
# venv内のpythonを使用してインストール
../../../../venv/bin/python3 setup.py install
cd ../../../ # 元のディレクトリに戻る

echo "--- セットアップスクリプトが完了しました ---"
echo "✅ 次のステップ: 'source venv/bin/activate' を実行して仮想環境を有効化し、プログラムを実行してください。"
