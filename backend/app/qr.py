import base64
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def qr_png_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, "PNG")
    return buf.getvalue()


def qr_data_uri(url: str) -> str:
    return "data:image/png;base64," + base64.b64encode(qr_png_bytes(url)).decode()
