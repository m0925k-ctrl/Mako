"""写真表示のヘルパー。

試作ではリポジトリにバイナリを置かず、写真名から
プレースホルダー画像を生成して表示する。
実運用では SharePoint ドキュメントライブラリの画像URL / パスに差し替える。
"""
from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_CACHE: dict[str, bytes] = {}

# 日本語が描ける可能性の高いフォント候補（環境ごとに存在するものを探す）
_CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",  # macOS
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/meiryo.ttc",  # Windows
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]
_cjk_font_path: str | None = None


def _cjk_font(size: int) -> ImageFont.FreeTypeFont:
    """日本語対応フォントを返す。見つからなければ英字フォントにフォールバック。"""
    global _cjk_font_path
    if _cjk_font_path is None:
        _cjk_font_path = next((p for p in _CJK_FONT_CANDIDATES if Path(p).exists()), "")
    if _cjk_font_path:
        try:
            return ImageFont.truetype(_cjk_font_path, size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


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
    font = _cjk_font(22)

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


def avatar_png(name: str, initial: str = "", size: int = 96) -> bytes:
    """作業員の顔写真プレースホルダー（頭文字入りの丸アバター）。

    実運用では SharePoint / 人事システムの顔写真URLに差し替える。
    """
    key = f"avatar:{name}:{initial}"
    if key in _CACHE:
        return _CACHE[key]

    img = Image.new("RGB", (size, size), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=_color_from_name(name))
    if initial:
        font = _cjk_font(int(size * 0.42))
        tb = draw.textbbox((0, 0), initial, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        draw.text(
            ((size - tw) / 2 - tb[0], (size - th) / 2 - tb[1]),
            initial,
            fill="white",
            font=font,
        )

    buf = BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    _CACHE[key] = data
    return data
