#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# ============================================================
# GPIO backend
# ============================================================

os.environ.setdefault(
    "GPIOZERO_PIN_FACTORY",
    os.environ.get("GPIOZERO_PIN_FACTORY", "lgpio")
)

# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

EPAPER_BASE_DIR = Path(
    os.environ.get(
        "EPAPER_BASE_DIR",
        "/home/yamalog-6/Desktop/QRe-paper/waveshare-e-Paper-latest/E-paper_Separate_Program/3in7_e-Paper_G/RaspberryPi_JetsonNano/python"
    )
)

picdir = str(EPAPER_BASE_DIR / "pic")
libdir = str(EPAPER_BASE_DIR / "lib")

# venv 側の waveshare_epd より、3in7g 用ローカルライブラリを優先する
if os.path.exists(libdir):
    sys.path.insert(0, libdir)

# ============================================================
# Libraries
# ============================================================

from waveshare_epd import epd3in7g  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore
import qrcode  # type: ignore

logging.basicConfig(level=logging.INFO)

# ============================================================
# Config
# ============================================================

NODE_ID = os.environ.get("NODE_ID", "node-s-3in7g")

NODE_BIN = os.environ.get("NODE_BIN", "node")
SEND_JS = os.environ.get("SEND_JS", "send_set_value.js")

CSV_FILENAME = os.environ.get("CSV_FILENAME", "qr_tx_log_yamalog_epaper_3in7g.csv")

N_TRIALS = int(os.environ.get("N_TRIALS", "0"))  # 0 = infinite

# 表示保持時間。既定値は3分。
DISPLAY_HOLD_SEC = int(os.environ.get("DISPLAY_HOLD_SEC", "180"))

SLEEP_BETWEEN_SEC = float(os.environ.get("SLEEP_BETWEEN_SEC", "0"))

NODE_SEND_TIMEOUT_SEC = float(os.environ.get("NODE_SEND_TIMEOUT_SEC", "180"))

# TXに送る value
# 1: {"payload": {...}} を送る
# 0: unique_id のみ送る
SEND_FULL_PAYLOAD = os.environ.get("SEND_FULL_PAYLOAD", "1") == "1"

# QRに txhash を追加するか
# payload 自体は5項目のまま維持し、txhash は payload の外側に入れる
INCLUDE_TXHASH_IN_QR = os.environ.get("INCLUDE_TXHASH_IN_QR", "1") == "1"


# ============================================================
# Timing
# ============================================================

@dataclass
class Timing:
    t0_ns: int
    t1_ns: int
    t2_ns: int

    @staticmethod
    def now_ns() -> int:
        return time.perf_counter_ns()

    @staticmethod
    def ns_to_ms(ns: int) -> float:
        return ns / 1e6

    @property
    def txhash_ms(self) -> float:
        return self.ns_to_ms(self.t1_ns - self.t0_ns)

    @property
    def display_ms(self) -> float:
        return self.ns_to_ms(self.t2_ns - self.t1_ns)

    @property
    def total_ms(self) -> float:
        return self.ns_to_ms(self.t2_ns - self.t0_ns)


# ============================================================
# Utility
# ============================================================

def safe_text(s: str) -> str:
    try:
        s.encode("latin-1")
        return s
    except UnicodeEncodeError:
        return s.encode("ascii", "replace").decode("ascii")


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    except Exception:
        return draw.textsize(text, font=font)


def clear_epd(epd) -> None:
    try:
        epd.Clear(0xFF)
    except TypeError:
        epd.Clear()


def display_epd(epd, image: Image.Image) -> None:
    """
    epd3in7g 用表示処理。

    3.7inch G は白・黒・赤・黄の4色系で、RGB画像を getbuffer に渡す。
    QR本体は読み取り安定性のため黒白で作成し、
    ステータス表示やヘッダには赤・黄を使用する。
    """
    rgb = image.convert("RGB")
    epd.display(epd.getbuffer(rgb))


def load_fonts():
    font_path = os.path.join(picdir, "Font.ttc")

    if os.path.exists(font_path):
        font_info = ImageFont.truetype(font_path, 14)
        font_main = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 13)
        font_status = ImageFont.truetype(font_path, 28)
    else:
        font_info = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_status = ImageFont.load_default()

    return font_info, font_main, font_small, font_status


def display_message(epd, font, message: str) -> None:
    message = safe_text(message)

    image = Image.new("RGB", (epd.width, epd.height), "white")
    draw = ImageDraw.Draw(image)

    # 枠とタイトル帯
    draw.rectangle((0, 0, epd.width - 1, epd.height - 1), outline="black", width=2)
    draw.rectangle((0, 0, epd.width - 1, 34), fill="yellow", outline="black")
    draw.text((8, 7), "YamaLog QRe-paper", font=font, fill="black")

    w, h = text_size(draw, message, font)
    x = (epd.width - w) // 2
    y = (epd.height - h) // 2

    draw.text((x, y), message, font=font, fill="red")
    display_epd(epd, image)


# ============================================================
# yamalog-epaper payload
# ============================================================

def make_yamalog_payload(node_id: str) -> Dict[str, Any]:
    """
    QR / TXで扱う yamalog-epaper payload。

    payload は5項目：
      - node_id
      - name
      - description
      - unique_id
      - qr_id
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    qr_id = uuid.uuid4().hex

    source_hash = {
        "node_id": node_id,
        "qr_id": qr_id,
        "timestamp": timestamp
    }

    source_string = json.dumps(source_hash, sort_keys=True)
    unique_id = hashlib.sha256(
        source_string.encode("utf-8")
    ).hexdigest()

    payload = {
        "node_id": node_id,
        "name": "yama log e-paper",
        "description": "yama log QRe-paper",
        "unique_id": unique_id,
        "qr_id": qr_id,
    }

    return {
        "payload": payload,
        "timestamp": timestamp,
    }


def make_qr_json(payload: Dict[str, Any], txhash: str) -> str:
    """
    QRに格納するJSON。

    payload は指定された5項目を維持する。
    txhash は payload の外側に付ける。
    """
    obj: Dict[str, Any] = {
        "payload": payload
    }

    if INCLUDE_TXHASH_IN_QR and txhash:
        obj["txhash"] = txhash

    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":")
    )


def make_qr_image(qr_json: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=3,
    )

    qr.add_data(qr_json)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")


# ============================================================
# Node.js TX sender
# ============================================================

def call_node_send(value: str, memo: str, timeout_sec: float) -> Dict[str, Any]:
    """
    send_set_value.js に JSON を stdin で渡して TX を送信する。

    入力：
      {
        "value": "...",
        "memo": "..."
      }

    期待出力：
      {
        "ok": true,
        "txhash": "...",
        ...
      }
    """
    inp_obj = {
        "value": value,
        "memo": memo
    }

    inp = json.dumps(
        inp_obj,
        ensure_ascii=False
    ).encode("utf-8")

    env = os.environ.copy()
    env["NODE_BROADCAST_TIMEOUT_SEC"] = env.get(
        "NODE_BROADCAST_TIMEOUT_SEC",
        str(timeout_sec)
    )

    try:
        p = subprocess.run(
            [NODE_BIN, SEND_JS],
            input=inp,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR),
            timeout=timeout_sec,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"node subprocess timeout after {timeout_sec}s",
            "error_type": "SubprocessTimeout",
            "subprocess_returncode": "timeout",
        }

    out = p.stdout.decode("utf-8", errors="replace").strip()
    err = p.stderr.decode("utf-8", errors="replace").strip()

    try:
        result = json.loads(out) if out else {
            "ok": False,
            "error": "empty stdout",
            "error_type": "EmptyStdout"
        }
    except Exception:
        result = {
            "ok": False,
            "error": f"stdout not json: {out[:300]}",
            "error_type": "InvalidJsonStdout"
        }

    if err:
        result["stderr"] = err[:2000]

    result["subprocess_returncode"] = p.returncode
    return result


# ============================================================
# CSV
# ============================================================

def append_csv(row: Dict[str, Any], csv_filename: str) -> None:
    path = Path(csv_filename)
    file_exists = path.exists()

    fieldnames = list(row.keys())

    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            w.writeheader()

        w.writerow(row)


# ============================================================
# Rendering
# ============================================================

def draw_truncated(
    draw: ImageDraw.ImageDraw,
    xy,
    label: str,
    value: str,
    font_label,
    font_value,
    max_chars: int = 26,
) -> int:
    x, y = xy

    value = safe_text(str(value))
    if len(value) > max_chars:
        value = value[:max_chars] + "..."

    draw.text((x, y), safe_text(label), font=font_label, fill="red")
    _, h1 = text_size(draw, label, font_label)
    y += h1 + 1

    draw.text((x + 4, y), value, font=font_value, fill="black")
    _, h2 = text_size(draw, value, font_value)
    y += h2 + 4

    return y


def render_qr_canvas(
    epd,
    font_info,
    font_main,
    font_small,
    payload: Dict[str, Any],
    timestamp: str,
    txhash: str,
) -> Image.Image:
    qr_json = make_qr_json(payload, txhash)
    qr_img = make_qr_image(qr_json)

    canvas = Image.new("RGB", (epd.width, epd.height), "white")
    draw = ImageDraw.Draw(canvas)

    margin = 8
    width = epd.width
    height = epd.height

    # 外枠
    draw.rectangle((0, 0, width - 1, height - 1), outline="black", width=2)

    # 上部タイトル帯
    header_h = 34
    draw.rectangle((0, 0, width - 1, header_h), fill="yellow", outline="black")
    draw.text((margin, 7), "YamaLog QRe-paper", font=font_main, fill="black")

    # --------------------------------------------------------
    # 情報表示：上部に横並び気味に圧縮
    # QRは画面下部中央に配置
    # --------------------------------------------------------
    y = header_h + 6

    left_x = margin
    right_x = width // 2 + 4

    # 左側
    y_left = y
    y_left = draw_truncated(draw, (left_x, y_left), "node_id:", payload["node_id"], font_small, font_small, 24)
    y_left = draw_truncated(draw, (left_x, y_left), "unique:", payload["unique_id"][:16] + "...", font_small, font_small, 24)

    # 右側
    y_right = y
    y_right = draw_truncated(draw, (right_x, y_right), "qr_id:", payload["qr_id"][:16] + "...", font_small, font_small, 24)
    y_right = draw_truncated(draw, (right_x, y_right), "tx:", (".." + txhash[-16:]) if txhash else "(none)", font_small, font_small, 24)

    # timestamp は中央寄せで1行
    ts_text = safe_text(timestamp)
    tw, th = text_size(draw, ts_text, font_small)
    draw.text(((width - tw) // 2, max(y_left, y_right) + 2), ts_text, font=font_small, fill="black")

    # --------------------------------------------------------
    # QRコード：画面下部中央
    # --------------------------------------------------------
    info_bottom = max(y_left, y_right) + th + 6

    qr_size = min(width - margin * 2, height - info_bottom - margin)
    qr_size = max(120, int(qr_size))

    # 画面内に収める
    qr_size = min(qr_size, width - margin * 2, height - header_h - margin * 2)

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

def main() -> None:
    epd = None

    try:
        epd = epd3in7g.EPD()

        logging.info("yamalog-epaper TX -> QR Display for epd3in7g")
        logging.info("GPIOZERO_PIN_FACTORY=%s", os.environ.get("GPIOZERO_PIN_FACTORY"))
        logging.info("EPAPER_BASE_DIR=%s", EPAPER_BASE_DIR)
        logging.info("libdir=%s", libdir)
        logging.info("width=%s height=%s", epd.width, epd.height)
        logging.info("DISPLAY_HOLD_SEC=%s", DISPLAY_HOLD_SEC)
        logging.info("SEND_JS=%s", str(BASE_DIR / SEND_JS))

        epd.init()
        clear_epd(epd)

        font_info, font_main, font_small, font_status = load_fonts()

        trial = 0

        while True:
            trial += 1

            if N_TRIALS > 0 and trial > N_TRIALS:
                break

            # --------------------------------------------------------
            # 1. payload作成
            # --------------------------------------------------------
            t0 = Timing.now_ns()

            payload_pack = make_yamalog_payload(NODE_ID)
            payload = payload_pack["payload"]
            timestamp = payload_pack["timestamp"]

            qr_id = payload["qr_id"]
            unique_id = payload["unique_id"]

            tx_value_obj = {
                "payload": payload
            }

            if SEND_FULL_PAYLOAD:
                value_onchain = json.dumps(
                    tx_value_obj,
                    ensure_ascii=False,
                    separators=(",", ":")
                )
            else:
                value_onchain = unique_id

            memo = f"yamalog-epaper:{qr_id[:12]}"

            # --------------------------------------------------------
            # 2. TX送信
            # --------------------------------------------------------
            display_message(epd, font_status, "Sending TX...")

            res = call_node_send(
                value=value_onchain,
                memo=memo,
                timeout_sec=NODE_SEND_TIMEOUT_SEC,
            )

            t1 = Timing.now_ns()

            ok = bool(res.get("ok", False))
            txhash = str(res.get("txhash", "")) if ok else ""

            # --------------------------------------------------------
            # 3. TX確定後にQR生成・表示
            # --------------------------------------------------------
            if ok and txhash:
                display_message(epd, font_status, "TX OK")
                time.sleep(1)

                canvas = render_qr_canvas(
                    epd=epd,
                    font_info=font_info,
                    font_main=font_main,
                    font_small=font_small,
                    payload=payload,
                    timestamp=timestamp,
                    txhash=txhash,
                )

                display_epd(epd, canvas)

            else:
                display_message(epd, font_status, "TX FAILED")

            t2 = Timing.now_ns()
            timing = Timing(t0_ns=t0, t1_ns=t1, t2_ns=t2)

            # --------------------------------------------------------
            # 4. CSV記録
            # --------------------------------------------------------
            row = {
                "trial": trial,
                "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_payload_generated": timestamp,
                "node_id": payload["node_id"],
                "name": payload["name"],
                "description": payload["description"],
                "qr_id": qr_id,
                "unique_id": unique_id,
                "tx_ok": ok,
                "txhash": txhash,
                "txhash_ms": round(timing.txhash_ms, 3),
                "display_ms": round(timing.display_ms, 3),
                "total_ms": round(timing.total_ms, 3),
                "broadcast_ms_node": res.get("broadcast_ms", ""),
                "height": res.get("height", ""),
                "code": res.get("code", ""),
                "gasWanted": res.get("gasWanted", ""),
                "gasUsed": res.get("gasUsed", ""),
                "timestamp_chain": res.get("timestamp", ""),
                "sender": res.get("sender", ""),
                "contract": res.get("contract", ""),
                "network": res.get("network", ""),
                "value_len": len(value_onchain),
                "subprocess_returncode": res.get("subprocess_returncode", ""),
                "error_type": res.get("error_type", ""),
                "error": res.get("error", ""),
                "stderr": res.get("stderr", ""),
            }

            append_csv(row, CSV_FILENAME)

            logging.info(
                "[%d] ok=%s txhash_ms=%.3f display_ms=%.3f total_ms=%.3f txhash=%s error_type=%s",
                trial,
                ok,
                row["txhash_ms"],
                row["display_ms"],
                row["total_ms"],
                txhash[-10:] if txhash else "-",
                row["error_type"] or "-",
            )

            # --------------------------------------------------------
            # 5. 表示保持
            # --------------------------------------------------------
            if DISPLAY_HOLD_SEC > 0:
                time.sleep(DISPLAY_HOLD_SEC)

            clear_epd(epd)

            if SLEEP_BETWEEN_SEC > 0:
                time.sleep(SLEEP_BETWEEN_SEC)

    except KeyboardInterrupt:
        logging.info("ctrl + c")

    finally:
        if epd is not None:
            try:
                clear_epd(epd)
                epd.sleep()
            except Exception:
                pass

        try:
            epd3in7g.epdconfig.module_exit(cleanup=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
