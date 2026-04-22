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
    # Медиана устойчива к выбросам (случайная задержка, отвлёкся на секунду)
    ideal     = statistics.median(flat)
    deviation = sum(abs(v - ideal) for v in flat) / len(flat)
    return round(ideal, 1), round(deviation, 1)

def compute_single_stats(intervals: list) -> tuple:
    """Для одной попытки авторизации."""
    return compute_stats([intervals])

# ══════════════════════════════════════════════
#  ОБЩИЙ CSS (РОЗОВО-ФУКСИЕВАЯ ТЕМА + ЖЕНСТВЕННЫЙ ШРИФТ)
# ══════════════════════════════════════════════
BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#fff5f8; --card:#ffffff; --border:#fbcfe8;
  --text:#831843; --muted:#be185d;
  --r:#ec4899; --g:#d946ef; --b:#c026d3; --warn:#f43f5e;
  --accent-light:#fdf2f8;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Quicksand',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;
  background:
    radial-gradient(ellipse 60% 40% at 10% 0%,  rgba(236,72,153,.12) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 90% 100%, rgba(192,38,211,.10) 0%,transparent 60%),
    radial-gradient(ellipse 40% 30% at 50%  50%, rgba(217,70,239,.08) 0%,transparent 70%);
}
nav{position:sticky;top:0;z-index:99;background:rgba(255,255,255,.95);border-bottom:2px solid var(--border);
    backdrop-filter:blur(14px);padding:13px 28px;display:flex;align-items:center;justify-content:space-between;
    box-shadow:0 4px 12px rgba(236,72,153,.08);}
.brand{font-family:'Poppins',sans-serif;font-size:14px;font-weight:700;
  background:linear-gradient(135deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.nav-links{display:flex;gap:6px}
.nl{padding:6px 14px;font-size:12px;font-weight:500;letter-spacing:0.5px;text-transform:none;
  color:var(--muted);text-decoration:none;border:1px solid transparent;border-radius:30px;transition:.2s;
  font-family:'Poppins',sans-serif;}
.nl:hover{color:var(--r);border-color:var(--border);background:var(--accent-light)}
.nl.red:hover{color:#e11d48;border-color:rgba(236,72,153,.3)}
.chip{display:flex;align-items:center;gap:8px;background:linear-gradient(135deg,#fdf2f8,#fce7f3);border:1px solid var(--border);
  border-radius:40px;padding:6px 16px;font-size:13px;font-weight:500;box-shadow:0 2px 8px rgba(236,72,153,.06)}
.dot{width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,var(--r),var(--g));animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.wrap{max-width:860px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;margin-bottom:16px;
  box-shadow:0 6px 20px rgba(236,72,153,.04)}
.grad-rgb{background:linear-gradient(135deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.ph{margin-bottom:24px}
.ph h1{font-family:'Poppins',sans-serif;font-size:22px;font-weight:700}
.ph h1 span{color:var(--g)}
.ph p{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.8}
.info-blue{background:linear-gradient(135deg,#fdf2f8,#fce7f3);border:1px solid var(--border);border-radius:16px;
  padding:16px 20px;font-size:13px;line-height:1.9;color:var(--text);margin-bottom:18px}
.info-blue strong{color:var(--r)}
.info-warn{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border:1px solid #fecdd3;border-radius:16px;
  padding:16px 20px;font-size:13px;line-height:1.9;color:#be123c;margin-bottom:18px}
.btn{padding:11px 24px;border:none;border-radius:40px;font-family:'Poppins',sans-serif;
  font-size:13px;font-weight:600;letter-spacing:0.5px;text-transform:none;cursor:pointer;transition:.25s}
.btn-g{background:linear-gradient(135deg,var(--g),#c084fc);color:#fff}
.btn-g:hover{background:linear-gradient(135deg,#c084fc,var(--g));box-shadow:0 8px 20px rgba(217,70,239,.25);transform:translateY(-2px)}
.btn-r{background:linear-gradient(135deg,var(--r),#f472b6);color:#fff}
.btn-r:hover{background:linear-gradient(135deg,#f472b6,var(--r));box-shadow:0 8px 20px rgba(236,72,153,.25)}
.btn-b{background:linear-gradient(135deg,var(--b),#a855f7);color:#fff}
.btn-b:hover{background:linear-gradient(135deg,#a855f7,var(--b));box-shadow:0 8px 20px rgba(192,38,211,.25)}
select,input[type=text],input[type=password],input[type=number]{
  padding:11px 16px;background:#fff;border:1.5px solid var(--border);
  border-radius:30px;color:var(--text);font-family:'Quicksand',sans-serif;font-size:14px;transition:.2s;width:100%}
select:focus,input:focus{outline:none;border-color:var(--r);box-shadow:0 0 0 4px rgba(236,72,153,.08)}
select option{background:#fff}
.fgroup{display:flex;flex-direction:column;gap:8px;margin-bottom:16px}
.flabel{font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;color:var(--muted);font-family:'Poppins',sans-serif}
.result{display:none;margin-top:16px;padding:16px;border-radius:16px;font-size:14px;line-height:1.9}
.result.ok{background:linear-gradient(135deg,#fdf2f8,#f5d0fe);border:1px solid #f0abfc;color:#a21caf}
.result.err{background:linear-gradient(135deg,#fff1f2,#ffe4e6);border:1px solid #fda4af;color:#be123c}
.result .expl{margin-top:10px;padding-top:10px;border-top:1px solid rgba(236,72,153,.1);
  font-size:12px;color:var(--muted);line-height:1.9}
/* PHRASE DISPLAY */
.phrase-box{background:linear-gradient(135deg,#fdf2f8,#fce7f3);border:1px solid var(--border);border-radius:16px;
  padding:18px 22px;margin-bottom:18px;text-align:center}
.phrase-text{font-size:20px;font-weight:700;color:#be123c;letter-spacing:1px;
  font-family:'Quicksand',sans-serif;word-break:break-all}
.phrase-label{font-size:11px;font-weight:600;color:var(--muted);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px;font-family:'Poppins',sans-serif}
/* PROGRESS */
.attempts-bar{display:flex;gap:8px;margin-bottom:18px}
.att-dot{width:32px;height:32px;border-radius:50%;background:#fce7f3;border:2px solid var(--border);
  display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:var(--muted);transition:.3s}
.att-dot.done{background:linear-gradient(135deg,#f5d0fe,#e879f9);border-color:var(--g);color:#fff}
.att-dot.active{background:linear-gradient(135deg,#fbcfe8,#f9a8d4);border-color:var(--r);color:#be185d;animation:pulse2 1s infinite}
@keyframes pulse2{0%,100%{box-shadow:0 0 0 0 rgba(236,72,153,.3)}50%{box-shadow:0 0 0 8px rgba(236,72,153,0)}}
/* STATS TABLE */
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.stat-item{background:linear-gradient(135deg,#fdf2f8,#fff);border:1px solid var(--border);border-radius:16px;padding:14px;text-align:center}
.stat-val{font-family:'Poppins',sans-serif;font-size:26px;font-weight:700;background:linear-gradient(135deg,var(--r),var(--g));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-lbl{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:0.5px;text-transform:uppercase;margin-top:6px;font-family:'Poppins',sans-serif}
/* LOCK OVERLAY */
#lock-overlay{
  display:none;position:fixed;inset:0;z-index:999;
  background:rgba(255,245,248,.98);
  flex-direction:column;align-items:center;justify-content:center;gap:20px;
  backdrop-filter:blur(12px);
}
#lock-overlay.show{display:flex}
.lock-icon{font-size:72px}
.lock-title{font-family:'Poppins',sans-serif;font-size:24px;font-weight:700;color:var(--r)}
.lock-sub{font-size:14px;color:var(--muted)}
/* USERS TABLE */
.utbl{width:100%;border-collapse:collapse;font-size:13px}
.utbl th,.utbl td{padding:12px 14px;border-bottom:1px solid var(--border);text-align:left}
.utbl th{color:var(--muted);font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;font-family:'Poppins',sans-serif}
.utbl tr:last-child td{border-bottom:none}
.utbl tr:hover td{background:linear-gradient(135deg,#fdf2f8,#fce7f3)}
/* LOGIN BODY */
.login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
.lw{width:500px;position:relative;z-index:1}
.badge{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,#fdf2f8,#fce7f3);
  border:1px solid var(--border);border-radius:40px;padding:6px 16px;font-size:11px;font-weight:600;
  color:var(--r);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:20px;font-family:'Poppins',sans-serif}
.badge::before{content:'✨';font-size:12px}
.lh1{font-family:'Poppins',sans-serif;font-size:28px;font-weight:700;line-height:1.3;margin-bottom:10px}
.lsub{font-size:13px;color:var(--muted);margin-bottom:28px;line-height:1.8}
.lsub span{color:var(--warn);font-weight:600}
.err-box{display:flex;align-items:center;gap:10px;background:linear-gradient(135deg,#fff1f2,#ffe4e6);
  border:1px solid #fda4af;border-radius:40px;padding:14px 18px;
  font-size:14px;color:#be123c;margin-bottom:18px}
.sec{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:10px;margin-bottom:14px;font-family:'Poppins',sans-serif}
.sec::after{content:'';flex:1;height:1.5px;background:linear-gradient(90deg,var(--border),transparent)}
code{background:var(--accent-light);padding:2px 8px;border-radius:20px;font-size:12px;color:var(--r)}
</style>"""

def nav_html():
    user = session.get('username', '')
    chip = f'<div class="chip"><div class="dot"></div>✨ {user}</div>' if user else ''
    links = [
        ("/dashboard", "Главная", ""),
        ("/register", "Регистрация", ""),
        ("/users", "Пользователи", ""),
        ("/logout", "Выход", "red"),
    ]
    lhtml = "".join(f'<a href="{h}" class="nl {c}">{l}</a>' for h,l,c in links)
    return f"""<nav>
  <div class="brand">💗 КП · Клавиатурный почерк</div>
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
        opts = '<option value="">— нет зарегистрированных пользователей —</option>'
    else:
        opts = '<option value="">— выберите пользователя —</option>'
        for uname in sorted(users.keys()):
            opts += f'<option value="{uname}">{uname}</option>'

    content = f"""
<div class="lw">
  <div class="badge">💗 Клавиатурный почерк</div>
  <div class="lh1 grad-rgb">Защита от НСД<br>по динамике набора</div>
  <p class="lsub">Практическое занятие №5 · <span>Защита информации</span><br>
  Идентификация пользователя по скорости ввода</p>
  {err}
  <div class="card">
    <div class="flabel" style="margin-bottom:12px">✨ Выберите пользователя</div>
    <form method="POST" action="/start_auth">
      <select name="username" required style="margin-bottom:14px">{opts}</select>
      <button type="submit" class="btn btn-g" style="width:100%">→ Войти</button>
    </form>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px">
    <a href="/register" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:16px">
        <div style="color:var(--b);font-size:13px;font-weight:600;letter-spacing:0.5px">✨ РЕГИСТРАЦИЯ</div>
        <div style="font-size:12px;color:var(--muted);margin-top:6px">Новый пользователь</div>
      </div>
    </a>
    <a href="/users" style="text-decoration:none">
      <div class="card" style="text-align:center;cursor:pointer;padding:16px">
        <div style="color:var(--warn);font-size:13px;font-weight:600;letter-spacing:0.5px">👥 ПОЛЬЗОВАТЕЛИ</div>
        <div style="font-size:12px;color:var(--muted);margin-top:6px">Список: {len(users)} чел.</div>
      </div>
    </a>
  </div>
  <div class="info-blue" style="margin-top:14px">
    💗 <strong>Метод:</strong> система измеряет интервалы между нажатиями клавиш при вводе фразы.
    При авторизации сравниваются среднее (ideal) и отклонение (dev) с точностью EPS={EPS} мс.
  </div>
</div>"""
    return page("Вход — Клавиатурный почерк", content, login=True)


# ══════════════════════════════════════════════
#  НАЧАЛО АВТОРИЗАЦИИ — показываем фразу
# ══════════════════════════════════════════════
@app.route('/start_auth', methods=['POST'])
def start_auth():
    username = request.form.get('username', '').strip()
    users = load_users()
    if username not in users:
        return redirect('/?err=Пользователь+не+найден')
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
    <h1>✨ Авторизация: <span>{username}</span></h1>
    <p>Введите фразу в точности как показано ниже. Система измерит ваш клавиатурный почерк.</p>
  </div>
  <div class="phrase-box">
    <div class="phrase-label">💗 Ваша фраза для ввода</div>
    <div class="phrase-text" id="phrase-text">{phrase}</div>
  </div>
  <div class="info-blue">
    <strong>✨ Как это работает:</strong> JavaScript фиксирует время между каждым нажатием клавиши (мс).
    После ввода вычисляется идеальное значение и отклонение, которые сравниваются
    с вашим профилем. Точность: EPS = {EPS} мс.
  </div>
  <div class="card">
    <div class="sec">✨ Введите фразу</div>
    <div class="fgroup">
      <div class="flabel">Набирайте фразу — система автоматически анализирует ввод</div>
      <input type="text" id="auth-input" autocomplete="off" spellcheck="false"
             placeholder="Начните набирать фразу..." style="font-size:16px;letter-spacing:0.5px">
    </div>
    <div id="timing-info" style="font-size:12px;color:var(--muted);margin-bottom:14px;display:none">
      ✨ Записано интервалов: <span id="interval-count">0</span>
    </div>
    <button class="btn btn-g" onclick="submitAuth()" id="auth-btn" disabled>→ Подтвердить</button>
    <a href="/" style="margin-left:12px"><button class="btn btn-r" type="button">Отмена</button></a>
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
  inp.style.borderColor = ok ? 'var(--r)' : (val.length > 0 ? 'var(--border)' : 'var(--border)');
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
    b.innerHTML = (d.success ? '✨ ' : '💔 ') + '<strong>' + d.message + '</strong>' +
      (d.explanation ? '<div class="expl">' + d.explanation + '</div>' : '');
    b.style.display = 'block';
    if (d.success) setTimeout(() => window.location.href = '/dashboard', 1800);
  }});
}}

inp.focus();

// Блокировка при бездействии — на странице авторизации оверлей скрывается кнопкой
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
  background:rgba(255,245,248,.98);flex-direction:column;align-items:center;
  justify-content:center;gap:18px;">
  <div style="font-size:80px">🔒</div>
  <div style="font-family:'Poppins',sans-serif;font-size:26px;font-weight:700;color:var(--r)">Сеанс заблокирован</div>
  <div style="font-size:14px;color:var(--muted);text-align:center;line-height:1.9">
    Бездействие более {LOCK_TIMEOUT} секунд<br>Введите фразу заново для разблокировки
  </div>
  <button id="lock-unlock-btn"
    style="margin-top:10px;padding:14px 32px;background:linear-gradient(135deg,var(--g),#c084fc);color:#fff;
           border:none;border-radius:40px;font-family:'Poppins',sans-serif;
           font-size:14px;font-weight:600;letter-spacing:0.5px;cursor:pointer">
    ✨ Разблокировать
  </button>
</div>"""
    return page(f"Авторизация — {username}", content)


@app.route('/api/auth', methods=['POST'])
def api_auth():
    data = request.get_json()
    username  = data.get('username', '')
    intervals = data.get('intervals', [])
    phrase_in = data.get('phrase', '')

    users = load_users()
    if username not in users:
        return jsonify({'success': False, 'message': 'Пользователь не найден'})

    stored = users[username]

    # Проверка правильности ввода фразы
    if phrase_in != stored['phrase']:
        return jsonify({'success': False, 'message': 'Фраза введена неверно'})

    if len(intervals) < 3:
        return jsonify({'success': False, 'message': 'Недостаточно данных о вводе'})

    # Вычисляем характеристики текущего ввода
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
        f"Эталон: ideal={ideal_stored} мс, dev={dev_stored} мс &nbsp;|&nbsp; "
        f"Текущий: ideal={ideal_cur} мс, dev={dev_cur} мс<br>"
        f"Δideal={diff_ideal:.1f} мс {'&lt;' if ok_ideal else '&ge;'} EPS={EPS} → {'✨' if ok_ideal else '💔'} &nbsp;|&nbsp; "
        f"Δdev={diff_dev:.1f} мс {'&lt;' if ok_dev else '&ge;'} EPS={EPS} → {'✨' if ok_dev else '💔'}"
    )

    msg = '✨ Авторизация успешна! Добро пожаловать.' if success else '💔 Клавиатурный почерк не совпадает. Попробуйте ещё раз.'
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
    <h1>✨ Регистрация <span>нового пользователя</span></h1>
    <p>Введите имя пользователя и фразу {MIN_ATTEMPTS} раза. Система создаст ваш профиль клавиатурного почерка.</p>
  </div>

  <div class="card" id="step-name">
    <div class="sec">✨ Шаг 1 — Имя пользователя</div>
    <div class="fgroup">
      <div class="flabel">Идентификатор</div>
      <input type="text" id="username-input" placeholder="Введите имя (латиница, без пробелов)"
             autocomplete="off" maxlength="32">
    </div>
    <button class="btn btn-b" onclick="startReg()">→ Далее</button>
    <div id="name-err" style="display:none;margin-top:12px;font-size:13px;color:var(--r)"></div>
  </div>

  <div class="card" id="step-typing" style="display:none">
    <div class="sec">✨ Шаг 2 — Ввод фразы</div>
    <div class="phrase-box">
      <div class="phrase-label">💗 Запомните и вводите эту фразу</div>
      <div class="phrase-text">{phrase}</div>
    </div>
    <div class="info-warn">
      ⚠ Вводите фразу <strong>в точности как показано</strong> (регистр, знаки, цифры).
      Требуется {MIN_ATTEMPTS} попытки для создания профиля.
    </div>
    <div class="attempts-bar" id="dots-bar">{dots}</div>
    <div class="fgroup">
      <div class="flabel" id="attempt-label">Попытка 1 из {MIN_ATTEMPTS}</div>
      <input type="text" id="reg-input" autocomplete="off" spellcheck="false"
             placeholder="Начните набирать фразу..." style="font-size:15px;letter-spacing:0.5px">
    </div>
    <button class="btn btn-g" onclick="submitAttempt()" id="reg-btn" disabled>→ Записать попытку</button>
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
  if (!val || val.length < 2) {{ err.textContent='Имя слишком короткое'; err.style.display='block'; return; }}
  if (!/^[a-zA-Z0-9_]+$/.test(val)) {{ err.textContent='Только латиница, цифры и _'; err.style.display='block'; return; }}
  err.style.display = 'none';

  fetch('/api/check_user', {{method:'POST',headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{username: val}})}}).then(r=>r.json()).then(d=>{{
    if(d.exists){{ err.textContent='Пользователь уже существует'; err.style.display='block'; return; }}
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

  // обновляем точки
  const dot = document.getElementById('dot-' + attempt);
  if(dot) {{ dot.classList.remove('active'); dot.classList.add('done'); dot.textContent='✓'; }}
  attempt++;

  if (attempt < minAttempts) {{
    const next = document.getElementById('dot-' + attempt);
    if(next) next.classList.add('active');
    document.getElementById('attempt-label').textContent = 'Попытка ' + (attempt+1) + ' из ' + minAttempts;
    inp.value = '';
    intervals = [];
    lastTime  = null;
    btn.disabled = true;
    inp.focus();
    const b = document.getElementById('reg-result');
    b.className = 'result ok';
    b.innerHTML = '✨ Попытка ' + attempt + ' записана. Продолжайте.';
    b.style.display = 'block';
  }} else {{
    // все попытки записаны — отправляем
    fetch('/api/register', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{username, phrase, all_intervals: allIntervals}})
    }}).then(r=>r.json()).then(d=>{{
      const b = document.getElementById('reg-result');
      b.className = 'result ' + (d.success ? 'ok' : 'err');
      b.innerHTML = (d.success?'✨ ':'💔 ') + '<strong>' + d.message + '</strong>' +
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
    return page("Регистрация — Клавиатурный почерк", content)


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
        return jsonify({'success': False, 'message': 'Некорректные данные'})

    # Проверяем что все интервалы не пустые
    valid = [lst for lst in all_intervals if len(lst) >= 2]
    if len(valid) < MIN_ATTEMPTS:
        return jsonify({'success': False, 'message': f'Нужно {MIN_ATTEMPTS} корректных попытки'})

    ideal, deviation = compute_stats(valid)

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'message': 'Пользователь уже существует'})

    users[username] = {
        'phrase':    phrase,
        'ideal':     ideal,
        'deviation': deviation,
        'registered': time.strftime('%Y-%m-%d %H:%M')
    }
    save_users(users)

    expl = (
        f"✨ Профиль создан на основе {len(valid)} попыток.<br>"
        f"Идеальное значение (ideal): <strong>{ideal} мс</strong> — среднее время между нажатиями.<br>"
        f"Отклонение (dev): <strong>{deviation} мс</strong> — стабильность ритма набора.<br>"
        f"При авторизации оба показателя должны совпасть с точностью EPS = {EPS} мс."
    )
    return jsonify({'success': True, 'message': f'✨ Пользователь {username} успешно зарегистрирован!', 'explanation': expl})


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
    <h1>✨ Добро пожаловать, <span>{username}</span></h1>
    <p>Авторизация по клавиатурному почерку прошла успешно. Доступ разрешён.</p>
  </div>

  <div class="info-blue">
    <strong>💗 Система защиты активна.</strong> При бездействии более {LOCK_TIMEOUT} секунд
    сессия будет заблокирована и потребуется повторная авторизация.
  </div>

  <div class="card">
    <div class="sec">✨ Ваш профиль клавиатурного почерка</div>
    <div class="stats-grid">
      <div class="stat-item">
        <div class="stat-val">{u['ideal']}</div>
        <div class="stat-lbl">Идеальное значение (мс)</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{u['deviation']}</div>
        <div class="stat-lbl">Отклонение (мс)</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{EPS}</div>
        <div class="stat-lbl">Точность EPS (мс)</div>
      </div>
      <div class="stat-item">
        <div class="stat-val">{u.get('registered', '—')}</div>
        <div class="stat-lbl">Дата регистрации</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="sec">✨ Ваша фраза (эталон)</div>
    <div class="phrase-box">
      <div class="phrase-label">💗 Фраза для авторизации</div>
      <div class="phrase-text">{u['phrase']}</div>
    </div>
    <p style="font-size:12px;color:var(--muted);margin-top:10px;line-height:1.8">
      Фраза назначается системой случайным образом при регистрации.
      Она хранится в зашифрованном файле <code>users.dat</code> (XOR + Base64).
    </p>
  </div>

  <div class="card">
    <div class="sec">✨ Действия</div>
    <a href="/users"><button class="btn btn-b" style="margin-right:12px">👥 Список пользователей</button></a>
    <a href="/register"><button class="btn" style="background:linear-gradient(135deg,#fbcfe8,#f9a8d4);color:#831843">✨ Добавить пользователя</button></a>
    <a href="/logout" style="margin-left:12px"><button class="btn btn-r">🚪 Выйти</button></a>
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

// Кнопка — прямой href, не JS-навигация
lockBtn.addEventListener('click', function() {{
  window.location.assign('/lock_auth');
}});

document.addEventListener('mousemove', resetLock);
document.addEventListener('keydown',   resetLock);
document.addEventListener('click',     resetLock);
resetLock();
</script>

<div id="lock-overlay" style="display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(255,245,248,.98);flex-direction:column;align-items:center;
  justify-content:center;gap:18px;">
  <div style="font-size:80px">🔒</div>
  <div style="font-family:'Poppins',sans-serif;font-size:26px;font-weight:700;color:var(--r)">Сессия заблокирована</div>
  <div style="font-size:14px;color:var(--muted);text-align:center;line-height:1.9">
    Бездействие более {LOCK_TIMEOUT} секунд<br>Требуется повторное подтверждение личности
  </div>
  <a href="/lock_auth" id="lock-confirm-btn"
     style="margin-top:10px;padding:14px 32px;background:linear-gradient(135deg,var(--g),#c084fc);color:#fff;
            border-radius:40px;font-family:'Poppins',sans-serif;font-size:14px;
            font-weight:600;letter-spacing:0.5px;text-decoration:none">
    ✨ Подтвердить личность
  </a>
</div>"""
    return page(f"Рабочий стол — {username}", content)


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
        me = ' <span style="color:var(--r);font-size:11px;font-weight:600">✨ вы</span>' if uname == session.get('username') else ''
        rows += f"""<tr>
  <td style="color:var(--muted)">{i}</td>
  <td style="font-weight:600">{uname}{me}</td>
  <td style="color:var(--warn)">{data['ideal']} мс</td>
  <td style="color:var(--b)">{data['deviation']} мс</td>
  <td style="color:var(--muted);font-size:12px">{data['phrase'][:20]}…</td>
  <td style="color:var(--muted);font-size:12px">{data.get('registered','—')}</td>
</tr>"""

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>✨ Зарегистрированные <span>пользователи</span></h1>
    <p>Все пользователи системы с профилями клавиатурного почерка. Данные хранятся в <code>users.dat</code>.</p>
  </div>
  <div class="info-blue">
    <strong>💗 Файл users.dat</strong> — зашифрован методом XOR (ключ 0x5A) + Base64.
    Фразы хранятся в <strong>phrases.dat</strong> (тот же метод). Прямое чтение файлов невозможно без ключа.
  </div>
  <div class="card" style="overflow:auto">
    <div class="sec">✨ Профили пользователей ({len(users)} чел.)</div>
    <table class="utbl">
      <thead><tr>
        <th>№</th><th>Пользователь</th><th>Ideal (мс)</th>
        <th>Dev (мс)</th><th>Фраза</th><th>Дата рег.</th>
      </tr></thead>
      <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">Нет пользователей</td></tr>'}</tbody>
    </table>
  </div>
  <div style="margin-top:12px">
    <a href="/dashboard"><button class="btn btn-g">← На главную</button></a>
    <a href="/register" style="margin-left:12px"><button class="btn btn-b">✨ Добавить</button></a>
  </div>
</div>"""
    return page("Пользователи — КП", content)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ══════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════
if __name__ == '__main__':
    # При первом запуске создаём файл фраз
    load_phrases()
    print(f"\n{'='*50}")
    print(f"  ЛР №5 — Клавиатурный почерк")
    print(f"  Файлы: users.dat, phrases.dat (XOR+Base64)")
    print(f"  EPS = {EPS} мс  |  Блокировка: {LOCK_TIMEOUT} сек")
    print(f"  http://127.0.0.1:5000")
    print(f"{'='*50}\n")
    app.run(debug=True)