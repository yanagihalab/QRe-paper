#!/usr/bin/python 
# -*- coding:utf-8 -*-
import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
#from waveshare_epd import epd2in7_V2 as epd2in7 # v2
from waveshare_epd import epd2in7 # v1
import time
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
import uuid
import json  # ★追加
import hashlib
import csv

logging.basicConfig(level=logging.DEBUG)

# --- ★重要★ ---
# この部分をあなたのRaspberry PiのIPアドレスに変更してください
SERVER_IP = "192.168.100.20" 
# -----------------

csv_filename = "qr_data2.csv"
file_exists = os.path.exists(csv_filename)

epd = None

def display_message(epd, font, message):
    """画面中央にメッセージを表示する関数"""
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    
    # テキストのサイズを取得して中央揃えにする
    bbox = draw.textbbox((0,0), message, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (epd.width - text_width) // 2
    y = (epd.height - text_height) // 2
    
    draw.text((x, y), message, font=font, fill=0)
    epd.display(epd.getbuffer(image))

try:
    epd = epd2in7.EPD()
    epd.init()
    epd.Clear()

    font_path = os.path.join(picdir, 'Font.ttc')
    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 14)
        font_main = ImageFont.truetype(font_path, 18)
        font_success = ImageFont.truetype(font_path, 24)
    else:
        font_info = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_success = ImageFont.load_default()

    node_id = "node-t-8823"

    while True:
        # --- 1. 新しいQRコードの準備 ---
        csv_data = {}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 各QRコードをユニークに識別するためのIDを生成
        qr_id = str(uuid.uuid4().hex)
        
        source_hash = {'node_id': node_id, 'qr_id':qr_id,'timestamp': timestamp}
        source_string = json.dumps(source_hash, sort_keys=True)
        unique_id = hashlib.sha256(source_string.encode('utf-8')).hexdigest()
        

        # ★変更: 指定のJSON + timestamp をQRの中身にする（URLではなくJSON）
        payload_obj = {
            "node_id": node_id,
            "name": "yama log e-paper",
            "description": "yama log QRe-paper",
            "unique_id": unique_id,
            "qr_id": qr_id
        }
        qr_payload = json.dumps(payload_obj, ensure_ascii=False, separators=(',', ':'))
        logging.info(f"Generated QR JSON (preview): {qr_payload[:80]}...")

        # ★変更: version=None（自動）でJSONをエンコード
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=4)
        qr.add_data(qr_payload)  # ← JSONを追加
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        csv_data.update(payload_obj)
        csv_data.update(source_hash)

        field_names = csv_data.keys()
        with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            if not file_exists:
                writer.writeheader()
            writer.writerow(csv_data)

        # ★追加: ページURL用の小さいQRを別途生成（payload_objとは別）
        page_qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=2)
        page_qr.add_data(qr_payload)
        page_qr.make(fit=True)
        page_qr_img = page_qr.make_image(fill_color="black", back_color="white")

        # --- 2. e-paperにQRコードと情報を表示 ---
        canvas = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 5), "Node ID:", font=font_info, fill=0)
        draw.text((10, 21), node_id, font=font_main, fill=0)
        draw.text((10, 47), "Timestamp:", font=font_info, fill=0)
        draw.text((10, 63), timestamp, font=font_info, fill=0)
        draw.text((10, 89), f"(QR ID: {qr_id[8:]})", font=font_info, fill=0)
        
        # 大きい（メイン）QR：JSON
        qr_size = 180
        qr_img_resized = qr_img.resize((qr_size, qr_size))
        qr_x = (epd.width - qr_size) // 2
        qr_y = epd.height - qr_size
        canvas.paste(qr_img_resized, (qr_x, qr_y))

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
                os.remove(flag_filename) # フラグファイルを削除
                break
            time.sleep(1)

        # --- 4. 結果を表示 ---
        if is_scanned:
            display_message(epd, font_success, "読み取り成功！")
            time.sleep(5) # 成功メッセージを5秒間表示
        else:
            logging.info("Timeout. Generating new QR code.")
            # タイムアウトした場合、メッセージは表示せずに次のループへ
        
        epd.Clear() # 次の表示のために画面をクリア

except IOError as e:
    logging.error(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    if epd is not None:
        epd.Clear()
        epd.sleep()
    # 存在する可能性のあるフラグファイルを削除
    import glob
    for f in glob.glob("scanned_*.flag"):
        os.remove(f)
    epd2in7.epdconfig.module_exit(cleanup=True)
    exit()
