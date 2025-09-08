from flask import Flask, request
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/scan')
def scan_qr():
    """
    QRコードからアクセスされるエンドポイント
    """
    # URLのクエリパラメータからqr_idを取得
    qr_id = request.args.get('qr_id', 'unknown')
    
    if qr_id != 'unknown':
        # どのQRコードがスキャンされたかを示す「フラグファイル」を作成する
        flag_filename = f"scanned_{qr_id}.flag"
        with open(flag_filename, "w") as f:
            f.write("scanned")
        logging.info(f"QR ID '{qr_id}' was scanned. Flag file '{flag_filename}' created.")
    
    # スキャンしたデバイスのブラウザに表示するメッセージ
    return """
    <html>
        <head>
            <title>QR Code Scanned</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f0f0; }
                .container { text-align: center; padding: 20px; border-radius: 10px; background-color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
                h1 { color: #4CAF50; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>読み取り成功！</h1>
                <p>QRコードのデータを正常に受信しました。</p>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    # ネットワーク上の他のデバイスからアクセスできるように host='0.0.0.0' を指定
    app.run(host='0.0.0.0', port=5000, debug=True)

