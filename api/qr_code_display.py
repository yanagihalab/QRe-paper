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

# --- ★設定 ---
SERVER_IP = "192.168.100.15"                # urlモードで使用
QR_MODE = os.environ.get("QR_MODE", "json").lower()   # "json" | "image" | "url"
WAIT_FOR_SCAN = os.environ.get("WAIT_FOR_SCAN", "0") == "1"
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "10"))
METADATA_FILE = os.environ.get("METADATA_FILE", os.path.join(os.path.dirname(__file__), "metadata.json"))
FONT_PATH_ENV = os.environ.get("FONT_PATH")           # 明示指定したい場合に使用
DEFAULT_METADATA = {
    "name": "Participation Certificate NFT",
    "description": "10042025深谷研菊地研合同イベント参加証NFT",
    "image": "https://ipfs.yamada.jo.sus.ac.jp/ipfs/QmTuDCtiZJjRFqiZ6D5X2iNX8ejwNu6Kv1F7EcThej9yHu"
}
# -----------

epd = None

# ===== フォントまわり =====
def _first_exists(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

def find_cjk_font():
    """CJK対応フォントを探す。見つからなければ None"""
    if FONT_PATH_ENV and os.path.exists(FONT_PATH_ENV):
        return FONT_PATH_ENV
    # よくある候補を順に
    candidates = [
        os.path.join(picdir, "FontCJK.ttc"),
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/opentype/adobe-source-han-sans/SourceHanSans-Regular.otf",
        "/usr/share/fonts/opentype/SourceHanSerifJP/SourceHanSerifJP-Regular.otf",
        os.path.join(picdir, "Font.ttc"),  # 最後にWaveshare付属（日本語非対応のこと多い）
    ]
    return _first_exists(candidates)

def load_fonts():
    font_path = find_cjk_font()
    if font_path:
        try:
            font_info = ImageFont.truetype(font_path, 14)
            font_main = ImageFont.truetype(font_path, 18)
            font_success = ImageFont.truetype(font_path, 24)
            logging.info(f"Using font: {font_path}")
            return font_info, font_main, font_success, True
        except Exception as e:
            logging.warning(f"Failed to load TrueType font '{font_path}': {e}")
    # ここに来ると日本語非対応のビットマップフォントの可能性大
    logging.warning("CJK TrueType font not found. Falling back to PIL default (Japanese may not render).")
    f = ImageFont.load_default()
    return f, f, f, False  # False = CJK不可の可能性

def safe_textlength(draw, s, font, cjk_capable):
    """
    フォントがCJK非対応でも落ちないように、幅計測を安全化。
    本来はCJK対応フォント使用が前提。
    """
    try:
        return draw.textlength(s, font=font)
    except UnicodeEncodeError:
        # 非対応フォント。代替: 置換で概算
        if not cjk_capable:
            s2 = s.encode("ascii", "replace").decode("ascii")
            try:
                return draw.textlength(s2, font=font)
            except Exception:
                pass
        # 最低限の概算（'A'幅×文字数）
        wA = draw.textlength("A", font=font) or 8
        return wA * len(s)

def wrap_by_width(draw, text, font, max_width, cjk_capable):
    lines = []
    for para in (text or "").splitlines() or [""]:
        buf = ""
        for ch in para:
            if safe_textlength(draw, buf + ch, font, cjk_capable) <= max_width:
                buf += ch
            else:
                lines.append(buf)
                buf = ch
        lines.append(buf)
    return lines

# ===== 表示補助 =====
def display_message(epd, font, message):
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0,0), message, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (epd.width - text_width) // 2
    y = (epd.height - text_height) // 2
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
        obj = {
            "name": metadata["name"],
            "description": metadata["description"],
            "image": metadata["image"]
        }
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    elif QR_MODE == "image":
        return str(metadata["image"])
    else:  # "url"
        return f"http://{SERVER_IP}:5000/scan?user_id={user_id}&qr_id={qr_id}"

def make_qr_image(payload):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.make_image(fill_color=0, back_color=255).convert("1")

def draw_screen(epd, fonts, user_id, timestamp, qr_id, metadata, payload, cjk_capable):
    font_info, font_main, _ = fonts
    canvas = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(canvas)

    margin = 10
    inner_w = epd.width - margin * 2

    # ヘッダ
    draw.text((margin, 5), "User ID:", font=font_info, fill=0)
    draw.text((margin, 21), user_id, font=font_main, fill=0)
    draw.text((margin, 47), "Timestamp:", font=font_info, fill=0)
    draw.text((margin, 63), timestamp, font=font_info, fill=0)

    # メタデータ
    y = 85
    draw.text((margin, y), "Name:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("name", ""), font_main, inner_w, cjk_capable):
        draw.text((margin, y), line, font=font_main, fill=0)
        y += 20

    draw.text((margin, y), "Description:", font=font_info, fill=0)
    y += 14
    for line in wrap_by_width(draw, metadata.get("description", ""), font_info, inner_w, cjk_capable):
        if y > epd.height * 0.55:
            draw.text((margin, y), "…", font=font_info, fill=0)
            y += 14
            break
        draw.text((margin, y), line, font=font_info, fill=0)
        y += 14

    # QRラベル
    mode_label = {"json": "QR: JSON", "image": "QR: image URL", "url": "QR: link"}[QR_MODE]
    preview = payload if QR_MODE != "json" else metadata.get("image", "")
    while safe_textlength(draw, f"{mode_label}  {preview}", font_info, cjk_capable) > inner_w and len(preview) > 8:
        preview = preview[:-2] + "…"
    y_label = int(epd.height - epd.height * 0.45) - 16
    y_label = max(y + 4, y_label)
    draw.text((margin, y_label), f"{mode_label}  {preview}", font=font_info, fill=0)

    # QR
    qr_img = make_qr_image(payload)
    qr_size = min(180, epd.width - 40, int(epd.height * 0.42))
    qr_img_resized = qr_img.resize((qr_size, qr_size))
    qr_x = (epd.width - qr_size) // 2
    qr_y = epd.height - qr_size
    canvas.paste(qr_img_resized, (qr_x, qr_y))

    # QR ID
    draw.text((margin, 89), f"(QR ID: {qr_id})", font=font_info, fill=0)

    epd.display(epd.getbuffer(canvas))

# ===== メイン =====
try:
    epd = epd2in7.EPD()
    epd.init()
    epd.Clear()

    font_info, font_main, font_success, cjk_capable = load_fonts()
    user_id = "user-t-8821"

    while True:
        metadata = load_metadata()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        qr_id = str(uuid.uuid4().hex)[:8]
        payload = build_qr_payload(user_id, qr_id, metadata)
        logging.info(f"QR_MODE={QR_MODE}, payload preview: {payload[:120]}{'...' if len(payload)>120 else ''}")

        draw_screen(epd, (font_info, font_main, font_success), user_id, timestamp, qr_id, metadata, payload, cjk_capable)

        is_scanned = False
        if WAIT_FOR_SCAN:
            flag_filename = f"scanned_{qr_id}.flag"
            logging.info(f"Waiting for scan... (Timeout: {TIMEOUT_SECONDS}s)")
            for _ in range(TIMEOUT_SECONDS):
                if os.path.exists(flag_filename):
                    is_scanned = True
                    os.remove(flag_filename)
                    break
                generic = glob.glob("scanned_*.flag")
                if generic:
                    is_scanned = True
                    for g in generic:
                        try: os.remove(g)
                        except Exception: pass
                    break
                time.sleep(1)
        else:
            logging.info(f"Displaying for {TIMEOUT_SECONDS}s (WAIT_FOR_SCAN=0)")
            time.sleep(TIMEOUT_SECONDS)

        if is_scanned:
            display_message(epd, font_success, "読み取り成功！")
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
