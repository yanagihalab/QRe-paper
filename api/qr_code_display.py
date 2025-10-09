#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
# ★ 2.13inch V4 用ライブラリに変更
from waveshare_epd import epd2in13_V4 as epd2in13

import time
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
import uuid
import json
import hashlib
import csv

logging.basicConfig(level=logging.DEBUG)

# --- ★重要★ ---
# この部分をあなたのRaspberry PiのIPアドレスに変更してください（使っていない場合は無視してOK）
SERVER_IP = "192.168.100.15"
# -----------------

csv_filename = "qr_data2.csv"
file_exists = os.path.exists(csv_filename)

epd = None

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """Pillowのバージョン差を吸収してテキストサイズを返す"""
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return (r - l, b - t)
    except Exception:
        return draw.textsize(text, font=font)

def display_message(epd, font, message):
    """画面中央にメッセージを表示する関数（2.13 V4: 250x122）"""
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    tw, th = _text_size(draw, message, font)
    x = (epd.width - tw) // 2
    y = (epd.height - th) // 2
    draw.text((x, y), message, font=font, fill=0)
    epd.display(epd.getbuffer(image))

try:
    epd = epd2in13.EPD()
    epd.init()
    # 一度全消去
    try:
        epd.Clear(0xFF)
    except TypeError:
        epd.Clear()

    # フォント準備
    font_path = os.path.join(picdir, 'Font.ttc')
    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 14)
        font_main = ImageFont.truetype(font_path, 18)
        font_success = ImageFont.truetype(font_path, 24)
    else:
        font_info = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_success = ImageFont.load_default()

    node_id = "node-s-8213"

    while True:
        # --- 1. 新しいQRコードの準備 ---
        csv_data = {}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qr_id = str(uuid.uuid4().hex)

        # 固有ID
        source_hash = {'node_id': node_id, 'qr_id': qr_id, 'timestamp': timestamp}
        source_string = json.dumps(source_hash, sort_keys=True)
        unique_id = hashlib.sha256(source_string.encode('utf-8')).hexdigest()

        # QR ペイロード（JSON）
        payload_obj = {
            "node_id": node_id,
            "name": "yama log e-paper",
            "description": "yama log QRe-paper",
            "unique_id": unique_id,
            "qr_id": qr_id
            # 必要なら "timestamp": timestamp を追加
        }
        qr_payload = json.dumps(payload_obj, ensure_ascii=False, separators=(',', ':'))
        logging.info(f"Generated QR JSON (preview): {qr_payload[:80]}...")

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=4
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

        # CSV 追記
        csv_data.update(payload_obj)
        csv_data.update(source_hash)
        field_names = list(csv_data.keys())
        write_header_now = (not file_exists) and (not os.path.exists(csv_filename))
        with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            if write_header_now:
                writer.writeheader()
            writer.writerow(csv_data)

        # --- 2. e-paperにQRコードと情報を表示 ---
        margin = 4
        canvas = Image.new('1', (epd.width, epd.height), 255)  # 2.13 V4 は (122, 250)（縦長）
        draw = ImageDraw.Draw(canvas)

        # 上部情報（動的に行間を計算）
        y = margin
        draw.text((10, y), "Node ID:", font=font_info, fill=0)
        _, h_info = _text_size(draw, "Node ID:", font_info)
        y += h_info + 2

        draw.text((10, y), node_id, font=font_main, fill=0)
        _, h_main = _text_size(draw, node_id, font_main)
        y += h_main + 6

        draw.text((10, y), "Timestamp:", font=font_info, fill=0)
        _, h_info2 = _text_size(draw, "Timestamp:", font=font_info)
        y += h_info2 + 2

        draw.text((10, y), timestamp, font=font_info, fill=0)
        _, h_stamp = _text_size(draw, timestamp, font=font_info)
        y += h_stamp + 2

        draw.text((10, y), f"(QR ID: {qr_id[-8:]})", font=font_info, fill=0)
        _, h_qrid = _text_size(draw, f"(QR ID: {qr_id[-8:]})", font=font_info)
        y += h_qrid + 4

        # QR サイズを自動決定（テキスト領域の下、画面下部に収める）
        max_qr_w = epd.width - 2 * margin
        max_qr_h = epd.height - y - 2 * margin
        qr_size = max(40, min(max_qr_w, max_qr_h))  # 最低40px、可能な最大

        # 万一スペースが足りない場合は、上の情報を少し圧縮
        if qr_size < 40:
            # 文字を最小限にして再計算
            canvas = Image.new('1', (epd.width, epd.height), 255)
            draw = ImageDraw.Draw(canvas)
            y = margin
            draw.text((10, y), node_id, font=font_main, fill=0)
            _, h_main = _text_size(draw, node_id, font=font_main)
            y += h_main + 4
            draw.text((10, y), timestamp, font=font_info, fill=0)
            _, h_stamp = _text_size(draw, timestamp, font=font_info)
            y += h_stamp + 4
            max_qr_h = epd.height - y - 2 * margin
            qr_size = max(32, min(max_qr_w, max_qr_h))

        # QR をリサイズして下部に配置（中央寄せ）
        qr_img_resized = qr_img.resize((int(qr_size), int(qr_size)), Image.NEAREST).convert("1")
        qr_x = (epd.width - int(qr_size)) // 2
        qr_y = epd.height - int(qr_size) - margin
        canvas.paste(qr_img_resized, (qr_x, qr_y))

        # 表示
        epd.display(epd.getbuffer(canvas))

        # --- 3. QRコードがスキャンされるのを待つ ---
        flag_filename = f"scanned_{qr_id}.flag"
        timeout_seconds = 10
        is_scanned = False

        logging.info(f"Waiting for scan... (Timeout: {timeout_seconds}s)")
        for _ in range(timeout_seconds):
            if os.path.exists(flag_filename):
                logging.info("QR Code has been scanned!")
                is_scanned = True
                try:
                    os.remove(flag_filename)  # フラグファイルを削除
                except Exception:
                    pass
                break
            time.sleep(1)

        # --- 4. 結果を表示 ---
        if is_scanned:
            display_message(epd, font_success, "読み取り成功！")
            time.sleep(5)  # 成功メッセージを5秒表示

        # 次の表示に備えてクリア
        try:
            epd.Clear(0xFF)
        except TypeError:
            epd.Clear()

except IOError as e:
    logging.error(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    if epd is not None:
        try:
            epd.Clear(0xFF)
        except Exception:
            pass
        try:
            epd.sleep()
        except Exception:
            pass
    # 存在する可能性のあるフラグファイルを削除
    import glob
    for f in glob.glob("scanned_*.flag"):
        try:
            os.remove(f)
        except Exception:
            pass
    # ★ 2.13inch V4 の終了処理
    epd2in13.epdconfig.module_exit(cleanup=True)
    exit()

