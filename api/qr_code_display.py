#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys, os, logging, time, uuid, json, glob
from datetime import datetime

picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in7_V2 as epd2in7
from PIL import Image, ImageDraw, ImageFont
import qrcode

logging.basicConfig(level=logging.DEBUG)

# --- Settings ---
SERVER_IP = "192.168.100.15"                       # used only in QR_MODE="url"
QR_MODE = os.environ.get("QR_MODE", "json").lower()  # "json" | "image" | "url"
WAIT_FOR_SCAN = os.environ.get("WAIT_FOR_SCAN", "0") == "1"
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "10"))
METADATA_FILE = os.environ.get("METADATA_FILE", os.path.join(os.path.dirname(__file__), "metadata.json"))
FONT_PATH = os.environ.get("FONT_PATH")  # set to a CJK font path if you later want Japanese rendering

DEFAULT_METADATA = {
    "name": "Participation Certificate NFT",
    "description": "10042025 Fukaya labo-Kikuchi labo Joint Event Participation NFT",
    "image": "https://ipfs.yamada.jo.sus.ac.jp/ipfs/QmTuDCtiZJjRFqiZ6D5X2iNX8ejwNu6Kv1F7EcThej9yHu"
}
# ---------------

epd = None

# ---------- Fonts ----------
def load_fonts():
    # If you later install a CJK font, point FONT_PATH to it.
    try:
        if FONT_PATH and os.path.exists(FONT_PATH):
            f_info = ImageFont.truetype(FONT_PATH, 14)
            f_main = ImageFont.truetype(FONT_PATH, 18)
            f_ok   = ImageFont.truetype(FONT_PATH, 24)
            logging.info(f"Using TrueType font: {FONT_PATH}")
            return f_info, f_main, f_ok, True
    except Exception as e:
        logging.warning(f"Failed to load TrueType font '{FONT_PATH}': {e}")

    # ASCII-safe fallback
    logging.warning("No CJK TrueType font. Falling back to PIL default (ASCII only).")
    f = ImageFont.load_default()
    return f, f, f, False

# Non-ASCII safe text length (avoid UnicodeEncodeError)
def safe_textlength(draw, s, font):
    try:
        return draw.textlength(s, font=font)
    except Exception:
        # very old Pillow: rough fallback
        wA = draw.textlength("A", font=font) or 8
        return wA * len(s)

# Display-only sanitizer (keeps QR payload untouched)
def to_ascii(s, keep='?'):
    if s is None:
        return ""
    try:
        return s.encode("ascii", "replace").decode("ascii").replace("?", keep)
    except Exception:
        return "".join(ch if ord(ch) < 128 else keep for ch in str(s))

def wrap_by_width(draw, text, font, max_width, ascii_only):
    if ascii_only:
        text = to_ascii(text)
    lines, buf = [], ""
    for para in (text or "").splitlines() or [""]:
        buf = ""
        for ch in para:
            nxt = buf + ch
            if safe_textlength(draw, nxt, font) <= max_width:
                buf = nxt
            else:
                lines.append(buf)
                buf = ch
        lines.append(buf)
    return lines

# ---------- Rendering helpers ----------
def display_message(epd, font, message):
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0,0), message, font=font)
    x = (epd.width - (bbox[2]-bbox[0])) // 2
    y = (epd.height - (bbox[3]-bbox[1])) // 2
    draw.text((x, y), message, font=font, fill=0)
    epd.display(epd.getbuffer(image))

def load_metadata():
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                m = json.load(f)
            for k in ("name", "description", "image"):
                if k not in m:
                    raise ValueError(f"metadata missing key: {k}")
            return m
    except Exception as e:
        logging.warning(f"Failed to load metadata file: {e}")
    return DEFAULT_METADATA

def build_qr_payload(user_id, qr_id, metadata):
    if QR_MODE == "json":
        obj = {"name": metadata["name"], "description": metadata["description"], "image": metadata["image"]}
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))  # QR stays UTF-8
    elif QR_MODE == "image":
        return str(metadata["image"])
    else:  # "url"
        return f"http://{SERVER_IP}:5000/scan?user_id={user_id}&qr_id={qr_id}"

def make_qr_image(payload):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(payload)   # qrcode handles UTF-8 fine
    qr.make(fit=True)
    return qr.make_image(fill_color=0, back_color=255).convert("1")

def draw_screen(epd, fonts, ascii_only, user_id, timestamp, qr_id, metadata, payload):
    font_info, font_main, _ = fonts
    canvas = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(canvas)

    margin = 10
    inner_w = epd.width - margin * 2

    # Header (English / ASCII only)
    draw.text((margin, 5),  "User ID:",   font=font_info, fill=0)
    draw.text((margin, 21), to_ascii(user_id) if ascii_only else user_id, font=font_main, fill=0)
    draw.text((margin, 47), "Timestamp:", font=font_info, fill=0)
    draw.text((margin, 63), timestamp,    font=font_info, fill=0)

    # Metadata (display-only sanitization if needed)
    y = 85
    draw.text((margin, y), "Name:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("name",""), font_main, inner_w, ascii_only):
        draw.text((margin, y), line, font=font_main, fill=0)
        y += 20

    draw.text((margin, y), "Description:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("description",""), font=font_info, max_width=inner_w, ascii_only=ascii_only):
        if y > epd.height * 0.55:
            draw.text((margin, y), "...", font=font_info, fill=0)  # ASCII ellipsis
            y += 14
            break
        draw.text((margin, y), line, font=font_info, fill=0)
        y += 14

    # QR label
    mode_label = {"json": "QR: JSON", "image": "QR: image URL", "url": "QR: link"}[QR_MODE]
    preview = payload if QR_MODE != "json" else metadata.get("image","")
    if ascii_only:
        preview = to_ascii(preview)
    # shorten preview using ASCII-only "..."
    while safe_textlength(draw, f"{mode_label}  {preview}", font_info) > inner_w and len(preview) > 8:
        preview = preview[:-2] + "..."
    y_label = max(y + 4, int(epd.height - epd.height * 0.45) - 16)
    draw.text((margin, y_label), f"{mode_label}  {preview}", font=font_info, fill=0)

    # QR image (bottom center)
    qr_img = make_qr_image(payload)
    qr_size = min(180, epd.width - 40, int(epd.height * 0.42))
    qr_img_resized = qr_img.resize((qr_size, qr_size))
    qr_x = (epd.width - qr_size) // 2
    qr_y = epd.height - qr_size
    canvas.paste(qr_img_resized, (qr_x, qr_y))

    # QR ID (ASCII)
    draw.text((margin, 89), f"(QR ID: {qr_id})", font=font_info, fill=0)

    epd.display(epd.getbuffer(canvas))

# ---------- Main ----------
try:
    epd = epd2in7.EPD()
    epd.init()
    epd.Clear()

    font_info, font_main, font_ok, cjk_capable = load_fonts()
    ascii_only = not cjk_capable  # force ASCII if we can't render CJK
    user_id = "user-t-8821"

    while True:
        metadata = load_metadata()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qr_id = str(uuid.uuid4().hex)[:8]
        payload = build_qr_payload(user_id, qr_id, metadata)

        logging.info(f"QR_MODE={QR_MODE}, payload preview: {payload[:120]}{'...' if len(payload)>120 else ''}")
        draw_screen(epd, (font_info, font_main, font_ok), ascii_only, user_id, timestamp, qr_id, metadata, payload)

        is_scanned = False
        if WAIT_FOR_SCAN:
            flag_filename = f"scanned_{qr_id}.flag"
            logging.info(f"Waiting for scan... (Timeout: {TIMEOUT_SECONDS}s)")
            for _ in range(TIMEOUT_SECONDS):
                if os.path.exists(flag_filename):
                    is_scanned = True
                    os.remove(flag_filename)
                    break
                for g in glob.glob("scanned_*.flag"):
                    is_scanned = True
                    try: os.remove(g)
                    except Exception: pass
                    break
                if is_scanned:
                    break
                time.sleep(1)
        else:
            logging.info(f"Displaying for {TIMEOUT_SECONDS}s (WAIT_FOR_SCAN=0)")
            time.sleep(TIMEOUT_SECONDS)

        if is_scanned:
            display_message(epd, font_ok, "Scan successful!")
            time.sleep(3)
        else:
            logging.info("Next QR...")

        epd.Clear()

except IOError as e:
    logging.error(e)
except KeyboardInterrupt:
    logging.info("ctrl + c:")
    if epd is not None:
        try:
            epd.Clear(); epd.sleep()
        except Exception:
            pass
    for f in glob.glob("scanned_*.flag"):
        try: os.remove(f)
        except Exception: pass
    epd2in7.epdconfig.module_exit(cleanup=True)
    sys.exit(0)
