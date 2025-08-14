from flask import Flask, render_template, request, jsonify, Response, url_for
import qrcode
import uuid
import json
from datetime import datetime
import io

app = Flask(__name__)

# ユーザーIDを仮定（実際はログイン機能などで取得）
USER_ID = "user_001"

# 生成したQRコードの状態を保存する簡単なデータベースの代わり
# 本番環境ではRedisやデータベースを使用してください
qr_code_db = {}

def generate_qr_data():
    """新しいQRコードのデータを生成する関数"""
    qr_id = str(uuid.uuid4()) # 固有の番号としてUUIDを生成
    timestamp = datetime.now().isoformat() # 現在時刻をISO形式で取得
    
    # このデータがQRコードの基本情報となる
    data = {
        "user_id": USER_ID,
        "qr_code_id": qr_id,
        "timestamp": timestamp
    }
    
    # サーバーの検証用URLを生成
    # url_forを使うと、関数の名前からURLを安全に生成できる
    validation_url = url_for('validate_qr', qr_id=qr_id, _external=True)

    # データベースに保存
    qr_code_db[qr_id] = {
        "data": data,
        "validated": False, # スキャンされたかどうか
        "validation_url": validation_url
    }
    
    return qr_id

@app.route("/")
def index():
    """QRコードを表示するメインページ"""
    new_qr_id = generate_qr_data()
    return render_template("index.html", qr_id=new_qr_id)

@app.route("/qr_image/<qr_id>")
def qr_image(qr_id):
    """QRコードの画像を生成して返すエンドポイント"""
    if qr_id not in qr_code_db:
        return "Not Found", 404

    # QRコードには検証用URLを埋め込む
    url_to_encode = qr_code_db[qr_id]["validation_url"]
    
    # メモリ上でQRコード画像を生成
    img_buffer = io.BytesIO()
    qr_img = qrcode.make(url_to_encode)
    qr_img.save(img_buffer, 'PNG')
    img_buffer.seek(0)
    
    return Response(img_buffer, mimetype="image/png")

@app.route("/validate/<qr_id>")
def validate_qr(qr_id):
    """QRコードがスキャンされたときにアクセスされるエンドポイント"""
    if qr_id in qr_code_db:
        if not qr_code_db[qr_id]["validated"]:
            # 有効なQRコードであれば「使用済み」にする
            qr_code_db[qr_id]["validated"] = True
            print(f"✅ QRコードが正常に検証されました: ID={qr_id}, データ={qr_code_db[qr_id]['data']}")
            return f"<h1>認証成功</h1><p>ID: {qr_id}</p>"
        else:
            # すでに使用済みのQRコード
            print(f"❗️ 使用済みのQRコードがスキャンされました: ID={qr_id}")
            return "<h1>このQRコードは既に使用されています</h1>", 400
    else:
        # 存在しないQRコード
        print(f"❌ 存在しないQRコードがスキャンされました: ID={qr_id}")
        return "<h1>無効なQRコードです</h1>", 404

@app.route("/status/<qr_id>")
def qr_status(qr_id):
    """WebページがQRコードの状態をポーリングするためのエンドポイント"""
    if qr_id in qr_code_db and qr_code_db[qr_id]["validated"]:
        return jsonify({"status": "validated"})
    return jsonify({"status": "pending"})

if __name__ == "__main__":
    # 外部からアクセス可能にするために host='0.0.0.0' を指定
    app.run(host='0.0.0.0', debug=True)