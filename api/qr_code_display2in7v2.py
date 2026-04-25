#!/usr/bin/python3
# -*- coding:utf-8 -*-

import sys
import os
import logging
import time
from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime
import uuid
import json
import hashlib
import csv
import glob

# ============================================================
# Path settings
# ============================================================

BASE_DIR = "/home/yamalog-8/Desktop/QRe-paper/e-Paper/RaspberryPi_JetsonNano/python"
picdir = os.path.join(BASE_DIR, "pic")
libdir = os.path.join(BASE_DIR, "lib")

if os.path.exists(libdir):
    sys.path.insert(0, libdir)

# ============================================================
# Waveshare 2.7inch V2 e-Paper driver
# ============================================================

from waveshare_epd import epd2in7_V2

logging.basicConfig(level=logging.DEBUG)

# ============================================================
# User settings
# ============================================================

csv_filename = "qr_data2in7v2.csv"
node_id = "node-s-2in7v2"

epd = None


# ============================================================
# Utility functions
# ============================================================

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """Pillowのバージョン差を吸収してテキストサイズを返す"""
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return (r - l, b - t)
    except Exception:
        return draw.textsize(text, font=font)


def _clear_epd(epd):
    """Waveshareドライバ差を吸収して画面をクリアする"""
    try:
        epd.Clear(0xFF)
    except TypeError:
        epd.Clear()


def _display_epd(epd, image):
    """
    2.7inch V2 用の表示処理。
    白黒e-Paperなので1bit画像として渡す。
    """
    image = image.convert("1")
    epd.display(epd.getbuffer(image))


def display_message(epd, font, message):
    """画面中央にメッセージを表示する"""
    image = Image.new("1", (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)

    tw, th = _text_size(draw, message, font)
    x = (epd.width - tw) // 2
    y = (epd.height - th) // 2

    draw.text((x, y), message, font=font, fill=0)
    _display_epd(epd, image)


def load_fonts():
    """フォントを読み込む。存在しない場合はデフォルトフォントを使う"""
    font_path = os.path.join(picdir, "Font.ttc")

    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 12)
        font_main = ImageFont.truetype(font_path, 16)
        font_small = ImageFont.truetype(font_path, 11)
        font_success = ImageFont.truetype(font_path, 22)
    else:
        font_info = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_success = ImageFont.load_default()

    return font_info, font_main, font_small, font_success


def write_csv(payload_obj, source_hash):
    """QR生成情報をCSVに追記する"""
    csv_data = {}
    csv_data.update(payload_obj)
    csv_data.update(source_hash)

    file_exists = os.path.exists(csv_filename)
    field_names = list(csv_data.keys())

    with open(csv_filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names)

        if not file_exists:
            writer.writeheader()

        writer.writerow(csv_data)


def make_qr_image(qr_payload):
    """QRコード画像を生成する"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )

    qr.add_data(qr_payload)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("1")


def create_display_canvas(epd, qr_img, timestamp, qr_id,
                          font_info, font_main, font_small):
    """
    2.7inch V2 用レイアウト。

    QRコードを画面下部中央に配置する。
    """
    width = epd.width
    height = epd.height

    canvas = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(canvas)

    margin = 5

    # 外枠
    draw.rectangle((0, 0, width - 1, height - 1), outline=0, width=1)

    # 上部情報
    y = margin

    title = "YamaLog QRe"
    draw.text((margin, y), title, font=font_main, fill=0)
    _, h = _text_size(draw, title, font_main)
    y += h + 3

    node_line = f"Node: {node_id}"
    draw.text((margin, y), node_line, font=font_small, fill=0)
    _, h = _text_size(draw, node_line, font_small)
    y += h + 2

    draw.text((margin, y), timestamp, font=font_small, fill=0)
    _, h = _text_size(draw, timestamp, font_small)
    y += h + 2

    short_qr_id = qr_id[-8:]
    qrid_line = f"QR: {short_qr_id}"
    draw.text((margin, y), qrid_line, font=font_small, fill=0)
    _, h = _text_size(draw, qrid_line, font_small)
    y += h + 2

    # QRコードを画面下部中央に配置
    qr_area_h = height - y - margin
    qr_size = min(width - margin * 2, qr_area_h)

    # 小さすぎる場合の下限
    qr_size = max(80, int(qr_size))

    # 画面からはみ出す場合の安全調整
    qr_size = min(qr_size, width - margin * 2, height - margin * 2)

    qr_img_resized = qr_img.resize(
        (qr_size, qr_size),
        Image.NEAREST
    ).convert("1")

    qr_x = (width - qr_size) // 2
    qr_y = height - qr_size - margin

    canvas.paste(qr_img_resized, (qr_x, qr_y))

    return canvas


# ============================================================
# Main
# ============================================================

try:
    epd = epd2in7_V2.EPD()

    logging.info("epd2in7_V2 QR Display")
    logging.info(f"width={epd.width}, height={epd.height}")

    epd.init()
    _clear_epd(epd)

    font_info, font_main, font_small, font_success = load_fonts()

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qr_id = str(uuid.uuid4().hex)

        source_hash = {
            "node_id": node_id,
            "qr_id": qr_id,
            "timestamp": timestamp,
        }

        source_string = json.dumps(source_hash, sort_keys=True)
        unique_id = hashlib.sha256(
            source_string.encode("utf-8")
        ).hexdigest()

        payload_obj = {
            "node_id": node_id,
            "name": "yama log e-paper",
            "description": "yama log QRe-paper",
            "unique_id": unique_id,
            "qr_id": qr_id,
        }

        qr_payload = json.dumps(
            payload_obj,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        logging.info(f"Generated QR JSON preview: {qr_payload[:100]}...")

        qr_img = make_qr_image(qr_payload)

        write_csv(payload_obj, source_hash)

        canvas = create_display_canvas(
            epd=epd,
            qr_img=qr_img,
            timestamp=timestamp,
            qr_id=qr_id,
            font_info=font_info,
            font_main=font_main,
            font_small=font_small,
        )

        _display_epd(epd, canvas)

        flag_filename = f"scanned_{qr_id}.flag"
        timeout_seconds = 3
        is_scanned = False

        logging.info(f"Waiting for scan... Timeout: {timeout_seconds}s")
        logging.info(f"Flag file: {flag_filename}")

        for _ in range(timeout_seconds):
            if os.path.exists(flag_filename):
                logging.info("QR Code has been scanned.")
                is_scanned = True

                try:
                    os.remove(flag_filename)
                except Exception:
                    pass

                break

            time.sleep(1)

        if is_scanned:
            display_message(epd, font_success, "OK")
            time.sleep(3)

        # 更新速度優先のため毎回Clearしない
        # _clear_epd(epd)

except IOError as e:
    logging.error(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")

    if epd is not None:
        try:
            _clear_epd(epd)
        except Exception:
            pass

        try:
            epd.sleep()
        except Exception:
            pass

    for f in glob.glob("scanned_*.flag"):
        try:
            os.remove(f)
        except Exception:
            pass

    try:
        epd2in7_V2.epdconfig.module_exit(cleanup=True)
    except Exception:
        pass

    exit()
