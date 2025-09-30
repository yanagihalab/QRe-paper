#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in7_V2 as epd2in7
import time
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
import uuid
import json
import glob

logging.basicConfig(level=logging.DEBUG)

# --- ★重要（必要に応じて変更）★ ---
SERVER_IP = "192.168.100.15"  # 旧URL方式(urlモード)で使用
QR_MODE = os.environ.get("QR_MODE", "json").lower()  # "json" | "image" | "url"
WAIT_FOR_SCAN = os.environ.get("WAIT_FOR_SCAN", "0") == "1"  # フラグ監視を使うなら1
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "10"))
METADATA_FILE = os.environ.get("METADATA_FILE", os.path.join(os.path.dirname(__file__), "metadata.json"))
# デフォルトのメタデータ（ファイルが無い時に使用）
DEFAULT_METADATA = {
    "name": "Participation Certificate NFT",
    "description": "10042025深谷研菊地研合同イベント参加証NFT",
    "image": "https://ipfs.yamada.jo.sus.ac.jp/ipfs/QmTuDCtiZJjRFqiZ6D5X2iNX8ejwNu6Kv1F7EcThej9yHu"
}
# -----------------------------------

epd = None

def display_message(epd, font, message):
    """画面中央にメッセージを表示"""
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0,0), message, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (epd.width - text_width) // 2
    y = (epd.height - text_height) // 2
    draw.text((x, y), message, font=font, fill=0)
    epd.display(epd.getbuffer(image))

def load_fonts():
    font_path = os.path.join(picdir, 'Font.ttc')
    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 14)
        font_main = ImageFont.truetype(font_path, 18)
        font_success = ImageFont.truetype(font_path, 24)
    else:
        font_info = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_success = ImageFont.load_default()
    return font_info, font_main, font_success

def wrap_by_width(draw, text, font, max_width):
    """幅ベースで折り返し（日本語対応）"""
    lines = []
    for para in (text or "").splitlines() or [""]:
        buf = ""
        for ch in para:
            if draw.textlength(buf + ch, font=font) <= max_width:
                buf += ch
            else:
                lines.append(buf)
                buf = ch
        lines.append(buf)
    return lines

def load_metadata():
    """metadata.json があれば取り込み。必須キー欠けはデフォルトにフォールバック"""
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                m = json.load(f)
            # 必須キーをチェック
            for k in ("name", "description", "image"):
                if k not in m:
                    raise ValueError(f"metadata missing key: {k}")
            return m
    except Exception as e:
        logging.warning(f"Failed to load metadata file: {e}")
    return DEFAULT_METADATA

def build_qr_payload(user_id, qr_id, metadata):
    """
    QR_MODEに応じてペイロードを生成
    - json  : {"name","description","image"} をそのままQR化（UTF-8）
    - image : image URLのみをQR化
    - url   : 旧仕様の http://SERVER_IP:5000/scan?... をQR化
    """
    if QR_MODE == "json":
        obj = {
            "name": metadata["name"],
            "description": metadata["description"],
            "image": metadata["image"]
        }
        payload = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    elif QR_MODE == "image":
        payload = str(metadata["image"])
    else:  # "url"
        payload = f"http://{SERVER_IP}:5000/scan?user_id={user_id}&qr_id={qr_id}"
    return payload

def make_qr_image(payload):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color=0, back_color=255).convert("1")
    return img

def draw_screen(epd, fonts, user_id, timestamp, qr_id, metadata, payload):
    font_info, font_main, _ = fonts
    canvas = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(canvas)

    margin = 10
    inner_w = epd.width - margin * 2

    # ヘッダ情報
    draw.text((margin, 5), "User ID:", font=font_info, fill=0)
    draw.text((margin, 21), user_id, font=font_main, fill=0)

    draw.text((margin, 47), "Timestamp:", font=font_info, fill=0)
    draw.text((margin, 63), timestamp, font=font_info, fill=0)

    # メタデータ表示（JSONのname/description）
    y = 85
    draw.text((margin, y), "Name:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("name", ""), font_main, inner_w):
        draw.text((margin, y), line, font=font_main, fill=0)
        y += 20

    draw.text((margin, y), "Description:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("description", ""), font=font_info, max_width=inner_w):
        if y > epd.height * 0.55:  # QRのための余白確保
            draw.text((margin, y), "…", font=font_info, fill=0)
            y += 14
            break
        draw.text((margin, y), line, font=font_info, fill=0)
        y += 14

    # QR種別ラベル
    mode_label = {"json": "QR: JSON", "image": "QR: image URL", "url": "QR: link"}[QR_MODE]
    # 長すぎるときはプレビューを省略
    preview = payload if QR_MODE != "json" else metadata.get("image", "")
    while draw.textlength(f"{mode_label}  {preview}", font=font_info) > inner_w and len(preview) > 8:
        preview = preview[:-2] + "…"
    y_label = int(epd.height - epd.height * 0.45) - 16
    y_label = max(y + 4, y_label)
    draw.text((margin, y_label), f"{mode_label}  {preview}", font=font_info, fill=0)

    # QRコードは下部中央
    qr_img = make_qr_image(payload)
    qr_size = min(180, epd.width - 40, int(epd.height * 0.42))
    qr_img_resized = qr_img.resize((qr_size, qr_size))
    qr_x = (epd.width - qr_size) // 2
    qr_y = epd.height - qr_size
    canvas.paste(qr_img_resized, (qr_x, qr_y))

    # QR ID表示（運用確認用）
    draw.text((margin, 5 + 84), f"(QR ID: {qr_id})", font=font_info, fill=0)

    epd.display(epd.getbuffer(canvas))

try:
    epd = epd2in7.EPD()
    epd.init()
    epd.Clear()

    font_info, font_main, font_success = load_fonts()
    user_id = "user-t-8821"

    while True:
        # --- 1) メタデータのロード & QR用ペイロード生成 ---
        metadata = load_metadata()  # metadata.json を配置すれば即時反映
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qr_id = str(uuid.uuid4().hex)[:8]

        payload = build_qr_payload(user_id, qr_id, metadata)
        logging.info(f"QR_MODE={QR_MODE}, payload preview: {payload[:120]}{'...' if len(payload)>120 else ''}")

        # --- 2) 画面描画 ---
        draw_screen(epd, (font_info, font_main, font_success), user_id, timestamp, qr_id, metadata, payload)

        # --- 3) スキャン監視 or 待機 ---
        is_scanned = False
        if WAIT_FOR_SCAN:
            flag_filename = f"scanned_{qr_id}.flag"
            logging.info(f"Waiting for scan... (Timeout: {TIMEOUT_SECONDS}s)")
            for _ in range(TIMEOUT_SECONDS):
                # 個別フラグ or 汎用フラグのどちらでもOKにしておく
                if os.path.exists(flag_filename):
                    is_scanned = True
                    os.remove(flag_filename)
                    break
                generic = glob.glob("scanned_*.flag")
                if generic:
                    is_scanned = True
                    for g in generic:
                        try:
                            os.remove(g)
                        except Exception:
                            pass
                    break
                time.sleep(1)
        else:
            logging.info(f"Displaying for {TIMEOUT_SECONDS}s (WAIT_FOR_SCAN=0)")
            time.sleep(TIMEOUT_SECONDS)

        # --- 4) 結果表示 ---
        if is_scanned:
            display_message(epd, font_success, "読み取り成功！")
            time.sleep(3)
        else:
            logging.info("Next QR...")

        epd.Clear()  # 次の表示へ

except IOError as e:
    logging.error(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    if epd is not None:
        try:
            epd.Clear()
            epd.sleep()
        except Exception:
            pass
    for f in glob.glob("scanned_*.flag"):
        try:
            os.remove(f)
        except Exception:
            pass
    epd2in7.epdconfig.module_exit(cleanup=True)
    sys.exit(0)
