"""生成不含真实照片或个人信息的 OCR 对比夹具。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    raise RuntimeError("未找到可生成中文夹具的系统字体。")


def make_image(
    file_name: str,
    lines: list[str],
    *,
    foreground: tuple[int, int, int] = (22, 27, 35),
    background: tuple[int, int, int] = (246, 247, 249),
    angle: float = 0,
) -> None:
    image = Image.new("RGB", (1000, 320), background)
    draw = ImageDraw.Draw(image)
    font = load_font(78 if len(lines) == 1 else 64)
    line_height = 104
    y = (image.height - line_height * len(lines)) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        width = box[2] - box[0]
        draw.text(((image.width - width) / 2, y), line, font=font, fill=foreground)
        y += line_height

    if angle:
        image = image.rotate(
            angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=background
        )
    image.save(FIXTURES / file_name, optimize=True)


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    make_image("01_chinese.png", ["婚礼跟拍"])
    make_image("02_chinese_spaces.png", ["新娘  准备"])
    make_image("03_mixed.png", ["Wedding 2026"])
    make_image("04_time.png", ["戒指交换 18:30"])
    make_image(
        "05_low_contrast.png",
        ["今日关键词", "拥抱"],
        foreground=(128, 132, 139),
        background=(221, 224, 228),
    )
    make_image("06_rotated.png", ["幸福定格"], angle=-3.0)


if __name__ == "__main__":
    main()
