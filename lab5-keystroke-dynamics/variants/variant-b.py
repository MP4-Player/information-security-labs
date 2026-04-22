# -*- coding: utf-8 -*-
"""
Лабораторная работа №5 — Защита данных от несанкционированного доступа
Метод: Клавиатурный почерк (Keystroke Dynamics)
Автор: Булгаров Марк Александрович

Алгоритм:
  Регистрация: пользователь вводит фразу 4 раза.
    Для каждого ввода фиксируются интервалы между нажатиями клавиш (мс).
    Идеальное значение = среднее арифметическое всех интервалов за 4 попытки.
    Отклонение = среднее(|интервал_i - идеальное|) по всем символам всех попыток.
    Данные шифруются (XOR + base64) и сохраняются в users.dat.

  Авторизация: пользователь вводит свою фразу 1 раз.
    Вычисляются идеальное значение и отклонение текущего ввода.
    Проверка: |ideal_current - ideal_stored| < EPS
          И  |dev_current   - dev_stored|   < EPS
    EPS настраивается (по умолчанию 200 мс).
    Ideal вычисляется через медиану (устойчива к выбросам).

  Блокировка: при бездействии более LOCK_TIMEOUT секунд окно блокируется.
"""

import json, base64, random, time, os, statistics
from flask import Flask, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'lab5_keystroke_dynamics_2024'

# ══════════════════════════════════════════════
#  КОНСТАНТЫ
# ══════════════════════════════════════════════
USERS_FILE   = 'users.dat'       # зашифрованный файл пользователей
PHRASES_FILE = 'phrases.dat'     # зашифрованный файл фраз
MIN_ATTEMPTS = 4                  # минимум вводов при регистрации
EPS          = 200                # точность сравнения (мс)
LOCK_TIMEOUT = 30                 # секунд бездействия до блокировки

# ══════════════════════════════════════════════
#  10 ФРАЗ (25+ символов, буквы+цифры+знаки)
# ══════════════════════════════════════════════
BUILTIN_PHRASES = [
    "apple grape lemon mango peach",
    "black white green coral beige",
    "delta sigma omega gamma kappa",
    "flask nginx redis mongo kafka",
    "sunny rainy foggy snowy windy",
    "stone water flame earth light",
    "bravo delta hotel lima oscar",
    "piano organ flute cello viola",
    "tiger eagle shark raven bison",
    "laser radar sonar tower relay",
]

# ══════════════════════════════════════════════
#  ШИФРОВАНИЕ (XOR + base64)
# ══════════════════════════════════════════════
XOR_KEY = 0x5A

def encrypt(data: str) -> str:
    b = data.encode('utf-8')
    xored = bytes([byte ^ XOR_KEY for byte in b])
    return base64.b64encode(xored).decode('ascii')

def decrypt(data: str) -> str:
    xored = base64.b64decode(data.encode('ascii'))
    b = bytes([byte ^ XOR_KEY for byte in xored])
    return b.decode('utf-8')

# ══════════════════════════════════════════════
#  РАБОТА С ФАЙЛАМИ
# ══════════════════════════════════════════════
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            return json.loads(decrypt(f.read().strip()))
    except Exception:
        return {}

def save_users(users: dict):
    with open(USERS_FILE, 'w') as f:
        f.write(encrypt(json.dumps(users, ensure_ascii=False)))

def load_phrases() -> list:
    if not os.path.exists(PHRASES_FILE):
        save_phrases(BUILTIN_PHRASES)
        return BUILTIN_PHRASES
    try:
        with open(PHRASES_FILE, 'r') as f:
            return json.loads(decrypt(f.read().strip()))
    except Exception:
        return BUILTIN_PHRASES

def save_phrases(phrases: list):
    with open(PHRASES_FILE, 'w') as f:
        f.write(encrypt(json.dumps(phrases, ensure_ascii=False)))

def get_random_phrase() -> str:
    return random.choice(load_phrases())

# ══════════════════════════════════════════════
#  ВЫЧИСЛЕНИЕ ХАРАКТЕРИСТИК КЛАВИАТУРНОГО ПОЧЕРКА
# ══════════════════════════════════════════════
def compute_stats(all_intervals: list) -> tuple:
    """
    all_intervals: список списков интервалов (по одному списку на попытку).
    Возвращает (ideal, deviation).
    ideal     = медиана по ВСЕМ интервалам всех попыток (устойчива к выбросам)
    deviation = среднее(|interval_i - ideal|) по всем интервалам
    """
    flat = [v for attempt in all_intervals for v in attempt if v > 0]
    if not flat:
        return 0.0, 0.0
    ideal     = statistics.median(flat)
    deviation = sum(abs(v - ideal) for v in flat) / len(flat)
    return round(ideal, 1), round(deviation, 1)

def compute_single_stats(intervals: list) -> tuple:
    """Для одной попытки авторизации."""
    return compute_stats([intervals])

# ══════════════════════════════════════════════
#  ОБЩИЙ CSS (ТЁМНАЯ ТЕМА + БРУТАЛЬНЫЙ ШРИФТ + ЗЕЛЁНЫЙ/ОРАНЖЕВЫЙ/ФИОЛЕТОВЫЙ)
# ══════════════════════════════════════════════
BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800;900&family=Anton&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0a0c; --card:#13141a; --border:#2a2d3a;
  --text:#e4e4e7; --muted:#71717a;
  --g:#10b981; --o:#f97316; --p:#8b5cf6; --warn:#f59e0b;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Rubik',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;
  background:
    radial-gradient(ellipse 70% 50% at 0% 0%,  rgba(16,185,129,.12) 0%,transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 100%, rgba(249,115,22,.10) 0%,transparent 50%),
    radial-gradient(ellipse 50% 40% at 50%  50%, rgba(139,92,246,.08) 0%,transparent 60%);
}
nav{position:sticky;top:0;z-index:99;background:rgba(10,10,12,.98);border-bottom:2px solid var(--border);
    backdrop-filter:blur(16px);padding:14px 32px;display:flex;align-items:center;justify-content:space-between;
    box-shadow:0 4px 20px rgba(0,0,0,.5);}
.brand{font-family:'Bebas Neue',sans-serif;font-size:22px;font-weight:700;letter-spacing:4px;
  background:linear-gradient(135deg,var(--g),var(--o),var(--p));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  text-transform:uppercase;}
.nav-links{display:flex;gap:4px}
.nl{padding:8px 18px;font-size:14px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--muted);text-decoration:none;border:2px solid transparent;transition:.2s;
  font-family:'Bebas Neue',sans-serif;}
.nl:hover{color:var(--text);border-bottom-color:var(--g);background:rgba(16,185,129,.05)}
.nl.red:hover{color:var(--o);border-bottom-color:var(--o)}
.chip{display:flex;align-items:center;gap:10px;background:var(--card);border:2px solid var(--border);
  padding:6px 18px;font-size:14px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  font-family:'Bebas Neue',sans-serif;box-shadow:0 2px 0 rgba(0,0,0,.3)}
.dot{width:10px;height:10px;background:linear-gradient(135deg,var(--g),var(--p));animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1;box-shadow:0 0 12px var(--g)}50%{opacity:.3;box-shadow:0 0 4px var(--g)}}
.wrap{max-width:900px;margin:0 auto;padding:32px 24px;position:relative;z-index:1}
.card{background:var(--card);border:2px solid var(--border);padding:26px;margin-bottom:20px;
  box-shadow:0 8px 0 rgba(0,0,0,.4),0 4px 20px rgba(0,0,0,.3);}
.grad-rgb{background:linear-gradient(135deg,var(--g),var(--o),var(--p));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.ph{margin-bottom:24px}
.ph h1{font-family:'Bebas Neue',sans-serif;font-size:36px;font-weight:700;letter-spacing:3px;text-transform:uppercase}
.ph h1 span{color:var(--g)}
.ph p{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.8;font-weight:500;letter-spacing:0.5px}
.info-blue{background:rgba(16,185,129,.04);border-left:4px solid var(--g);border-bottom:2px solid var(--border);border-right:2px solid var(--border);border-top:2px solid var(--border);
  padding:18px 22px;font-size:13px;line-height:1.9;color:#a7f3d0;margin-bottom:20px;font-weight:500}
.info-blue strong{color:var(--g);font-weight:800;text-transform:uppercase;letter-spacing:1px}
.info-warn{background:rgba(249,115,22,.04);border-left:4px solid var(--o);border-bottom:2px solid var(--border);border-right:2px solid var(--border);border-top:2px solid var(--border);
  padding:18px 22px;font-size:13px;line-height:1.9;color:#fdba74;margin-bottom:20px;font-weight:500}
.btn{padding:14px 28px;border:none;font-family:'Bebas Neue',sans-serif;
  font-size:18px;font-weight:700;letter-spacing:3px;text-transform:uppercase;cursor:pointer;transition:.2s;
  border:2px solid;box-shadow:0 4px 0 rgba(0,0,0,.4);}
.btn:active{transform:translateY(4px);box-shadow:none}
.btn-g{background:var(--g);border-color:#047857;color:#022c22}
.btn-g:hover{background:#059669;box-shadow:0 6px 0 #047857,0 0 24px rgba(16,185,129,.4)}
.btn-o{background:var(--o);border-color:#c2410c;color:#431407}
.btn-o:hover{background:#ea580c;box-shadow:0 6px 0 #c2410c,0 0 24px rgba(249,115,22,.4)}
.btn-p{background:var(--p);border-color:#6d28d9;color:#ede9fe}
.btn-p:hover{background:#7c3aed;box-shadow:0 6px 0 #6d28d9,0 0 24px rgba(139,92,246,.4)}
select,input[type=text],input[type=password],input[type=number]{
  padding:14px 18px;background:#0a0a0c;border:2px solid var(--border);
  color:var(--text);font-family:'Rubik',sans-serif;font-size:14px;font-weight:500;transition:.2s;width:100%}
select:focus,input:focus{outline:none;border-color:var(--g);box-shadow:0 0 0 4px rgba(16,185,129,.1)}
select option{background:#13141a}
.fgroup{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}
.flabel{font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);
  font-family:'Bebas Neue',sans-serif}
.result{display:none;margin-top:18px;padding:18px;font-size:14px;line-height:1.9;border:2px solid;font-weight:500}
.result.ok{background:rgba(16,185,129,.06);border-color:var(--g);color:#6ee7b7}
.result.err{background:rgba(249,115,22,.06);border-color:var(--o);color:#fdba74}
.result .expl{margin-top:12px;padding-top:12px;border-top:2px dashed var(--border);
  font-size:12px;color:var(--muted);line-height:1.9}
/* PHRASE DISPLAY */
.phrase-box{background:#0a0a0c;border:3px solid var(--border);padding:20px 24px;margin-bottom:20px;text-align:center}
.phrase-text{font-size:26px;font-weight:900;background:linear-gradient(135deg,var(--g),var(--o));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  letter-spacing:2px;font-family:'Rubik',sans-serif;word-break:break-all;text-transform:uppercase}
.phrase-label{font-size:13px;font-weight:700;color:var(--muted);letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;
  font-family:'Bebas Neue',sans-serif}
/* PROGRESS */
.attempts-bar{display:flex;gap:10px;margin-bottom:20px}
.att-dot{width:36px;height:36px;background:#0a0a0c;border:3px solid var(--border);
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;color:var(--muted);transition:.2s;
  font-family:'Bebas Neue',sans-serif}
.att-dot.done{background:var(--g);border-color:#047857;color:#022c22;box-shadow:0 0 16px rgba(16,185,129,.3)}
.att-dot.active{background:transparent;border-color:var(--o);color:var(--o);animation:pulse2 1s infinite}
@keyframes pulse2{0%,100%{box-shadow:0 0 0 0 rgba(249,115,22,.5)}50%{box-shadow:0 0 0 10px rgba(249,115,22,0)}}
/* STATS TABLE */
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
.stat-item{background:#0a0a0c;border:2px solid var(--border);padding:18px;text-align:center}
.stat-val{font-family:'Bebas Neue',sans-serif;font-size:38px;font-weight:700;letter-spacing:2px;
  background:linear-gradient(135deg,var(--g),var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-lbl{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:6px;
  font-family:'Bebas Neue',sans-serif}
/* LOCK OVERLAY */
#lock-overlay{
  display:none;position:fixed;inset:0;z-index:999;
  background:rgba(10,10,12,.98);
  flex-direction:column;align-items:center;justify-content:center;gap:24px;
  backdrop-filter:blur(16px);
}
#lock-overlay.show{display:flex}
.lock-icon{font-size:100px}
.lock-title{font-family:'Bebas Neue',sans-serif;font-size:48px;font-weight:700;letter-spacing:6px;color:var(--o);text-transform:uppercase}
.lock-sub{font-size:16px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;font-weight:600}
/* USERS TABLE */
.utbl{width:100%;border-collapse:collapse;font-size:13px}
.utbl th,.utbl td{padding:14px 16px;border-bottom:2px solid var(--border);text-align:left}
.utbl th{color:var(--muted);font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  font-family:'Bebas Neue',sans-serif}
.utbl tr:last-child td{border-bottom:none}
.utbl tr:hover td{background:rgba(16,185,129,.02)}
/* LOGIN BODY */
.login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
.lw{width:540px;position:relative;z-index:1}
.badge{display:inline-flex;align-items:center;gap:10px;background:var(--card);border:2px solid var(--border);
  padding:8px 20px;font-size:14px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:var(--g);margin-bottom:24px;font-family:'Bebas Neue',sans-serif;box-shadow:0 4px 0 rgba(0,0,0,.3)}
.badge::before{content:'⚡';font-size:16px;color:var(--o)}
.lh1{font-family:'Bebas Neue',sans-serif;font-size:44px;font-weight:700;line-height:1.1;margin-bottom:12px;letter-spacing:2px;text-transform:uppercase}
.lsub{font-size:14px;color:var(--muted);margin-bottom:28px;line-height:1.8;font-weight:500;letter-spacing:0.5px}
.lsub span{color:var(--p);font-weight:700;text-transform:uppercase}
.err-box{display:flex;align-items:center;gap:12px;background:rgba(249,115,22,.06);
  border-left:4px solid var(--o);border-bottom:2px solid var(--border);border-right:2px solid var(--border);border-top:2px solid var(--border);
  padding:16px 20px;font-size:14px;font-weight:600;color:#fdba74;margin-bottom:20px}
.sec{font-size:14px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:12px;margin-bottom:16px;font-family:'Bebas Neue',sans-serif}
.sec::after{content:'';flex:1;height:3px;background:linear-gradient(90deg,var(--border),transparent)}
code{background:#0a0a0c;padding:3px 10px;border:2px solid var(--border);font-size:12px;color:var(--g);font-weight:600}
</style>"""

def nav_html():
    user = session.get('username', '')
    chip = f'<div class="chip"><div class="dot"></div>⚡ {user}</div>' if user else ''
    links = [
        ("/dashboard", "ГЛАВНАЯ", ""),
        ("/register", "РЕГИСТРАЦИЯ", ""),
        ("/users", "ЮЗЕРЫ", ""),
        ("/logout", "ВЫХОД", "red"),
    ]
    lhtml = "".join(f'<a href="{h}" class="nl {c}">{l}</a>' for h,l,c in links)
    return f"""<nav>
  <div class="brand">⚡ КП // ПОЧЕРК</div>
  <div class="nav-links">{lhtml}</div>
  {chip}
</nav>"""

def page(title, content, login=False):
    bc = "login-body" if login else ""
    nav = "" if login else nav_html()
    return f"""<!DOCTYPE html>
<html lang="ru"><head><title>{title}</title>{BASE_STYLE}</head>
<body class="{bc}">
{nav}
{content}
</body></html>"""

# ══════════════════════════════════════════════
#  СТРАНИЦА ВХОДА (выбор пользователя)
# ══════════════════════════════════════════════
@app.route('/')
def index():
    users = load_users()
    err = f'<div class="err-box">⚠ {request.args.get("err")}</div>' if request.args.get('err') else ''
    if not users:
        opts = '<option value="">— НЕТ ЗАРЕГИСТРИРОВАННЫХ —</option>'
    else:
        opts = '<option value="">— ВЫБЕРИ БОЙЦА —</option>'
        for uname in sorted(users.keys()):
            opts += f'<option value="{uname}">{uname.upper()}</option>'

    content = f"""
<div class="lw">
  <div class="badge">КЛАВИАТУРНЫЙ ПОЧЕРК</div>
  <div class="lh1 grad-rgb">ЗАЩИТА ОТ НСД<br>ПО ДИНАМИКЕ НАБОРА</div>
  <p class="lsub">ПРАКТИЧЕСКОЕ ЗАНЯТИЕ №5 · <span>ЗАЩИТА ИНФОРМАЦИИ</span><br>
  ИДЕНТИФИКАЦИЯ ПОЛЬЗОВАТЕЛЯ ПО СКОРОСТИ ВВОДА</p>
  {err}
  <div class="card">
    <div class="flabel" style="margin-bottom:14px">// ВЫБОР ЦЕЛИ</div>
    <form method="POST" action="/start_auth">
      <select name="username" required style="margin-bottom:16px">{opts}</select>
      <button type="submit" class="btn btn-g" style="width:100%">→ ВОЙТИ</button>
    </form>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px">
    <a href="/register" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:18px">
        <div style="color:var(--p);font-size:18px;font-weight:700;letter-spacing:3px;font-family:'Bebas Neue'">РЕГИСТРАЦИЯ</div>
        <div style="font-size:12px;color:var(--muted);margin-top:6px;font-weight:600">НОВЫЙ БОЕЦ</div>
      </div>
    </a>
    <a href="/users" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:18px">
        <div style="color:var(--o);font-size:18px;font-weight:700;letter-spacing:3px;font-family:'Bebas Neue'">ЮЗЕРЫ</div>
        <div style="font-size:12px;color:var(--muted);margin-top:6px;font-weight:600">СПИСОК: {len(users)} ЧЕЛ.</div>
      </div>
    </a>
  </div>
  <div class="info-blue" style="margin-top:16px">
    ⚡ <strong>МЕТОД:</strong> СИСТЕМА ИЗМЕРЯЕТ ИНТЕРВАЛЫ МЕЖДУ НАЖАТИЯМИ КЛАВИШ ПРИ ВВОДЕ ФРАЗЫ.
    ПРИ АВТОРИЗАЦИИ СРАВНИВАЮТСЯ IDEAL И DEV С ТОЧНОСТЬЮ EPS={EPS} МС.
  </div>
</div>"""
    return page("ВХОД — КЛАВИАТУРНЫЙ ПОЧЕРК", content, login=True)


# ══════════════════════════════════════════════
#  НАЧАЛО АВТОРИЗАЦИИ — показываем фразу
# ══════════════════════════════════════════════
@app.route('/start_auth', methods=['POST'])
def start_auth():
    username = request.form.get('username', '').strip()
    users = load_users()
    if username not in users:
        return redirect('/?err=БОЕЦ+НЕ+НАЙДЕН')
    session['auth_user'] = username
    phrase = users[username]['phrase']
    session['auth_phrase'] = phrase
    return redirect('/auth')

@app.route('/auth')
def auth():
    if 'auth_user' not in session:
        return redirect('/')
    username = session['auth_user']
    phrase   = session['auth_phrase']
    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>АВТОРИЗАЦИЯ: <span>{username.upper()}</span></h1>
    <p>ВВЕДИ ФРАЗУ В ТОЧНОСТИ КАК ПОКАЗАНО НИЖЕ. СИСТЕМА ИЗМЕРИТ ТВОЙ КЛАВИАТУРНЫЙ ПОЧЕРК.</p>
  </div>
  <div class="phrase-box">
    <div class="phrase-label">// ТВОЯ ФРАЗА ДЛЯ ВВОДА</div>
    <div class="phrase-text" id="phrase-text">{phrase.upper()}</div>
  </div>
  <div class="info-blue">
    <strong>⚡ КАК ЭТО РАБОТАЕТ:</strong> JAVASCRIPT ФИКСИРУЕТ ВРЕМЯ МЕЖДУ КАЖДЫМ НАЖАТИЕМ КЛАВИШИ (МС).
    ПОСЛЕ ВВОДА ВЫЧИСЛЯЕТСЯ ИДЕАЛЬНОЕ ЗНАЧЕНИЕ И ОТКЛОНЕНИЕ, КОТОРЫЕ СРАВНИВАЮТСЯ
    С ТВОИМ ПРОФИЛЕМ. ТОЧНОСТЬ: EPS = {EPS} МС.
  </div>
  <div class="card">
    <div class="sec">// ВВОД ФРАЗЫ</div>
    <div class="fgroup">
      <div class="flabel">НАБИРАЙ ФРАЗУ — СИСТЕМА АВТОМАТИЧЕСКИ АНАЛИЗИРУЕТ ВВОД</div>
      <input type="text" id="auth-input" autocomplete="off" spellcheck="false"
             placeholder="НАЧНИ НАБИРАТЬ ФРАЗУ..." style="font-size:16px;letter-spacing:1px">
    </div>
    <div id="timing-info" style="font-size:12px;color:var(--muted);margin-bottom:14px;display:none">
      ⚡ ЗАПИСАНО ИНТЕРВАЛОВ: <span id="interval-count">0</span>
    </div>
    <button class="btn btn-g" onclick="submitAuth()" id="auth-btn" disabled>→ ПОДТВЕРДИТЬ</button>
    <a href="/" style="margin-left:12px"><button class="btn btn-o" type="button">ОТМЕНА</button></a>
    <div id="result" class="result"></div>
  </div>
</div>

<script>
const phrase = {json.dumps(phrase)};
const intervals = [];
let lastTime = null;
let correct = false;

const inp = document.getElementById('auth-input');
const btn = document.getElementById('auth-btn');
const info = document.getElementById('timing-info');
const cnt  = document.getElementById('interval-count');

inp.addEventListener('keydown', function(e) {{
  const now = performance.now();
  if (lastTime !== null) {{
    intervals.push(Math.round(now - lastTime));
    cnt.textContent = intervals.length;
    info.style.display = 'block';
  }}
  lastTime = now;
}});

inp.addEventListener('input', function() {{
  const val = inp.value;
  const ok  = val === phrase;
  correct = ok;
  inp.style.borderColor = ok ? 'var(--g)' : (val.length > 0 ? 'var(--border)' : 'var(--border)');
  btn.disabled = !ok;
  if(ok) btn.style.opacity = '1';
}});

function submitAuth() {{
  if (!correct) return;
  const b = document.getElementById('result');
  b.style.display = 'none';

  fetch('/api/auth', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{
      username: {json.dumps(username)},
      intervals: intervals,
      phrase: inp.value
    }})
  }}).then(r => r.json()).then(d => {{
    b.className = 'result ' + (d.success ? 'ok' : 'err');
    b.innerHTML = (d.success ? '⚡ ' : '💀 ') + '<strong>' + d.message + '</strong>' +
      (d.explanation ? '<div class="expl">' + d.explanation + '</div>' : '');
    b.style.display = 'block';
    if (d.success) setTimeout(() => window.location.href = '/dashboard', 1800);
  }});
}}

inp.focus();

// Блокировка при бездействии
let lockTimer;
const LOCK_SEC = {LOCK_TIMEOUT};
const authOverlay = document.getElementById('lock-overlay');

function resetLock() {{
  clearTimeout(lockTimer);
  lockTimer = setTimeout(function() {{ authOverlay.style.display = 'flex'; }}, LOCK_SEC * 1000);
}}
document.addEventListener('mousemove', resetLock);
document.addEventListener('keydown',   resetLock);
document.addEventListener('click',     resetLock);
resetLock();

document.getElementById('lock-unlock-btn').addEventListener('click', function() {{
  authOverlay.style.display = 'none';
  inp.value    = '';
  intervals    = [];
  lastTime     = null;
  correct      = false;
  btn.disabled = true;
  inp.style.borderColor = '';
  inp.focus();
  resetLock();
}});
</script>

<div id="lock-overlay" style="display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(10,10,12,.98);flex-direction:column;align-items:center;
  justify-content:center;gap:24px;">
  <div style="font-size:100px">🔒</div>
  <div style="font-family:'Bebas Neue',sans-serif;font-size:48px;font-weight:700;letter-spacing:6px;color:var(--o);text-transform:uppercase">СЕАНС ЗАБЛОКИРОВАН</div>
  <div style="font-size:16px;color:var(--muted);text-align:center;line-height:1.9;letter-spacing:2px;text-transform:uppercase;font-weight:600">
    БЕЗДЕЙСТВИЕ БОЛЕЕ {LOCK_TIMEOUT} СЕКУНД<br>ВВЕДИ ФРАЗУ ЗАНОВО ДЛЯ РАЗБЛОКИРОВКИ
  </div>
  <button id="lock-unlock-btn"
    style="margin-top:12px;padding:16px 36px;background:var(--g);color:#022c22;
           border:none;border-bottom:4px solid #047857;font-family:'Bebas Neue',sans-serif;
           font-size:20px;font-weight:700;letter-spacing:4px;cursor:pointer;text-transform:uppercase">
    ⚡ РАЗБЛОКИРОВАТЬ
  </button>
</div>"""
    return page(f"АВТОРИЗАЦИЯ — {username.upper()}", content)


@app.route('/api/auth', methods=['POST'])
def api_auth():
    data = request.get_json()
    username  = data.get('username', '')
    intervals = data.get('intervals', [])
    phrase_in = data.get('phrase', '')

    users = load_users()
    if username not in users:
        return jsonify({'success': False, 'message': 'БОЕЦ НЕ НАЙДЕН'})

    stored = users[username]

    if phrase_in != stored['phrase']:
        return jsonify({'success': False, 'message': 'ФРАЗА ВВЕДЕНА НЕВЕРНО'})

    if len(intervals) < 3:
        return jsonify({'success': False, 'message': 'НЕДОСТАТОЧНО ДАННЫХ О ВВОДЕ'})

    ideal_cur, dev_cur = compute_single_stats(intervals)
    ideal_stored = stored['ideal']
    dev_stored   = stored['deviation']

    diff_ideal = abs(ideal_cur - ideal_stored)
    diff_dev   = abs(dev_cur   - dev_stored)

    ok_ideal = diff_ideal < EPS
    ok_dev   = diff_dev   < EPS
    success  = ok_ideal and ok_dev

    if success:
        session['username'] = username
        session['last_active'] = time.time()

    expl = (
        f"ЭТАЛОН: IDEAL={ideal_stored} МС, DEV={dev_stored} МС &nbsp;|&nbsp; "
        f"ТЕКУЩИЙ: IDEAL={ideal_cur} МС, DEV={dev_cur} МС<br>"
        f"ΔIDEAL={diff_ideal:.1f} МС {'&lt;' if ok_ideal else '&ge;'} EPS={EPS} → {'⚡' if ok_ideal else '💀'} &nbsp;|&nbsp; "
        f"ΔDEV={diff_dev:.1f} МС {'&lt;' if ok_dev else '&ge;'} EPS={EPS} → {'⚡' if ok_dev else '💀'}"
    )

    msg = '⚡ АВТОРИЗАЦИЯ УСПЕШНА! ДОБРО ПОЖАЛОВАТЬ.' if success else '💀 КЛАВИАТУРНЫЙ ПОЧЕРК НЕ СОВПАДАЕТ. ПОПРОБУЙ ЕЩЁ РАЗ.'
    return jsonify({'success': success, 'message': msg, 'explanation': expl})


# ══════════════════════════════════════════════
#  РЕГИСТРАЦИЯ
# ══════════════════════════════════════════════
@app.route('/register')
def register():
    phrase = get_random_phrase()
    session['reg_phrase'] = phrase
    session['reg_attempts'] = []

    dots = "".join(
        f'<div class="att-dot {"active" if i == 0 else ""}" id="dot-{i}">{i+1}</div>'
        for i in range(MIN_ATTEMPTS)
    )

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>РЕГИСТРАЦИЯ <span>НОВОГО БОЙЦА</span></h1>
    <p>ВВЕДИ ИМЯ ПОЛЬЗОВАТЕЛЯ И ФРАЗУ {MIN_ATTEMPTS} РАЗА. СИСТЕМА СОЗДАСТ ТВОЙ ПРОФИЛЬ КЛАВИАТУРНОГО ПОЧЕРКА.</p>
  </div>

  <div class="card" id="step-name">
    <div class="sec">// ШАГ 1 — ИМЯ БОЙЦА</div>
    <div class="fgroup">
      <div class="flabel">ИДЕНТИФИКАТОР</div>
      <input type="text" id="username-input" placeholder="ВВЕДИ ИМЯ (ЛАТИНИЦА, БЕЗ ПРОБЕЛОВ)"
             autocomplete="off" maxlength="32" style="text-transform:uppercase">
    </div>
    <button class="btn btn-p" onclick="startReg()">→ ДАЛЕЕ</button>
    <div id="name-err" style="display:none;margin-top:12px;font-size:14px;color:var(--o);font-weight:600"></div>
  </div>

  <div class="card" id="step-typing" style="display:none">
    <div class="sec">// ШАГ 2 — ВВОД ФРАЗЫ</div>
    <div class="phrase-box">
      <div class="phrase-label">⚡ ЗАПОМНИ И ВВОДИ ЭТУ ФРАЗУ</div>
      <div class="phrase-text">{phrase.upper()}</div>
    </div>
    <div class="info-warn">
      ⚠ ВВОДИ ФРАЗУ <strong>В ТОЧНОСТИ КАК ПОКАЗАНО</strong> (РЕГИСТР, ЗНАКИ, ЦИФРЫ).
      ТРЕБУЕТСЯ {MIN_ATTEMPTS} ПОПЫТКИ ДЛЯ СОЗДАНИЯ ПРОФИЛЯ.
    </div>
    <div class="attempts-bar" id="dots-bar">{dots}</div>
    <div class="fgroup">
      <div class="flabel" id="attempt-label">ПОПЫТКА 1 ИЗ {MIN_ATTEMPTS}</div>
      <input type="text" id="reg-input" autocomplete="off" spellcheck="false"
             placeholder="НАЧНИ НАБИРАТЬ ФРАЗУ..." style="font-size:15px;letter-spacing:1px;text-transform:uppercase">
    </div>
    <button class="btn btn-g" onclick="submitAttempt()" id="reg-btn" disabled>→ ЗАПИСАТЬ ПОПЫТКУ</button>
    <div id="reg-result" class="result"></div>
  </div>
</div>

<script>
const phrase    = {json.dumps(phrase)};
const minAttempts = {MIN_ATTEMPTS};
let attempt     = 0;
let intervals   = [];
let lastTime    = null;
let allIntervals= [];
let username    = '';

function startReg() {{
  const val = document.getElementById('username-input').value.trim();
  const err = document.getElementById('name-err');
  if (!val || val.length < 2) {{ err.textContent='ИМЯ СЛИШКОМ КОРОТКОЕ'; err.style.display='block'; return; }}
  if (!/^[a-zA-Z0-9_]+$/.test(val)) {{ err.textContent='ТОЛЬКО ЛАТИНИЦА, ЦИФРЫ И _'; err.style.display='block'; return; }}
  err.style.display = 'none';

  fetch('/api/check_user', {{method:'POST',headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username: val}})}}).then(r=>r.json()).then(d=>{{
    if(d.exists){{ err.textContent='БОЕЦ УЖЕ СУЩЕСТВУЕТ'; err.style.display='block'; return; }}
    username = val;
    document.getElementById('step-name').style.display='none';
    document.getElementById('step-typing').style.display='block';
    document.getElementById('reg-input').focus();
  }});
}}

const inp = document.getElementById('reg-input');
const btn = document.getElementById('reg-btn');

inp.addEventListener('keydown', function(e) {{
  const now = performance.now();
  if (lastTime !== null) intervals.push(Math.round(now - lastTime));
  lastTime = now;
}});
inp.addEventListener('input', function() {{
  btn.disabled = inp.value !== phrase;
}});

function submitAttempt() {{
  if (inp.value !== phrase) return;
  allIntervals.push([...intervals]);

  const dot = document.getElementById('dot-' + attempt);
  if(dot) {{ dot.classList.remove('active'); dot.classList.add('done'); dot.textContent='✓'; }}
  attempt++;

  if (attempt < minAttempts) {{
    const next = document.getElementById('dot-' + attempt);
    if(next) next.classList.add('active');
    document.getElementById('attempt-label').textContent = 'ПОПЫТКА ' + (attempt+1) + ' ИЗ ' + minAttempts;
    inp.value = '';
    intervals = [];
    lastTime  = null;
    btn.disabled = true;
    inp.focus();
    const b = document.getElementById('reg-result');
    b.className = 'result ok';
    b.innerHTML = '⚡ ПОПЫТКА ' + attempt + ' ЗАПИСАНА. ПРОДОЛЖАЙ.';
    b.style.display = 'block';
  }} else {{
    fetch('/api/register', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{username, phrase, all_intervals: allIntervals}})
    }}).then(r=>r.json()).then(d=>{{
      const b = document.getElementById('reg-result');
      b.className = 'result ' + (d.success ? 'ok' : 'err');
      b.innerHTML = (d.success?'⚡ ':'💀 ') + '<strong>' + d.message + '</strong>' +
        (d.explanation ? '<div class="expl">' + d.explanation + '</div>' : '');
      b.style.display = 'block';
      btn.disabled = true;
      if(d.success) setTimeout(()=>window.location.href='/', 2500);
    }});
  }}
}}

inp.addEventListener('keypress', e => {{ if(e.key==='Enter') submitAttempt(); }});
document.getElementById('username-input').addEventListener('keypress', e => {{ if(e.key==='Enter') startReg(); }});
</script>"""
    return page("РЕГИСТРАЦИЯ — КЛАВИАТУРНЫЙ ПОЧЕРК", content)


@app.route('/api/check_user', methods=['POST'])
def api_check_user():
    data = request.get_json()
    users = load_users()
    return jsonify({'exists': data.get('username', '') in users})


@app.route('/api/register', methods=['POST'])
def api_register():
    data         = request.get_json()
    username     = data.get('username', '').strip()
    phrase       = data.get('phrase', '')
    all_intervals= data.get('all_intervals', [])

    if not username or not phrase:
        return jsonify({'success': False, 'message': 'НЕКОРРЕКТНЫЕ ДАННЫЕ'})

    valid = [lst for lst in all_intervals if len(lst) >= 2]
    if len(valid) < MIN_ATTEMPTS:
        return jsonify({'success': False, 'message': f'НУЖНО {MIN_ATTEMPTS} КОРРЕКТНЫХ ПОПЫТКИ'})

    ideal, deviation = compute_stats(valid)

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'message': 'БОЕЦ УЖЕ СУЩЕСТВУЕТ'})

    users[username] = {
        'phrase':    phrase,
        'ideal':     ideal,
        'deviation': deviation,
        'registered': time.strftime('%Y-%m-%d %H:%M')
    }
    save_users(users)

    expl = (
        f"⚡ ПРОФИЛЬ СОЗДАН НА ОСНОВЕ {len(valid)} ПОПЫТОК.<br>"
        f"ИДЕАЛЬНОЕ ЗНАЧЕНИЕ (IDEAL): <strong>{ideal} МС</strong> — СРЕДНЕЕ ВРЕМЯ МЕЖДУ НАЖАТИЯМИ.<br>"
        f"ОТКЛОНЕНИЕ (DEV): <strong>{deviation} МС</strong> — СТАБИЛЬНОСТЬ РИТМА НАБОРА.<br>"
        f"ПРИ АВТОРИЗАЦИИ ОБА ПОКАЗАТЕЛЯ ДОЛЖНЫ СОВПАСТЬ С ТОЧНОСТЬЮ EPS = {EPS} МС."
    )
    return jsonify({'success': True, 'message': f'⚡ БОЕЦ {username.upper()} УСПЕШНО ЗАРЕГИСТРИРОВАН!', 'explanation': expl})


# ══════════════════════════════════════════════
#  DASHBOARD (после успешной авторизации)
# ══════════════════════════════════════════════
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    users = load_users()
    if username not in users:
        return redirect('/')

    u = users[username]
    session['last_active'] = time.time()

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>⚡ ДОБРО ПОЖАЛОВАТЬ, <span>{username.upper()}</span></h1>
    <p>АВТОРИЗАЦИЯ ПО КЛАВИАТУРНОМУ ПОЧЕРКУ ПРОШЛА УСПЕШНО. ДОСТУП РАЗРЕШЁН.</p>
  </div>

  <div class="info-blue">
    <strong>⚡ СИСТЕМА ЗАЩИТЫ АКТИВНА.</strong> ПРИ БЕЗДЕЙСТВИИ БОЛЕЕ {LOCK_TIMEOUT} СЕКУНД
    СЕССИЯ БУДЕТ ЗАБЛОКИРОВАНА И ПОТРЕБУЕТСЯ ПОВТОРНАЯ АВТОРИЗАЦИЯ.
  </div>

  <div class="card">
    <div class="sec">// ТВОЙ ПРОФИЛЬ КЛАВИАТУРНОГО ПОЧЕРКА</div>
    <div class="stats-grid">
      <div class="stat-item">
        <div class="stat-val">{u['ideal']}</div>
        <div class="stat-lbl">IDEAL (МС)</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{u['deviation']}</div>
        <div class="stat-lbl">DEVIATION (МС)</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{EPS}</div>
        <div class="stat-lbl">ТОЧНОСТЬ EPS</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{u.get('registered', '—')}</div>
        <div class="stat-lbl">ДАТА РЕГИСТРАЦИИ</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="sec">// ТВОЯ ФРАЗА (ЭТАЛОН)</div>
    <div class="phrase-box">
      <div class="phrase-label">⚡ ФРАЗА ДЛЯ АВТОРИЗАЦИИ</div>
      <div class="phrase-text">{u['phrase'].upper()}</div>
    </div>
    <p style="font-size:12px;color:var(--muted);margin-top:12px;line-height:1.8;font-weight:500">
      ФРАЗА НАЗНАЧАЕТСЯ СИСТЕМОЙ СЛУЧАЙНЫМ ОБРАЗОМ ПРИ РЕГИСТРАЦИИ.
      ОНА ХРАНИТСЯ В ЗАШИФРОВАННОМ ФАЙЛЕ <code>USERS.DAT</code> (XOR + BASE64).
    </p>
  </div>

  <div class="card">
    <div class="sec">// ДЕЙСТВИЯ</div>
    <a href="/users"><button class="btn btn-p" style="margin-right:12px">👥 СПИСОК БОЙЦОВ</button></a>
    <a href="/register"><button class="btn" style="background:var(--border);color:var(--text);border-color:#3f3f46">⚡ ДОБАВИТЬ БОЙЦА</button></a>
    <a href="/logout" style="margin-left:12px"><button class="btn btn-o">🚪 ВЫХОД</button></a>
  </div>
</div>

<script>
let lockTimer;
const LOCK_SEC = {LOCK_TIMEOUT};
const overlay  = document.getElementById('lock-overlay');
const lockBtn  = document.getElementById('lock-confirm-btn');

function resetLock() {{
  clearTimeout(lockTimer);
  lockTimer = setTimeout(showLock, LOCK_SEC * 1000);
}}
function showLock() {{
  overlay.style.display = 'flex';
}}

lockBtn.addEventListener('click', function() {{
  window.location.assign('/lock_auth');
}});

document.addEventListener('mousemove', resetLock);
document.addEventListener('keydown',   resetLock);
document.addEventListener('click',     resetLock);
resetLock();
</script>

<div id="lock-overlay" style="display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(10,10,12,.98);flex-direction:column;align-items:center;
  justify-content:center;gap:24px;">
  <div style="font-size:100px">🔒</div>
  <div style="font-family:'Bebas Neue',sans-serif;font-size:48px;font-weight:700;letter-spacing:6px;color:var(--o);text-transform:uppercase">СЕССИЯ ЗАБЛОКИРОВАНА</div>
  <div style="font-size:16px;color:var(--muted);text-align:center;line-height:1.9;letter-spacing:2px;text-transform:uppercase;font-weight:600">
    БЕЗДЕЙСТВИЕ БОЛЕЕ {LOCK_TIMEOUT} СЕКУНД<br>ТРЕБУЕТСЯ ПОВТОРНОЕ ПОДТВЕРЖДЕНИЕ ЛИЧНОСТИ
  </div>
  <a href="/lock_auth" id="lock-confirm-btn"
     style="margin-top:12px;padding:16px 36px;background:var(--g);color:#022c22;
            border-bottom:4px solid #047857;font-family:'Bebas Neue',sans-serif;font-size:20px;
            font-weight:700;letter-spacing:4px;text-decoration:none;text-transform:uppercase">
    ⚡ ПОДТВЕРДИТЬ ЛИЧНОСТЬ
  </a>
</div>"""
    return page(f"РАБОЧИЙ СТОЛ — {username.upper()}", content)


# ══════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ ПОСЛЕ БЛОКИРОВКИ
# ══════════════════════════════════════════════
@app.route('/lock_auth')
def lock_auth():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    users = load_users()
    phrase = users[username]['phrase']
    session['auth_user']   = username
    session['auth_phrase'] = phrase
    return redirect('/auth')


# ══════════════════════════════════════════════
#  СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ══════════════════════════════════════════════
@app.route('/users')
def users_list():
    if 'username' not in session:
        return redirect('/')
    users = load_users()
    rows = ""
    for i, (uname, data) in enumerate(sorted(users.items()), 1):
        me = ' <span style="color:var(--g);font-size:12px;font-weight:800">⚡ ТЫ</span>' if uname == session.get('username') else ''
        rows += f"""<tr>
  <td style="color:var(--muted);font-weight:700">{i}</td>
  <td style="font-weight:700;text-transform:uppercase">{uname}{me}</td>
  <td style="color:var(--o);font-weight:600">{data['ideal']} МС</td>
  <td style="color:var(--p);font-weight:600">{data['deviation']} МС</td>
  <td style="color:var(--muted);font-size:12px;font-weight:500;text-transform:uppercase">{data['phrase'][:20]}…</td>
  <td style="color:var(--muted);font-size:12px;font-weight:500">{data.get('registered','—')}</td>
</tr>"""

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>ЗАРЕГИСТРИРОВАННЫЕ <span>БОЙЦЫ</span></h1>
    <p>ВСЕ ПОЛЬЗОВАТЕЛИ СИСТЕМЫ С ПРОФИЛЯМИ КЛАВИАТУРНОГО ПОЧЕРКА. ДАННЫЕ ХРАНЯТСЯ В <code>USERS.DAT</code>.</p>
  </div>
  <div class="info-blue">
    <strong>⚡ ФАЙЛ USERS.DAT</strong> — ЗАШИФРОВАН МЕТОДОМ XOR (КЛЮЧ 0X5A) + BASE64.
    ФРАЗЫ ХРАНЯТСЯ В <strong>PHRASES.DAT</strong> (ТОТ ЖЕ МЕТОД). ПРЯМОЕ ЧТЕНИЕ ФАЙЛОВ НЕВОЗМОЖНО БЕЗ КЛЮЧА.
  </div>
  <div class="card" style="overflow:auto">
    <div class="sec">// ПРОФИЛИ БОЙЦОВ ({len(users)} ЧЕЛ.)</div>
    <table class="utbl">
      <thead><tr>
        <th>№</th><th>БОЕЦ</th><th>IDEAL (МС)</th>
        <th>DEV (МС)</th><th>ФРАЗА</th><th>ДАТА РЕГ.</th>
      </tr></thead>
      <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px;font-weight:600">НЕТ БОЙЦОВ</td></tr>'}</tbody>
    </table>
  </div>
  <div style="margin-top:16px">
    <a href="/dashboard"><button class="btn btn-g">← НА ГЛАВНУЮ</button></a>
    <a href="/register" style="margin-left:12px"><button class="btn btn-p">⚡ ДОБАВИТЬ</button></a>
  </div>
</div>"""
    return page("БОЙЦЫ — КП", content)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ══════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════
if __name__ == '__main__':
    load_phrases()
    print(f"\n{'='*50}")
    print(f"  ЛР №5 — КЛАВИАТУРНЫЙ ПОЧЕРК")
    print(f"  ФАЙЛЫ: USERS.DAT, PHRASES.DAT (XOR+BASE64)")
    print(f"  EPS = {EPS} МС  |  БЛОКИРОВКА: {LOCK_TIMEOUT} СЕК")
    print(f"  http://127.0.0.1:5000")
    print(f"{'='*50}\n")
    app.run(debug=True)