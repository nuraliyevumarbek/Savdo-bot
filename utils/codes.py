import os
import io
import random
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from pyzbar.pyzbar import decode as zbar_decode

from config import QR_DIR, BARCODE_DIR


def gen_internal_code():
    """Har bir mahsulot uchun ichki noyob kod (QR ichiga yoziladi)."""
    return f"PRD{random.randint(100000, 999999)}"


def generate_qr_image(data: str, save_path: str) -> str:
    img = qrcode.make(data)
    img.save(save_path)
    return save_path


def generate_barcode_image(code: str, save_path_no_ext: str) -> str:
    """EAN13 formatida emas, Code128 - istalgan matn/raqamni qo'llab-quvvatlaydi."""
    writer = ImageWriter()
    code128 = barcode.get("code128", code, writer=writer)
    full_path = code128.save(save_path_no_ext)
    return full_path


def read_code_from_image(image_path: str):
    """Rasmdan QR yoki shtrix-kodni o'qib, matnini qaytaradi (topilmasa None)."""
    img = Image.open(image_path)
    results = zbar_decode(img)
    if not results:
        return None
    return results[0].data.decode("utf-8")


def qr_file_path(product_code: str) -> str:
    return os.path.join(QR_DIR, f"{product_code}.png")


def barcode_file_path_no_ext(product_code: str) -> str:
    return os.path.join(BARCODE_DIR, f"{product_code}")
