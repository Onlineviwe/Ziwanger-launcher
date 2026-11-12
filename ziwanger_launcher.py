"""
Ziwanger Launcher: сборки, темы, раскладки, копии миров, иконки, .mrpack, Microsoft.
Установка: pip install PySide6 minecraft-launcher-lib
Запуск:    python ziwanger_launcher.py
"""
import json, math, os, random, shutil, sys, time, urllib.error, urllib.parse, urllib.request, uuid, webbrowser, zipfile
from pathlib import Path
import minecraft_launcher_lib as mll
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QUrl, QTimer, QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QLinearGradient, QPixmap, QIcon, QImage, QDesktopServices, QPolygonF, QPainterPath, QPen, QFontDatabase
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import *

VERSION = "1.0.0"
HOME = Path.home() / ".quiet_launcher"
CFG, INST, ICONS, BACKUPS = HOME / "config.json", HOME / "instances", HOME / "icons", HOME / "backups"
for d in (INST, ICONS, BACKUPS):
    d.mkdir(parents=True, exist_ok=True)
MC_DIR = mll.utils.get_minecraft_directory()
REDIRECT = "http://localhost"

THEMES = {  # фон, панели, текст, приглушённый
    "Чёрная": ("#141518", "#202227", "#e8e8ec", "#8b8f9a"),
    "Графит": ("#1d1e21", "#2a2c30", "#ececf0", "#9a9ea8"),
    "Тёмно-синяя": ("#0f1626", "#1a2438", "#e6ecf8", "#8793ad"),
    "Фиолетовая": ("#18131f", "#251d33", "#eee8f8", "#9a8fb0"),
}
BGS = [("day", "Пейзаж"), ("night", "Ночь"), ("nether", "Незер"), ("end", "Энд"), ("none", "Без фона")]
ACCENTS = ["#43b05c", "#4a8fe0", "#9a6fe0", "#d9784a", "#e0558a", "#e0b84a", "#3fb8c8"]
PRESETS = {
    "По умолчанию": [],
    "Баланс": ["-XX:+UseG1GC", "-XX:MaxGCPauseMillis=100"],
    "Максимум FPS": ["-XX:+UseG1GC", "-XX:+UnlockExperimentalVMOptions", "-XX:G1NewSizePercent=30",
                     "-XX:G1MaxNewSizePercent=40", "-XX:+AlwaysPreTouch"],
    "Слабый ПК": ["-XX:+UseSerialGC", "-Xss512k"],
}
TEX = ["grass_block_side", "stone", "dirt", "oak_planks", "cobblestone", "sand", "gold_block", "diamond_block",
       "iron_block", "netherrack", "tnt_side", "bookshelf", "glass", "bricks", "obsidian", "emerald_block",
       "lapis_block", "pumpkin_side", "redstone_block", "glowstone"]
DEFAULT = dict(style="pixel", music_dir="", volume=60, bg="day", theme="Графит", accent=ACCENTS[0], layout="tl", preset="По умолчанию", backup=True,
               client_id="", accounts=[], account=0, builds=[], build=0, seen="")


def load():
    cfg = dict(DEFAULT)
    try:
        cfg.update(json.loads(CFG.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save(cfg):
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


def rgba(c, a):
    q = QColor(c)
    return f"rgba({q.red()},{q.green()},{q.blue()},{a})"


def pixel_qss(t, a):
    """Пиксельный стиль: рамки с «фасками», как в меню Minecraft."""
    bg, pn, fg, mu = t
    hi, lo = QColor(a).lighter(145).name(), QColor(a).darker(190).name()
    out = "border:2px solid;border-radius:0;"
    raised = out + "border-color:#c8c8c8 #333 #333 #c8c8c8;"
    sunk = out + "border-color:#333 #c8c8c8 #c8c8c8 #333;"
    return f"""
QWidget{{color:#f2f2f2;font-family:"Minecraft","Consolas","Courier New",monospace;font-size:14px;}}
QDialog{{background:{pn};}}
QFrame#panel{{background:transparent;border:none;}}
QPushButton{{background:#6b6b6b;{raised}padding:7px 14px;}}
QPushButton:hover{{background:#7c82b8;color:#ffffa0;}}
QPushButton:checked{{background:{a};}}
QPushButton:disabled{{background:#4a4a4a;color:#a0a0a0;}}
QPushButton#accent{{background:{a};font-weight:bold;font-size:16px;padding:10px 28px;border:2px solid;border-color:{hi} {lo} {lo} {hi};}}
QPushButton#accent:hover{{background:{QColor(a).lighter(120).name()};color:#ffffa0;}}
QPushButton#accent:disabled{{background:#4a4a4a;color:#a0a0a0;border-color:#666 #222 #222 #666;}}
QLabel#muted{{color:#a8a8a8;}}
QLabel#title{{font-size:22px;font-weight:bold;color:#fff;}}
QPlainTextEdit,QTableWidget,QListWidget,QLineEdit,QComboBox,QSpinBox{{background:rgba(0,0,0,150);{sunk}padding:4px;}}
QComboBox::drop-down{{border:none;width:22px;}}
QComboBox QAbstractItemView{{background:#2b2b2b;border:2px solid #000;selection-background-color:{a};}}
QListWidget::item{{padding:8px;}}
QListWidget::item:hover{{background:rgba(255,255,255,40);}}
QListWidget::item:selected{{background:{a};color:#fff;}}
QHeaderView::section{{background:#3a3a3a;border:1px solid #000;padding:6px;}}
QTabBar::tab{{background:#6b6b6b;{raised}padding:6px 14px;margin-right:3px;}}
QTabBar::tab:selected{{background:{a};}}
QTabWidget::pane{{border:none;}}
QSlider::groove:horizontal{{height:8px;background:#000;border:2px solid #555;}}
QSlider::sub-page:horizontal{{background:{a};}}
QSlider::handle:horizontal{{background:#c8c8c8;border:2px solid #000;width:12px;margin:-6px 0;}}
QProgressBar{{background:#000;{sunk}max-height:14px;}}
QProgressBar::chunk{{background:{a};}}
"""


def qss(t, a, glass=False, pixel=False):
    if pixel:
        return pixel_qss(t, a)
    bg, pn, fg, mu = t
    pbg = "transparent" if glass else pn
    pb = rgba("#ffffff", 30) if glass else pn
    ib = rgba("#000000", 85) if glass else bg
    bd = rgba("#ffffff", 45) if glass else pn
    rad = 18
    gv = rgba("#ffffff", 40)
    return f"""
QWidget{{color:{fg};font-size:13px;}}
QDialog{{background:{bg};}}
QFrame#panel{{background:{pbg};border-radius:{rad}px;}}
QPushButton{{background:{pb};border:none;border-radius:16px;padding:8px 16px;}}
QPushButton:hover{{background:{rgba(a,90)};}}
QPushButton:checked{{background:{rgba(a,150)};border:2px solid {a};}}
QPushButton:disabled{{color:{mu};}}
QPushButton#accent{{background:{a};color:#fff;font-weight:bold;border-radius:22px;padding:12px 30px;font-size:15px;}}
QLabel#muted{{color:{mu};}}
QLabel#title{{font-size:20px;font-weight:bold;}}
QPlainTextEdit,QTableWidget,QListWidget,QLineEdit,QComboBox,QSpinBox{{background:{ib};border:1px solid {bd};border-radius:10px;padding:4px;}}
QComboBox QAbstractItemView{{background:{pn};selection-background-color:{a};}}
QListWidget{{border:none;background:transparent;}}
QListWidget::item{{padding:8px;border-radius:10px;}}
QListWidget::item:selected{{background:{rgba(a,110)};}}
QHeaderView::section{{background:{bg};border:none;padding:6px;color:{mu};}}
QTabBar::tab{{padding:8px 16px;border-radius:14px;color:{mu};margin-right:4px;}}
QTabBar::tab:selected{{background:{rgba(a,80)};color:{fg};}}
QTabWidget::pane{{border:none;}}
QSlider::groove:horizontal{{height:6px;background:{gv};border-radius:3px;}}
QSlider::sub-page:horizontal{{background:{a};border-radius:3px;}}
QSlider::handle:horizontal{{background:#fff;width:14px;margin:-5px 0;border-radius:7px;}}
QProgressBar{{background:{bg};border:none;border-radius:4px;max-height:8px;}}
QProgressBar::chunk{{background:{a};border-radius:4px;}}
"""


def head(size=30):
    img = QImage(8, 8, QImage.Format_ARGB32)
    for y in range(8):
        for x in range(8):
            c = "#4a3320" if y < 2 or (y == 2 and x in (0, 7)) else "#b78a64"
            if y == 4:
                c = {1: "#fff", 2: "#3b3b8f", 5: "#3b3b8f", 6: "#fff"}.get(x, c)
            if y == 6 and 2 <= x <= 5:
                c = "#8a5a3c"
            img.setPixelColor(x, y, QColor(c))
    return QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)


def textures():
    for jar in sorted(MC_DIR.glob("versions/*/*.jar")):
        try:
            z = zipfile.ZipFile(jar)
            names = set(z.namelist())
            out = []
            for d in ("block", "blocks"):
                out = [(n, z.read(p)) for n in TEX if (p := f"assets/minecraft/textures/{d}/{n}.png") in names]
                if out:
                    return out
        except Exception:
            continue
    return []


def icon_for(b, size=28):
    p = ICONS / f"{b['name']}.png"
    if p.exists():
        return QIcon(QPixmap(str(p)).scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation))
    return QIcon()


def folder_size(p):
    return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file())


def fmt_size(n):
    for u in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or u == "ГБ":
            return f"{n:.0f} {u}" if u == "Б" else f"{n:.1f} {u}"
        n /= 1024


def backup_worlds(name, inst, keep=3):
    saves = inst / "saves"
    if not saves.exists():
        return
    for w in [x for x in saves.iterdir() if x.is_dir()]:
        sig = max((f.stat().st_mtime for f in w.rglob("*") if f.is_file()), default=0)
        dst = BACKUPS / name / w.name
        dst.mkdir(parents=True, exist_ok=True)
        snaps = sorted(dst.iterdir())
        if snaps and (snaps[-1] / ".sig").exists() and float((snaps[-1] / ".sig").read_text()) >= sig:
            continue  # мир не менялся
        new = dst / time.strftime("%Y%m%d-%H%M%S")
        shutil.copytree(w, new)
        (new / ".sig").write_text(str(sig))
        for old in sorted(dst.iterdir())[:-keep]:
            shutil.rmtree(old, ignore_errors=True)


class Job(QThread):
    status, prog, done, fail = Signal(str), Signal(int, int), Signal(object), Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        mx = [0]
        cb = {"setStatus": self.status.emit, "setMax": lambda m: mx.__setitem__(0, m),
              "setProgress": lambda p: self.prog.emit(p, mx[0])}
        try:
            self.done.emit(self.fn(cb))
        except Exception as e:
            self.fail.emit(str(e))


def ely_post(path, payload):
    req = urllib.request.Request("https://authserver.ely.by/auth/" + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("errorMessage", "")
        except Exception:
            msg = ""
        raise RuntimeError(msg or f"Ely.by: ошибка {e.code}")


def authlib_jar(cb):
    jar = HOME / "authlib-injector.jar"
    if not jar.exists():
        cb["setStatus"]("Загрузка authlib-injector…")
        meta = json.loads(urllib.request.urlopen("https://authlib-injector.yushi.moe/artifact/latest.json", timeout=20).read())
        urllib.request.urlretrieve(meta["download_url"], jar)
    return str(jar)


def prepare(b, acc, cfg, cb):
    inst = INST / b["name"]
    inst.mkdir(parents=True, exist_ok=True)
    extra = []
    if acc["type"] == "microsoft":
        cb["setStatus"]("Обновление токена…")
        d = mll.microsoft_account.complete_refresh(cfg["client_id"], None, REDIRECT, acc["refresh"])
        acc["refresh"] = d["refresh_token"]
        user, uid, tok = d["name"], d["id"], d["access_token"]
    elif acc["type"] == "ely":
        cb["setStatus"]("Вход Ely.by…")
        d = ely_post("refresh", {"accessToken": acc["access"], "clientToken": acc["client"], "requestUser": False})
        acc["access"] = d["accessToken"]
        user, uid, tok = acc["name"], acc["uuid"], d["accessToken"]
        extra = [f"-javaagent:{authlib_jar(cb)}=ely.by"]
    else:
        user, tok = acc["name"], ""
        uid = str(uuid.uuid3(uuid.NAMESPACE_DNS, "OfflinePlayer:" + user))
    vid = b.get("vid")
    if not vid:
        if b["loader"] == "Fabric":
            mll.fabric.install_fabric(b["version"], MC_DIR, callback=cb)
            vid = f"fabric-loader-{mll.fabric.get_latest_loader_version()}-{b['version']}"
        else:
            mll.install.install_minecraft_version(b["version"], MC_DIR, callback=cb)
            vid = b["version"]
    if cfg["backup"]:
        cb["setStatus"]("Копия миров…")
        backup_worlds(b["name"], inst)
    jvm = extra + [f"-Xmx{b['ram']}G"] + PRESETS.get(b.get("preset") or cfg["preset"], [])
    cmd = mll.command.get_minecraft_command(vid, MC_DIR, {
        "username": user, "uuid": uid, "token": tok, "gameDirectory": str(inst), "jvmArguments": jvm})
    return cmd, str(inst)


_rnd = random.Random(7)
STARS = [(_rnd.random(), _rnd.random() * 0.6, _rnd.random() * 6.28) for _ in range(70)]
PARTS = [(_rnd.random(), _rnd.random(), _rnd.random() * 6.28) for _ in range(45)]


def bedrock(size=64):
    """Иконка: изометрический кубик бедрока."""
    img = QImage(32, 32, QImage.Format_ARGB32)
    img.fill(0)
    faces = [(QPolygonF([QPointF(16, 2), QPointF(29, 9), QPointF(16, 16), QPointF(3, 9)]), 128),
             (QPolygonF([QPointF(3, 9), QPointF(16, 16), QPointF(16, 30), QPointF(3, 23)]), 88),
             (QPolygonF([QPointF(16, 16), QPointF(29, 9), QPointF(29, 23), QPointF(16, 30)]), 58)]
    for y in range(32):
        for x in range(32):
            for poly, base in faces:
                if poly.containsPoint(QPointF(x + .5, y + .5), Qt.WindingFill):
                    r = random.Random(x * 131 + y * 7).random()
                    v = max(10, base + int((r - .5) * 46) - (30 if r < .12 else 0))
                    img.setPixelColor(x, y, QColor(v, v, v + 4))
                    break
    return QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)


def terrain(p, w, h, t, colors, base_f=0.66, speed=12):
    s, off = 32, t * speed
    c0, base = int(off // s), int(h * base_f)
    top_c, dirt_c, stone_c = (QColor(c) for c in colors)
    for i in range(-1, w // s + 3):
        c = c0 + i
        x = int(c * s - off)
        top = base + int(math.sin(c * 0.19) * 2.2 + math.sin(c * 0.53) * 0.8) * s
        p.fillRect(x, top, s, h - top, dirt_c)
        p.fillRect(x, top + 3 * s, s, h, stone_c)
        p.fillRect(x, top, s, s, top_c)
        p.fillRect(x, top + s - 5, s, 5, top_c.darker(130))
        p.fillRect(x, top, 1, h - top, QColor(0, 0, 0, 45))


def sky(p, w, h, c1, c2):
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor(c1)); g.setColorAt(1, QColor(c2))
    p.fillRect(0, 0, w, h, g)


def stars(p, w, h, t, color=(255, 255, 255)):
    for fx, fy, ph in STARS:
        a = max(0, int(110 + 110 * math.sin(t * 2 + ph)))
        p.fillRect(int(fx * w), int(fy * h), 3, 3, QColor(*color, a))


def scene_day(p, w, h, t):
    sky(p, w, h, "#4f98ec", "#d3ebff")
    p.fillRect(w - 200, 60, 70, 70, QColor("#fff2a8"))
    for i in range(5):
        x = int((i * (w // 4) + t * 18) % (w + 360)) - 240
        y = 60 + (i * 53) % 150
        for dx, dy, cw in ((0, 0, 140), (30, -24, 90), (-24, 24, 110)):
            p.fillRect(x + dx, y + dy, cw, 24, QColor(255, 255, 255, 215))
    terrain(p, w, h, t, ("#5fb04a", "#6e5035", "#7b7b80"))


def scene_night(p, w, h, t):
    sky(p, w, h, "#070b22", "#1d2c58")
    stars(p, w, h, t)
    p.fillRect(w - 220, 70, 60, 60, QColor("#e8ecff"))
    p.fillRect(w - 200, 90, 14, 14, QColor("#c3c9ea"))
    terrain(p, w, h, t, ("#2a5a3a", "#3a2c22", "#40424a"), speed=8)
    for i in range(14):
        x = (i * 131) % w + math.sin(t * 0.7 + i) * 30
        y = h * 0.55 + math.cos(t * 0.9 + i * 2) * 40
        p.fillRect(int(x), int(y), 4, 4, QColor(200, 255, 120, int(140 + 110 * math.sin(t * 3 + i))))


def scene_nether(p, w, h, t):
    sky(p, w, h, "#240404", "#8a2208")
    terrain(p, w, h, t, ("#8a3434", "#5e2222", "#3d1515"), base_f=0.7, speed=10)
    p.fillRect(0, h - 36, w, 36, QColor(255, 120, 20, int(200 + 50 * math.sin(t * 2))))
    p.fillRect(0, int(h * 0.55), w, int(h * 0.45), QColor(255, 90, 10, int(32 + 22 * math.sin(t * 1.5))))
    for fx, fy, ph in PARTS:
        y = h - ((t * 40 + fy * h) % h)
        p.fillRect(int(fx * w + math.sin(t + ph) * 18), int(y), 4, 4, QColor(255, 170, 50, int(220 * y / h)))


def scene_end(p, w, h, t):
    sky(p, w, h, "#06030e", "#1c0c36")
    stars(p, w, h, t, (190, 150, 255))
    s = 32
    for i in range(3):
        cx, cy = w * (0.2 + 0.3 * i), h * 0.55 + math.sin(t * 0.8 + i * 2) * 12 + i * 20
        for r in range(4):
            n = 7 - 2 * r
            x = int(cx - n * s / 2)
            p.fillRect(x, int(cy + r * s), n * s, s, QColor("#d9d5a3").darker(100 + r * 18))
            p.fillRect(x, int(cy + r * s), n * s, 2, QColor(255, 255, 255, 50))
    for fx, fy, ph in PARTS:
        y = h - ((t * 25 + fy * h) % h)
        p.fillRect(int(fx * w + math.sin(t * 0.6 + ph) * 25), int(y), 4, 4, QColor(200, 120, 255, int(200 * (1 - y / h) + 40)))


SCENES = {"day": scene_day, "night": scene_night, "nether": scene_nether, "end": scene_end}


_DIRT = []


def dirt_tile():
    if not _DIRT:
        img, r = QImage(16, 16, QImage.Format_ARGB32), random.Random(3)
        for y in range(16):
            for x in range(16):
                v = r.randint(-18, 18)
                img.setPixelColor(x, y, QColor(121 + v, 85 + v, 58 + v))
        _DIRT.append(QPixmap.fromImage(img).scaled(64, 64, Qt.IgnoreAspectRatio, Qt.FastTransformation))
    return _DIRT[0]


class Glow(QWidget):
    theme, accent, bg, pixel = THEMES["Чёрная"], ACCENTS[0], "day", False

    def __init__(self):
        super().__init__()
        self.panels, self.t0 = [], time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

    def set_bg(self, bg):
        self.bg = bg
        if bg == "none":
            self.timer.stop()
        else:
            self.timer.start(40)
        self.update()

    def paint_pixel(self, p, w, h):
        if self.bg in SCENES:
            SCENES[self.bg](p, w, h, time.time() - self.t0)
            p.fillRect(0, 0, w, h, QColor(0, 0, 0, 90))
        else:
            p.drawTiledPixmap(0, 0, w, h, dirt_tile())
            p.fillRect(0, 0, w, h, QColor(0, 0, 0, 150))
        fill = QColor(self.theme[1]); fill.setAlpha(240)
        for wd in self.panels:
            if not wd.isVisible():
                continue
            r = QRect(wd.mapTo(self, QPoint(0, 0)), wd.size())
            p.fillRect(r, QColor(0, 0, 0))
            i = r.adjusted(2, 2, -2, -2)
            p.fillRect(i, fill)
            p.fillRect(i.left(), i.top(), i.width(), 3, fill.lighter(170))
            p.fillRect(i.left(), i.top(), 3, i.height(), fill.lighter(170))
            p.fillRect(i.left(), i.bottom() - 2, i.width(), 3, fill.darker(190))
            p.fillRect(i.right() - 2, i.top(), 3, i.height(), fill.darker(190))

    def paintEvent(self, e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        if self.pixel:
            self.paint_pixel(p, w, h)
            return
        if self.bg not in SCENES:
            p.fillRect(self.rect(), QColor(self.theme[0]))
            for (fx, fy, r, al) in ((0.8, 0.0, 520, 80), (0.05, 1.0, 420, 45)):
                g = QRadialGradient(w * fx, h * fy, r)
                c = QColor(self.accent); c.setAlpha(al)
                g.setColorAt(0, c); c.setAlpha(0); g.setColorAt(1, c)
                p.fillRect(self.rect(), g)
            return
        scene, t = SCENES[self.bg], time.time() - self.t0
        scene(p, w, h, t)
        p.fillRect(0, 0, w, h, QColor(0, 0, 0, 60))
        # размытая копия фона для «жидкого стекла»
        small = QImage(max(w // 8, 1), max(h // 8, 1), QImage.Format_ARGB32_PREMULTIPLIED)
        small.fill(0)
        sp = QPainter(small)
        sp.scale(small.width() / w, small.height() / h)
        scene(sp, w, h, t)
        sp.fillRect(0, 0, w, h, QColor(0, 0, 0, 60))
        sp.end()
        blur = QPixmap.fromImage(small).scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        tint = QColor(self.theme[1]); tint.setAlpha(110)
        for wd in self.panels:
            if not wd.isVisible():
                continue
            r = QRect(wd.mapTo(self, QPoint(0, 0)), wd.size())
            path = QPainterPath(); path.addRoundedRect(QRectF(r), 18, 18)
            p.save(); p.setClipPath(path)
            p.drawPixmap(r.topLeft(), blur, r)
            p.fillRect(r, tint)
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, QColor(255, 255, 255, 75)); g.setColorAt(0.4, QColor(255, 255, 255, 12)); g.setColorAt(1, QColor(255, 255, 255, 0))
            p.fillRect(r, g)
            p.restore()
            p.setPen(QPen(QColor(255, 255, 255, 95), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)


class Choice(QWidget):
    def __init__(self, items, cur, color=False):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.g = QButtonGroup(self)
        for k, txt in items:
            b = QPushButton("" if color else txt)
            b.setCheckable(True)
            b.setChecked(k == cur)
            b.key = k
            if color:
                b.setFixedSize(30, 30)
                b.setStyleSheet(f"QPushButton{{background:{k};border-radius:15px;border:2px solid transparent;}}"
                                f"QPushButton:checked{{border:2px solid #fff;}}")
            self.g.addButton(b)
            lay.addWidget(b)
        lay.addStretch()

    def value(self):
        b = self.g.checkedButton()
        return b.key if b else None


class Settings(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win, self.cfg = win, win.cfg
        self.orig = {k: win.cfg[k] for k in ("theme", "accent", "layout", "bg", "style")}
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        tabs = QTabWidget()
        v.addWidget(tabs)

        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("Azure CLIENT_ID для входа через Microsoft"))
        self.cid = QLineEdit(self.cfg["client_id"]); l.addWidget(self.cid)
        h = QLabel("Регистрация: portal.azure.com → App registrations. Redirect URI: http://localhost "
                   "(Public client), Allow public client flows = Yes."); h.setObjectName("muted"); h.setWordWrap(True)
        l.addWidget(h); l.addStretch(); tabs.addTab(w, "Основное")

        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("Пресет производительности"))
        self.preset = QComboBox(); self.preset.addItems(PRESETS); self.preset.setCurrentText(self.cfg["preset"])
        l.addWidget(self.preset)
        h = QLabel("Баланс: G1GC. Максимум FPS: тонкая настройка G1GC. Слабый ПК: лёгкий SerialGC."); h.setObjectName("muted"); h.setWordWrap(True)
        l.addWidget(h); l.addStretch(); tabs.addTab(w, "Производительность")

        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("Тема")); self.theme = Choice([(k, k) for k in THEMES], self.cfg["theme"]); l.addWidget(self.theme)
        l.addWidget(QLabel("Цвет акцента"))
        row = QHBoxLayout()
        self.accent = Choice([(c, c) for c in ACCENTS], self.cfg["accent"], color=True); row.addWidget(self.accent)
        self.custom = self.cfg["accent"] if self.cfg["accent"] not in ACCENTS else None
        cb = QPushButton("Свой цвет…"); cb.clicked.connect(self.pick); row.addWidget(cb)
        l.addLayout(row)
        l.addWidget(QLabel("Расположение элементов"))
        self.layout_ = Choice([("tl", "Как TL"), ("classic", "Классика"), ("mirror", "Зеркальная"), ("compact", "Компактная")], self.cfg["layout"])
        l.addWidget(self.layout_)
        l.addWidget(QLabel("Анимированный фон")); self.bgc = Choice(BGS, self.cfg["bg"]); l.addWidget(self.bgc)
        l.addWidget(QLabel("Стиль интерфейса")); self.stc = Choice([("pixel", "Пиксельный"), ("glass", "Стекло")], self.cfg["style"]); l.addWidget(self.stc)
        l.addStretch(); tabs.addTab(w, "Оформление")

        w = QWidget(); l = QVBoxLayout(w)
        self.backup = QCheckBox("Копировать миры перед запуском (последние 3, только если мир изменился)")
        self.backup.setChecked(self.cfg["backup"]); l.addWidget(self.backup)
        ob = QPushButton("Открыть папку с копиями")
        ob.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(BACKUPS))))
        l.addWidget(ob); l.addStretch(); tabs.addTab(w, "Миры")

        for ch in (self.theme, self.accent, self.layout_, self.bgc, self.stc):
            ch.g.buttonClicked.connect(self.preview)  # живой предпросмотр
        hint = QLabel("Изменения видны сразу. «Отмена» вернёт прежний вид."); hint.setObjectName("muted"); v.addWidget(hint)
        row = QHBoxLayout(); row.addStretch()
        ok = QPushButton("Сохранить"); ok.setObjectName("accent"); ok.clicked.connect(self.apply)
        no = QPushButton("Отмена"); no.clicked.connect(self.reject)
        row.addWidget(ok); row.addWidget(no); v.addLayout(row)

    def preview(self, *_):
        self.cfg.update(theme=self.theme.value(), layout=self.layout_.value(), bg=self.bgc.value(), style=self.stc.value(),
                        accent=self.accent.value() or self.custom or self.orig["accent"])
        self.win.apply_all()

    def reject(self):
        self.cfg.update(self.orig)
        self.win.apply_all()
        super().reject()

    def pick(self):
        c = QColorDialog.getColor(QColor(self.cfg["accent"]), self)
        if c.isValid():
            self.custom = c.name()
            self.accent.g.setExclusive(False)
            for b in self.accent.g.buttons():
                b.setChecked(False)
            self.accent.g.setExclusive(True)
            self.preview()

    def apply(self):
        self.cfg.update(client_id=self.cid.text().strip(), preset=self.preset.currentText(),
                        theme=self.theme.value(), layout=self.layout_.value(), bg=self.bgc.value(), style=self.stc.value(), backup=self.backup.isChecked(),
                        accent=self.accent.value() or self.custom or self.cfg["accent"])
        save(self.cfg)
        self.win.apply_all()
        self.accept()


class Worlds(QDialog):
    def __init__(self, win, b):
        super().__init__(win)
        self.b = b
        self.setWindowTitle(f"Миры: {b['name']}")
        self.resize(560, 420)
        v = QVBoxLayout(self)
        t = QLabel(f"Сборка: {b['name']}\nВосстановление создаёт новый мир рядом со старым, ничего не перезаписывается.")
        t.setObjectName("muted"); v.addWidget(t)
        self.t = QTableWidget(0, 3)
        self.t.setHorizontalHeaderLabels(["Мир", "Дата копии", "Размер"])
        self.t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        v.addWidget(self.t)
        row = QHBoxLayout()
        nb = QPushButton("Сделать копию сейчас"); nb.clicked.connect(self.now); row.addWidget(nb); row.addStretch()
        rb = QPushButton("Восстановить"); rb.setObjectName("accent"); rb.clicked.connect(self.restore); row.addWidget(rb)
        cb = QPushButton("Закрыть"); cb.clicked.connect(self.accept); row.addWidget(cb)
        v.addLayout(row)
        self.fill()

    def fill(self):
        self.items = []
        base = BACKUPS / self.b["name"]
        if base.exists():
            for w in sorted(base.iterdir()):
                for s in sorted(w.iterdir(), reverse=True):
                    self.items.append((w.name, s))
        self.t.setRowCount(len(self.items))
        for i, (w, s) in enumerate(self.items):
            d = time.strftime("%d.%m.%Y %H:%M", time.localtime(s.stat().st_mtime))
            for j, x in enumerate((w, d, fmt_size(folder_size(s)))):
                self.t.setItem(i, j, QTableWidgetItem(x))

    def now(self):
        inst = INST / self.b["name"]
        for w in (inst / "saves").glob("*") if (inst / "saves").exists() else []:
            for s in (BACKUPS / self.b["name"] / w.name).glob("*") if (BACKUPS / self.b["name"] / w.name).exists() else []:
                (s / ".sig").write_text("0")  # принудительно считаем мир изменённым
        backup_worlds(self.b["name"], inst)
        self.fill()

    def restore(self):
        r = self.t.currentRow()
        if r < 0:
            return
        w, s = self.items[r]
        saves = INST / self.b["name"] / "saves"
        dst, n = saves / f"{w} (восстановлено)", 2
        while dst.exists():
            dst, n = saves / f"{w} (восстановлено {n})", n + 1
        shutil.copytree(s, dst, ignore=shutil.ignore_patterns(".sig"))
        QMessageBox.information(self, "Готово", f"Создан мир «{dst.name}»")


class IconPicker(QDialog):
    def __init__(self, win, b):
        super().__init__(win)
        self.b = b
        self.setWindowTitle("Иконка")
        v = QVBoxLayout(self)
        t = QLabel(f"Иконка для «{b['name']}»\nКартинки берутся из вашей копии Minecraft и хранятся только у вас.")
        t.setObjectName("muted"); v.addWidget(t)
        grid = QGridLayout()
        self.tex = textures()
        for i, (n, data) in enumerate(self.tex):
            pm = QPixmap(); pm.loadFromData(data)
            bt = QToolButton(); bt.setIcon(QIcon(pm.scaled(40, 40, Qt.KeepAspectRatio, Qt.FastTransformation)))
            bt.setIconSize(pm.scaled(40, 40).size()); bt.clicked.connect(lambda _=0, d=data: self.set(d))
            grid.addWidget(bt, i // 7, i % 7)
        v.addLayout(grid)
        if not self.tex:
            v.addWidget(QLabel("Сначала запусти любую сборку, чтобы скачалась игра."))
        row = QHBoxLayout(); row.addStretch()
        nb = QPushButton("Без иконки"); nb.clicked.connect(lambda: self.set(None)); row.addWidget(nb)
        cb = QPushButton("Закрыть"); cb.clicked.connect(self.accept); row.addWidget(cb)
        v.addLayout(row)

    def set(self, data):
        p = ICONS / f"{self.b['name']}.png"
        if data:
            p.write_bytes(data)
        elif p.exists():
            p.unlink()
        self.accept()


UA = {"User-Agent": "ZiwangerLauncher/1.0 (personal launcher)"}
TIERS = {
    "Слабый ПК": dict(ram=2, preset="Слабый ПК",
                      desc="Старые ПК и ноутбуки, 4 ГБ ОЗУ, встроенная графика. Максимум FPS: Sodium, Lithium и оптимизаторы. Дальность прорисовки лучше 6-8.",
                      mods=["fabric-api", "sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "krypton", "moreculling"]),
    "Средний ПК": dict(ram=4, preset="Баланс",
                       desc="8 ГБ ОЗУ и обычная видеокарта. Оптимизация, шейдеры (Iris), экономия ресурсов в свёрнутом окне.",
                       mods=["fabric-api", "sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "dynamic-fps", "modmenu", "iris"]),
    "Мощный ПК": dict(ram=8, preset="Максимум FPS",
                      desc="16+ ГБ ОЗУ и отдельная видеокарта. Шейдеры Iris и Distant Horizons (очень дальняя прорисовка).",
                      mods=["fabric-api", "sodium", "lithium", "ferrite-core", "immediatelyfast", "iris", "distanthorizons", "modmenu"]),
}


def mr_get(path, **params):
    q = urllib.parse.urlencode({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in params.items()})
    req = urllib.request.Request(f"https://api.modrinth.com/v2/{path}?{q}", headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def mr_search(query, version, loader):
    facets = [["project_type:mod"], [f"categories:{loader}"], [f"versions:{version}"]]
    extra = {} if query else {"index": "downloads"}
    return mr_get("search", query=query, facets=facets, limit=25, **extra)["hits"]


def mr_install(project, version, loader, mods_dir, seen):
    """Скачивает мод и его обязательные зависимости. None, если нет версии под игру."""
    vs = mr_get(f"project/{project}/version", game_versions=[version], loaders=[loader])
    if not vs:
        return None
    v = vs[0]
    if v["project_id"] in seen:
        return []
    seen.add(v["project_id"])
    f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
    mods_dir.mkdir(parents=True, exist_ok=True)
    dst = mods_dir / f["filename"]
    if not dst.exists():
        with urllib.request.urlopen(urllib.request.Request(f["url"], headers=UA), timeout=60) as r, open(dst, "wb") as o:
            shutil.copyfileobj(r, o)
    got = [f["filename"]]
    for d in v.get("dependencies", []):
        if d.get("dependency_type") == "required" and d.get("project_id") and d["project_id"] not in seen:
            got += mr_install(d["project_id"], version, loader, mods_dir, seen) or []
    return got


def build_tier(name, version, cb):
    t, bname = TIERS[name], f"{name} {version}"
    seen, got, miss = set(), [], []
    cb["setMax"](len(t["mods"]))
    for i, m in enumerate(t["mods"]):
        cb["setStatus"](f"Скачивание мода: {m}")
        try:
            r = mr_install(m, version, "fabric", INST / bname / "mods", seen)
        except Exception:
            r = None
        if r is None:
            miss.append(m)
        else:
            got += r
        cb["setProgress"](i + 1)
    return bname, got, miss


class Mods(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.hits = win, []
        v = QVBoxLayout(self)
        row = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText("Поиск модов на Modrinth (пусто = популярные)")
        self.q.returnPressed.connect(self.search)
        sb = QPushButton("Найти"); sb.clicked.connect(self.search)
        row.addWidget(self.q, 1); row.addWidget(sb); v.addLayout(row)
        self.info = QLabel("Выбери сборку на Fabric и нажми «Найти»"); self.info.setObjectName("muted"); self.info.setWordWrap(True)
        v.addWidget(self.info)
        self.list = QListWidget(); v.addWidget(self.list, 1)
        row = QHBoxLayout()
        ib = QPushButton("Установить в сборку"); ib.clicked.connect(self.install)
        ob = QPushButton("Папка mods"); ob.clicked.connect(self.open_mods)
        row.addWidget(ib); row.addWidget(ob); row.addStretch(); v.addLayout(row)

    def ctx(self):
        b = self.win.cur_build()
        if not b:
            self.info.setText("Сначала создай сборку"); return None
        if b["loader"] != "Fabric":
            self.info.setText("Моды ставятся в сборки на Fabric. Создай такую сборку или возьми готовую."); return None
        return b

    def run(self, fn, ok):
        self.job = Job(fn)
        self.job.status.connect(self.win.say)
        self.job.done.connect(ok)
        self.job.fail.connect(lambda m: (self.win.say("Ошибка сети"), self.info.setText(m)))
        self.job.start()
        self.win.say("Запрос к Modrinth…")

    def search(self):
        b = self.ctx()
        if b:
            q = self.q.text().strip()
            self.run(lambda cb: mr_search(q, b["version"], "fabric"), lambda hits: self.fill(hits, b))

    def fill(self, hits, b):
        self.hits = hits
        self.list.clear()
        for h in hits:
            self.list.addItem(f"{h['title']}  ·  {h['downloads']:,} загрузок\n{h['description']}")
        self.win.say("Готово")
        self.info.setText(f"Найдено: {len(hits)} для Fabric {b['version']}" if hits else "Ничего не найдено для этой версии")

    def install(self):
        b, r = self.ctx(), self.list.currentRow()
        if not b or r < 0:
            return
        h = self.hits[r]
        self.run(lambda cb: mr_install(h["project_id"], b["version"], "fabric", INST / b["name"] / "mods", set()),
                 lambda res: self.done(h["title"], b, res))

    def done(self, title, b, res):
        msg = f"Нет версии «{title}» для {b['version']}" if res is None else f"Установлено: {title} (+зависимости: {max(len(res) - 1, 0)})"
        self.win.say(msg); self.info.setText(msg)

    def open_mods(self):
        b = self.win.cur_build()
        if b:
            p = INST / b["name"] / "mods"; p.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


AUDIO = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".opus"}


def mmss(ms):
    s = max(int(ms // 1000), 0)
    return f"{s // 60}:{s % 60:02d}"


class Music(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.files, self.idx = win, [], -1
        self.player = QMediaPlayer(self)
        self.out = QAudioOutput(self)
        self.player.setAudioOutput(self.out)
        self.out.setVolume(win.cfg["volume"] / 100)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.folder = QLabel(); self.folder.setObjectName("muted")
        fb = QPushButton("Выбрать папку"); fb.clicked.connect(self.choose)
        rb = QPushButton("Обновить"); rb.clicked.connect(self.scan)
        top.addWidget(self.folder, 1); top.addWidget(fb); top.addWidget(rb)
        v.addLayout(top)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda it: self.play_at(self.list.row(it)))
        v.addWidget(self.list, 1)
        self.now = QLabel("Ничего не играет"); v.addWidget(self.now)
        row = QHBoxLayout()
        self.pos = QSlider(Qt.Horizontal)
        self.pos.sliderMoved.connect(self.player.setPosition)
        self.time = QLabel("0:00 / 0:00")
        row.addWidget(self.pos, 1); row.addWidget(self.time)
        v.addLayout(row)
        ctl = QHBoxLayout()
        pb, self.pp, nb = QPushButton("«"), QPushButton("▶"), QPushButton("»")
        pb.clicked.connect(lambda: self.step(-1)); self.pp.clicked.connect(self.toggle); nb.clicked.connect(lambda: self.step(1))
        self.shuf = QPushButton("Случайно"); self.shuf.setCheckable(True)
        self.vol = QSlider(Qt.Horizontal); self.vol.setRange(0, 100); self.vol.setValue(win.cfg["volume"]); self.vol.setFixedWidth(120)
        self.vol.valueChanged.connect(self.set_volume)
        for w in (pb, self.pp, nb, self.shuf):
            ctl.addWidget(w)
        ctl.addStretch(); ctl.addWidget(QLabel("Громкость")); ctl.addWidget(self.vol)
        v.addLayout(ctl)
        self.player.positionChanged.connect(self.on_pos)
        self.player.durationChanged.connect(lambda d: self.pos.setRange(0, d))
        self.player.playbackStateChanged.connect(
            lambda st: self.pp.setText("❚❚" if st == QMediaPlayer.PlayingState else "▶"))
        self.player.mediaStatusChanged.connect(lambda st: self.step(1) if st == QMediaPlayer.EndOfMedia else None)
        self.scan()

    def choose(self):
        d = QFileDialog.getExistingDirectory(self, "Папка с музыкой", self.win.cfg["music_dir"] or str(Path.home()))
        if d:
            self.win.cfg["music_dir"] = d; save(self.win.cfg); self.scan()

    def scan(self):
        d = self.win.cfg["music_dir"]
        self.folder.setText(d or "Папка не выбрана")
        self.files = sorted(f for f in Path(d).rglob("*") if f.suffix.lower() in AUDIO) if d and Path(d).is_dir() else []
        self.list.clear()
        for f in self.files:
            self.list.addItem(f.stem)
        if d and not self.files:
            self.now.setText("В папке нет аудиофайлов (mp3, ogg, wav, flac, m4a)")

    def play_at(self, i):
        if 0 <= i < len(self.files):
            self.idx = i
            self.player.setSource(QUrl.fromLocalFile(str(self.files[i])))
            self.player.play()
            self.list.setCurrentRow(i)
            self.now.setText("♪ " + self.files[i].stem)

    def toggle(self):
        if self.idx < 0:
            self.play_at(max(self.list.currentRow(), 0))
        elif self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def step(self, d):
        n = len(self.files)
        if not n:
            return
        if self.shuf.isChecked() and n > 1:
            i = random.choice([k for k in range(n) if k != self.idx])
        else:
            i = (self.idx + d) % n
        self.play_at(i)

    def set_volume(self, v):
        self.out.setVolume(v / 100)
        self.win.cfg["volume"] = v

    def on_pos(self, ms):
        if not self.pos.isSliderDown():
            self.pos.setValue(ms)
        self.time.setText(f"{mmss(ms)} / {mmss(self.player.duration())}")


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ziwanger Launcher")
        self.setWindowIcon(QIcon(bedrock(256)))
        self.resize(1000, 640)
        self.cfg = load()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(lambda: self.log.appendPlainText(
            bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))
        self.proc.finished.connect(self.game_closed)
        self.versions = None

        self.glow = Glow()
        self.setCentralWidget(self.glow)
        root = QVBoxLayout(self.glow)
        root.setContentsMargins(16, 16, 16, 16)

        # шапка
        self.hd = hd = QFrame(); hd.setObjectName("panel"); h = self.hl = QHBoxLayout(hd)
        logo = QLabel(); logo.setPixmap(bedrock(40)); logo.setFixedSize(40, 40)
        self.logo = logo; h.addWidget(logo)
        brand = QLabel("Ziwanger Launcher"); brand.setObjectName("title"); h.addWidget(brand); h.addStretch()
        self.headpic = QLabel(); self.headpic.setPixmap(head()); h.addWidget(self.headpic)
        self.acc = QComboBox(); self.acc.setMinimumWidth(190); self.acc.currentIndexChanged.connect(self.acc_changed)
        h.addWidget(self.acc)
        for txt, fn in (("Аккаунты", self.accounts), ("Журнал", lambda: self.tabs.setCurrentIndex(0)),
                        ("Настройки", lambda: Settings(self).exec())):
            b = QPushButton(txt); b.clicked.connect(fn); h.addWidget(b)
        root.addWidget(hd)

        # сборки
        self.bp = QFrame(); self.bp.setObjectName("panel"); bl = QVBoxLayout(self.bp)
        lb = QLabel("СБОРКИ"); lb.setObjectName("muted"); bl.addWidget(lb)
        self.blist = QListWidget(); self.blist.setIconSize(QPixmap(28, 28).size())
        self.blist.currentRowChanged.connect(self.pick_build); bl.addWidget(self.blist)
        row = QHBoxLayout()
        for txt, fn in (("Создать", self.create_build), ("Готовые", self.ready_builds)):
            b = QPushButton(txt); b.clicked.connect(fn); row.addWidget(b)
        bl.addLayout(row)
        ib = QPushButton("Импорт .mrpack"); ib.clicked.connect(self.import_pack); bl.addWidget(ib)

        # основная панель
        self.mp = QFrame(); self.mp.setObjectName("panel"); m = QVBoxLayout(self.mp)
        top = QHBoxLayout(); col = QVBoxLayout()
        self.title = QLabel("Нет сборок"); self.title.setObjectName("title"); col.addWidget(self.title)
        self.info = QLabel(""); self.info.setObjectName("muted"); col.addWidget(self.info)
        top.addLayout(col); top.addStretch()
        self.stop = QPushButton("Остановить"); self.stop.clicked.connect(self.proc.kill); self.stop.setEnabled(False)
        self.play_btn = QPushButton("Играть"); self.play_btn.setObjectName("accent"); self.play_btn.clicked.connect(self.play)
        self.actions = QHBoxLayout(); self.actions.addWidget(self.stop); self.actions.addWidget(self.play_btn)
        top.addLayout(self.actions); m.addLayout(top)
        self.tabs = QTabWidget(); m.addWidget(self.tabs)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.tabs.addTab(self.log, "Журнал")
        bt = QWidget(); bv = QVBoxLayout(bt); self.details = QLabel(); self.details.setObjectName("muted"); bv.addWidget(self.details)
        for txt, fn in (("Сменить иконку", self.change_icon), ("Миры и копии", self.worlds),
                        ("Открыть папку", self.open_folder), ("Удалить сборку", self.delete_build)):
            b = QPushButton(txt); b.clicked.connect(fn); bv.addWidget(b)
        bv.addStretch(); self.tabs.addTab(bt, "Сборка")
        self.mods = Mods(self); self.tabs.addTab(self.mods, "Моды")
        self.music = Music(self); self.tabs.addTab(self.music, "Музыка")

        self.body = QBoxLayout(QBoxLayout.LeftToRight); root.addLayout(self.body, 1)

        # нижняя панель в стиле T Launcher
        self.tlbar = QFrame(); self.tlbar.setObjectName("panel"); self.tlh = QHBoxLayout(self.tlbar)
        self.bsel = QComboBox(); self.bsel.setMinimumWidth(220)
        self.bsel.currentIndexChanged.connect(lambda i: self.blist.setCurrentRow(i) if i >= 0 else None)
        self.newb = QPushButton("＋ Сборка"); self.newb.clicked.connect(self.create_build)
        self.impb = QPushButton("Импорт .mrpack"); self.impb.clicked.connect(self.import_pack)
        self.readyb = QPushButton("Готовые сборки"); self.readyb.clicked.connect(self.ready_builds)
        root.addWidget(self.tlbar)

        # статус
        self.sp = sp = QFrame(); sp.setObjectName("panel"); sl = QHBoxLayout(sp)
        self.status = QLabel("Готово"); sl.addWidget(self.status, 1)
        self.bar = QProgressBar(); self.bar.setFixedWidth(240); self.bar.setTextVisible(False); self.bar.hide(); sl.addWidget(self.bar)
        root.addWidget(sp)

        self.apply_all()
        self.refresh_accounts()
        self.refresh_builds()
        if self.cfg["seen"] != VERSION:
            self.cfg["seen"] = VERSION; save(self.cfg)
            QMessageBox.information(self, f"Обновлено до {VERSION}",
                "Что нового:\n• 4 темы и любой цвет акцента\n• 3 раскладки без перезапуска\n"
                "• Пресеты производительности\n• Иконки сборок из вашей копии игры\n"
                "• Копии миров перед запуском и восстановление\n• Вход через Microsoft, импорт .mrpack")

    # ---- оформление
    def apply_all(self):
        t, a = THEMES[self.cfg["theme"]], self.cfg["accent"]
        tl = self.cfg["layout"] == "tl"
        QApplication.instance().setStyleSheet(qss(t, a, self.cfg["bg"] != "none", self.cfg["style"] == "pixel"))
        self.glow.theme, self.glow.accent, self.glow.pixel = t, a, self.cfg["style"] == "pixel"
        self.glow.set_bg(self.cfg["bg"])
        while self.body.count():
            self.body.takeAt(0)
        lay = self.cfg["layout"]
        self.body.setDirection(QBoxLayout.TopToBottom if lay == "compact" else QBoxLayout.LeftToRight)
        self.bp.setMaximumHeight(170 if lay == "compact" else 16777215)
        self.bp.setMaximumWidth(16777215 if lay == "compact" else 270)
        order = [self.mp] if tl else ([self.mp, self.bp] if lay == "mirror" else [self.bp, self.mp])
        self.bp.setVisible(not tl)
        self.tlbar.setVisible(tl)
        for w in order:
            self.body.addWidget(w, 1 if w is self.mp else 0)
        self.place(tl)
        self.glow.panels = [self.hd, self.bp, self.mp, self.tlbar, self.sp]
        self.glow.update()

    def place(self, tl):
        movable = (self.headpic, self.acc, self.bsel, self.stop, self.play_btn)
        for lay in (self.hl, self.actions, self.tlh):
            for w in movable:
                lay.removeWidget(w)
        while self.tlh.count():
            self.tlh.takeAt(0)
        if tl:
            for w in (self.headpic, self.acc, self.bsel, self.newb, self.readyb, self.impb):
                self.tlh.addWidget(w)
            self.tlh.addStretch()
            self.tlh.addWidget(self.stop); self.tlh.addWidget(self.play_btn)
        else:
            self.hl.insertWidget(3, self.headpic); self.hl.insertWidget(4, self.acc)
            self.actions.addWidget(self.stop); self.actions.addWidget(self.play_btn)
        for w in movable + (self.newb, self.readyb, self.impb):
            w.setVisible(tl or w in (self.headpic, self.acc, self.stop, self.play_btn))

    def say(self, t):
        self.status.setText(t)

    # ---- аккаунты
    def refresh_accounts(self):
        if not self.cfg["accounts"]:
            self.cfg["accounts"].append({"type": "offline", "name": "Player"})
        self.acc.blockSignals(True); self.acc.clear()
        for a in self.cfg["accounts"]:
            self.acc.addItem(f"{a['name']}  ·  { {'microsoft': 'Microsoft', 'ely': 'Ely.by'}.get(a['type'], 'Офлайн') }")
        self.acc.setCurrentIndex(min(self.cfg["account"], self.acc.count() - 1)); self.acc.blockSignals(False)

    def acc_changed(self, i):
        self.cfg["account"] = max(i, 0); save(self.cfg)

    def cur_acc(self):
        return self.cfg["accounts"][min(self.cfg["account"], len(self.cfg["accounts"]) - 1)]

    def accounts(self):
        d = QDialog(self); d.setWindowTitle("Аккаунты"); d.setMinimumWidth(560); v = QVBoxLayout(d)
        lst = QListWidget(); v.addWidget(lst)

        def fill():
            lst.clear()
            for a in self.cfg["accounts"]:
                lst.addItem(f"{a['name']} ({a['type']})")

        def add_off():
            n, ok = QInputDialog.getText(d, "Офлайн", "Ник:")
            if ok and n.strip():
                self.cfg["accounts"].append({"type": "offline", "name": n.strip()}); done()

        def add_ms():
            if not self.cfg["client_id"]:
                QMessageBox.information(d, "Нужен CLIENT_ID", "Впиши Azure CLIENT_ID в Настройки → Основное."); return
            url, state, ver = mll.microsoft_account.get_secure_login_data(self.cfg["client_id"], REDIRECT)
            webbrowser.open(url)
            ans, ok = QInputDialog.getText(d, "Microsoft", "После входа вставь сюда весь URL из адресной строки:")
            if not ok:
                return
            try:
                code = mll.microsoft_account.parse_auth_code_url(ans.strip(), state)
                r = mll.microsoft_account.complete_login(self.cfg["client_id"], None, REDIRECT, code, ver)
                self.cfg["accounts"].append({"type": "microsoft", "name": r["name"], "refresh": r["refresh_token"]}); done()
            except Exception as e:
                QMessageBox.critical(d, "Ошибка входа", str(e))

        def add_ely():
            login, ok = QInputDialog.getText(d, "Ely.by", "Ник или e-mail:")
            if not ok or not login.strip():
                return
            pw, ok = QInputDialog.getText(d, "Ely.by", "Пароль (с 2FA: пароль:код):", QLineEdit.Password)
            if not ok:
                return
            try:
                r = ely_post("authenticate", {"username": login.strip(), "password": pw,
                                              "clientToken": uuid.uuid4().hex, "requestUser": False})
                pr = r["selectedProfile"]
                self.cfg["accounts"].append({"type": "ely", "name": pr["name"], "uuid": pr["id"],
                                             "access": r["accessToken"], "client": r["clientToken"]}); done()
            except Exception as e:
                QMessageBox.critical(d, "Ошибка входа", str(e))

        def rem():
            r = lst.currentRow()
            if r >= 0 and len(self.cfg["accounts"]) > 1:
                self.cfg["accounts"].pop(r); done()

        def done():
            save(self.cfg); fill(); self.refresh_accounts()

        row = QHBoxLayout()
        for txt, fn in (("Офлайн", add_off), ("Microsoft", add_ms), ("Ely.by", add_ely),
                        ("Регистрация Ely.by", lambda: webbrowser.open("https://account.ely.by/register")),
                        ("Удалить", rem), ("Закрыть", d.accept)):
            b = QPushButton(txt); b.clicked.connect(fn); row.addWidget(b)
        v.addLayout(row); fill(); d.exec()

    # ---- сборки
    def cur_build(self):
        bs = self.cfg["builds"]
        return bs[self.blist.currentRow()] if 0 <= self.blist.currentRow() < len(bs) else None

    def refresh_builds(self, select=None):
        self.blist.blockSignals(True); self.blist.clear()
        for b in self.cfg["builds"]:
            it = QListWidgetItem(icon_for(b), b["name"]); self.blist.addItem(it)
        self.blist.blockSignals(False)
        self.bsel.blockSignals(True); self.bsel.clear()
        self.bsel.addItems([b["name"] for b in self.cfg["builds"]]); self.bsel.blockSignals(False)
        if self.cfg["builds"]:
            self.blist.setCurrentRow(select if select is not None else min(self.cfg["build"], len(self.cfg["builds"]) - 1))
        else:
            self.pick_build(-1)

    def pick_build(self, i):
        if i >= 0:
            self.bsel.blockSignals(True); self.bsel.setCurrentIndex(i); self.bsel.blockSignals(False)
        b = self.cur_build()
        self.play_btn.setEnabled(b is not None)
        if not b:
            self.title.setText("Нет сборок"); self.info.setText("Нажми «Создать» или импортируй .mrpack"); self.details.setText(""); return
        self.cfg["build"] = i; save(self.cfg)
        self.title.setText(b["name"])
        last = b.get("last") or "ещё не запускалась"
        self.info.setText(f"{b['loader']} {b['version']}  ·  Последний запуск: {last}")
        self.details.setText(f"Версия: {b['version']}\nЗагрузчик: {b['loader']}\nПамять: {b['ram']} ГБ\nПапка: {INST / b['name']}")

    def versions_list(self):
        if self.versions is None:
            try:
                self.versions = [v["id"] for v in mll.utils.get_version_list() if v["type"] == "release"]
            except Exception:
                self.versions = [v["id"] for v in mll.utils.get_installed_versions(MC_DIR)]
        return self.versions

    def create_build(self):
        d = QDialog(self); d.setWindowTitle("Новая сборка"); f = QFormLayout(d)
        name = QLineEdit(); ver = QComboBox(); ver.addItems(self.versions_list())
        ld = QComboBox(); ld.addItems(["Vanilla", "Fabric"]); ram = QSpinBox(); ram.setRange(1, 32); ram.setValue(4)
        for lbl, w in (("Название", name), ("Версия", ver), ("Загрузчик", ld), ("Память, ГБ", ram)):
            f.addRow(lbl, w)
        ok = QPushButton("Создать"); ok.setObjectName("accent"); ok.clicked.connect(d.accept); f.addRow(ok)
        if d.exec() and name.text().strip():
            n = name.text().strip()
            if any(b["name"] == n for b in self.cfg["builds"]):
                QMessageBox.warning(self, "Ошибка", "Сборка с таким названием уже есть"); return
            self.cfg["builds"].append(dict(name=n, version=ver.currentText(), loader=ld.currentText(), ram=ram.value()))
            save(self.cfg); self.refresh_builds(len(self.cfg["builds"]) - 1)

    def import_pack(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт .mrpack", "", "Modrinth pack (*.mrpack)")
        if not path:
            return
        try:
            info = mll.mrpack.get_mrpack_information(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e)); return
        n = info["name"]
        inst = INST / n
        self.run_job(lambda cb: (mll.mrpack.install_mrpack(path, MC_DIR, modpack_directory=inst, callback=cb),
                                 mll.mrpack.get_mrpack_launch_version(path))[1],
                     lambda vid: self.pack_done(n, info, vid))

    def pack_done(self, n, info, vid):
        self.cfg["builds"].append(dict(name=n, version=info["minecraftVersion"], loader="mrpack", ram=4, vid=vid))
        save(self.cfg); self.refresh_builds(len(self.cfg["builds"]) - 1); self.say(f"Сборка «{n}» импортирована")

    def ready_builds(self):
        d = QDialog(self); d.setWindowTitle("Готовые сборки"); d.setMinimumWidth(580); v = QVBoxLayout(d)
        h = QLabel("Fabric и подобранные моды с Modrinth. Моды скачаются сразу, сама игра при первом запуске.")
        h.setObjectName("muted"); h.setWordWrap(True); v.addWidget(h)
        row = QHBoxLayout(); row.addWidget(QLabel("Версия Minecraft"))
        ver = QComboBox(); ver.addItems(self.versions_list())
        if ver.findText("1.20.1") >= 0:
            ver.setCurrentIndex(ver.findText("1.20.1"))
        row.addWidget(ver, 1); v.addLayout(row)

        def go(n):
            vv = ver.currentText(); d.accept()
            self.run_job(lambda cb: build_tier(n, vv, cb), lambda r: self.tier_done(n, vv, r))

        for name, t in TIERS.items():
            r = QHBoxLayout(); col = QVBoxLayout()
            col.addWidget(QLabel(f"<b>{name}</b> · {t['ram']} ГБ"))
            ds = QLabel(t["desc"]); ds.setObjectName("muted"); ds.setWordWrap(True); col.addWidget(ds)
            r.addLayout(col, 1)
            b = QPushButton("Установить"); b.clicked.connect(lambda _=0, n=name: go(n)); r.addWidget(b)
            v.addLayout(r)
        d.exec()

    def tier_done(self, name, ver, r):
        bname, got, miss = r
        if not any(b["name"] == bname for b in self.cfg["builds"]):
            t = TIERS[name]
            self.cfg["builds"].append(dict(name=bname, version=ver, loader="Fabric", ram=t["ram"], preset=t["preset"]))
        save(self.cfg)
        self.refresh_builds(next(i for i, b in enumerate(self.cfg["builds"]) if b["name"] == bname))
        msg = f"«{bname}»: скачано файлов {len(got)}" + (f"; нет для {ver}: {', '.join(miss)}" if miss else "")
        self.log.appendPlainText(msg); self.say(msg)

    def change_icon(self):
        b = self.cur_build()
        if b:
            IconPicker(self, b).exec(); self.refresh_builds(self.blist.currentRow())

    def worlds(self):
        b = self.cur_build()
        if b:
            Worlds(self, b).exec()

    def open_folder(self):
        b = self.cur_build()
        if b:
            p = INST / b["name"]; p.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def delete_build(self):
        b = self.cur_build()
        if b and QMessageBox.question(self, "Удалить", f"Убрать «{b['name']}» из списка? Файлы на диске останутся.") == QMessageBox.Yes:
            self.cfg["builds"].remove(b); save(self.cfg); self.refresh_builds(0)

    # ---- запуск
    def run_job(self, fn, on_done):
        self.play_btn.setEnabled(False); self.bar.show()
        self.job = Job(fn)
        self.job.status.connect(self.say)
        self.job.prog.connect(lambda p, m: (self.bar.setMaximum(max(m, 1)), self.bar.setValue(p)))
        self.job.done.connect(lambda r: (self.bar.hide(), self.play_btn.setEnabled(True), on_done(r)))
        self.job.fail.connect(self.job_failed)
        self.job.start()

    def job_failed(self, msg):
        self.bar.hide(); self.play_btn.setEnabled(True); self.say("Ошибка"); self.log.appendPlainText(msg)
        QMessageBox.critical(self, "Ошибка", msg)

    def play(self):
        b, acc = self.cur_build(), self.cur_acc()
        if b:
            self.run_job(lambda cb: prepare(b, acc, self.cfg, cb), lambda r: self.launch(b, r))

    def launch(self, b, r):
        cmd, inst = r
        b["last"] = time.strftime("%d.%m.%Y %H:%M"); save(self.cfg); self.pick_build(self.blist.currentRow())
        self.music.player.pause()  # игра запускается со своей музыкой
        self.log.clear(); self.tabs.setCurrentIndex(0)
        self.proc.setWorkingDirectory(inst); self.proc.start(cmd[0], cmd[1:])
        self.say("Игра запущена"); self.stop.setEnabled(True); self.play_btn.setEnabled(False)

    def game_closed(self, code, _):
        self.say(f"Игра закрыта (код {code})"); self.stop.setEnabled(False); self.play_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    for f in (Path(__file__).with_name("minecraft.ttf"), HOME / "minecraft.ttf"):
        if f.exists():
            QFontDatabase.addApplicationFont(str(f))
    if "--icon" in sys.argv:
        bedrock(256).save("icon.png"); bedrock(256).save("icon.ico")
        print("Создано: icon.ico и icon.png"); sys.exit()
    w = Main()
    w.show()
    sys.exit(app.exec())
