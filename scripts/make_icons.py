"""Regenerate the spkup app icon assets.

Usage (macOS, needs `iconutil`):
    QT_QPA_PLATFORM=offscreen python scripts/make_icons.py src/spkup/resources

Writes spkup.icns (macOS bundle), spkup.ico (Windows exe) and icon.png (Qt window icon).
The menu-bar/tray glyph is drawn at runtime by `_make_tray_icon` in app.py.
"""
import struct, subprocess, sys
from pathlib import Path
from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QRadialGradient, QBrush

app = QGuiApplication(sys.argv[:1])
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
BARS = [0.30, 0.58, 1.0, 0.72, 0.42]  # asymmetric: reads as live voice, not a static logo

def draw_bars(p, cx, cy, height, bar_w, gap, colors):
    total = len(BARS) * bar_w + (len(BARS) - 1) * gap
    x = cx - total / 2
    for h, c in zip(BARS, colors):
        bh = max(bar_w, height * h)
        p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x, cy - bh / 2, bar_w, bh), bar_w / 2, bar_w / 2)
        x += bar_w + gap

def app_icon(size):
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied); img.fill(0)
    p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 1024
    body = QRectF(100 * s, 100 * s, 824 * s, 824 * s)  # macOS grid: 824 body in 1024 canvas
    path = QPainterPath(); path.addRoundedRect(body, 185 * s, 185 * s)
    # drop shadow
    for i, a in enumerate((10, 16, 24)):
        d = (3 - i) * 6 * s
        sh = QPainterPath(); sh.addRoundedRect(body.adjusted(-d, -d + 12 * s, d, d + 12 * s), 185 * s + d, 185 * s + d)
        p.fillPath(sh, QColor(0, 0, 0, a))
    g = QLinearGradient(body.topLeft(), body.bottomLeft())
    g.setColorAt(0, QColor("#2C2C31")); g.setColorAt(1, QColor("#0E0E10"))
    p.fillPath(path, QBrush(g))
    glow = QRadialGradient(QPointF(512 * s, 330 * s), 520 * s)
    glow.setColorAt(0, QColor(255, 255, 255, 22)); glow.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillPath(path, QBrush(glow))
    p.setClipPath(path)
    white = QColor(255, 255, 255, 240); red = QColor("#FF453A")
    draw_bars(p, 512 * s, 512 * s, 430 * s, 70 * s, 46 * s, [white, white, red, white, white])
    p.setClipping(False)
    p.setPen(QColor(255, 255, 255, 28)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    p.end(); return img

app_icon(512).save(str(out / "icon.png"))
import shutil, tempfile
iconset = Path(tempfile.mkdtemp()) / "spkup.iconset"; iconset.mkdir()
for n in (16, 32, 128, 256, 512):
    app_icon(n).save(str(iconset / f"icon_{n}x{n}.png"))
    app_icon(n * 2).save(str(iconset / f"icon_{n}x{n}@2x.png"))
subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out / "spkup.icns")], check=True)
shutil.rmtree(iconset.parent)

# ICO with PNG-encoded entries (valid since Windows Vista); Qt's writer stores one size only.
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
entries = []
for n in (16, 24, 32, 48, 64, 128, 256):
    ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.OpenModeFlag.WriteOnly)
    app_icon(n).save(buf, "PNG"); entries.append((n, bytes(ba)))
offset = 6 + 16 * len(entries); head = struct.pack("<HHH", 0, 1, len(entries)); dirs = b""; blobs = b""
for n, data in entries:
    dirs += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset + len(blobs)); blobs += data
(out / "spkup.ico").write_bytes(head + dirs + blobs)

print("wrote", out / "spkup.icns", out / "spkup.ico", out / "icon.png")
