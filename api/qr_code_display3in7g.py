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
# Waveshare 3.7 inch G e-Paper driver
# White / Black / Red / Yellow
# ============================================================

from waveshare_epd import epd3in7g

logging.basicConfig(level=logging.DEBUG)

# ============================================================
# User settings
# ============================================================

SERVER_IP = "192.168.100.15"

csv_filename = "qr_data3in7g.csv"

node_id = "node-s-3in7g"

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
    3.7inch G 用の表示処理。

    epd3in7g は白・黒・赤・黄の4色系なので、
    1bit画像ではなくRGB画像として渡す。
    """
    image = image.convert("RGB")
    epd.display(epd.getbuffer(image))


def display_message(epd, font, message):
    """画面中央にメッセージを表示する"""
    image = Image.new("RGB", (epd.width, epd.height), "white")
    draw = ImageDraw.Draw(image)

    tw, th = _text_size(draw, message, font)
    x = (epd.width - tw) // 2
    y = (epd.height - th) // 2

    draw.text((x, y), message, font=font, fill="red")
    _display_epd(epd, image)


def load_fonts():
    """フォントを読み込む。存在しない場合はデフォルトフォントを使う"""
    font_path = os.path.join(picdir, "Font.ttc")

    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 14)
        font_main = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 13)
        font_success = ImageFont.truetype(font_path, 28)
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
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )

    qr.add_data(qr_payload)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")


def create_display_canvas(epd, qr_img, timestamp, qr_id,
                          font_info, font_main, font_small):
    """
    3.7inch G 用レイアウト。

    表示内容：
      - タイトル
      - Node ID
      - Timestamp
      - QR ID 下8桁
      - QR code

    3.7inch G は色表示が可能なので、
    タイトルや区切り線に赤・黄を使う。
    QR本体は読み取り安定性のため黒白のみ。
    """
    width = epd.width
    height = epd.height

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    margin = 8

    # 枠
    draw.rectangle((0, 0, width - 1, height - 1), outline="black", width=2)

    # 上部タイトル帯
    header_h = 34
    draw.rectangle((0, 0, width - 1, header_h), fill="yellow", outline="black")
    draw.text((margin, 7), "YamaLog QRe-paper", font=font_main, fill="black")

    # 3.7inch G は通常横長として扱う
    left_w = int(width * 0.43)

    x_text = margin
    y = header_h + 10

    draw.text((x_text, y), "Node ID", font=font_info, fill="red")
    _, h = _text_size(draw, "Node ID", font_info)
    y += h + 2

    draw.text((x_text, y), node_id, font=font_main, fill="black")
    _, h = _text_size(draw, node_id, font_main)
    y += h + 10

    draw.text((x_text, y), "Timestamp", font=font_info, fill="red")
    _, h = _text_size(draw, "Timestamp", font_info)
    y += h + 2

    draw.text((x_text, y), timestamp, font=font_small, fill="black")
    _, h = _text_size(draw, timestamp, font_small)
    y += h + 10

    short_qr_id = qr_id[-8:]
    draw.text((x_text, y), "QR ID", font=font_info, fill="red")
    _, h = _text_size(draw, "QR ID", font_info)
    y += h + 2

    draw.text((x_text, y), short_qr_id, font=font_main, fill="black")

    # 左右区切り線は表示しない
    # line_x = left_w
    # draw.line((line_x, header_h + 4, line_x, height - margin), fill="red", width=2)

    # QR配置：画面下部中央
    # 上部の情報表示領域を避けつつ、QRを下中央に配置する
    qr_size = min(width - margin * 2, height - header_h - 56)
    qr_size = max(120, int(qr_size))

    qr_img_resized = qr_img.resize(
        (qr_size, qr_size),
        Image.NEAREST
    ).convert("RGB")

    qr_x = (width - qr_size) // 2
    qr_y = height - qr_size - margin

    # QR背景
    draw.rectangle(
        (qr_x - 4, qr_y - 4, qr_x + qr_size + 4, qr_y + qr_size + 4),
        fill="white",
        outline="black",
        width=2
    )

    canvas.paste(qr_img_resized, (qr_x, qr_y))

    return canvas


# ============================================================
# Main
# ============================================================

try:
    epd = epd3in7g.EPD()

    logging.info("epd3in7g QR Display")
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
        timeout_seconds = 40
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
            display_message(epd, font_success, "読み取り成功！")
            time.sleep(5)

        _clear_epd(epd)

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
        epd3in7g.epdconfig.module_exit(cleanup=True)
    except Exception:
        pass

    exit()
