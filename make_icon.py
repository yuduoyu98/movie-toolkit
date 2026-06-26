"""渲染 icon.svg -> icon.ico，供 Windows 可执行文件图标使用。

用 QtSvg 把矢量 SVG 渲染为 256px PNG，再用 Pillow 生成多尺寸 .ico。
"""
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt, QByteArray
from PIL import Image


def main():
    app = QApplication([])  # QPixmap 必须在 QApplication 之后构造
    svg_bytes = Path("icon.svg").read_bytes()
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    if not renderer.isValid():
        print("[ERR] icon.svg 解析失败", file=sys.stderr)
        return 1

    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()

    tmp_png = Path("_icon_256.png")
    pm.save(str(tmp_png), "PNG")

    img = Image.open(tmp_png).convert("RGBA")
    img.save(
        "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    tmp_png.unlink()
    print("icon.ico written (multi-size)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
