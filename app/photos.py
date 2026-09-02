"""写真表示のヘルパー。

試作ではリポジトリにバイナリを置かず、写真名から
プレースホルダー画像を生成して表示する。
実運用では SharePoint ドキュメントライブラリの画像URL / パスに差し替える。
"""
from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

_CACHE: dict[str, bytes] = {}


def _color_from_name(name: str) -> tuple[int, int, int]:
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    # 濃すぎ・薄すぎを避ける
    return (60 + r % 120, 60 + g % 120, 60 + b % 120)


def placeholder_png(name: str, size: tuple[int, int] = (480, 360)) -> bytes:
    """写真名からプレースホルダーPNGを生成して返す（キャッシュ付き）。"""
    if name in _CACHE:
        return _CACHE[name]

    img = Image.new("RGB", size, _color_from_name(name))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    label = f"[写真] {name}"
    tb = draw.textbbox((0, 0), label, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    draw.text(((size[0] - tw) / 2, (size[1] - th) / 2), label, fill="white", font=font)
    draw.rectangle([6, 6, size[0] - 6, size[1] - 6], outline="white", width=2)

    buf = BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    _CACHE[name] = data
    return data
