"""Generator asset Network Engineer Simulator (gambar, suara, font).

Jalankan:  python tools/generate_assets.py
Semua asset dibuat prosedural (original, bebas lisensi) kecuali font
yang diunduh (SIL OFL) jika koneksi tersedia.
"""
import math, os, random, sys, wave, struct, urllib.request
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

pygame.init()
ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
IMG = A / "images"

NAVY = (8, 14, 28); BODY = (26, 42, 74); BODY2 = (38, 58, 98)
CYAN = (0, 229, 255); BLUE = (41, 121, 255); GREEN = (46, 214, 110)
RED = (240, 66, 76); AMBER = (255, 196, 61); WHITE = (222, 232, 248)
GRAY = (90, 104, 128); DARK = (14, 22, 40); ORANGE = (255, 140, 50)


def surf(w, h=None):
    return pygame.Surface((w, h or w), pygame.SRCALPHA)


def save(s, path, size=None):
    if size:
        s = pygame.transform.smoothscale(s, size if isinstance(size, tuple) else (size, size))
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(s, str(path))


def rr(s, color, rect, r=16, w=0):
    pygame.draw.rect(s, color, rect, w, border_radius=r)


def body(s, rect, r=18, fill=BODY, edge=CYAN):
    rr(s, fill, rect, r); rr(s, edge, rect, r, 6)


def dot(s, pos, color, r=7):
    pygame.draw.circle(s, color, pos, r)


def ports(s, x0, y, n, step=22, size=14, color=DARK, edge=CYAN):
    for i in range(n):
        r = pygame.Rect(x0 + i * step, y, size, size)
        rr(s, color, r, 3); rr(s, edge, r, 3, 2)


def arc_wifi(s, cx, cy, color=CYAN, n=3):
    for i in range(1, n + 1):
        r = 22 * i
        pygame.draw.arc(s, color, (cx - r, cy - r, 2 * r, 2 * r), math.radians(45), math.radians(135), 7)
    dot(s, (cx, cy), color, 8)


# ---------------- DEVICES (256 -> 128) ----------------
def d_router(s):
    body(s, (24, 130, 208, 80))
    for x in (64, 192):
        pygame.draw.line(s, CYAN, (x, 130), (x, 66), 8); dot(s, (x, 60), CYAN, 9)
    for i in range(4):
        dot(s, (56 + i * 26, 170), GREEN if i < 3 else AMBER)
    cx, cy = 178, 170
    pygame.draw.circle(s, BLUE, (cx, cy), 26, 5)
    pygame.draw.line(s, WHITE, (cx - 16, cy), (cx + 16, cy), 5); pygame.draw.line(s, WHITE, (cx, cy - 16), (cx, cy + 16), 5)
    for p in ((cx + 18, cy), (cx - 18, cy), (cx, cy - 18), (cx, cy + 18)):
        dot(s, p, WHITE, 5)


def d_switch(s, managed=False):
    body(s, (20, 108, 216, 84))
    ports(s, 36, 128, 8)
    ports(s, 36, 156, 8)
    dot(s, (40, 98), GREEN, 5)
    if managed:
        rr(s, BLUE, (168, 80, 60, 28), 6); pygame.draw.circle(s, WHITE, (198, 94), 8, 3)
        rr(s, BODY2, (176, 160, 40, 20), 4); pygame.draw.line(s, CYAN, (182, 170), (210, 170), 3)


def d_hub(s):
    body(s, (30, 100, 196, 96), fill=(52, 60, 80), edge=GRAY)
    for row in range(2):
        for i in range(4):
            r = pygame.Rect(58 + i * 36, 120 + row * 32, 22, 18)
            rr(s, DARK, r, 3); rr(s, GRAY, r, 3, 2)
    dot(s, (50, 112), AMBER, 5)
    pygame.draw.line(s, GRAY, (60, 90), (196, 90), 6)


def d_pc(s):
    rr(s, BODY, (34, 52, 116, 90), 10); rr(s, CYAN, (34, 52, 116, 90), 10, 6)
    rr(s, (10, 30, 60), (46, 64, 92, 66), 4)
    pygame.draw.line(s, CYAN, (56, 80), (96, 80), 4); pygame.draw.line(s, BLUE, (56, 94), (118, 94), 4)
    pygame.draw.rect(s, GRAY, (84, 142, 14, 22)); rr(s, GRAY, (60, 162, 62, 10), 4)
    body(s, (160, 70, 62, 130), r=10)
    rr(s, DARK, (172, 84, 38, 10), 3); dot(s, (191, 186), GREEN, 6)
    pygame.draw.circle(s, CYAN, (191, 130), 14, 4)


def d_laptop(s):
    rr(s, BODY, (52, 62, 152, 98), 10); rr(s, CYAN, (52, 62, 152, 98), 10, 6)
    rr(s, (10, 30, 60), (64, 74, 128, 74), 4)
    pygame.draw.line(s, CYAN, (76, 92), (120, 92), 4); pygame.draw.line(s, BLUE, (76, 108), (150, 108), 4)
    pygame.draw.polygon(s, BODY2, [(30, 196), (226, 196), (206, 164), (50, 164)])
    pygame.draw.polygon(s, CYAN, [(30, 196), (226, 196), (206, 164), (50, 164)], 5)
    rr(s, GRAY, (108, 176, 40, 8), 4)


def d_server(s):
    for i in range(3):
        y = 48 + i * 56
        body(s, (40, y, 176, 48), r=8)
        for j in range(3):
            dot(s, (62 + j * 18, y + 24), GREEN if (i + j) % 3 else AMBER, 5)
        rr(s, DARK, (130, y + 14, 70, 20), 4)
        for k in range(5):
            pygame.draw.line(s, CYAN, (138 + k * 12, y + 18), (138 + k * 12, y + 30), 3)


def d_ap(s):
    arc_wifi(s, 128, 110, CYAN)
    rr(s, BODY, (56, 160, 144, 40), 20); rr(s, CYAN, (56, 160, 144, 40), 20, 6)
    dot(s, (92, 180), GREEN, 6); dot(s, (128, 180), GREEN, 6); dot(s, (164, 180), AMBER, 6)


def d_firewall(s):
    rr(s, (60, 24, 34), (28, 60, 200, 140), 10); rr(s, RED, (28, 60, 200, 140), 10, 6)
    for row in range(4):
        y = 66 + row * 32
        pygame.draw.line(s, RED, (34, y + 28), (222, y + 28), 4)
        off = 0 if row % 2 == 0 else 24
        for x in range(34 + off, 222, 48):
            pygame.draw.line(s, RED, (x, y), (x, y + 28), 4)
    pts = [(128, 40), (176, 58), (176, 120), (128, 168), (80, 120), (80, 58)]
    pygame.draw.polygon(s, NAVY, pts); pygame.draw.polygon(s, AMBER, pts, 7)
    pygame.draw.polygon(s, ORANGE, [(128, 140), (108, 112), (122, 96), (126, 108), (140, 84), (150, 112)])


def d_printer(s):
    rr(s, WHITE, (76, 36, 104, 52), 6); rr(s, GRAY, (76, 36, 104, 52), 6, 4)
    for y in (52, 64, 76):
        pygame.draw.line(s, GRAY, (88, y), (168, y), 3)
    body(s, (30, 88, 196, 80), r=14)
    rr(s, DARK, (52, 128, 152, 12), 4)
    dot(s, (190, 106), GREEN, 6)
    rr(s, WHITE, (70, 150, 116, 52), 4); rr(s, GRAY, (70, 150, 116, 52), 4, 4)
    pygame.draw.line(s, GRAY, (84, 170), (172, 170), 3); pygame.draw.line(s, GRAY, (84, 184), (150, 184), 3)


def d_modem(s):
    body(s, (30, 112, 196, 80))
    pygame.draw.line(s, CYAN, (62, 112), (46, 56), 8); dot(s, (45, 52), CYAN, 9)
    for i in range(5):
        dot(s, (62 + i * 24, 152), GREEN if i != 3 else AMBER, 7)
    pygame.draw.line(s, GRAY, (128, 192), (128, 226), 8); pygame.draw.line(s, GRAY, (128, 226), (190, 226), 8)
    pygame.draw.circle(s, BLUE, (190, 128), 8, 3)


def d_cloud(s):
    col = (20, 48, 92)
    blobs = [(96, 140, 44), (136, 112, 52), (180, 140, 42), (128, 156, 46), (80, 160, 30), (190, 164, 30)]
    for x, y, r in blobs:
        pygame.draw.circle(s, CYAN, (x, y), r + 6)
    for x, y, r in blobs:
        pygame.draw.circle(s, col, (x, y), r)
    pygame.draw.circle(s, WHITE, (128, 144), 26, 4)
    pygame.draw.ellipse(s, WHITE, (110, 118, 36, 52), 4); pygame.draw.line(s, WHITE, (102, 144), (154, 144), 4)


DEVICES = {
    "router": d_router, "switch": d_switch, "managed_switch": lambda s: d_switch(s, True),
    "hub": d_hub, "pc": d_pc, "laptop": d_laptop, "server": d_server,
    "access_point": d_ap, "firewall": d_firewall, "printer": d_printer,
    "modem": d_modem, "internet_cloud": d_cloud,
}


def make_devices():
    for name, fn in DEVICES.items():
        s = surf(256); fn(s)
        save(s, IMG / "devices" / f"{name}.png", 128)
        save(s, IMG / "devices" / f"{name}_small.png", 48)


# ---------------- ICONS (128 -> 48) ----------------
def star_pts(cx, cy, ro, ri):
    return [(cx + (ro if i % 2 == 0 else ri) * math.sin(i * math.pi / 5),
             cy - (ro if i % 2 == 0 else ri) * math.cos(i * math.pi / 5)) for i in range(10)]


def i_select(s): pygame.draw.polygon(s, WHITE, [(36, 20), (36, 100), (56, 82), (70, 112), (84, 106), (70, 78), (96, 78)])
def i_cable(s):
    pygame.draw.line(s, CYAN, (30, 96), (98, 32), 10); pygame.draw.circle(s, CYAN, (28, 98), 14); pygame.draw.circle(s, CYAN, (100, 30), 14)
def i_delete(s):
    pygame.draw.line(s, RED, (30, 30), (98, 98), 14); pygame.draw.line(s, RED, (98, 30), (30, 98), 14)
def i_rotate(s):
    pygame.draw.arc(s, WHITE, (24, 24, 80, 80), 0.6, 5.2, 12)
    ex, ey = 64 + 40 * math.cos(5.2), 64 - 40 * math.sin(5.2)
    pygame.draw.polygon(s, WHITE, [(ex - 16, ey - 4), (ex + 14, ey - 14), (ex + 6, ey + 18)])
def i_play(s): pygame.draw.polygon(s, GREEN, [(38, 24), (38, 104), (100, 64)])
def i_pause(s): rr(s, AMBER, (34, 26, 22, 76), 4); rr(s, AMBER, (72, 26, 22, 76), 4)
def i_stop(s): rr(s, RED, (30, 30, 68, 68), 8)
def i_settings(s):
    for k in range(8):
        a = k * math.pi / 4
        pygame.draw.line(s, WHITE, (64 + 34 * math.cos(a), 64 + 34 * math.sin(a)), (64 + 52 * math.cos(a), 64 + 52 * math.sin(a)), 16)
    pygame.draw.circle(s, WHITE, (64, 64), 38); pygame.draw.circle(s, (0, 0, 0, 0), (64, 64), 16)
def i_terminal(s):
    rr(s, WHITE, (12, 24, 104, 80), 10, 8)
    pygame.draw.lines(s, CYAN, False, [(32, 46), (52, 62), (32, 78)], 8); pygame.draw.line(s, CYAN, (62, 82), (92, 82), 8)
def i_packet(s):
    rr(s, CYAN, (20, 32, 88, 64), 8, 8); pygame.draw.lines(s, CYAN, False, [(20, 36), (64, 70), (108, 36)], 8)
def i_check(s): pygame.draw.lines(s, GREEN, False, [(24, 68), (50, 94), (104, 36)], 16)
def i_error(s):
    pygame.draw.circle(s, RED, (64, 64), 50, 10)
    pygame.draw.line(s, RED, (44, 44), (84, 84), 10); pygame.draw.line(s, RED, (84, 44), (44, 84), 10)
def i_warning(s):
    pygame.draw.polygon(s, AMBER, [(64, 14), (118, 108), (10, 108)], 10)
    pygame.draw.line(s, AMBER, (64, 44), (64, 76), 10); dot(s, (64, 94), AMBER, 6)
def i_star(s): pygame.draw.polygon(s, AMBER, star_pts(64, 68, 54, 24))
def i_star_empty(s): pygame.draw.polygon(s, GRAY, star_pts(64, 68, 54, 24), 8)
def i_coin(s):
    pygame.draw.circle(s, AMBER, (64, 64), 48); pygame.draw.circle(s, ORANGE, (64, 64), 48, 8)
    pygame.draw.circle(s, ORANGE, (64, 64), 30, 6); pygame.draw.polygon(s, ORANGE, star_pts(64, 66, 18, 8))
def i_xp(s):
    pts = [(64 + 52 * math.cos(math.radians(60 * k + 30)), 64 + 52 * math.sin(math.radians(60 * k + 30))) for k in range(6)]
    pygame.draw.polygon(s, BLUE, pts); pygame.draw.polygon(s, CYAN, pts, 8)
    pygame.draw.line(s, WHITE, (44, 48), (84, 80), 9); pygame.draw.line(s, WHITE, (84, 48), (44, 80), 9)
def i_lock(s):
    rr(s, WHITE, (28, 58, 72, 52), 8); pygame.draw.arc(s, WHITE, (40, 18, 48, 70), 0, math.pi, 10)
    pygame.draw.line(s, WHITE, (40, 38), (40, 60), 10); pygame.draw.line(s, WHITE, (88, 38), (88, 60), 10); dot(s, (64, 84), DARK, 8)
def i_music(s):
    pygame.draw.circle(s, WHITE, (46, 94), 20); pygame.draw.line(s, WHITE, (64, 94), (64, 24), 10)
    pygame.draw.polygon(s, WHITE, [(64, 24), (104, 40), (104, 62), (64, 46)])
def i_sound(s):
    pygame.draw.polygon(s, WHITE, [(18, 50), (42, 50), (68, 26), (68, 102), (42, 78), (18, 78)])
    pygame.draw.arc(s, WHITE, (52, 34, 40, 60), -1.0, 1.0, 8); pygame.draw.arc(s, WHITE, (52, 18, 70, 92), -0.9, 0.9, 8)
def i_fullscreen(s):
    for (x, y, dx, dy) in ((20, 20, 1, 1), (108, 20, -1, 1), (20, 108, 1, -1), (108, 108, -1, -1)):
        pygame.draw.line(s, WHITE, (x, y), (x + 34 * dx, y), 10); pygame.draw.line(s, WHITE, (x, y), (x, y + 34 * dy), 10)
def i_save(s):
    rr(s, WHITE, (20, 20, 88, 88), 8, 8); rr(s, WHITE, (40, 20, 48, 30), 2); rr(s, CYAN, (38, 68, 52, 40), 4)
def i_home(s):
    pygame.draw.polygon(s, WHITE, [(64, 16), (116, 62), (12, 62)], 8); pygame.draw.lines(s, WHITE, False, [(28, 62), (28, 108), (100, 108), (100, 62)], 8)
def i_wifi(s): arc_wifi(s, 64, 96, CYAN)
def i_firewall(s):
    pts = [(64, 12), (104, 28), (104, 70), (64, 116), (24, 70), (24, 28)]
    pygame.draw.polygon(s, ORANGE, pts, 9)
def i_ping(s):
    pygame.draw.circle(s, CYAN, (64, 64), 14); pygame.draw.circle(s, CYAN, (64, 64), 34, 6); pygame.draw.circle(s, CYAN, (64, 64), 54, 6)
def i_trophy(s):
    rr(s, AMBER, (36, 20, 56, 56), 14); pygame.draw.rect(s, AMBER, (56, 70, 16, 24)); rr(s, AMBER, (38, 94, 52, 14), 4)
    pygame.draw.arc(s, AMBER, (10, 24, 36, 36), math.pi / 2, 3 * math.pi / 2, 7); pygame.draw.arc(s, AMBER, (82, 24, 36, 36), -math.pi / 2, math.pi / 2, 7)
def i_clock(s):
    pygame.draw.circle(s, WHITE, (64, 64), 48, 9); pygame.draw.lines(s, WHITE, False, [(64, 32), (64, 64), (86, 76)], 8)
def i_budget(s):
    pygame.draw.circle(s, GREEN, (64, 64), 48, 9); pygame.draw.line(s, GREEN, (64, 30), (64, 98), 8)
    pygame.draw.lines(s, GREEN, False, [(84, 46), (50, 46), (50, 62), (78, 66), (78, 82), (44, 82)], 7)

ICONS = {k[2:]: v for k, v in list(globals().items()) if k.startswith("i_") and callable(v)}


def make_icons():
    for name, fn in ICONS.items():
        s = surf(128); fn(s)
        save(s, IMG / "icons" / f"{name}.png", 48)


# ---------------- BACKGROUNDS ----------------
def gradient(w, h, top, bottom):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / (h - 1)
        pygame.draw.line(s, tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)), (0, y), (w, y))
    return s


def make_backgrounds():
    # menu: gradient + jaringan node acak
    w, h = 1920, 1080
    bg = surf(w, h); bg.blit(gradient(w, h, (6, 12, 26), (14, 30, 66)), (0, 0))
    ov = surf(w, h); rnd = random.Random(7)
    nodes = [(rnd.randint(0, w), rnd.randint(0, h)) for _ in range(55)]
    for i, (x, y) in enumerate(nodes):
        near = sorted(nodes, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[1:3]
        for nx, ny in near:
            pygame.draw.line(ov, (0, 229, 255, 38), (x, y), (nx, ny), 2)
    for x, y in nodes:
        pygame.draw.circle(ov, (0, 229, 255, 90), (x, y), 5); pygame.draw.circle(ov, (0, 229, 255, 30), (x, y), 14, 2)
    for x in range(0, w, 64): pygame.draw.line(ov, (30, 60, 110, 40), (x, 0), (x, h))
    for y in range(0, h, 64): pygame.draw.line(ov, (30, 60, 110, 40), (0, y), (w, y))
    bg.blit(ov, (0, 0))
    vig = surf(w, h)
    for i in range(14):
        pygame.draw.rect(vig, (0, 0, 0, 7), (i * 40, i * 24, w - i * 80, h - i * 48), 40, border_radius=60)
    bg.blit(vig, (0, 0))
    save(bg, IMG / "backgrounds" / "menu_bg.png")
    # tile workspace (bisa di-tile)
    t = pygame.Surface((256, 256)); t.fill((10, 18, 36))
    for i in range(0, 256, 32):
        c = (28, 48, 84) if i % 128 == 0 else (18, 32, 58)
        pygame.draw.line(t, c, (i, 0), (i, 255)); pygame.draw.line(t, c, (0, i), (255, i))
    save(t, IMG / "backgrounds" / "workspace_tile.png")
    # dashboard & laporan misi
    d = gradient(1920, 1080, (8, 16, 34), (10, 22, 46))
    for x in range(-1080, 1920, 90): pygame.draw.line(d, (14, 28, 54), (x, 0), (x + 1080, 1080), 2)
    save(d, IMG / "backgrounds" / "dashboard_bg.png")
    r = gradient(1920, 1080, (8, 22, 24), (8, 30, 40))
    for y in range(0, 1080, 54): pygame.draw.line(r, (14, 44, 52), (0, y), (1920, y))
    save(r, IMG / "backgrounds" / "mission_report_bg.png")


# ---------------- UI ----------------
def font_path(name):
    p = A / "fonts" / name
    return str(p) if p.exists() else None


def make_ui():
    for state, (fill, edge) in {"normal": (DARK, BLUE), "hover": (BODY2, CYAN), "pressed": (BLUE, CYAN), "disabled": ((20, 28, 44), GRAY)}.items():
        s = surf(320, 60); rr(s, fill, (0, 0, 320, 60), 10); rr(s, edge, (0, 0, 320, 60), 10, 3)
        save(s, IMG / "ui" / f"button_{state}.png")
    p = surf(512, 384); rr(p, (16, 26, 46, 235), (0, 0, 512, 384), 14); rr(p, BLUE, (0, 0, 512, 384), 14, 3)
    rr(p, (24, 40, 72), (3, 3, 506, 40), 12); pygame.draw.line(p, CYAN, (3, 43), (509, 43), 2)
    save(p, IMG / "ui" / "panel.png")
    for name, col in (("green", GREEN), ("red", RED), ("amber", AMBER), ("off", (50, 60, 78))):
        s = surf(64)
        if name != "off": pygame.draw.circle(s, (*col, 70), (32, 32), 30)
        pygame.draw.circle(s, col, (32, 32), 18); pygame.draw.circle(s, WHITE if name != "off" else GRAY, (26, 26), 5)
        save(s, IMG / "ui" / f"led_{name}.png", 16)
    bar = surf(400, 24); rr(bar, DARK, (0, 0, 400, 24), 10); rr(bar, BLUE, (0, 0, 400, 24), 10, 2)
    save(bar, IMG / "ui" / "progress_frame.png")
    fill = surf(400, 24); rr(fill, CYAN, (2, 2, 396, 20), 8); rr(fill, (120, 245, 255), (6, 4, 388, 6), 3)
    save(fill, IMG / "ui" / "progress_fill.png")
    # swatch kabel
    for name, col, dashed, width in (("straight", CYAN, False, 8), ("crossover", ORANGE, True, 8), ("fiber", AMBER, False, 4), ("console", (120, 190, 255), True, 6)):
        s = surf(128, 32)
        if dashed:
            for x in range(4, 124, 20): pygame.draw.line(s, col, (x, 16), (x + 12, 16), width)
        else:
            pygame.draw.line(s, col, (4, 16), (124, 16), width)
        pygame.draw.circle(s, col, (6, 16), 8); pygame.draw.circle(s, col, (122, 16), 8)
        save(s, IMG / "ui" / f"cable_{name}.png")
    # logo
    big = font_path("Orbitron.ttf"); f1 = pygame.font.Font(big, 96) if big else pygame.font.SysFont("arial", 96, bold=True)
    f2 = pygame.font.Font(big, 58) if big else pygame.font.SysFont("arial", 58, bold=True)
    l1 = f1.render("NETWORK ENGINEER", True, CYAN); l2 = f2.render("S I M U L A T O R", True, WHITE)
    w = max(l1.get_width(), l2.get_width()) + 40; logo = surf(w, 230)
    logo.blit(l1, ((w - l1.get_width()) // 2, 8)); logo.blit(l2, ((w - l2.get_width()) // 2, 118))
    pygame.draw.line(logo, BLUE, (20, 200), (w - 20, 200), 4)
    for x in range(40, w - 30, (w - 80) // 6): pygame.draw.circle(logo, CYAN, (x, 200), 8)
    save(logo, IMG / "ui" / "logo.png")
    # ikon aplikasi
    ic = surf(256); rr(ic, DARK, (8, 8, 240, 240), 40); rr(ic, CYAN, (8, 8, 240, 240), 40, 8)
    d_router(ic)
    save(ic, IMG / "ui" / "app_icon.png", 128)


# ---------------- SOUNDS ----------------
SR = 22050


def tone(freq, dur, vol=0.5, kind="sine", attack=0.004, freq_end=None, curve=2.0):
    n = int(SR * dur); out = []; ph = 0.0
    for i in range(n):
        t = i / n
        f = freq if freq_end is None else freq + (freq_end - freq) * t
        ph += 2 * math.pi * f / SR
        if kind == "sine": v = math.sin(ph)
        elif kind == "square": v = 1.0 if math.sin(ph) >= 0 else -1.0
        else: v = 2 * ((ph / (2 * math.pi)) % 1) - 1
        out.append(v * min(1.0, i / (SR * attack)) * (1 - t) ** curve * vol)
    return out


def silence(d): return [0.0] * int(SR * d)


def mix(base, add, offset=0.0, wrap=False):
    o = int(SR * offset)
    for i, v in enumerate(add):
        j = o + i
        if wrap: j %= len(base)
        elif j >= len(base): base.extend([0.0] * (j - len(base) + 1))
        base[j] += v
    return base


def write_wav(path, samples, peak=0.9):
    path.parent.mkdir(parents=True, exist_ok=True)
    m = max(1e-9, max(abs(x) for x in samples)); k = min(1.0, peak / m) if m > peak else 1.0
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x * k)) * 32767)) for x in samples))


def make_sounds():
    S = A / "sounds"
    write_wav(S / "click.wav", tone(1300, 0.05, 0.5, "square", curve=3))
    write_wav(S / "hover.wav", tone(900, 0.03, 0.18, "sine", curve=2))
    write_wav(S / "place.wav", mix(tone(180, 0.14, 0.7, "sine", freq_end=90), tone(700, 0.05, 0.25, "square", curve=4)))
    write_wav(S / "connect.wav", tone(600, 0.1, 0.4) + tone(900, 0.16, 0.4))
    write_wav(S / "disconnect.wav", tone(900, 0.1, 0.4) + tone(520, 0.16, 0.4))
    write_wav(S / "packet.wav", tone(1200, 0.07, 0.25, "sine", freq_end=2200, curve=1.2))
    write_wav(S / "success.wav", sum((tone(f, 0.14, 0.4) for f in (523.25, 659.25, 783.99)), []) + tone(1046.5, 0.32, 0.45))
    write_wav(S / "failure.wav", tone(300, 0.45, 0.45, "saw", freq_end=110, curve=1.0))
    write_wav(S / "error.wav", tone(160, 0.12, 0.45, "square", curve=0.5) + silence(0.05) + tone(160, 0.16, 0.45, "square", curve=1))
    write_wav(S / "notification.wav", tone(1000, 0.09, 0.35) + tone(1500, 0.14, 0.35))
    write_wav(S / "level_up.wav", sum((tone(f, 0.12, 0.4) for f in (392, 493.88, 587.33, 783.99, 987.77)), []) + tone(1174.66, 0.5, 0.45))
    write_wav(S / "typing.wav", tone(2200, 0.018, 0.25, "square", curve=2))
    # musik latar 16 detik (loop mulus)
    L = 16 * SR; bgm = [0.0] * L
    chords = [([220, 261.63, 329.63], 110), ([174.61, 220, 261.63], 87.31), ([261.63, 329.63, 392], 130.81), ([196, 246.94, 293.66], 98)]
    for c, (notes, root) in enumerate(chords):
        t0 = c * 4.0; n = 4 * SR
        pad = [0.0] * n
        for f in notes + [root]:
            amp = 0.15 if f == root else 0.08
            for i in range(n):
                pad[i] += (math.sin(2 * math.pi * f * i / SR) + 0.5 * math.sin(2 * math.pi * f * 1.004 * i / SR)) * amp * math.sin(math.pi * i / n) ** 0.7
        mix(bgm, pad, t0, wrap=True)
        for k in range(16):
            mix(bgm, tone(notes[(k * 2) % 3] * 2 if k % 4 else notes[0] * 4, 0.5, 0.07, "sine", attack=0.002, curve=2.5), t0 + k * 0.25, wrap=True)
    write_wav(S / "music" / "bgm_noc.wav", bgm, peak=0.6)


# ---------------- FONTS ----------------
FONT_URLS = {
    "JetBrainsMono.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    "Orbitron.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf",
}


def fetch_fonts():
    (A / "fonts").mkdir(parents=True, exist_ok=True)
    for name, url in FONT_URLS.items():
        dest = A / "fonts" / name
        if dest.exists(): continue
        try:
            data = urllib.request.urlopen(url, timeout=25).read()
            if len(data) > 10000: dest.write_bytes(data); print("font OK:", name)
        except Exception as e:
            print("font GAGAL:", name, "->", e)
    (A / "fonts" / "LICENSE.txt").write_text(
        "JetBrains Mono (c) JetBrains; Orbitron (c) Matt McInerney. Keduanya SIL Open Font License 1.1 (https://openfontlicense.org).\n", encoding="utf-8")


if __name__ == "__main__":
    fetch_fonts(); make_devices(); make_icons(); make_backgrounds(); make_ui(); make_sounds()
    print("Selesai. Asset ada di", A)
