# -*- coding: utf-8 -*-
"""
Лабораторная работа №2 — Дискреционная модель политики безопасности
Вариант 6: 8 субъектов, 3 объекта
БЕЗ Jinja2 — весь HTML генерируется через f-строки Python
"""

import random
from flask import Flask, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'lab2_v6_nosecret'

# ======== ВАРИАНТ 6 ========
NUM_USERS = 8
NUM_OBJECTS = 3
USERS = ['admin', 'Sergey', 'Ivan', 'Boris', 'Anna', 'Maria', 'Dmitry', 'Elena']

RIGHTS_NAMES = {
    0: "Запрет",          1: "Передача прав",
    2: "Запись",          3: "Запись + Передача прав",
    4: "Чтение",          5: "Чтение + Передача прав",
    6: "Чтение + Запись", 7: "Полные права"
}

def generate_access_matrix():
    matrix = []
    for i in range(NUM_USERS):
        row = []
        for j in range(NUM_OBJECTS):
            row.append(7 if USERS[i] == 'admin' else random.randint(0, 7))
        matrix.append(row)
    return matrix

def check_access(val, op):
    return (val & {'read': 4, 'write': 2, 'grant': 1}[op]) != 0

def format_rights(val):
    return RIGHTS_NAMES.get(val, "Запрет")

def get_bits(val):
    return (val >> 2) & 1, (val >> 1) & 1, val & 1

def get_user_index(username):
    try: return USERS.index(username)
    except ValueError: return -1

def grant_right(matrix, fi, ti, oi, right):
    fa = matrix[fi][oi]
    if not check_access(fa, 'grant'): return False
    if right in ('read', 'write') and not check_access(fa, right): return False
    mask = {'read': 4, 'write': 2, 'grant': 1}[right]
    matrix[ti][oi] |= mask
    return True

access_matrix = generate_access_matrix()

# ─────────────────────────────────────────────
# ОБЩИЙ CSS + стили (инлайн, одни на все страницы)
# ─────────────────────────────────────────────
BASE_STYLE = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Unbounded:wght@700;900&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#07090f;
    --card:#0f1621;
    --border:#1a2236;
    --text:#e2e8f0;
    --muted:#55677d;
    --r:#ff4d6d;   /* красный  */
    --g:#00d4aa;   /* зелёный  */
    --b:#3b82f6;   /* синий    */
    --warn:#f59e0b;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'JetBrains Mono',monospace;background:var(--bg);color:var(--text);min-height:100vh}
  body::before{
    content:'';position:fixed;inset:0;pointer-events:none;
    background:
      radial-gradient(ellipse 60% 40% at 10% 0%,   rgba(255,77,109,.10) 0%,transparent 60%),
      radial-gradient(ellipse 50% 40% at 90% 100%,  rgba(59,130,246,.10) 0%,transparent 60%),
      radial-gradient(ellipse 40% 30% at 50%  50%,  rgba(0,212,170,.06) 0%,transparent 70%);
  }
  /* nav */
  nav{position:sticky;top:0;z-index:99;background:rgba(7,9,15,.92);border-bottom:1px solid var(--border);
      backdrop-filter:blur(14px);padding:13px 28px;display:flex;align-items:center;justify-content:space-between}
  .brand{font-family:'Unbounded',sans-serif;font-size:12px;
    background:linear-gradient(90deg,var(--r),var(--g),var(--b));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  .nav-links{display:flex;gap:4px}
  .nav-link{padding:5px 13px;font-size:11px;letter-spacing:1px;text-transform:uppercase;
    color:var(--muted);text-decoration:none;border:1px solid transparent;border-radius:4px;transition:.2s}
  .nav-link:hover{color:var(--text);border-color:var(--border)}
  .nav-link.red:hover{color:var(--r);border-color:rgba(255,77,109,.3)}
  .chip{display:flex;align-items:center;gap:7px;background:var(--card);border:1px solid var(--border);
    border-radius:20px;padding:5px 13px;font-size:12px}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--g);animation:blink 2s infinite}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
  /* container */
  .wrap{max-width:1050px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}
  /* cards */
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:22px;margin-bottom:16px}
  .card-title{font-family:'Unbounded',sans-serif;font-size:13px;font-weight:700;margin-bottom:4px}
  .card-sub{font-size:11px;color:var(--muted);margin-bottom:14px}
  /* gradient text headings */
  .grad{background:linear-gradient(135deg,#fff 30%,var(--g));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  .grad-rgb{background:linear-gradient(90deg,var(--r),var(--g),var(--b));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  /* info boxes */
  .info-blue{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);border-radius:8px;
    padding:14px 18px;font-size:12px;line-height:1.85;color:#93c5fd;margin-bottom:18px}
  .info-blue strong{color:#60a5fa}
  /* section label */
  .sec{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);
    display:flex;align-items:center;gap:10px;margin-bottom:11px}
  .sec::after{content:'';flex:1;height:1px;background:var(--border)}
  /* buttons */
  .btn{padding:10px 22px;border:none;border-radius:6px;font-family:'JetBrains Mono',monospace;
    font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:.2s}
  .btn-g{background:var(--g);color:#07090f}
  .btn-g:hover{background:#00f5c4;box-shadow:0 4px 18px rgba(0,212,170,.3);transform:translateY(-1px)}
  .btn-r{background:var(--r);color:#fff}
  .btn-r:hover{background:#ff6b85;box-shadow:0 4px 18px rgba(255,77,109,.3)}
  /* form */
  select,input[type=number]{padding:9px 13px;background:#111827;border:1px solid var(--border);
    border-radius:6px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;transition:.2s}
  select:focus,input:focus{outline:none;border-color:var(--g)}
  select option{background:#1e293b}
  .fgroup{display:flex;flex-direction:column;gap:5px}
  .flabel{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted)}
  .frow{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:12px}
  /* result */
  .result{display:none;margin-top:14px;padding:15px;border-radius:7px;font-size:13px;line-height:1.8}
  .result.ok{background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.25);color:#6ee7d0}
  .result.err{background:rgba(255,77,109,.08);border:1px solid rgba(255,77,109,.25);color:#fca5a5}
  .result .expl{margin-top:9px;padding-top:9px;border-top:1px solid rgba(255,255,255,.07);
    font-size:11px;color:var(--muted);line-height:1.9}
  /* tabs */
  .tabs{display:flex;gap:3px;border-bottom:1px solid var(--border);margin-bottom:16px}
  .tab{padding:7px 15px;font-size:11px;cursor:pointer;color:var(--muted);background:transparent;
    border:1px solid transparent;border-bottom:none;border-radius:4px 4px 0 0;
    font-family:'JetBrains Mono',monospace;transition:.2s;margin-bottom:-1px;letter-spacing:.5px}
  .tab:hover{color:var(--text)}
  .tab.on{color:var(--g);background:var(--card);border-color:var(--border);border-bottom-color:var(--card)}
  .tabp{display:none}.tabp.on{display:block}
  /* op hint */
  .op-hint{background:rgba(59,130,246,.05);border:1px solid rgba(59,130,246,.15);border-radius:6px;
    padding:11px 14px;font-size:11px;color:#93c5fd;line-height:1.85;margin-bottom:12px}
  /* rights grid */
  .rg{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-bottom:22px}
  .rc{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:17px;transition:.2s}
  .rc:hover{border-color:var(--g)}
  .rc.has{border-left:3px solid var(--g)}
  .rc.no{border-left:3px solid #1f2d3d}
  .rc .oname{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
  .rv{font-family:'Unbounded',sans-serif;font-size:34px;font-weight:900;line-height:1}
  .rv.ok{color:var(--g)}.rv.deny{color:#1f2d3d}
  .blabels{display:flex;gap:3px;font-size:9px;color:var(--muted);margin:8px 0 3px}
  .bl{width:26px;text-align:center}
  .bits{display:flex;gap:3px;margin-bottom:8px}
  .bb{width:26px;height:26px;display:flex;align-items:center;justify-content:center;
      font-size:13px;font-weight:700;border-radius:3px}
  .bb.one{background:rgba(0,212,170,.18);color:var(--g);border:1px solid rgba(0,212,170,.35)}
  .bb.zero{background:#141c2e;color:#2a3a50;border:1px solid var(--border)}
  .rtxt{font-size:11px;color:var(--text);margin-top:6px}
  .otags{display:flex;gap:3px;margin-top:8px;flex-wrap:wrap}
  .ot{font-size:9px;padding:2px 7px;border-radius:3px}
  .ot.y{background:rgba(0,212,170,.13);color:var(--g);border:1px solid rgba(0,212,170,.28)}
  .ot.n{background:#111827;color:#1f2d3d;border:1px solid var(--border)}
  /* matrix table */
  .mtable{width:100%;border-collapse:collapse;font-size:12px;min-width:500px}
  .mtable th{padding:11px 14px;font-size:10px;letter-spacing:1px;text-transform:uppercase;
    color:var(--muted);background:#0d1320;border-bottom:1px solid var(--border);text-align:center}
  .mtable th:first-child{text-align:left}
  .mtable td{padding:11px 14px;border-bottom:1px solid var(--border);vertical-align:middle;text-align:center}
  .mtable td:first-child{text-align:left;font-weight:600}
  .mtable tr:last-child td{border-bottom:none}
  .mtable tr:hover td{background:rgba(0,212,170,.02)}
  .mval{font-family:'Unbounded',sans-serif;font-size:19px;font-weight:900}
  .mval.full{color:var(--g)}.mval.partial{color:var(--b)}.mval.deny{color:#1f2d3d}
  .mbits{display:flex;gap:2px;justify-content:center;margin:4px 0}
  .mbit{width:16px;height:16px;display:flex;align-items:center;justify-content:center;
    font-size:9px;font-weight:700;border-radius:2px}
  .mbit.one{background:rgba(0,212,170,.18);color:var(--g)}
  .mbit.zero{background:#141c2e;color:#2a3a50}
  .mtxt{font-size:9px;color:var(--muted);line-height:1.4}
  /* legend */
  .lgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:10px}
  .li{background:#0d1320;border:1px solid var(--border);border-radius:6px;padding:9px 11px;
    display:flex;align-items:center;gap:8px}
  .lv{font-family:'Unbounded',sans-serif;font-size:17px;font-weight:700;color:var(--g);min-width:20px;text-align:center}
  .lv.d{color:#1f2d3d}
  .lbin{color:var(--warn);font-weight:600;font-size:10px}
  .ltxt{color:var(--muted);font-size:9px;margin-top:1px}
  /* QA */
  .qa{margin-bottom:10px}
  .qq{background:#0d1320;border:1px solid var(--border);border-left:3px solid var(--b);
    border-radius:0 6px 6px 0;padding:13px 15px;font-size:13px;font-weight:600;cursor:pointer;
    display:flex;justify-content:space-between;align-items:center;transition:.2s}
  .qq:hover{border-left-color:var(--g)}
  .qq .arr{font-size:10px;color:var(--muted);transition:.2s}
  .qq.open .arr{transform:rotate(180deg)}
  .qa-a{display:none;background:rgba(0,212,170,.03);border:1px solid var(--border);border-top:none;
    border-radius:0 0 6px 6px;padding:15px;font-size:12px;line-height:1.9}
  .qa-a strong{color:var(--g)}
  .qa-a code{background:#0d1320;border:1px solid var(--border);border-radius:3px;
    padding:1px 6px;color:var(--warn);font-size:11px}
  /* login */
  .login-wrap{width:440px;position:relative;z-index:1}
  .login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
  .badge{display:inline-flex;align-items:center;gap:7px;background:rgba(0,212,170,.09);
    border:1px solid rgba(0,212,170,.25);border-radius:4px;padding:4px 12px;font-size:10px;
    color:var(--g);letter-spacing:2px;text-transform:uppercase;margin-bottom:18px}
  .badge::before{content:'';width:6px;height:6px;background:var(--g);border-radius:50%;animation:blink 2s infinite}
  .lh1{font-family:'Unbounded',sans-serif;font-size:26px;font-weight:900;line-height:1.2;margin-bottom:7px}
  .lsub{font-size:11px;color:var(--muted);margin-bottom:28px;line-height:1.7}
  .lsub span{color:var(--warn)}
  .igrid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
  .iitem{background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:12px;text-align:center}
  .iitem .iv{font-family:'Unbounded',sans-serif;font-size:26px;font-weight:700;color:var(--g)}
  .iitem .il{font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-top:3px}
  .tip{font-size:10px;color:var(--muted);margin-top:13px;padding:9px 12px;
    border-left:2px solid var(--b);background:rgba(59,130,246,.05);border-radius:0 4px 4px 0;line-height:1.75}
  .err-box{display:flex;align-items:center;gap:9px;background:rgba(255,77,109,.09);
    border:1px solid rgba(255,77,109,.28);border-radius:6px;padding:11px 15px;
    font-size:13px;color:#fca5a5;margin-bottom:14px}
  /* example */
  .exbox{background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:15px;
    font-size:12px;line-height:1.9;margin-top:10px}
  .exbox .st{color:var(--g);font-weight:600}
  .exbox .rs{color:var(--warn)}
  .exbox .ok2{color:var(--g)}.exbox .er2{color:var(--r)}
  /* page header */
  .ph{margin-bottom:24px}
  .ph h1{font-family:'Unbounded',sans-serif;font-size:19px;font-weight:700}
  .ph h1 span{color:var(--g)}
  .ph p{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.75}
  /* overflow wrapper for table */
  .tover{overflow:auto;background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:16px}
  /* main tabs (theory) */
  .mtabs{display:flex;gap:3px;border-bottom:1px solid var(--border);margin-bottom:22px}
  .mtab{padding:9px 19px;font-size:12px;cursor:pointer;color:var(--muted);background:transparent;
    border:1px solid transparent;border-bottom:none;border-radius:4px 4px 0 0;
    font-family:'JetBrains Mono',monospace;transition:.2s;margin-bottom:-1px}
  .mtab:hover{color:var(--text)}
  .mtab.on{color:var(--g);background:var(--bg);border-color:var(--border);border-bottom-color:var(--bg)}
  .mpanel{display:none}.mpanel.on{display:block}
  .bit-tbl{width:100%;border-collapse:collapse;margin-top:11px;font-size:12px}
  .bit-tbl th,.bit-tbl td{padding:7px 11px;border:1px solid var(--border);text-align:center}
  .bit-tbl th{background:#0d1320;color:var(--muted);font-size:10px;letter-spacing:1px;text-transform:uppercase}
  .bit-tbl td:first-child{font-family:'Unbounded',sans-serif;color:var(--g);text-align:left}
  .bit-tbl tr:nth-child(even) td{background:rgba(0,212,170,.02)}
  .tag-r{color:#ff4d6d}.tag-w{color:#3b82f6}.tag-g{color:#f59e0b}
</style>"""

def page(title, body_class, content, active_nav=""):
    nav_items = [
        ("/dashboard", "Панель", ""),
        ("/matrix",    "Матрица", ""),
        ("/theory",    "Теория", ""),
        ("/logout",    "Выход", "red"),
    ]
    links = ""
    for href, label, cls in nav_items:
        links += f'<a href="{href}" class="nav-link {cls}">{label}</a>'

    user = session.get('username', '')
    chip = f'<div class="chip"><div class="dot"></div>{user}</div>' if user else ''

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<title>{title}</title>
{BASE_STYLE}
</head>
<body class="{body_class}">
<nav>
  <div class="brand">ДМБ · Вариант 6</div>
  <div class="nav-links">{links}</div>
  {chip}
</nav>
{content}
</body>
</html>"""

# ──────────── LOGIN ────────────
@app.route('/')
def index():
    opts = "".join(
        f'<option value="{u}">{"⚡ " if u=="admin" else "○ "}{u}{"  (Администратор)" if u=="admin" else ""}</option>'
        for u in USERS
    )
    err_html = ""
    if request.args.get('err'):
        err_html = f'<div class="err-box">⚠ {request.args.get("err")}</div>'

    content = f"""
<div class="login-body">
<div class="login-wrap">
  <div class="badge">Система контроля доступа</div>
  <div class="lh1 grad-rgb">Дискреционная<br>модель безопасности</div>
  <p class="lsub">Лабораторная работа №2 · <span>Вариант 6</span><br>
  Идентифицируйтесь для входа в систему</p>
  {err_html}
  <div class="card">
    <div class="flabel" style="margin-bottom:10px">// Идентификатор субъекта</div>
    <form method="POST" action="/login">
      <select name="username" required style="width:100%;margin-bottom:12px">
        <option value="">— выберите пользователя —</option>
        {opts}
      </select>
      <button type="submit" class="btn btn-g" style="width:100%">→ Войти в систему</button>
    </form>
  </div>
  <div class="igrid">
    <div class="iitem"><div class="iv">{NUM_USERS}</div><div class="il">Субъектов</div></div>
    <div class="iitem"><div class="iv">{NUM_OBJECTS}</div><div class="il">Объектов</div></div>
  </div>
  <div class="tip">
    💡 Матрица доступа {NUM_USERS}×{NUM_OBJECTS}. Каждая ячейка — 3-битное число (0–7):<br>
    бит₃=Чтение · бит₂=Запись · бит₁=Передача прав
  </div>
</div>
</div>"""
    return page("Вход — ДМБ", "", content)


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    if username not in USERS:
        return redirect('/?err=Пользователь+не+найден+в+системе')
    session['username'] = username
    session['user_index'] = get_user_index(username)
    return redirect(url_for('dashboard'))

# ──────────── DASHBOARD ────────────
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']
    ui = session['user_index']
    is_admin = username == 'admin'

    # Карточки прав
    rights_cards = ""
    for j in range(NUM_OBJECTS):
        val = access_matrix[ui][j]
        rb, wb, gb = get_bits(val)
        label = format_rights(val)
        ok = val > 0
        cr = check_access(val, 'read')
        cw = check_access(val, 'write')
        cg = check_access(val, 'grant')
        rights_cards += f"""
<div class="rc {'has' if ok else 'no'}">
  <div class="oname">Объект {j+1}</div>
  <div class="rv {'ok' if ok else 'deny'}">{val}</div>
  <div class="blabels"><div class="bl">R</div><div class="bl">W</div><div class="bl">G</div></div>
  <div class="bits">
    <div class="bb {'one' if rb else 'zero'}">{rb}</div>
    <div class="bb {'one' if wb else 'zero'}">{wb}</div>
    <div class="bb {'one' if gb else 'zero'}">{gb}</div>
  </div>
  <div class="rtxt">{label}</div>
  <div class="otags">
    <span class="ot {'y' if cr else 'n'}">read</span>
    <span class="ot {'y' if cw else 'n'}">write</span>
    <span class="ot {'y' if cg else 'n'}">grant</span>
  </div>
</div>"""

    # Опции объектов для select
    def obj_opts(sid):
        out = ""
        for j in range(NUM_OBJECTS):
            val = access_matrix[ui][j]
            out += f'<option value="{j+1}">Объект {j+1}  (значение: {val} = {bin(val)[2:].zfill(3)}₂)</option>'
        return out

    user_opts = "".join(
        f'<option value="{u}">{u}</option>'
        for u in USERS if u != username
    )

    admin_note = ""
    if is_admin:
        admin_note = '<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);border-radius:6px;padding:9px 14px;font-size:11px;color:#fcd34d;margin-bottom:14px">⚡ Вы — Администратор. Полные права (7 = 111₂) ко всем объектам.</div>'

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Панель субъекта: <span>{username}</span></h1>
    <p>Дискреционная модель · {NUM_OBJECTS} объекта · {NUM_USERS} субъектов в системе</p>
  </div>
  {admin_note}
  <div class="info-blue">
    <strong>Как читать карточки:</strong> Число (0–7) = трёхбитный код [R|W|G].
    <strong>R</strong>=Чтение (маска 4, бит₃), <strong>W</strong>=Запись (маска 2, бит₂),
    <strong>G</strong>=Передача прав (маска 1, бит₁). Проверка: <code>значение & маска ≠ 0</code>.
    Пример: 6 = 110₂ → 6&amp;4=4≠0 ✓ Чтение, 6&amp;2=2≠0 ✓ Запись, 6&amp;1=0 ✗ Передача прав.
  </div>
  <div class="sec">// Ваши права доступа к объектам</div>
  <div class="rg">{rights_cards}</div>

  <div class="card">
    <div class="card-title">// Жду ваших указаний</div>
    <div class="card-sub" style="margin-bottom:14px">
      Выберите операцию. Система проверит соответствующий бит матрицы доступов и выдаст пояснение.
    </div>

    <div class="tabs">
      <button class="tab on" onclick="swTab('read',this)">read</button>
      <button class="tab" onclick="swTab('write',this)">write</button>
      <button class="tab" onclick="swTab('grant',this)">grant</button>
      <button class="tab" onclick="swTab('quit',this)" style="color:var(--r)">quit</button>
    </div>

    <div id="tp-read" class="tabp on">
      <div class="op-hint"><strong>read:</strong> проверка бит₃ → <code>M[вы][объект] & 4 ≠ 0</code></div>
      <div class="frow">
        <div class="fgroup"><div class="flabel">Объект</div>
          <select id="r-obj">{obj_opts('r')}</select></div>
        <button class="btn btn-g" onclick="exec_read()">→ Выполнить</button>
      </div>
    </div>

    <div id="tp-write" class="tabp">
      <div class="op-hint"><strong>write:</strong> проверка бит₂ → <code>M[вы][объект] & 2 ≠ 0</code></div>
      <div class="frow">
        <div class="fgroup"><div class="flabel">Объект</div>
          <select id="w-obj">{obj_opts('w')}</select></div>
        <button class="btn btn-g" onclick="exec_write()">→ Выполнить</button>
      </div>
    </div>

    <div id="tp-grant" class="tabp">
      <div class="op-hint">
        <strong>grant:</strong> Условие 1 — у вас есть G (бит₁): <code>M[вы][O] & 1 ≠ 0</code><br>
        Условие 2 — у вас есть передаваемое право. Результат: <code>M[получатель][O] |= маска</code>
      </div>
      <div class="frow">
        <div class="fgroup"><div class="flabel">Объект</div>
          <select id="g-obj">{obj_opts('g')}</select></div>
        <div class="fgroup"><div class="flabel">Право</div>
          <select id="g-right">
            <option value="read">read (бит₃, маска 4)</option>
            <option value="write">write (бит₂, маска 2)</option>
            <option value="grant">grant (бит₁, маска 1)</option>
          </select></div>
        <div class="fgroup"><div class="flabel">Получатель</div>
          <select id="g-user">{user_opts}</select></div>
        <button class="btn btn-g" onclick="exec_grant()">→ Передать</button>
      </div>
    </div>

    <div id="tp-quit" class="tabp">
      <div class="op-hint" style="border-color:rgba(255,77,109,.2);background:rgba(255,77,109,.05);color:#fca5a5">
        <strong>quit:</strong> Завершает сеанс. Матрица остаётся в памяти сервера.
      </div>
      <div style="margin-top:12px">
        <button class="btn btn-r" onclick="exec_quit()">→ Завершить сеанс</button>
      </div>
    </div>

    <div id="result" class="result"></div>
  </div>
</div>

<script>
function swTab(name, btn) {{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.tabp').forEach(p=>p.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('tp-'+name).classList.add('on');
  document.getElementById('result').style.display='none';
}}
function show(data) {{
  const b = document.getElementById('result');
  if(data.error){{b.className='result err';b.innerHTML='⚠ '+data.error;}}
  else if(data.quit){{b.className='result ok';b.innerHTML='✓ '+data.message;setTimeout(()=>location.href='/',2000);}}
  else{{
    b.className='result '+(data.success?'ok':'err');
    b.innerHTML=(data.success?'✓ ':'✗ ')+'<strong>'+data.message+'</strong>'+
      (data.explanation?'<div class="expl"><strong>Пояснение:</strong> '+data.explanation+'</div>':'');
  }}
  b.style.display='block';
}}
function post(body){{fetch('/execute',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:new URLSearchParams(body)}}).then(r=>r.json()).then(show);}}
function exec_read(){{post({{operation:'read',object_num:document.getElementById('r-obj').value}});}}
function exec_write(){{post({{operation:'write',object_num:document.getElementById('w-obj').value}});}}
function exec_grant(){{post({{operation:'grant',object_num:document.getElementById('g-obj').value,right_name:document.getElementById('g-right').value,target_user:document.getElementById('g-user').value}});}}
function exec_quit(){{post({{operation:'quit'}});}}
</script>"""
    return page(f"Панель — {username}", "", content)


@app.route('/execute', methods=['POST'])
def execute():
    if 'username' not in session:
        return jsonify({'error': 'Сессия истекла'}), 401
    op = request.form.get('operation')
    username = session['username']
    ui = session['user_index']

    if op == 'quit':
        session.clear()
        return jsonify({'quit': True, 'message': f'Работа пользователя {username} завершена. До свидания.'})

    onum = request.form.get('object_num')
    if not onum:
        return jsonify({'error': 'Не указан объект'})
    try:
        oi = int(onum) - 1
        if not (0 <= oi < NUM_OBJECTS):
            return jsonify({'error': f'Объект от 1 до {NUM_OBJECTS}'})
    except ValueError:
        return jsonify({'error': 'Некорректный номер'})

    val = access_matrix[ui][oi]
    rb, wb, gb = get_bits(val)
    binv = f"{rb}{wb}{gb}"

    if op == 'read':
        ok = check_access(val, 'read')
        return jsonify({'success': ok,
            'message': 'Операция прошла успешно' if ok else 'Отказ в выполнении операции',
            'explanation': f'M[{username}][Объект{onum}] = {val} ({binv}₂). Проверка: {val} & 4 = {val&4} {"≠ 0 → доступ разрешён ✓" if ok else "= 0 → доступ запрещён ✗"}. Бит₃ (R) = {rb}.'
        })

    if op == 'write':
        ok = check_access(val, 'write')
        return jsonify({'success': ok,
            'message': 'Операция прошла успешно' if ok else 'Отказ в выполнении операции',
            'explanation': f'M[{username}][Объект{onum}] = {val} ({binv}₂). Проверка: {val} & 2 = {val&2} {"≠ 0 → доступ разрешён ✓" if ok else "= 0 → доступ запрещён ✗"}. Бит₂ (W) = {wb}.'
        })

    if op == 'grant':
        right = request.form.get('right_name')
        target = request.form.get('target_user')
        if not right or not target:
            return jsonify({'error': 'Укажите право и получателя'})
        if target not in USERS:
            return jsonify({'error': 'Получатель не найден'})
        if target == username:
            return jsonify({'error': 'Нельзя передавать права самому себе'})
        ti = get_user_index(target)
        mask = {'read': 4, 'write': 2, 'grant': 1}[right]
        ru = {'read': 'Чтение', 'write': 'Запись', 'grant': 'Передача прав'}

        if not check_access(val, 'grant'):
            return jsonify({'success': False,
                'message': 'Отказ в выполнении операции',
                'explanation': f'Нет права G (бит₁). {val} & 1 = {val&1} = 0. Передача прав невозможна.'
            })
        if right in ('read','write') and not check_access(val, right):
            return jsonify({'success': False,
                'message': 'Отказ в выполнении операции',
                'explanation': f'Нет права «{ru[right]}». {val} & {mask} = {val&mask} = 0. Нельзя передать право которого нет.'
            })

        old_t = access_matrix[ti][oi]
        grant_right(access_matrix, ui, ti, oi, right)
        new_t = access_matrix[ti][oi]
        rb2, wb2, gb2 = get_bits(new_t)
        return jsonify({'success': True,
            'message': f'Право «{ru[right]}» передано пользователю {target}',
            'explanation': f'M[{target}][Объект{onum}]: {old_t} ({bin(old_t)[2:].zfill(3)}₂) | {mask} = {new_t} ({rb2}{wb2}{gb2}₂). Матрица обновлена.'
        })

    return jsonify({'error': f'Неизвестная операция: {op}'})


# ──────────── MATRIX ────────────
@app.route('/matrix')
def show_matrix():
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']

    header = "<th>Субъект</th>"
    for j in range(NUM_OBJECTS):
        header += f"<th>Объект {j+1}</th>"

    rows = ""
    for i, user in enumerate(USERS):
        cells = ""
        for j in range(NUM_OBJECTS):
            val = access_matrix[i][j]
            rb, wb, gb = get_bits(val)
            cls = "full" if val == 7 else ("deny" if val == 0 else "partial")
            cells += f"""<td>
  <div class="mval {cls}">{val}</div>
  <div class="mbits">
    <div class="mbit {'one' if rb else 'zero'}">{rb}</div>
    <div class="mbit {'one' if wb else 'zero'}">{wb}</div>
    <div class="mbit {'one' if gb else 'zero'}">{gb}</div>
  </div>
  <div class="mtxt">{format_rights(val)}</div>
</td>"""
        you = ' <span style="color:var(--g);font-size:10px">← вы</span>' if user == username else ''
        adm = '⚡ ' if user == 'admin' else ''
        rows += f'<tr><td style="{"color:var(--warn)" if user=="admin" else ""}">{adm}{user}{you}</td>{cells}</tr>'

    legend_items = ""
    data = [(0,'000','Полный запрет'),(1,'001','Передача прав'),(2,'010','Запись'),
            (3,'011','Запись+Пер.'),(4,'100','Чтение'),(5,'101','Чтение+Пер.'),
            (6,'110','Чтение+Запись'),(7,'111','Полный доступ')]
    for v, b, t in data:
        d = ' d' if v == 0 else ''
        legend_items += f'<div class="li"><div class="lv{d}">{v}</div><div><div class="lbin">{b}</div><div class="ltxt">{t}</div></div></div>'

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Матрица доступа <span>{NUM_OBJECTS}×{NUM_USERS}</span></h1>
    <p>Текущее состояние · изменяется операцией grant через побитовое OR</p>
  </div>
  <div class="info-blue">
    <strong>Ячейка матрицы:</strong> Число (0–7) → [R|W|G]. Проверка: <code>M[i][j] & маска ≠ 0</code>.
    Добавление права: <code>M[i][j] |= маска</code> (побитовое ИЛИ).
  </div>
  <div class="tover">
    <table class="mtable">
      <thead><tr>{header}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="card">
    <div class="card-title">// Кодировка прав</div>
    <div class="lgrid">{legend_items}</div>
  </div>
</div>"""
    return page("Матрица — ДМБ", "", content)


# ──────────── THEORY ────────────
@app.route('/theory')
def theory():
    if 'username' not in session:
        return redirect(url_for('index'))

    bit_rows = ""
    table_data = [
        (0,'0','0','0','Полный запрет'),
        (1,'0','0','1','<span class="tag-g">Передача прав</span>'),
        (2,'0','1','0','<span class="tag-w">Запись</span>'),
        (3,'0','1','1','<span class="tag-w">Запись</span> + <span class="tag-g">Передача прав</span>'),
        (4,'1','0','0','<span class="tag-r">Чтение</span>'),
        (5,'1','0','1','<span class="tag-r">Чтение</span> + <span class="tag-g">Передача прав</span>'),
        (6,'1','1','0','<span class="tag-r">Чтение</span> + <span class="tag-w">Запись</span>'),
        (7,'1','1','1','<span class="tag-r">Чтение</span> + <span class="tag-w">Запись</span> + <span class="tag-g">Передача прав</span>'),
    ]
    for v, r, w, g, label in table_data:
        bit_rows += f"<tr><td>{v}</td><td>{r}</td><td>{w}</td><td>{g}</td><td style='text-align:left'>{label}</td></tr>"

    qa_items = [
        ("Что такое дискреционная модель управления доступом?",
         "Дискреционная (избирательная) модель управления доступом — политика безопасности, в которой "
         "<strong>права задаются явно</strong> в матрице доступа. Владелец объекта сам решает, кто и что может делать. "
         "Называется дискреционной, потому что права распределяются по усмотрению (discretion) владельца."),
        ("Что такое матрица доступа и как она устроена?",
         "Матрица M[i][j] — двумерный массив <strong>Субъекты × Объекты</strong>. В варианте 6: 8×3.<br>"
         "Строка i — субъект, столбец j — объект, M[i][j] — трёхбитное число (0–7) с кодом прав.<br>"
         "Пример: M[Boris][Объект1] = 4 (<code>100₂</code>) → только Чтение."),
        ("Как кодируются права? Что означает значение 5?",
         "Трёхбитный код: <strong>бит₃=Чтение (R, маска 4)</strong>, <strong>бит₂=Запись (W, маска 2)</strong>, "
         "<strong>бит₁=Передача прав (G, маска 1)</strong>.<br>"
         "5 = <code>101₂</code>: R=1 ✓, W=0 ✗, G=1 ✓ → Чтение + Передача прав."),
        ("Как программно проверить наличие права?",
         "Побитовое AND: <code>M[i][j] & маска ≠ 0</code><br>"
         "Чтение: <code>val & 4 ≠ 0</code> · Запись: <code>val & 2 ≠ 0</code> · Передача: <code>val & 1 ≠ 0</code><br>"
         "Метод из задания: <code>val ÷ 2^(n-1)</code>, если результат нечётный — бит n равен 1."),
        ("Каковы условия операции передачи прав (grant)?",
         "<strong>Условие 1:</strong> M[A][O] & 1 ≠ 0 (есть право G)<br>"
         "<strong>Условие 2:</strong> M[A][O] & маска_P ≠ 0 (есть само передаваемое право P)<br>"
         "<strong>Результат:</strong> <code>M[B][O] = M[B][O] | маска_P</code> — право добавляется через побитовое ИЛИ."),
        ("Чем дискреционная модель отличается от мандатной?",
         "<strong>Дискреционная (DAC):</strong> права задаются явно, владелец управляет ими, гибкая.<br>"
         "<strong>Мандатная (MAC):</strong> права определяются уровнями секретности, правило: "
         "уровень субъекта ≥ уровень объекта → доступ разрешён. Централизованная, жёсткая."),
        ("Какова роль администратора?",
         "admin — субъект с <strong>полными правами (7 = 111₂)</strong> ко всем объектам (R=1, W=1, G=1). "
         "Задаётся явно при инициализации, не генерируется случайно."),
        ("Пример: проверить право записи, M[i][j] = 3",
         "<strong>Шаг 1:</strong> 3 = <code>011₂</code>. Бит₂ (Запись) — второй слева.<br>"
         "<strong>Шаг 2 (побитовый AND):</strong> <code>3 & 2 = 2 ≠ 0</code> → право есть.<br>"
         "<strong>Шаг 2 (метод деления):</strong> <code>3 ÷ 2^(2-1) = 3 ÷ 2 = 1</code> — нечётное → бит = 1.<br>"
         "Вывод: <strong>доступ по записи разрешён ✓</strong>"),
    ]

    qa_html = ""
    for i, (q, a) in enumerate(qa_items):
        qa_html += f"""<div class="qa">
  <div class="qq" onclick="tqa(this)">{i+1}. {q}<span class="arr">▼</span></div>
  <div class="qa-a">{a}</div>
</div>"""

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Теория и <span>ответы на вопросы</span></h1>
    <p>Лабораторная работа №2 · Дискреционная модель · Вариант 6</p>
  </div>

  <div class="mtabs">
    <button class="mtab on" onclick="swM('theory',this)">Теория</button>
    <button class="mtab" onclick="swM('qa',this)">Контрольные вопросы</button>
    <button class="mtab" onclick="swM('example',this)">Пример прогонки</button>
  </div>

  <!-- ТЕОРИЯ -->
  <div id="mp-theory" class="mpanel on">
    <div class="card">
      <div class="card-title grad-rgb">Дискреционная модель (DAC)</div>
      <div class="card-sub">Discretionary Access Control</div>
      <p style="font-size:13px;line-height:1.9">
        Дискреционная политика безопасности — каждой паре [субъект, объект] явно сопоставляется
        множество разрешённых операций. Хранится в виде матрицы M[i][j].
        Субъект может передавать свои права другим субъектам (операция grant).
      </p>
    </div>
    <div class="card">
      <div class="card-title">3-битное кодирование прав</div>
      <div class="card-sub">Множество S = {{Чтение, Запись, Передача прав}}</div>
      <table class="bit-tbl">
        <thead><tr><th>Дес.</th><th><span class="tag-r">R</span> бит₃</th><th><span class="tag-w">W</span> бит₂</th><th><span class="tag-g">G</span> бит₁</th><th>Разрешённые операции</th></tr></thead>
        <tbody>{bit_rows}</tbody>
      </table>
      <p style="font-size:11px;color:var(--muted);margin-top:11px;line-height:1.8">
        Проверка: <code>M[i][j] & маска ≠ 0</code> · Добавление: <code>M[i][j] |= маска</code>
      </p>
    </div>
    <div class="card">
      <div class="card-title">Параметры варианта 6</div>
      <p style="font-size:13px;line-height:2">
        Субъектов: <strong style="color:var(--g)">{NUM_USERS}</strong> &nbsp;·&nbsp;
        Объектов: <strong style="color:var(--g)">{NUM_OBJECTS}</strong> &nbsp;·&nbsp;
        Матрица: <strong style="color:var(--g)">{NUM_USERS}×{NUM_OBJECTS}</strong><br>
        Субъекты: {', '.join(USERS)}<br>
        Администратор: <strong style="color:var(--warn)">admin</strong> — всегда значение 7 (111₂)
      </p>
    </div>
  </div>

  <!-- КВ -->
  <div id="mp-qa" class="mpanel">
    <div class="card" style="padding:0;overflow:hidden">
      <div style="padding:18px 22px;border-bottom:1px solid var(--border)">
        <div class="card-title">Контрольные вопросы</div>
        <div class="card-sub" style="margin:0">Нажмите на вопрос для просмотра ответа</div>
      </div>
      <div style="padding:18px 22px">{qa_html}</div>
    </div>
  </div>

  <!-- ПРИМЕР -->
  <div id="mp-example" class="mpanel">
    <div class="card">
      <div class="card-title">Пример прогонки программы</div>
      <div class="card-sub">Демонстрация работы — аналог из задания</div>
      <div class="exbox">
        <p><span class="st">User:</span> Sergey</p>
        <p><span class="st">Идентификация прошла успешно, добро пожаловать в систему</span></p>
        <br>
        <p>Перечень Ваших прав:</p>
        <p>Объект1: Полные права &nbsp;<span style="color:var(--muted);font-size:10px">(7 = 111₂)</span></p>
        <p>Объект2: Полные права</p>
        <p>Объект3: Полные права</p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">quit</span></p>
        <p>Работа пользователя Sergey завершена. До свидания.</p>
      </div>
      <div class="exbox" style="margin-top:10px">
        <p><span class="st">User:</span> Boris</p>
        <p>Объект1: Чтение (4 = 100₂) · Объект2: Запрет (0) · Объект3: Полные права (7 = 111₂)</p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">read</span></p>
        <p>Над каким объектом? <span class="rs">1</span></p>
        <p>Проверка: 4 & 4 = 4 ≠ 0 → <span class="ok2">Операция прошла успешно</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">write</span></p>
        <p>Над каким объектом? <span class="rs">2</span></p>
        <p>Проверка: 0 & 2 = 0 → <span class="er2">Отказ. У Вас нет прав для её осуществления</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">grant</span></p>
        <p>Объект: <span class="rs">3</span> · Право: <span class="rs">read</span> · Кому: <span class="rs">Ivan</span></p>
        <p>G-бит: 7 & 1 = 1 ≠ 0 ✓ · R-бит: 7 & 4 = 4 ≠ 0 ✓</p>
        <p>M[Ivan][3] = M[Ivan][3] | 4 → <span class="ok2">Операция прошла успешно</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">quit</span></p>
        <p>Работа пользователя Boris завершена. До свидания.</p>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Пример вычисления бита (метод деления)</div>
      <p style="font-size:12px;line-height:1.9">
        Задача: проверить право <strong>Записи</strong>, M[i][j] = <strong>3</strong>.<br>
        Запись = бит₂ (n=2). Делим: <code>3 ÷ 2^(2-1) = 3 ÷ 2 = 1</code> (целая часть).<br>
        1 — нечётное → бит₂ = 1 → <strong style="color:var(--g)">доступ по записи разрешён ✓</strong><br>
        Проверка через AND: <code>3 & 2 = 2 ≠ 0</code> — тот же результат.
      </p>
    </div>
  </div>
</div>

<script>
function swM(name, btn) {{
  document.querySelectorAll('.mtab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.mpanel').forEach(p=>p.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('mp-'+name).classList.add('on');
}}
function tqa(el) {{
  const a = el.nextElementSibling;
  const open = a.style.display==='block';
  a.style.display = open?'none':'block';
  el.classList.toggle('open',!open);
}}
</script>"""
    return page("Теория — ДМБ", "", content)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    print(f"\n{'='*45}")
    print(f"  ДМБ Лабораторная №2 — Вариант 6")
    print(f"  Субъектов: {NUM_USERS}  |  Объектов: {NUM_OBJECTS}")
    print(f"  http://127.0.0.1:5000")
    print(f"{'='*45}\n")
    app.run(debug=True)
