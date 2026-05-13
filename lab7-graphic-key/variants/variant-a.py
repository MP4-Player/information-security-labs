# -*- coding: utf-8 -*-
"""
Лабораторная работа №7 — Графический ключ
Биометрическая аутентификация по графическому образцу (паттерну)
Автор: Булгаров Марк Александрович

Алгоритм:
  Регистрация: пользователь рисует паттерн на сетке 3×3 (минимум 4 точки).
    Паттерн = последовательность индексов точек [0..8].
    "Цифровой отпечаток" = SHA-256(имя_пользователя + JSON(паттерн) + соль).
    Данные шифруются (XOR + Base64) и сохраняются в users.dat.

  Аутентификация: пользователь рисует паттерн заново.
    Хэш сравнивается с сохранённым. Совпадение → доступ разрешён.
    При 5 неудачных попытках учётная запись временно блокируется.

  Умная логика паттерна:
    - Нельзя пропускать точки (как на Android: если ведёшь через точку — она добавляется)
    - Нельзя повторно использовать уже задействованные точки
    - Минимальная длина паттерна: 4 точки
    - Линии рисуются с градиентом красный→зелёный→синий
"""

import json, base64, hashlib, os, time, secrets, math
from flask import Flask, request, session, redirect, jsonify

app = Flask(__name__)
app.secret_key = 'lab7_graphic_key_v1_2025'

USERS_FILE   = 'gk_users.dat'
MIN_POINTS   = 4
MAX_ATTEMPTS = 5
XOR_KEY      = 0x7B

# ─── Шифрование ──────────────────────────────────────────────────────────────
def encrypt(data: str) -> str:
    b = data.encode('utf-8')
    return base64.b64encode(bytes([x ^ XOR_KEY for x in b])).decode()

def decrypt(data: str) -> str:
    b = base64.b64decode(data.encode())
    return bytes([x ^ XOR_KEY for x in b]).decode('utf-8')

# ─── Файл пользователей ───────────────────────────────────────────────────────
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE) as f:
            return json.loads(decrypt(f.read().strip()))
    except Exception:
        return {}

def save_users(u: dict):
    with open(USERS_FILE, 'w') as f:
        f.write(encrypt(json.dumps(u, ensure_ascii=False)))

# ─── Хэш паттерна ─────────────────────────────────────────────────────────────
def hash_pattern(username: str, pattern: list, salt: str) -> str:
    raw = username + json.dumps(pattern) + salt
    return hashlib.sha256(raw.encode()).hexdigest()

# ─── Умная логика: вставка промежуточных точек (как Android) ──────────────────
# Сетка 3×3, точки пронумерованы 0..8 слева-направо, сверху-вниз
# Координаты центров точек (в единицах сетки 0..2):
POINT_COORDS = [(c % 3, c // 3) for c in range(9)]

def between(a: int, b: int) -> int | None:
    """Возвращает индекс точки, лежащей ровно между a и b, или None."""
    ax, ay = POINT_COORDS[a]
    bx, by = POINT_COORDS[b]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    # Проверяем, попадает ли середина в центр какой-либо точки
    for i, (px, py) in enumerate(POINT_COORDS):
        if abs(px - mx) < 0.01 and abs(py - my) < 0.01:
            return i
    return None

def expand_pattern(raw: list) -> list:
    """
    Расширяет паттерн: если между двумя последовательными точками
    лежит ещё не задействованная точка — автоматически включает её.
    Дубликаты удаляются.
    """
    result = []
    visited = set()
    for pt in raw:
        if pt in visited:
            continue
        if result:
            mid = between(result[-1], pt)
            if mid is not None and mid not in visited:
                result.append(mid)
                visited.add(mid)
        result.append(pt)
        visited.add(pt)
    return result

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS + HTML
# ═══════════════════════════════════════════════════════════════════════════════
BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
/* ════ ПЕРЕМЕННЫЕ ═══════════════════════════════════════════════════════ */
:root{
  /* Светлая база */
  --bg:      #fdf6fb;
  --card:    #ffffff;
  --border:  #e8d5f0;
  --text:    #2d1f3a;
  --muted:   #9b7fb6;

  /* Женственная палитра */
  --sky:     #7ec8e3;
  --rose:    #f4a7b9;
  --crimson: #e63c6e;
  --indigo:  #6c63ff;
  --lilac:   #c9b3f5;
  --blush:   #fce4ec;
}

/* ════ СБРОС ════════════════════════════════════════════════════════════ */
*{margin:0;padding:0;box-sizing:border-box}

/* ════ БАЗОВАЯ СТРАНИЦА (светлая) ══════════════════════════════════════ */
body{
  font-family:'Inter',sans-serif;
  background:var(--bg);
  color:var(--text);
  min-height:100vh;
}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 70% 50% at 0% 0%,   rgba(126,200,227,.18) 0%,transparent 55%),
    radial-gradient(ellipse 60% 45% at 100% 0%,  rgba(108,99,255,.12) 0%,transparent 55%),
    radial-gradient(ellipse 50% 40% at 50% 100%, rgba(244,167,185,.20) 0%,transparent 55%);
}

/* ════ НАВБАР (светлый) ════════════════════════════════════════════════ */
nav{
  position:sticky;top:0;z-index:99;
  background:rgba(253,246,251,.92);
  border-bottom:1px solid var(--border);
  backdrop-filter:blur(16px);
  padding:12px 28px;
  display:flex;align-items:center;justify-content:space-between;
}
.brand{
  font-family:'Playfair Display',serif;
  font-size:15px;font-weight:700;letter-spacing:.5px;
  background:linear-gradient(90deg,var(--sky),var(--crimson),var(--indigo));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.nav-links{display:flex;gap:4px}
.nl{
  padding:5px 14px;font-size:11px;letter-spacing:.5px;
  color:var(--muted);text-decoration:none;
  border:1px solid transparent;border-radius:20px;transition:.2s;
  font-family:'Inter',sans-serif;font-weight:500;
}
.nl:hover{color:var(--crimson);border-color:var(--rose);background:var(--blush)}
.nl.red:hover{color:var(--crimson);border-color:var(--crimson)}
.chip{
  display:flex;align-items:center;gap:7px;
  background:linear-gradient(135deg,var(--blush),#f3e5f5);
  border:1px solid var(--rose);border-radius:20px;padding:5px 14px;font-size:12px;
}
.dot{
  width:7px;height:7px;border-radius:50%;
  background:linear-gradient(135deg,var(--crimson),var(--indigo));
  animation:blink 2s infinite;flex-shrink:0;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* Плавающие лепестки на фоне */
@keyframes float{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-14px) rotate(6deg)}}
.petal{position:fixed;pointer-events:none;z-index:0;opacity:.13;font-size:22px;animation:float 5s ease-in-out infinite;}

/* ════ КОНТЕЙНЕР ═══════════════════════════════════════════════════════ */
.wrap{max-width:860px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}

/* ════ КАРТОЧКИ (светлые) ══════════════════════════════════════════════ */
.card{
  background:#fff;
  border:1px solid var(--border);
  border-radius:20px;
  padding:24px;
  margin-bottom:16px;
  box-shadow:0 2px 20px rgba(200,150,220,.08);
}

/* ════ ТИПОГРАФИКА ══════════════════════════════════════════════════════ */
.grad-fem{
  background:linear-gradient(90deg,var(--sky),var(--crimson),var(--indigo));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.ph h1{font-family:'Playfair Display',serif;font-size:22px;font-weight:700;margin-bottom:6px}
.ph h1 span{color:var(--crimson)}
.ph p{font-size:12px;color:var(--muted);line-height:1.75}

/* ════ INFO BOXES (светлые) ════════════════════════════════════════════ */
.info-blue{
  background:linear-gradient(135deg,rgba(126,200,227,.1),rgba(108,99,255,.08));
  border:1px solid rgba(108,99,255,.25);border-radius:14px;
  padding:14px 18px;font-size:12px;line-height:1.85;color:#4a3a7a;margin-bottom:16px;
}
.info-blue strong{color:var(--indigo)}
.info-warn{
  background:linear-gradient(135deg,rgba(244,167,185,.15),rgba(230,60,110,.08));
  border:1px solid rgba(230,60,110,.25);border-radius:14px;
  padding:12px 16px;font-size:12px;line-height:1.85;color:#8b2a4a;margin-bottom:16px;
}
.info-ok{
  background:linear-gradient(135deg,rgba(126,200,227,.12),rgba(201,179,245,.12));
  border:1px solid var(--lilac);border-radius:14px;
  padding:12px 16px;font-size:12px;line-height:1.85;color:#4a3a7a;margin-bottom:16px;
}

/* ════ КНОПКИ (светлые) ════════════════════════════════════════════════ */
.btn{
  padding:10px 24px;border:none;border-radius:30px;
  font-family:'Inter',sans-serif;font-size:12px;font-weight:600;
  letter-spacing:.5px;cursor:pointer;transition:.25s;
}
.btn-g{
  background:linear-gradient(135deg,var(--crimson),var(--indigo));
  color:#fff;box-shadow:0 4px 15px rgba(108,99,255,.25);
}
.btn-g:hover{box-shadow:0 6px 22px rgba(108,99,255,.4);transform:translateY(-2px)}
.btn-g:disabled{background:#d8cce8;color:#a090b8;cursor:not-allowed;transform:none;box-shadow:none}
.btn-r{background:linear-gradient(135deg,#ff8fab,var(--crimson));color:#fff}
.btn-r:hover{box-shadow:0 4px 14px rgba(230,60,110,.3);transform:translateY(-1px)}
.btn-gray{background:#f3edf8;color:var(--muted);border:1px solid var(--border);margin-right:8px}
.btn-gray:hover{background:var(--blush);color:var(--crimson)}

/* ════ ФОРМЫ (светлые) ════════════════════════════════════════════════ */
select,input[type=text]{
  padding:10px 16px;
  background:#fdf6fb;
  border:1.5px solid var(--border);
  border-radius:12px;color:var(--text);
  font-family:'Inter',sans-serif;font-size:13px;
  transition:.2s;width:100%;
}
select:focus,input:focus{outline:none;border-color:var(--indigo);box-shadow:0 0 0 3px rgba(108,99,255,.12)}
select option{background:#fff}
.fgroup{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.flabel{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);font-weight:500}

/* ════ РЕЗУЛЬТАТ ═══════════════════════════════════════════════════════ */
.result{margin-top:14px;padding:16px;border-radius:14px;font-size:13px;line-height:1.8}
.result.ok{background:linear-gradient(135deg,rgba(126,200,227,.15),rgba(201,179,245,.15));
  border:1px solid var(--lilac);color:#4a3a7a}
.result.err{background:rgba(230,60,110,.07);border:1px solid rgba(230,60,110,.3);color:#8b2a4a}

/* ════ ЛОГИН ═══════════════════════════════════════════════════════════ */
.login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
.lw{width:480px;position:relative;z-index:1}
.badge{
  display:inline-flex;align-items:center;gap:8px;
  background:linear-gradient(135deg,rgba(244,167,185,.25),rgba(201,179,245,.25));
  border:1px solid var(--rose);border-radius:30px;
  padding:5px 16px;font-size:10px;color:var(--crimson);
  letter-spacing:2px;text-transform:uppercase;margin-bottom:18px;
  font-family:'Inter',sans-serif;font-weight:600;
}
.badge::before{content:'♡';font-size:12px;animation:blink 2s infinite}
.lh1{font-family:'Playfair Display',serif;font-size:28px;font-weight:900;line-height:1.2;margin-bottom:8px}
.lsub{font-size:12px;color:var(--muted);margin-bottom:24px;line-height:1.7}
.lsub span{color:var(--indigo);font-weight:600}
.err-box{
  display:flex;align-items:center;gap:9px;
  background:rgba(230,60,110,.08);border:1px solid rgba(230,60,110,.3);
  border-radius:12px;padding:11px 15px;font-size:13px;color:var(--crimson);margin-bottom:14px;
}
.sec{
  font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:10px;margin-bottom:12px;font-weight:500;
}
.sec::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--rose),transparent)}

/* ════ ХОЛСТ СЕТКИ 3×3 ════════════════════════════════════════════════ */
.canvas-wrap{display:flex;flex-direction:column;align-items:center;gap:12px;margin:16px 0}
#gk-canvas{
  border-radius:24px;
  border:2px solid var(--border);
  background:linear-gradient(145deg,#fef9ff,#f8f0fc);
  cursor:crosshair;touch-action:none;display:block;
  box-shadow:inset 0 2px 20px rgba(200,150,220,.1),0 8px 30px rgba(200,150,220,.15);
}
.status-row{display:flex;align-items:center;justify-content:space-between;width:360px}
.pts-count{font-size:12px;color:var(--muted)}
.pts-count span{color:var(--crimson);font-weight:700}

/* ════ ТАБЛИЦА ══════════════════════════════════════════════════════════ */
.utbl{width:100%;border-collapse:collapse;font-size:12px}
.utbl th,.utbl td{padding:10px 14px;border-bottom:1px solid var(--border);text-align:left}
.utbl th{color:var(--muted);font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:600}
.utbl tr:last-child td{border-bottom:none}
.utbl tr:hover td{background:var(--blush)}

/* ════ ТОЧКИ ПОПЫТОК ════════════════════════════════════════════════════ */
.att-row{display:flex;gap:6px;margin:8px 0}
.att-d{width:10px;height:10px;border-radius:50%;background:var(--border)}
.att-d.used{background:var(--crimson)}
.att-d.ok{background:var(--indigo)}

/* ════ ВКЛАДКИ РЕЖИМОВ ══════════════════════════════════════════════════ */
.tab-switcher{display:flex;gap:0;margin-bottom:24px;border-radius:16px;overflow:hidden;
  border:1.5px solid var(--border);background:#f8f0fc}
.tab-sw-btn{flex:1;padding:12px;font-size:12px;font-weight:600;cursor:pointer;
  border:none;background:transparent;transition:.2s;font-family:'Inter',sans-serif}
.tab-sw-btn.fem{color:var(--crimson)}
.tab-sw-btn.term{color:#3f3fa8;font-family:'Courier New',Courier,monospace}
.tab-sw-btn.active-fem{background:linear-gradient(135deg,#fce4ec,#f3e5f5);color:var(--crimson)}
.tab-sw-btn.active-term{background:#eef4fb;color:#0d47a1;font-family:'Courier New',Courier,monospace;border-left:3px solid #2196f3;font-weight:700}

/* ════ ТЕРМИНАЛЬНЫЕ СЕКЦИИ (светлые, голубой-индиго, без градиентов) ═══ */
:root{
  --term-bg:     #f5f9ff;
  --term-card:   #ffffff;
  --term-border: #b8d0ea;
  --term-text:   #0d1f3c;
  --term-muted:  #5a78a0;
  --term-blue:   #1565c0;
  --term-indigo: #283593;
  --term-sky:    #0277bd;
  --term-ok:     #0d47a1;
  --term-err:    #b71c1c;
  --TF: 'Courier New',Courier,monospace;
}
.term-wrap{
  max-width:860px;margin:0 auto;padding:28px 22px;position:relative;z-index:1;
}
.term-card{
  background:#fff;
  border:1px solid var(--term-border);
  border-left:3px solid #2196f3;
  border-radius:4px;padding:20px;margin-bottom:12px;
  font-family:'Courier New',Courier,monospace;
}
.term-header{
  font-family:'Courier New',Courier,monospace;font-size:11px;
  color:var(--term-muted);letter-spacing:1px;text-transform:uppercase;
  display:flex;align-items:center;gap:6px;margin-bottom:12px;
}
.term-header::before{content:'$ ';color:var(--term-blue);font-weight:700}
.term-prompt{color:var(--term-blue);font-size:12px;font-family:'Courier New',Courier,monospace;font-weight:700}
.term-title{
  font-family:'Courier New',Courier,monospace;
  font-size:17px;font-weight:700;
  color:var(--term-indigo);margin-bottom:4px;
  letter-spacing:-.3px;
}
.term-title span{color:var(--term-sky)}
.term-sub{font-size:11px;color:var(--term-muted);font-family:'Courier New',Courier,monospace;line-height:1.7}
.term-info{
  background:#eef4fb;
  border:1px solid #b8d0ea;
  border-left:3px solid #1565c0;
  border-radius:3px;padding:11px 15px;font-size:11px;line-height:1.85;
  color:var(--term-text);margin-bottom:14px;font-family:'Courier New',Courier,monospace;
}
.term-info strong{color:var(--term-indigo);font-weight:700}
.term-warn{
  background:#e8f5ff;
  border:1px solid #b8d0ea;
  border-left:3px solid #0277bd;
  border-radius:3px;padding:11px 15px;font-size:11px;line-height:1.85;
  color:#01579b;margin-bottom:14px;font-family:'Courier New',Courier,monospace;
}
.term-warn strong{color:var(--term-blue);font-weight:700}
.term-btn{
  padding:7px 18px;
  border:1.5px solid #1565c0;
  border-radius:3px;
  background:#fff;color:#1565c0;
  font-family:'Courier New',Courier,monospace;
  font-size:11px;font-weight:700;
  letter-spacing:.5px;text-transform:uppercase;cursor:pointer;transition:.15s;
}
.term-btn:hover{background:#eef4fb}
.term-btn:disabled{border-color:#b8d0ea;color:#9ab5d0;cursor:not-allowed;background:#fff}
.term-btn-red{border-color:#c62828;color:#c62828}
.term-btn-red:hover{background:#fff5f5}
.term-btn-amber{border-color:#0277bd;color:#0277bd}
.term-btn-amber:hover{background:#e8f5ff}
.term-input{
  padding:8px 12px;
  background:#f5f9ff;
  border:1.5px solid var(--term-border);
  border-radius:3px;color:var(--term-text);
  font-family:'Courier New',Courier,monospace;
  font-size:13px;transition:.15s;width:100%;
}
.term-input:focus{outline:none;border-color:#1565c0;box-shadow:0 0 0 2px rgba(21,101,192,.12)}
.term-label{
  font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--term-muted);font-family:'Courier New',Courier,monospace;
  margin-bottom:5px;display:block;font-weight:700;
}
.term-result{
  margin-top:12px;padding:12px 14px;border-radius:3px;
  font-size:12px;line-height:1.8;font-family:'Courier New',Courier,monospace;
}
.term-result.ok{
  background:#e8f5e9;border:1px solid #81c784;color:#1b5e20;
}
.term-result.err{
  background:#ffebee;border:1px solid #ef9a9a;color:#b71c1c;
}
.term-sec{
  font-size:9px;letter-spacing:2px;text-transform:uppercase;
  color:var(--term-muted);
  display:flex;align-items:center;gap:8px;margin-bottom:12px;
  font-family:'Courier New',Courier,monospace;font-weight:700;
}
.term-sec::after{content:'';flex:1;height:1px;background:var(--term-border)}

/* Терминальный navbar */
nav.term-nav{
  background:#f5f9ff !important;
  border-bottom:1.5px solid #b8d0ea !important;
}
nav.term-nav .brand{
  font-family:'Courier New',Courier,monospace !important;
  font-size:13px !important;
  background:none !important;
  -webkit-text-fill-color:#1565c0 !important;
  color:#1565c0 !important;
  font-weight:700 !important;
  letter-spacing:0 !important;
}
nav.term-nav .nl{
  color:#5a78a0 !important;border-radius:3px !important;
  font-family:'Courier New',Courier,monospace !important;
  font-size:11px !important;
}
nav.term-nav .nl:hover{
  color:#1565c0 !important;
  border-color:#b8d0ea !important;
  background:#eef4fb !important;
}
nav.term-nav .chip{
  background:#eef4fb !important;
  border-color:#b8d0ea !important;
  color:#1565c0 !important;
  font-family:'Courier New',Courier,monospace !important;
}
nav.term-nav .dot{
  background:#1565c0 !important;
}

/* Холст рисования */
#draw-canvas{
  border-radius:3px;
  border:1.5px solid #b8d0ea;
  background:#f5f9ff;
  cursor:crosshair;touch-action:none;display:block;
}

/* Терминальная страница */
body.term-body{
  background:#f5f9ff !important;
}
body.term-body::before{
  background:
    radial-gradient(ellipse 60% 40% at 0% 0%,   rgba(21,101,192,.07) 0%,transparent 55%),
    radial-gradient(ellipse 50% 40% at 100% 100%, rgba(40,53,147,.05) 0%,transparent 55%) !important;
}
</style>"""

def nav_html(u="", terminal=False):
    chip = f'<div class="chip"><div class="dot"></div>{u}</div>' if u else ''
    if terminal:
        ls = [("/dashboard","~/home",""),("/draw_register","reg --draw",""),
              ("/users","ls -users",""),("/logout","exit","red")]
        lh = "".join(f'<a href="{h}" class="nl {c}">{l}</a>' for h,l,c in ls)
        return f'<nav class="term-nav"><div class="brand">[graphic-key]$ _</div><div class="nav-links">{lh}</div>{chip}</nav>'
    else:
        ls = [("/dashboard","Главная",""),("/register","Регистрация",""),
              ("/users","Пользователи",""),("/logout","Выход","red")]
        lh = "".join(f'<a href="{h}" class="nl {c}">{l}</a>' for h,l,c in ls)
        return f'<nav><div class="brand">✦ Графический ключ</div><div class="nav-links">{lh}</div>{chip}</nav>'

PETALS_HTML = """
<div class="petal" style="left:5%;top:15%;animation-delay:0s">🌸</div>
<div class="petal" style="left:88%;top:8%;animation-delay:1.2s">🌺</div>
<div class="petal" style="left:3%;top:70%;animation-delay:2.5s">✿</div>
<div class="petal" style="left:92%;top:60%;animation-delay:.8s">🌷</div>
<div class="petal" style="left:50%;top:5%;animation-delay:1.8s">🌸</div>
"""

def page(title, content, login=False, user="", terminal=False):
    bc  = "login-body" if login else ""
    bc += " term-body" if terminal else ""
    nav = "" if login else nav_html(user, terminal)
    petals = PETALS_HTML if not terminal and not login else ""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><title>{title}</title>{BASE_STYLE}</head>
<body class="{bc.strip()}">{petals}{nav}{content}</body></html>"""

# ─── Canvas JS — сетка 3×3 с сердечками ─────────────────────────────────────
def canvas_js(mode: str, username: str = "", min_pts: int = MIN_POINTS) -> str:
    return f"""
<script>
(function(){{
const USERNAME = {json.dumps(username)};
const MIN_PTS  = {min_pts};
const canvas   = document.getElementById('gk-canvas');
const ctx      = canvas.getContext('2d');
const SIZE     = 360;
canvas.width   = SIZE;
canvas.height  = SIZE;
// курсор только через CSS — не трогаем через JS

// 9 точек сетки
const PAD=60, STEP=(SIZE-PAD*2)/2;
const pts=[];
for(let r=0;r<3;r++) for(let c=0;c<3;c++)
  pts.push({{x:PAD+c*STEP, y:PAD+r*STEP, idx:r*3+c}});

// Градиент по прогрессу t∈[0,1] → всегда возвращает rgb(...)
const STOPS=[[0,'#7ec8e3'],[0.25,'#f9a8d4'],[0.5,'#e63c6e'],[0.75,'#f4a7b9'],[1,'#6c63ff']];
function gc(t){{
  t=Math.max(0,Math.min(1,t));
  let i=0;
  while(i<STOPS.length-2 && STOPS[i+1][0]<=t) i++;
  const s=(t-STOPS[i][0])/Math.max(STOPS[i+1][0]-STOPS[i][0],1e-6);
  const h=c=>parseInt(c.slice(1),16);
  const lr=(a,b)=>Math.round(a+(b-a)*s);
  const A=h(STOPS[i][1]),B=h(STOPS[i+1][1]);
  return [lr(A>>16,B>>16), lr((A>>8)&255,(B>>8)&255), lr(A&255,B&255)];
}}
// rgb-массив → строка
function rgb(v){{ return `rgb(${{v[0]}},${{v[1]}},${{v[2]}})`; }}
function rgba(v,a){{ return `rgba(${{v[0]}},${{v[1]}},${{v[2]}},${{a}})`; }}

// Сердечко-мыльный пузырь. col — массив [r,g,b]
function heart(x,y,sz,col,alpha,rot){{
  if(alpha<=0||sz<=2) return;
  ctx.save();
  ctx.globalAlpha=Math.min(1,alpha);
  ctx.translate(x,y);
  if(rot) ctx.rotate(rot);
  ctx.scale(sz/16,sz/16);
  ctx.beginPath();
  ctx.moveTo(0,-2);
  ctx.bezierCurveTo(5,-9,13,-8,13,-2);
  ctx.bezierCurveTo(13,5,5,11,0,17);
  ctx.bezierCurveTo(-5,11,-13,5,-13,-2);
  ctx.bezierCurveTo(-13,-8,-5,-9,0,-2);
  ctx.closePath();
  // Радиальный градиент — мыльный пузырь
  const g=ctx.createRadialGradient(-3,-5,1,0,0,13);
  g.addColorStop(0,'rgba(255,255,255,0.8)');
  g.addColorStop(0.4,rgba(col,0.85));
  g.addColorStop(1,rgba(col,0.25));
  ctx.fillStyle=g;
  ctx.fill();
  ctx.strokeStyle='rgba(255,255,255,0.55)';
  ctx.lineWidth=0.8;
  ctx.stroke();
  ctx.restore();
}}

// Частицы-пузырьки при нажатии
const bubbles=[];
function spawn(x,y,col){{
  for(let i=0;i<3;i++)
    bubbles.push({{x,y,
      vx:(Math.random()-.5)*2.5,
      vy:-2.5-Math.random()*2,
      sz:7+Math.random()*9,
      life:1,col,
      rot:Math.random()*.6-.3
    }});
}}
function tickBubbles(){{
  for(let i=bubbles.length-1;i>=0;i--){{
    const b=bubbles[i];
    b.x+=b.vx;b.y+=b.vy;b.vy+=0.07;b.life-=0.02;b.rot+=0.03;
    if(b.life<=0)bubbles.splice(i,1);
  }}
}}

// Состояние
let pattern=[],raw=[],down=false,mx=SIZE/2,my=SIZE/2,hov=-1;

// Android-логика промежуточных точек
function midPt(a,b){{
  const mmx=(pts[a].x+pts[b].x)/2, mmy=(pts[a].y+pts[b].y)/2;
  for(let i=0;i<9;i++)
    if(Math.abs(pts[i].x-mmx)<1&&Math.abs(pts[i].y-mmy)<1) return i;
  return -1;
}}
function expand(r){{
  const res=[],vis=new Set();
  for(const p of r){{
    if(vis.has(p)) continue;
    if(res.length){{
      const m=midPt(res[res.length-1],p);
      if(m!==-1&&!vis.has(m)){{res.push(m);vis.add(m);}}
    }}
    res.push(p);vis.add(p);
  }}
  return res;
}}
function nearest(x,y,radius,skipUsed){{
  let best=-1,bd=1e9;
  for(const p of pts){{
    if(skipUsed&&pattern.includes(p.idx)) continue;
    const d=Math.hypot(p.x-x,p.y-y);
    if(d<radius&&d<bd){{bd=d;best=p.idx;}}
  }}
  return best;
}}

// Главный цикл
function draw(){{
  ctx.clearRect(0,0,SIZE,SIZE);

  // Нежная фоновая сетка
  ctx.save();
  ctx.strokeStyle='rgba(230,60,110,0.05)';
  ctx.lineWidth=0.8;
  for(let i=0;i<SIZE;i+=30){{
    ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,SIZE);ctx.stroke();
    ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(SIZE,i);ctx.stroke();
  }}
  ctx.restore();

  const n=pattern.length;
  const tot=Math.max(n-1,1);

  // Линии паттерна
  for(let i=1;i<n;i++){{
    const a=pts[pattern[i-1]],b=pts[pattern[i]];
    const c0=gc((i-1)/tot),c1=gc(i/tot);
    const g=ctx.createLinearGradient(a.x,a.y,b.x,b.y);
    g.addColorStop(0,rgb(c0));
    g.addColorStop(1,rgb(c1));
    ctx.save();
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    ctx.strokeStyle=g;ctx.lineWidth=3;ctx.lineCap='round';
    ctx.shadowColor=rgb(gc((i-.5)/tot));ctx.shadowBlur=7;
    ctx.stroke();
    ctx.restore();
  }}

  // Пунктир к позиции мыши (только когда тянем)
  if(down&&n>0){{
    const L=pts[pattern[n-1]];
    ctx.save();
    ctx.beginPath();ctx.moveTo(L.x,L.y);ctx.lineTo(mx,my);
    ctx.strokeStyle=rgb(gc((n-1)/tot));
    ctx.lineWidth=1.5;ctx.setLineDash([5,5]);ctx.globalAlpha=0.35;
    ctx.stroke();
    ctx.restore();
  }}

  // Сердечки — 9 точек
  for(const p of pts){{
    const act=pattern.includes(p.idx);
    const ord=pattern.indexOf(p.idx);
    const isHov=!down&&hov===p.idx;
    const t=act?Math.max(0,(ord)/(Math.max(n-1,1))):0;
    const col=act?gc(t):isHov?[230,60,110]:[201,179,245];
    const sz=act?21:isHov?18:13;
    const al=act?0.92:isHov?0.78:0.48;
    heart(p.x,p.y,sz,col,al,0);

    if(isHov){{
      ctx.save();ctx.globalAlpha=0.22;
      ctx.beginPath();ctx.arc(p.x,p.y,26,0,Math.PI*2);
      ctx.strokeStyle='#e63c6e';ctx.lineWidth=1.5;ctx.setLineDash([4,4]);
      ctx.stroke();ctx.restore();
    }}
    if(act&&ord>=0){{
      ctx.save();ctx.globalAlpha=0.92;
      ctx.font='bold 11px Arial,sans-serif';
      ctx.fillStyle='#fff';
      ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(ord+1,p.x,p.y+3);
      ctx.restore();
    }}
  }}

  // Пузырьки
  tickBubbles();
  for(const b of bubbles) heart(b.x,b.y,b.sz*b.life,b.col,b.life*0.7,b.rot);

  const el=document.getElementById('pt-count');
  if(el) el.textContent=n;
  requestAnimationFrame(draw);
}}

// Координаты мыши/тача относительно canvas
function pos(e){{
  const r=canvas.getBoundingClientRect();
  const src=e.touches?e.touches[0]:e;
  return {{
    x:(src.clientX-r.left)*(SIZE/r.width),
    y:(src.clientY-r.top)*(SIZE/r.height)
  }};
}}

// ── СОБЫТИЯ ──────────────────────────────────────────────────────────────
canvas.addEventListener('mousedown',e=>{{
  e.preventDefault();
  const p=pos(e);mx=p.x;my=p.y;
  pattern=[];raw=[];down=true;hov=-1;
  const hit=nearest(p.x,p.y,38,false);
  if(hit!==-1){{
    raw.push(hit);pattern=expand(raw);
    spawn(pts[hit].x,pts[hit].y,gc(0));
  }}
}});

canvas.addEventListener('mousemove',e=>{{
  const p=pos(e);mx=p.x;my=p.y;
  if(!down){{
    hov=nearest(p.x,p.y,38,false);
    return;
  }}
  const hit=nearest(p.x,p.y,32,true);
  if(hit!==-1&&!raw.includes(hit)){{
    raw.push(hit);pattern=expand(raw);
    spawn(pts[hit].x,pts[hit].y,gc(pattern.length/9));
  }}
}});

// mouseup слушаем на document — надёжно ловит даже если мышь вышла за канвас
document.addEventListener('mouseup',e=>{{
  if(!down) return;
  down=false;
  if(pattern.length>=MIN_PTS){{
    handleComplete();
  }} else {{
    showMsg('Соедините минимум '+MIN_PTS+' сердечки 💕',false);
    setTimeout(()=>{{pattern=[];raw=[];}},1400);
  }}
}});

canvas.addEventListener('mouseleave',e=>{{
  hov=-1;
  // down остаётся true — пользователь может вернуть мышь
}});

// Touch
canvas.addEventListener('touchstart',e=>{{
  e.preventDefault();
  const p=pos(e);mx=p.x;my=p.y;
  pattern=[];raw=[];down=true;
  const hit=nearest(p.x,p.y,40,false);
  if(hit!==-1){{raw.push(hit);pattern=expand(raw);spawn(pts[hit].x,pts[hit].y,gc(0));}}
}},{{passive:false}});

canvas.addEventListener('touchmove',e=>{{
  e.preventDefault();
  const p=pos(e);mx=p.x;my=p.y;
  const hit=nearest(p.x,p.y,34,true);
  if(hit!==-1&&!raw.includes(hit)){{
    raw.push(hit);pattern=expand(raw);
    spawn(pts[hit].x,pts[hit].y,gc(pattern.length/9));
  }}
}},{{passive:false}});

canvas.addEventListener('touchend',e=>{{
  down=false;
  if(pattern.length>=MIN_PTS){{
    handleComplete();
  }} else {{
    showMsg('Соедините минимум '+MIN_PTS+' сердечки 💕',false);
    setTimeout(()=>{{pattern=[];raw=[];}},1400);
  }}
}});

function showMsg(text,ok){{
  const el=document.getElementById('gk-result');if(!el)return;
  el.className='result '+(ok?'ok':'err');
  el.textContent=(ok?'✓ ':'✗ ')+text;
  el.style.display='block';
}}
function resetCanvas(){{
  pattern=[];raw=[];down=false;hov=-1;
  const el=document.getElementById('gk-result');
  if(el)el.style.display='none';
}}
window._resetCanvas=resetCanvas;

{_handle_complete_js(mode)}

draw();
}})();
</script>"""


def _handle_complete_js(mode: str) -> str:
    if mode == 'register':
        return """
function handleComplete(){{
  fetch('/api/reg_attempt',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username:USERNAME, pattern:pattern}})
  }}).then(r=>r.json()).then(d=>{{
    showMsg(d.message, d.success||d.pending);
    updateProgress(d.attempt, d.total_needed);
    if(d.success){{ setTimeout(()=>window.location.href='/', 2000); return; }}
    setTimeout(()=>{{ pattern=[]; rawPts=[]; draw(); }}, d.success?0:1400);
  }});
}}
function updateProgress(done, need){{
  const bar=document.getElementById('reg-bar');
  if(!bar) return;
  bar.innerHTML='';
  for(let i=0;i<need;i++){{
    const d=document.createElement('div');
    d.className='att-d'+(i<done?' ok':'');
    bar.appendChild(d);
  }}
}}
""".replace("{{", "{").replace("}}", "}")
    else:
        return """
function handleComplete(){{
  fetch('/api/auth_check',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username:USERNAME, pattern:pattern}})
  }}).then(r=>r.json()).then(d=>{{
    showMsg(d.message, d.success);
    updateAttempts(d.attempts_left);
    if(d.success) setTimeout(()=>window.location.href='/dashboard',1800);
    else setTimeout(()=>{{ pattern=[]; rawPts=[]; draw(); }}, 1400);
  }});
}}
function updateAttempts(left){{
  const el=document.getElementById('att-left');
  if(el) el.textContent = left;
  const bar=document.getElementById('att-bar');
  if(!bar) return;
  bar.innerHTML='';
  const max={max_att};
  for(let i=0;i<max;i++){{
    const d=document.createElement('div');
    d.className='att-d'+(i<(max-left)?' used':'');
    bar.appendChild(d);
  }}
}}
""".replace("{{", "{").replace("}}", "}").replace("{max_att}", str(MAX_ATTEMPTS))


# ═══════════════════════════════════════════════════════════════════════════════
#  МАРШРУТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    users = load_users()
    err   = f'<div class="err-box">⚠ {request.args.get("err")}</div>' if request.args.get('err') else ''
    if not users:
        opts = '<option value="">— нет зарегистрированных пользователей —</option>'
    else:
        opts = '<option value="">— выберите пользователя —</option>'
        for name in sorted(users):
            locked = users[name].get('locked_until', 0) > time.time()
            opts += f'<option value="{name}">{"🔒 " if locked else "○ "}{name}</option>'

    content = f"""
<div class="lw">
  <div class="badge">Графический ключ</div>
  <div class="lh1 grad-rgb">Биометрическая<br>аутентификация</div>
  <p class="lsub">Лабораторная работа №7 · <span>Защита информации</span><br>
  Аутентификация по графическому паттерну на сетке 3×3</p>
  {err}
  <div class="card">
    <div class="flabel" style="margin-bottom:10px">// Выберите пользователя</div>
    <form method="POST" action="/start_auth">
      <select name="username" required style="margin-bottom:12px">{opts}</select>
      <button type="submit" class="btn btn-g" style="width:100%">→ Войти</button>
    </form>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
    <a href="/register" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:14px">
        <div style="color:var(--b);font-size:11px;letter-spacing:1px">РЕГИСТРАЦИЯ</div>
        <div style="font-size:10px;color:var(--muted);margin-top:4px">Новый пользователь</div>
      </div>
    </a>
    <a href="/users" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:14px">
        <div style="color:var(--warn);font-size:11px;letter-spacing:1px">ПОЛЬЗОВАТЕЛИ</div>
        <div style="font-size:10px;color:var(--muted);margin-top:4px">Записей: {len(users)}</div>
      </div>
    </a>
  </div>
  <div class="info-blue" style="margin-top:12px">
    💡 <strong>Алгоритм:</strong> паттерн сохраняется как SHA-256 хэш последовательности точек.
    Умная логика автоматически вставляет промежуточные точки (как на Android).
    Градиентная линия: красный→зелёный→синий.
  </div>
</div>"""
    return page("Вход — Графический ключ", content, login=True)


@app.route('/start_auth', methods=['POST'])
def start_auth():
    username = request.form.get('username', '').strip()
    users    = load_users()
    if username not in users:
        return redirect('/?err=Пользователь+не+найден')
    if users[username].get('locked_until', 0) > time.time():
        return redirect('/?err=Учётная+запись+заблокирована.+Попробуйте+позже.')
    session['auth_user'] = username
    return redirect('/auth')


@app.route('/auth')
def auth():
    if 'auth_user' not in session:
        return redirect('/')
    username = session['auth_user']
    users    = load_users()
    left     = MAX_ATTEMPTS - users[username].get('fail_count', 0)

    att_dots = "".join(
        f'<div class="att-d{"" if i < left else " used"}"></div>'
        for i in range(MAX_ATTEMPTS)
    )

    content = f"""
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Авторизация: <span>{username}</span></h1>
    <p>Нарисуйте ваш графический паттерн — минимум {MIN_POINTS} точки.</p>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div style="display:flex;gap:8px;margin-bottom:20px">
    <div style="background:rgba(0,212,170,.08);border:1px solid var(--g);border-radius:8px;
         padding:12px;text-align:center;font-size:12px;color:var(--g);flex:1">
        ⬡ Сетка 3×3 ←
    </div>
    <a href="/draw_auth" style="text-decoration:none;flex:1">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;
           padding:12px;text-align:center;font-size:12px;color:var(--muted)">
        ✏ Свободный рисунок
      </div>
    </a>
  </div>
    <strong>Как это работает:</strong> проведите пальцем или мышью через точки сетки.
    Промежуточные точки добавляются автоматически.
    Паттерн хэшируется SHA-256 и сравнивается с сохранённым «цифровым отпечатком».
  </div>
  <div class="card" style="text-align:center">
    <div class="sec">// Нарисуйте паттерн</div>
    <div class="canvas-wrap">
      <canvas id="gk-canvas"></canvas>
      <div class="status-row">
        <div class="pts-count">Точек: <span id="pt-count">0</span> / мин. {MIN_POINTS}</div>
        <div style="font-size:11px;color:var(--muted)">
          Попыток осталось: <span id="att-left">{left}</span>
        </div>
      </div>
      <div id="att-bar" class="att-row">{att_dots}</div>
    </div>
    <button class="btn btn-gray" onclick="window._resetCanvas()">↺ Сброс</button>
    <a href="/"><button class="btn btn-r" type="button">Отмена</button></a>
    <div id="gk-result" class="result" style="display:none"></div>
  </div>
</div>
{canvas_js('auth', username)}"""
    return page(f"Авторизация — {username}", content, user=username)


@app.route('/api/auth_check', methods=['POST'])
def api_auth_check():
    data     = request.get_json()
    username = data.get('username', '')
    pattern  = data.get('pattern', [])
    users    = load_users()

    if username not in users:
        return jsonify({'success': False, 'message': 'Пользователь не найден', 'attempts_left': 0})

    u = users[username]

    if u.get('locked_until', 0) > time.time():
        return jsonify({'success': False, 'message': 'Учётная запись заблокирована', 'attempts_left': 0})

    if len(pattern) < MIN_POINTS:
        return jsonify({'success': False, 'message': f'Минимум {MIN_POINTS} точки', 'attempts_left': MAX_ATTEMPTS - u.get('fail_count', 0)})

    # Расширяем паттерн (умная логика) и считаем хэш
    expanded = expand_pattern(pattern)
    h        = hash_pattern(username, expanded, u['salt'])
    ok       = h == u['hash']

    if ok:
        u['fail_count'] = 0
        save_users(users)
        session['username'] = username
        return jsonify({'success': True, 'message': 'Паттерн верный! Добро пожаловать.', 'attempts_left': MAX_ATTEMPTS})
    else:
        u['fail_count'] = u.get('fail_count', 0) + 1
        left = MAX_ATTEMPTS - u['fail_count']
        if left <= 0:
            u['locked_until'] = time.time() + 120  # блокировка на 2 минуты
            save_users(users)
            return jsonify({'success': False, 'message': 'Превышено число попыток. Блокировка на 2 минуты.', 'attempts_left': 0})
        save_users(users)
        return jsonify({'success': False, 'message': f'Неверный паттерн. Осталось попыток: {left}', 'attempts_left': left})


# ─── РЕГИСТРАЦИЯ ──────────────────────────────────────────────────────────────
REG_NEEDED = 2   # сколько одинаковых вводов нужно для подтверждения

@app.route('/register')
def register():
    session.pop('reg_patterns', None)
    content = f"""
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Регистрация <span>нового пользователя</span></h1>
    <p>Введите имя и нарисуйте паттерн {REG_NEEDED} раза для подтверждения.</p>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div style="display:flex;gap:8px;margin-bottom:20px">
    <div style="background:rgba(0,212,170,.08);border:1px solid var(--g);border-radius:8px;
         padding:12px;text-align:center;font-size:12px;color:var(--g);flex:1">
        ⬡ Сетка 3×3 ←
    </div>
    <a href="/draw_register" style="text-decoration:none;flex:1">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;
           padding:12px;text-align:center;font-size:12px;color:var(--muted)">
        ✏ Свободный рисунок
      </div>
    </a>
  </div>

  <div class="info-warn">
    ⚠ Запомните паттерн! Нарисуйте его <strong>{REG_NEEDED} раза</strong> одинаково.
    Умная логика автоматически добавит пропущенные промежуточные точки.
  </div>
  <div class="card" id="step-name">
    <div class="sec">// Шаг 1 — Имя пользователя</div>
    <div class="fgroup">
      <div class="flabel">Идентификатор</div>
      <input type="text" id="uname-inp" placeholder="Только латиница и цифры" maxlength="32" autocomplete="off">
    </div>
    <button class="btn btn-g" onclick="checkName()">→ Далее</button>
    <div id="name-err" style="display:none;margin-top:10px;font-size:12px;color:var(--r)"></div>
  </div>
  <div class="card" id="step-draw" style="display:none;text-align:center">
    <div class="sec">// Шаг 2 — Нарисуйте паттерн</div>
    <div class="canvas-wrap">
      <canvas id="gk-canvas"></canvas>
      <div class="status-row">
        <div class="pts-count">Точек: <span id="pt-count">0</span> / мин. {MIN_POINTS}</div>
        <div id="reg-bar" class="att-row"></div>
      </div>
    </div>
    <button class="btn btn-gray" onclick="window._resetCanvas()">↺ Сброс</button>
    <div id="gk-result" class="result" style="display:none"></div>
  </div>
</div>

<script>
let regUsername = '';
function checkName(){{
  const val = document.getElementById('uname-inp').value.trim();
  const err = document.getElementById('name-err');
  if(!val || val.length<2){{ err.textContent='Имя слишком короткое'; err.style.display='block'; return; }}
  if(!/^[a-zA-Z0-9_]+$/.test(val)){{ err.textContent='Только латиница, цифры и _'; err.style.display='block'; return; }}
  err.style.display='none';
  fetch('/api/check_user',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:val}})}})
    .then(r=>r.json()).then(d=>{{
      if(d.exists){{ err.textContent='Пользователь уже существует'; err.style.display='block'; return; }}
      regUsername=val;
      document.getElementById('step-name').style.display='none';
      document.getElementById('step-draw').style.display='block';
      initCanvas(val);
    }});
}}
function initCanvas(name){{
  // подставляем имя в URL для API
  window._regUsername = name;
}}
document.getElementById('uname-inp').addEventListener('keypress',e=>{{ if(e.key==='Enter') checkName(); }});
</script>

{canvas_js('register', '__DYNAMIC__', MIN_POINTS).replace("'__DYNAMIC__'", "window._regUsername||''")}"""
    return page("Регистрация — Графический ключ", content)


@app.route('/api/check_user', methods=['POST'])
def api_check_user():
    d = request.get_json()
    return jsonify({'exists': d.get('username', '') in load_users()})


@app.route('/api/reg_attempt', methods=['POST'])
def api_reg_attempt():
    data     = request.get_json()
    username = data.get('username', '').strip()
    pattern  = data.get('pattern', [])

    if not username:
        return jsonify({'success': False, 'pending': False, 'message': 'Имя не указано', 'attempt': 0, 'total_needed': REG_NEEDED})

    expanded = expand_pattern(pattern)

    if len(expanded) < MIN_POINTS:
        return jsonify({'success': False, 'pending': False,
                        'message': f'Минимум {MIN_POINTS} точки', 'attempt': 0, 'total_needed': REG_NEEDED})

    if 'reg_patterns' not in session:
        session['reg_patterns'] = []
    session['reg_patterns'].append(expanded)
    session.modified = True

    done = len(session['reg_patterns'])

    if done < REG_NEEDED:
        return jsonify({'success': False, 'pending': True,
                        'message': f'Попытка {done} записана. Нарисуйте ещё раз.',
                        'attempt': done, 'total_needed': REG_NEEDED})

    # Проверяем что все попытки совпадают
    first = session['reg_patterns'][0]
    for p in session['reg_patterns'][1:]:
        if p != first:
            session.pop('reg_patterns', None)
            return jsonify({'success': False, 'pending': False,
                            'message': 'Паттерны не совпали. Начните заново.',
                            'attempt': 0, 'total_needed': REG_NEEDED})

    # Сохраняем
    salt  = secrets.token_hex(16)
    h     = hash_pattern(username, first, salt)
    users = load_users()
    if username in users:
        session.pop('reg_patterns', None)
        return jsonify({'success': False, 'pending': False,
                        'message': 'Пользователь уже существует',
                        'attempt': 0, 'total_needed': REG_NEEDED})

    users[username] = {
        'hash':         h,
        'salt':         salt,
        'pattern_len':  len(first),
        'fail_count':   0,
        'locked_until': 0,
        'registered':   time.strftime('%Y-%m-%d %H:%M'),
    }
    save_users(users)
    session.pop('reg_patterns', None)
    return jsonify({'success': True, 'pending': False,
                    'message': f'Пользователь {username} зарегистрирован!',
                    'attempt': REG_NEEDED, 'total_needed': REG_NEEDED})


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    u     = session['username']
    users = load_users()
    info  = users.get(u, {})

    content = f"""
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Добро пожаловать, <span>{u}</span></h1>
    <p>Аутентификация по графическому ключу прошла успешно.</p>
  </div>
  <div class="info-ok">
    ✓ <strong>Доступ разрешён.</strong> Ваш паттерн верифицирован по SHA-256 хэшу.
    Данные хранятся в зашифрованном файле <code>gk_users.dat</code> (XOR + Base64).
  </div>
  <div class="card">
    <div class="sec">// Профиль</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div style="background:#f0f7ff;border:1.5px solid #c5d8f0;border-radius:12px;padding:16px;text-align:center">
        <div style="font-size:28px;font-weight:700;color:#3f3fa8;font-family:'Playfair Display',serif">{info.get('pattern_len','?')}</div>
        <div style="font-size:10px;color:#6b82a8;letter-spacing:1px;text-transform:uppercase;margin-top:6px">Длина паттерна</div>
      </div>
      <div style="background:#fdf6fb;border:1.5px solid var(--border);border-radius:12px;padding:16px;text-align:center">
        <div style="font-size:13px;color:var(--text);font-weight:500">{info.get('registered','—')}</div>
        <div style="font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-top:6px">Дата регистрации</div>
      </div>
    </div>
    <div style="margin-top:10px;padding:10px 14px;background:#f0f7ff;border:1px solid #c5d8f0;border-radius:8px;font-size:11px;color:#3a5080;word-break:break-all;font-family:'JetBrains Mono',monospace">
      SHA-256: <span style="color:#3f3fa8;font-weight:600">{info.get('hash','—')[:32]}…</span>
    </div>
  </div>
  <div class="card">
    <div class="sec">// Действия</div>
    <a href="/users"><button class="btn btn-g" style="margin-right:8px">Список пользователей</button></a>
    <a href="/register"><button class="btn btn-gray">+ Добавить пользователя</button></a>
    <a href="/logout" style="margin-left:8px"><button class="btn btn-r">Выйти</button></a>
  </div>
</div>"""
    return page(f"Рабочий стол — {u}", content, user=u)


# ─── ПОЛЬЗОВАТЕЛИ ─────────────────────────────────────────────────────────────
@app.route('/users')
def users_list():
    if 'username' not in session:
        return redirect('/')
    users = load_users()
    rows  = ""
    for i, (name, d) in enumerate(sorted(users.items()), 1):
        me     = ' <span style="color:var(--g);font-size:10px">← вы</span>' if name == session.get('username') else ''
        locked = '🔒' if d.get('locked_until', 0) > time.time() else '✓'
        rows  += f"""<tr>
  <td style="color:var(--muted)">{i}</td>
  <td style="font-weight:600">{name}{me}</td>
  <td style="color:var(--g)">{d.get('pattern_len','?')}</td>
  <td style="color:{'var(--r)' if locked=='🔒' else 'var(--g)'}">{locked}</td>
  <td style="color:var(--muted);font-size:11px">{d.get('registered','—')}</td>
  <td style="color:var(--muted);font-size:11px">{d.get('fail_count',0)}</td>
</tr>"""

    content = f"""
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Зарегистрированные <span>пользователи</span></h1>
    <p>Данные хранятся в <code>gk_users.dat</code> (XOR 0x7B + Base64). SHA-256 хэш паттерна.</p>
  </div>
  <div class="info-blue">
    <strong>Безопасность:</strong> хранится только хэш паттерна + соль, восстановить сам паттерн невозможно.
    После {MAX_ATTEMPTS} неудачных попыток — блокировка на 2 минуты.
  </div>
  <div class="card" style="overflow:auto">
    <div class="sec">// Список ({len(users)} чел.)</div>
    <table class="utbl">
      <thead><tr>
        <th>№</th><th>Пользователь</th><th>Длина паттерна</th>
        <th>Статус</th><th>Дата рег.</th><th>Неудачных попыток</th>
      </tr></thead>
      <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Нет пользователей</td></tr>'}</tbody>
    </table>
  </div>
  <a href="/dashboard"><button class="btn btn-g">← Назад</button></a>
  <a href="/register" style="margin-left:8px"><button class="btn btn-gray">+ Добавить</button></a>
</div>"""
    return page("Пользователи — ГК", content, user=session.get('username', ''))


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')



# ═══════════════════════════════════════════════════════════════════════════════
#  АЛГОРИТМ СВОБОДНОГО РИСОВАНИЯ
#  Рисунок нормализуется → сэмплируется N точками → считается хэш координат
#  Для сравнения при аутентификации используется метрика DTW-подобного расстояния
# ═══════════════════════════════════════════════════════════════════════════════

DRAW_SAMPLE_N  = 64    # количество точек после ресэмплирования
DRAW_THRESHOLD = 0.18  # порог нормализованного расстояния (0..1, меньше = строже)

def normalize_stroke(points: list) -> list:
    """
    Нормализует список точек [{x,y}]:
    1) Вычисляет bounding box
    2) Масштабирует в квадрат [0,1]×[0,1]
    3) Ресэмплирует в DRAW_SAMPLE_N равноудалённых точек
    """
    if len(points) < 2:
        return points

    # Bounding box
    xs = [p['x'] for p in points]
    ys = [p['y'] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    W = maxx - minx or 1
    H = maxy - miny or 1
    side = max(W, H)

    # Нормализация с сохранением пропорций
    norm = [{'x': (p['x'] - minx) / side,
             'y': (p['y'] - miny) / side} for p in points]

    # Длины сегментов
    dists = [0.0]
    for i in range(1, len(norm)):
        dx = norm[i]['x'] - norm[i-1]['x']
        dy = norm[i]['y'] - norm[i-1]['y']
        dists.append(dists[-1] + math.hypot(dx, dy))

    total = dists[-1]
    if total == 0:
        return norm

    # Ресэмплирование
    step  = total / (DRAW_SAMPLE_N - 1)
    resampled = [norm[0]]
    j = 1
    dist_acc = 0.0

    for i in range(1, DRAW_SAMPLE_N - 1):
        target = i * step
        while j < len(dists) - 1 and dists[j] < target:
            j += 1
        # интерполяция
        if dists[j] - dists[j-1] < 1e-9:
            resampled.append(norm[j])
        else:
            t = (target - dists[j-1]) / (dists[j] - dists[j-1])
            ix = norm[j-1]['x'] + t * (norm[j]['x'] - norm[j-1]['x'])
            iy = norm[j-1]['y'] + t * (norm[j]['y'] - norm[j-1]['y'])
            resampled.append({'x': ix, 'y': iy})

    resampled.append(norm[-1])
    return resampled


def draw_distance(a: list, b: list) -> float:
    """
    Среднее евклидово расстояние между двумя нормализованными наборами точек.
    Оба набора должны иметь длину DRAW_SAMPLE_N.
    """
    if len(a) != len(b):
        return 1.0
    total = sum(math.hypot(a[i]['x'] - b[i]['x'],
                           a[i]['y'] - b[i]['y'])
                for i in range(len(a)))
    return total / len(a)


def hash_drawing(username: str, norm_pts: list, salt: str) -> str:
    """SHA-256 от округлённых координат нормализованного рисунка."""
    # Округляем до 3 знаков чтобы хэш был стабильным
    rounded = [{'x': round(p['x'], 3), 'y': round(p['y'], 3)} for p in norm_pts]
    raw = username + json.dumps(rounded) + salt
    return hashlib.sha256(raw.encode()).hexdigest()


# ─── Страница: свободный рисунок (вход) ───────────────────────────────────────
@app.route('/draw_auth')
def draw_auth():
    if 'auth_user' not in session:
        return redirect('/')
    username = session['auth_user']
    users    = load_users()
    if username not in users:
        return redirect('/?err=Пользователь+не+найден')
    left     = MAX_ATTEMPTS - users[username].get('draw_fail', 0)

    att_dots = "".join(
        f'<div class="att-d{"" if i < left else " used"}"></div>'
        for i in range(MAX_ATTEMPTS)
    )

    content = f"""
<div class="term-wrap">
  <div style="margin-bottom:20px">
    <div class="term-title">draw_auth<span>({username})</span></div>
    <div class="term-sub">$ Нарисуйте ваш рисунок так же, как при регистрации.</div>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div class="tab-switcher">
    <a href="/auth" style="text-decoration:none;flex:1">
      <button class="tab-sw-btn fem">♡ Сетка 3×3</button>
    </a>
    <button class="tab-sw-btn term active-term">✏ Свободный рисунок</button>
  </div>

  <div class="term-info">
    <strong>// АЛГОРИТМ:</strong> нормализация → bbox → resample({DRAW_SAMPLE_N}pts)
    → avg_euclidean_distance → compare(threshold={DRAW_THRESHOLD})
    | gradient: sky→white→crimson→rose→indigo
  </div>

  <div class="term-card" style="text-align:center">
    <div class="term-sec">// AUTH_CANVAS</div>
    <div class="canvas-wrap">
      <canvas id="draw-canvas" width="400" height="340"></canvas>
      <div class="status-row" style="width:400px">
        <div class="term-prompt">pts: <span id="pt-cnt" style="color:#fff">0</span></div>
        <div style="font-size:11px;color:var(--term-muted);font-family:'JetBrains Mono',monospace">
          attempts_left: <span id="att-left">{left}</span>
        </div>
      </div>
      <div id="att-bar" class="att-row">{att_dots}</div>
    </div>
    <button class="term-btn term-btn-amber" onclick="resetDraw()">RESET</button>
    <button class="term-btn" id="submit-btn" onclick="submitDraw()" disabled style="margin-left:8px">
      RUN CHECK →
    </button>
    <a href="/"><button class="term-btn term-btn-red" type="button" style="margin-left:8px">EXIT</button></a>
    <div id="draw-result" class="term-result" style="display:none"></div>
  </div>
</div>

{_draw_canvas_js('auth', username)}"""
    return page(f"draw_auth({username})", content, user=username, terminal=True)


# ─── Страница: свободный рисунок (регистрация) ────────────────────────────────
@app.route('/draw_register')
def draw_register():
    session.pop('draw_reg_pts', None)

    content = f"""
<div class="term-wrap">
  <div style="margin-bottom:20px">
    <div class="term-title">draw_register<span>(new_user)</span></div>
    <div class="term-sub">$ Введите имя и нарисуйте рисунок {REG_NEEDED} раза одинаково.</div>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div class="tab-switcher">
    <a href="/register" style="text-decoration:none;flex:1">
      <button class="tab-sw-btn fem">♡ Сетка 3×3</button>
    </a>
    <button class="tab-sw-btn term active-term">✏ Свободный рисунок</button>
  </div>

  <div class="term-warn">
    <strong>// WARNING:</strong> нарисуйте одинаковый рисунок {REG_NEEDED} раза.
    normalize → resample({DRAW_SAMPLE_N}pts) → avg_vector → store.
    threshold={DRAW_THRESHOLD} | 0.0=perfect 1.0=random
  </div>

  <div class="term-card" id="step-name">
    <div class="term-sec">// STEP_1: SET_USERNAME</div>
    <div style="margin-bottom:12px">
      <div class="term-label">username:</div>
      <input class="term-input" type="text" id="uname-inp"
        placeholder="[a-z0-9_] only" maxlength="32" autocomplete="off">
    </div>
    <button class="term-btn" onclick="checkName()">NEXT →</button>
    <div id="name-err" style="display:none;margin-top:10px;font-size:11px;
      color:var(--term-red);font-family:'JetBrains Mono',monospace"></div>
  </div>

  <div class="term-card" id="step-draw" style="display:none;text-align:center">
    <div class="term-sec">// STEP_2: DRAW_PATTERN</div>
    <div class="canvas-wrap">
      <canvas id="draw-canvas" width="400" height="340"></canvas>
      <div class="status-row" style="width:400px">
        <div class="term-prompt">pts: <span id="pt-cnt" style="color:#fff">0</span></div>
        <div id="reg-bar" class="att-row"></div>
      </div>
    </div>
    <button class="term-btn term-btn-amber" onclick="resetDraw()">RESET</button>
    <button class="term-btn" id="submit-btn" onclick="submitDraw()" disabled style="margin-left:8px">
      COMMIT ATTEMPT →
    </button>
    <div id="draw-result" class="term-result" style="display:none"></div>
  </div>
</div>

<script>
let drUsername = '';
function checkName(){{
  const val = document.getElementById('uname-inp').value.trim();
  const err = document.getElementById('name-err');
  if(!val || val.length<2){{ err.textContent='error: username too short'; err.style.display='block'; return; }}
  if(!/^[a-zA-Z0-9_]+$/.test(val)){{ err.textContent='error: invalid chars ([a-z0-9_] only)'; err.style.display='block'; return; }}
  err.style.display='none';
  fetch('/api/check_user',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{username:val}})}}).then(r=>r.json()).then(d=>{{
    if(d.exists){{ err.textContent='error: user already exists'; err.style.display='block'; return; }}
    drUsername = val;
    document.getElementById('step-name').style.display='none';
    document.getElementById('step-draw').style.display='block';
  }});
}}
document.getElementById('uname-inp').addEventListener('keypress',e=>{{ if(e.key==='Enter') checkName(); }});
</script>
{_draw_canvas_js('register', '__DR_USER__')}"""
    return page("draw_register — ГК", content, terminal=True)


# ─── JS для свободного рисования ──────────────────────────────────────────────
def _draw_canvas_js(mode: str, username: str) -> str:
    """
    Canvas для произвольного рисования.
    Градиентная линия красный→зелёный→синий по прогрессу пути.
    Нормализация и ресэмплирование — на сервере.
    """
    if mode == 'register':
        user_expr = 'drUsername'
        handle = f"""
async function submitDraw(){{
  if(allPts.length < 20){{ showRes('Нарисуйте рисунок (минимум 20 точек)', false); return; }}
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  const res = await fetch('/api/draw_reg',{{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username: {user_expr}, points: allPts}})
  }}).then(r=>r.json());
  showRes(res.message, res.success || res.pending);
  updateBar(res.attempt, res.total_needed);
  if(res.success) {{ setTimeout(()=>window.location.href='/', 2200); return; }}
  setTimeout(()=>{{ resetDraw(); }}, 1600);
}}
function updateBar(done, need){{
  const bar = document.getElementById('reg-bar');
  if(!bar) return;
  bar.innerHTML = '';
  for(let i=0;i<need;i++){{
    const d=document.createElement('div');
    d.className = 'att-d' + (i<done?' ok':'');
    bar.appendChild(d);
  }}
}}"""
    else:
        user_expr = json.dumps(username)
        handle = f"""
async function submitDraw(){{
  if(allPts.length < 20){{ showRes('Нарисуйте рисунок (минимум 20 точек)', false); return; }}
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  const res = await fetch('/api/draw_auth',{{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username: {user_expr}, points: allPts}})
  }}).then(r=>r.json());
  showRes(res.message, res.success);
  updateAttempts(res.attempts_left);
  if(res.success) setTimeout(()=>window.location.href='/dashboard', 1800);
  else setTimeout(()=>{{ resetDraw(); }}, 1600);
}}
function updateAttempts(left){{
  const el = document.getElementById('att-left');
  if(el) el.textContent = left;
  const bar = document.getElementById('att-bar');
  if(!bar) return;
  bar.innerHTML='';
  for(let i=0;i<{MAX_ATTEMPTS};i++){{
    const d=document.createElement('div');
    d.className='att-d'+(i<({MAX_ATTEMPTS}-left)?' used':'');
    bar.appendChild(d);
  }}
}}"""

    return f"""<script>
(function(){{
const canvas  = document.getElementById('draw-canvas');
const ctx     = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;

let allPts    = [];   // все точки [{{x,y}}] в пикселях
let segments  = [];   // массив сегментов (каждый mousedown → новый)
let curSeg    = null; // текущий сегмент
let drawing   = false;
let totalLen  = 0;    // накопленная длина всего пути

// Фоновая сетка (тонкие линии — светлая версия)
function drawBg(){{
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle = 'rgba(21,101,192,0.07)';
  ctx.lineWidth   = 0.8;
  for(let x=0;x<W;x+=40){{ ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke(); }}
  for(let y=0;y<H;y+=40){{ ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke(); }}
}}

// Цвет линии — плоский, по прогрессу: голубой → индиго (без градиента)
function gradColor(t){{
  // Простая интерполяция без градиентных эффектов
  const r=Math.round(13  + (33-13)*t*0 + (21-33)*(t>0.5?1:0));
  // Чистый синий во всём диапазоне, чуть темнее к концу
  if(t < 0.33) return '#0277bd';
  if(t < 0.66) return '#1565c0';
  return '#283593';
}}

// Длина сегмента
function segLen(seg){{
  let l=0;
  for(let i=1;i<seg.length;i++) l+=Math.hypot(seg[i].x-seg[i-1].x, seg[i].y-seg[i-1].y);
  return l;
}}

// Перерисовка всего
function redraw(){{
  drawBg();
  // Считаем общую длину всех сегментов
  const lengths = segments.map(segLen);
  const grand   = lengths.reduce((a,b)=>a+b,0) || 1;

  let acc = 0;
  for(let si=0; si<segments.length; si++){{
    const seg = segments[si];
    if(seg.length < 2) continue;
    let segAcc = 0;
    // Плоский цвет по позиции сегмента — без createLinearGradient
    const tSeg = grand > 0 ? acc/grand : 0;
    const col = gradColor(tSeg);
    ctx.beginPath();
    ctx.moveTo(seg[0].x, seg[0].y);
    for(let i=1;i<seg.length;i++) ctx.lineTo(seg[i].x, seg[i].y);
    ctx.strokeStyle = col;
    ctx.lineWidth   = 2.5;
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.stroke();
    // Точка начала сегмента
    ctx.beginPath(); ctx.arc(seg[0].x,seg[0].y,4,0,Math.PI*2);
    ctx.fillStyle=col; ctx.fill();
    acc+=lengths[si];
  }}
  // Обновляем счётчик
  const cnt=document.getElementById('pt-cnt');
  if(cnt) cnt.textContent=allPts.length;
  // Активируем кнопку
  const btn=document.getElementById('submit-btn');
  if(btn) btn.disabled = allPts.length<20;
}}

function getPos(e){{
  const r=canvas.getBoundingClientRect();
  const cl=e.touches?e.touches[0]:e;
  return {{x:(cl.clientX-r.left)*(W/r.width), y:(cl.clientY-r.top)*(H/r.height)}};
}}

canvas.addEventListener('mousedown', e=>{{
  e.preventDefault(); drawing=true;
  const p=getPos(e);
  curSeg=[p]; segments.push(curSeg); allPts.push(p); redraw();
}});
canvas.addEventListener('mousemove', e=>{{
  if(!drawing) return; e.preventDefault();
  const p=getPos(e);
  curSeg.push(p); allPts.push(p); redraw();
}});
canvas.addEventListener('mouseup',    e=>{{ drawing=false; }});
canvas.addEventListener('mouseleave', e=>{{ drawing=false; }});
canvas.addEventListener('touchstart', e=>{{
  e.preventDefault(); drawing=true;
  const p=getPos(e);
  curSeg=[p]; segments.push(curSeg); allPts.push(p); redraw();
}},{{passive:false}});
canvas.addEventListener('touchmove',  e=>{{
  if(!drawing) return; e.preventDefault();
  const p=getPos(e);
  curSeg.push(p); allPts.push(p); redraw();
}},{{passive:false}});
canvas.addEventListener('touchend',   e=>{{ drawing=false; }});

function resetDraw(){{
  allPts=[]; segments=[]; curSeg=null; drawing=false;
  drawBg();
  const el=document.getElementById('draw-result');
  if(el) el.style.display='none';
  const btn=document.getElementById('submit-btn');
  if(btn) btn.disabled=true;
  const cnt=document.getElementById('pt-cnt');
  if(cnt) cnt.textContent='0';
}}
window.resetDraw=resetDraw;

function showRes(text, ok){{
  const el=document.getElementById('draw-result');
  if(!el) return;
  el.className='result '+(ok?'ok':'err');
  el.textContent=(ok?'✓ ':'✗ ')+text;
  el.style.display='block';
  const btn=document.getElementById('submit-btn');
  if(btn) btn.disabled=false;
}}

{handle}

window.submitDraw=submitDraw;
drawBg();
}})();
</script>"""


# ─── API: регистрация рисунка ──────────────────────────────────────────────────
@app.route('/api/draw_reg', methods=['POST'])
def api_draw_reg():
    data     = request.get_json()
    username = data.get('username', '').strip()
    points   = data.get('points', [])

    if not username:
        return jsonify({'success': False, 'pending': False,
                        'message': 'Имя не указано', 'attempt': 0, 'total_needed': REG_NEEDED})
    if len(points) < 20:
        return jsonify({'success': False, 'pending': False,
                        'message': 'Слишком мало точек', 'attempt': 0, 'total_needed': REG_NEEDED})

    norm = normalize_stroke(points)

    if 'draw_reg_pts' not in session:
        session['draw_reg_pts'] = []
    session['draw_reg_pts'].append(norm)
    session.modified = True

    done = len(session['draw_reg_pts'])

    if done < REG_NEEDED:
        return jsonify({'success': False, 'pending': True,
                        'message': f'Попытка {done} записана. Нарисуйте ещё раз.',
                        'attempt': done, 'total_needed': REG_NEEDED})

    # Проверяем схожесть всех попыток
    first = session['draw_reg_pts'][0]
    max_dist = 0.0
    for p in session['draw_reg_pts'][1:]:
        d = draw_distance(first, p)
        if d > max_dist:
            max_dist = d

    if max_dist > DRAW_THRESHOLD:
        session.pop('draw_reg_pts', None)
        return jsonify({'success': False, 'pending': False,
                        'message': f'Рисунки слишком разные (расстояние {max_dist:.3f} > порог {DRAW_THRESHOLD}). Начните заново.',
                        'attempt': 0, 'total_needed': REG_NEEDED})

    # Сохраняем среднее из всех попыток как эталон
    all_pts  = session['draw_reg_pts']
    avg_norm = [
        {'x': sum(a[i]['x'] for a in all_pts) / len(all_pts),
         'y': sum(a[i]['y'] for a in all_pts) / len(all_pts)}
        for i in range(DRAW_SAMPLE_N)
    ]

    salt  = secrets.token_hex(16)
    users = load_users()

    if username in users:
        session.pop('draw_reg_pts', None)
        return jsonify({'success': False, 'pending': False,
                        'message': 'Пользователь уже существует',
                        'attempt': 0, 'total_needed': REG_NEEDED})

    # Сохраняем нормализованный эталон (для сравнения) + хэш (для display)
    users[username] = {
        'mode':         'draw',
        'norm_pts':     avg_norm,          # эталон для DTW-сравнения
        'hash':         hash_drawing(username, avg_norm, salt),
        'salt':         salt,
        'draw_fail':    0,
        'locked_until': 0,
        'registered':   time.strftime('%Y-%m-%d %H:%M'),
        'pattern_len':  DRAW_SAMPLE_N,
    }
    save_users(users)
    session.pop('draw_reg_pts', None)
    return jsonify({'success': True, 'pending': False,
                    'message': f'Пользователь {username} зарегистрирован!',
                    'attempt': REG_NEEDED, 'total_needed': REG_NEEDED})


# ─── API: аутентификация рисунком ─────────────────────────────────────────────
@app.route('/api/draw_auth', methods=['POST'])
def api_draw_auth():
    data     = request.get_json()
    username = data.get('username', '')
    points   = data.get('points', [])
    users    = load_users()

    if username not in users:
        return jsonify({'success': False, 'message': 'Пользователь не найден', 'attempts_left': 0})

    u = users[username]
    if u.get('locked_until', 0) > time.time():
        return jsonify({'success': False, 'message': 'Учётная запись заблокирована', 'attempts_left': 0})

    if u.get('mode') != 'draw':
        return jsonify({'success': False, 'message': 'Этот пользователь использует режим сетки 3×3', 'attempts_left': 0})

    if len(points) < 20:
        left = MAX_ATTEMPTS - u.get('draw_fail', 0)
        return jsonify({'success': False, 'message': 'Слишком мало точек', 'attempts_left': left})

    norm    = normalize_stroke(points)
    etalon  = u['norm_pts']
    dist    = draw_distance(norm, etalon)
    ok      = dist <= DRAW_THRESHOLD

    if ok:
        u['draw_fail'] = 0
        save_users(users)
        session['username'] = username
        return jsonify({'success': True,
                        'message': f'Рисунок совпал! Расстояние: {dist:.3f} ≤ {DRAW_THRESHOLD}',
                        'attempts_left': MAX_ATTEMPTS})
    else:
        u['draw_fail'] = u.get('draw_fail', 0) + 1
        left = MAX_ATTEMPTS - u['draw_fail']
        if left <= 0:
            u['locked_until'] = time.time() + 120
            save_users(users)
            return jsonify({'success': False,
                            'message': f'Превышено число попыток. Блокировка 2 мин. Расстояние: {dist:.3f}',
                            'attempts_left': 0})
        save_users(users)
        return jsonify({'success': False,
                        'message': f'Рисунок не совпал. Расстояние: {dist:.3f} > {DRAW_THRESHOLD}. Осталось: {left}',
                        'attempts_left': left})


if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"  ЛР №7 — Графический ключ")
    print(f"  Сетка 3×3, мин. точек: {MIN_POINTS}")
    print(f"  Хэш: SHA-256, шифрование: XOR+Base64")
    print(f"  Блокировка: {MAX_ATTEMPTS} неудачных попыток → 2 мин.")
    print(f"  http://127.0.0.1:5000")
    print(f"{'='*50}\n")
    app.run(debug=True)