# -*- coding: utf-8 -*-
"""
Лабораторная работа №3 — Мандатная модель политики безопасности
Вариант 6: 8 субъектов, 3 объекта (берём из ЛР №2)
БЕЗ Jinja2 — весь HTML через f-строки Python
"""

import random
from flask import Flask, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'lab3_mandatory_v6'

# ======== ВАРИАНТ 6 ========
NUM_USERS   = 8
NUM_OBJECTS = 3

LEVELS = ["Открытые данные", "Секретно", "Совершенно секретно"]
LEVEL_SHORT = ["Откр.", "Секр.", "СС"]

USERS = ['admin', 'Sergey', 'Ivan', 'Boris', 'Anna', 'Maria', 'Dmitry', 'Elena']

# Уровни допуска субъектов — случайные при старте (кроме admin = макс)
random.seed()
USER_LEVELS_LIST = [2] + [random.randint(0, 2) for _ in range(NUM_USERS - 1)]
USER_LEVELS = {u: USER_LEVELS_LIST[i] for i, u in enumerate(USERS)}

# Уровни конфиденциальности объектов — случайные при старте
OBJECT_NAMES  = [f"Объект_{i}" for i in range(1, NUM_OBJECTS + 1)]
OBJECT_LEVELS = [random.randint(0, 2) for _ in OBJECT_NAMES]

print("\n" + "="*50)
print("  ЛР №3 — Мандатная модель · Вариант 6")
print(f"  Субъектов: {NUM_USERS}  |  Объектов: {NUM_OBJECTS}")
print("  Уровни объектов (O):")
for i, name in enumerate(OBJECT_NAMES):
    print(f"    {name}: {LEVELS[OBJECT_LEVELS[i]]}")
print("  Уровни допуска субъектов (S):")
for u in USERS:
    print(f"    {u}: {LEVELS[USER_LEVELS[u]]}")
print(f"  http://127.0.0.1:5000")
print("="*50 + "\n")

# ─────────────────── ОБЩИЙ CSS ───────────────────
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
    --r:#ff4d6d;
    --g:#00d4aa;
    --b:#3b82f6;
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
  /* NAV */
  nav{position:sticky;top:0;z-index:99;background:rgba(7,9,15,.92);border-bottom:1px solid var(--border);
      backdrop-filter:blur(14px);padding:13px 28px;display:flex;align-items:center;justify-content:space-between}
  .brand{font-family:'Unbounded',sans-serif;font-size:12px;letter-spacing:.5px;
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
  /* LAYOUT */
  .wrap{max-width:1050px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}
  /* CARD */
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:22px;margin-bottom:16px}
  .card-title{font-family:'Unbounded',sans-serif;font-size:13px;font-weight:700;margin-bottom:4px}
  .card-sub{font-size:11px;color:var(--muted);margin-bottom:14px}
  /* PAGE HEADER */
  .ph{margin-bottom:24px}
  .ph h1{font-family:'Unbounded',sans-serif;font-size:19px;font-weight:700}
  .ph h1 span{color:var(--g)}
  .ph p{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.75}
  /* GRADIENTS */
  .grad-rgb{background:linear-gradient(90deg,var(--r),var(--g),var(--b));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  /* INFO BOX */
  .info-blue{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);border-radius:8px;
    padding:14px 18px;font-size:12px;line-height:1.85;color:#93c5fd;margin-bottom:18px}
  .info-blue strong{color:#60a5fa}
  .info-blue code{background:#0d1320;border:1px solid var(--border);border-radius:3px;padding:1px 6px;color:var(--warn);font-size:11px}
  /* SECTION LABEL */
  .sec{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);
    display:flex;align-items:center;gap:10px;margin-bottom:11px}
  .sec::after{content:'';flex:1;height:1px;background:var(--border)}
  /* BUTTONS */
  .btn{padding:10px 22px;border:none;border-radius:6px;font-family:'JetBrains Mono',monospace;
    font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:.2s}
  .btn-g{background:var(--g);color:#07090f}
  .btn-g:hover{background:#00f5c4;box-shadow:0 4px 18px rgba(0,212,170,.3);transform:translateY(-1px)}
  .btn-r{background:var(--r);color:#fff}
  .btn-r:hover{background:#ff6b85;box-shadow:0 4px 18px rgba(255,77,109,.3)}
  /* FORM */
  select,input[type=number]{padding:9px 13px;background:#111827;border:1px solid var(--border);
    border-radius:6px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;transition:.2s}
  select:focus,input:focus{outline:none;border-color:var(--g)}
  select option{background:#1e293b}
  .fgroup{display:flex;flex-direction:column;gap:5px}
  .flabel{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted)}
  .frow{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:12px}
  /* RESULT */
  .result{display:none;margin-top:14px;padding:15px;border-radius:7px;font-size:13px;line-height:1.8}
  .result.ok{background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.25);color:#6ee7d0}
  .result.err{background:rgba(255,77,109,.08);border:1px solid rgba(255,77,109,.25);color:#fca5a5}
  .result .expl{margin-top:9px;padding-top:9px;border-top:1px solid rgba(255,255,255,.07);
    font-size:11px;color:var(--muted);line-height:1.9}
  /* LEVEL BADGES */
  .lv0{background:rgba(0,212,170,.15);color:var(--g);border:1px solid rgba(0,212,170,.3);
    padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
  .lv1{background:rgba(245,158,11,.15);color:var(--warn);border:1px solid rgba(245,158,11,.3);
    padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
  .lv2{background:rgba(255,77,109,.15);color:var(--r);border:1px solid rgba(255,77,109,.3);
    padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
  /* ACCESS BADGES */
  .yes{color:var(--g);font-weight:700}
  .no{color:#2a3a50;font-weight:700}
  /* TABLE */
  .tover{overflow:auto;background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:16px}
  .dtable{width:100%;border-collapse:collapse;font-size:12px;min-width:400px}
  .dtable th{padding:11px 14px;font-size:10px;letter-spacing:1px;text-transform:uppercase;
    color:var(--muted);background:#0d1320;border-bottom:1px solid var(--border);text-align:left}
  .dtable td{padding:11px 14px;border-bottom:1px solid var(--border);vertical-align:middle}
  .dtable tr:last-child td{border-bottom:none}
  .dtable tr:hover td{background:rgba(0,212,170,.02)}
  .dtable td.center{text-align:center}
  /* OBJECTS GRID */
  .og{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-bottom:22px}
  .oc{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:17px;transition:.2s}
  .oc:hover{border-color:var(--g)}
  .oc.allow{border-left:3px solid var(--g)}
  .oc.deny{border-left:3px solid #1f2d3d}
  .oc .oname{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px}
  .oc .olevel{margin-bottom:8px}
  .oc .orule{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.6}
  /* TABS */
  .tabs{display:flex;gap:3px;border-bottom:1px solid var(--border);margin-bottom:16px}
  .tab{padding:7px 15px;font-size:11px;cursor:pointer;color:var(--muted);background:transparent;
    border:1px solid transparent;border-bottom:none;border-radius:4px 4px 0 0;
    font-family:'JetBrains Mono',monospace;transition:.2s;margin-bottom:-1px;letter-spacing:.5px}
  .tab:hover{color:var(--text)}
  .tab.on{color:var(--g);background:var(--card);border-color:var(--border);border-bottom-color:var(--card)}
  .tabp{display:none}.tabp.on{display:block}
  /* MAIN TABS (theory) */
  .mtabs{display:flex;gap:3px;border-bottom:1px solid var(--border);margin-bottom:22px}
  .mtab{padding:9px 19px;font-size:12px;cursor:pointer;color:var(--muted);background:transparent;
    border:1px solid transparent;border-bottom:none;border-radius:4px 4px 0 0;
    font-family:'JetBrains Mono',monospace;transition:.2s;margin-bottom:-1px}
  .mtab:hover{color:var(--text)}
  .mtab.on{color:var(--g);background:var(--bg);border-color:var(--border);border-bottom-color:var(--bg)}
  .mpanel{display:none}.mpanel.on{display:block}
  /* OP HINT */
  .op-hint{background:rgba(59,130,246,.05);border:1px solid rgba(59,130,246,.15);border-radius:6px;
    padding:11px 14px;font-size:11px;color:#93c5fd;line-height:1.85;margin-bottom:12px}
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
  /* EXAMPLE */
  .exbox{background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:15px;
    font-size:12px;line-height:1.9;margin-top:10px}
  .exbox .st{color:var(--g);font-weight:600}
  .exbox .rs{color:var(--warn)}
  .exbox .ok2{color:var(--g)}.exbox .er2{color:var(--r)}
  /* LOGIN */
  .login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
  .login-wrap{width:440px;position:relative;z-index:1}
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
  /* MATRIX CELLS */
  .mac-yes{background:rgba(0,212,170,.08);color:var(--g);font-weight:700;text-align:center}
  .mac-no{background:rgba(255,77,109,.05);color:#2a3a50;font-weight:700;text-align:center}
  /* USER LEVEL ROW */
  .urow-0 td{border-left:2px solid var(--g) !important}
  .urow-1 td:first-child{border-left:2px solid var(--warn)}
  .urow-2 td:first-child{border-left:2px solid var(--r)}
</style>"""

def level_badge(lv):
    cls = ['lv0','lv1','lv2'][lv]
    return f'<span class="{cls}">{LEVELS[lv]}</span>'

def page(title, content):
    username = session.get('username', '')
    chip = f'<div class="chip"><div class="dot"></div>{username}</div>' if username else ''
    links = ""
    for href, label, cls in [
        ("/dashboard", "Панель", ""),
        ("/matrix",    "Матрица", ""),
        ("/theory",    "Теория", ""),
        ("/logout",    "Выход", "red"),
    ]:
        links += f'<a href="{href}" class="nav-link {cls}">{label}</a>'
    return f"""<!DOCTYPE html>
<html lang="ru">
<head><title>{title}</title>{BASE_STYLE}</head>
<body>
<nav>
  <div class="brand">МАМ · Вариант 6</div>
  <div class="nav-links">{links}</div>
  {chip}
</nav>
{content}
</body></html>"""

# ─────────── LOGIN ───────────
@app.route('/')
def index():
    opts = "".join(
        f'<option value="{u}">{"⚡ " if u=="admin" else "○ "}{u}{"  (Администратор)" if u=="admin" else ""}</option>'
        for u in USERS
    )
    err = f'<div class="err-box">⚠ {request.args.get("err")}</div>' if request.args.get('err') else ''
    content = f"""
<div class="login-body">
<div class="login-wrap">
  <div class="badge">Мандатная модель безопасности</div>
  <div class="lh1 grad-rgb">Мандатная<br>политика безопасности</div>
  <p class="lsub">Лабораторная работа №3 · <span>Вариант 6</span><br>
  Правило доступа: уровень субъекта ≥ уровень объекта</p>
  {err}
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
    💡 Мандатная модель: уровни L = {{«Совершенно секретно», «Секретно», «Открытые данные»}}.<br>
    Доступ разрешён если <strong>S(субъект) ≥ O(объект)</strong>.
  </div>
</div>
</div>"""
    return page("Вход — МАМ", content)


@app.route('/login', methods=['POST'])
def login():
    u = request.form.get('username', '').strip()
    if u not in USERS:
        return redirect('/?err=Пользователь+не+найден+в+системе')
    session['username'] = u
    return redirect(url_for('dashboard'))

# ─────────── DASHBOARD ───────────
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']
    ul = USER_LEVELS[username]

    # Карточки объектов
    obj_cards = ""
    for j, name in enumerate(OBJECT_NAMES):
        ol = OBJECT_LEVELS[j]
        allowed = ul >= ol
        rule = f"S={ul} ≥ O={ol} → Разрешён" if allowed else f"S={ul} &lt; O={ol} → Запрещён"
        obj_cards += f"""
<div class="oc {'allow' if allowed else 'deny'}">
  <div class="oname">{name}</div>
  <div class="olevel">{level_badge(ol)}</div>
  <div class="orule">{rule}</div>
  <div style="margin-top:8px;font-size:13px;font-weight:700;color:{'var(--g)' if allowed else 'var(--r)'}">
    {'✓ Доступ разрешён' if allowed else '✗ Доступ запрещён'}
  </div>
</div>"""

    # select объектов
    obj_opts = "".join(
        f'<option value="{j+1}">{name}  [уровень: {LEVELS[OBJECT_LEVELS[j]]}]</option>'
        for j, name in enumerate(OBJECT_NAMES)
    )

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Субъект: <span>{username}</span></h1>
    <p>Мандатная модель · Уровень допуска: {level_badge(ul)} · {NUM_OBJECTS} объекта в системе</p>
  </div>
  <div class="info-blue">
    <strong>Правило мандатного доступа:</strong> субъект S получает доступ к объекту O только если
    <code>S(уровень допуска) ≥ O(уровень конфиденциальности)</code>.
    Ваш уровень: <strong>{LEVELS[ul]} ({ul})</strong>.
    Сравниваются числовые коды: 0=Открытые, 1=Секретно, 2=Совершенно секретно.
  </div>
  <div class="sec">// Доступ к объектам системы</div>
  <div class="og">{obj_cards}</div>

  <div class="card">
    <div class="card-title">// Жду ваших указаний</div>
    <div class="card-sub" style="margin-bottom:14px">
      Операция <strong>request</strong>: запрос доступа к объекту.
      Система проверит правило: <code>S({ul}) ≥ O(?)</code>
    </div>
    <div class="tabs">
      <button class="tab on" onclick="swTab('request',this)">request</button>
      <button class="tab" onclick="swTab('quit',this)" style="color:var(--r)">quit</button>
    </div>

    <div id="tp-request" class="tabp on">
      <div class="op-hint">
        <strong>request:</strong> запрос доступа к объекту. Условие: <code>USER_LEVELS[{username}]({ul}) ≥ OBJECT_LEVELS[j]</code>
      </div>
      <div class="frow">
        <div class="fgroup"><div class="flabel">Объект</div>
          <select id="req-obj">{obj_opts}</select></div>
        <button class="btn btn-g" onclick="exec_req()">→ Запросить доступ</button>
      </div>
    </div>

    <div id="tp-quit" class="tabp">
      <div class="op-hint" style="border-color:rgba(255,77,109,.2);background:rgba(255,77,109,.05);color:#fca5a5">
        <strong>quit:</strong> Завершает сеанс пользователя {username}.
      </div>
      <div style="margin-top:12px">
        <button class="btn btn-r" onclick="exec_quit()">→ Завершить сеанс</button>
      </div>
    </div>
    <div id="result" class="result"></div>
  </div>
</div>

<script>
function swTab(name,btn){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.tabp').forEach(p=>p.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('tp-'+name).classList.add('on');
  document.getElementById('result').style.display='none';
}}
function show(data){{
  const b=document.getElementById('result');
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
function exec_req(){{post({{operation:'request',object_num:document.getElementById('req-obj').value}});}}
function exec_quit(){{post({{operation:'quit'}});}}
</script>"""
    return page(f"Панель — {username}", content)


@app.route('/execute', methods=['POST'])
def execute():
    if 'username' not in session:
        return jsonify({'error': 'Сессия истекла'}), 401
    op = request.form.get('operation')
    username = session['username']
    ul = USER_LEVELS[username]

    if op == 'quit':
        session.clear()
        return jsonify({'quit': True, 'message': f'Работа пользователя {username} завершена. До свидания.'})

    if op == 'request':
        onum = request.form.get('object_num')
        if not onum:
            return jsonify({'error': 'Не указан объект'})
        try:
            oi = int(onum) - 1
            if not (0 <= oi < NUM_OBJECTS):
                return jsonify({'error': f'Объект от 1 до {NUM_OBJECTS}'})
        except ValueError:
            return jsonify({'error': 'Некорректный номер'})

        ol = OBJECT_LEVELS[oi]
        name = OBJECT_NAMES[oi]
        ok = ul >= ol

        expl = (
            f'Правило: S({username})={ul} [{LEVELS[ul]}] ≥ O({name})={ol} [{LEVELS[ol]}] → '
            f'{"Истина ✓ — доступ разрешён" if ok else "Ложь ✗ — доступ запрещён"}.'
        )
        return jsonify({
            'success': ok,
            'message': f'Операция прошла успешно. Доступ к {name} разрешён.' if ok
                       else f'Отказ в выполнении операции. Недостаточно прав.',
            'explanation': expl
        })

    return jsonify({'error': f'Неизвестная операция: {op}'})


# ─────────── MATRIX ───────────
@app.route('/matrix')
def show_matrix():
    if 'username' not in session:
        return redirect(url_for('index'))
    username = session['username']

    # Заголовки
    obj_headers = "".join(
        f'<th>{OBJECT_NAMES[j]}<br><span style="font-size:9px;color:var(--muted);font-weight:400">{LEVELS[OBJECT_LEVELS[j]]}</span></th>'
        for j in range(NUM_OBJECTS)
    )

    rows = ""
    for i, u in enumerate(USERS):
        ul = USER_LEVELS[u]
        cells = ""
        for j in range(NUM_OBJECTS):
            ol = OBJECT_LEVELS[j]
            ok = ul >= ol
            cells += f'<td class="{"mac-yes" if ok else "mac-no"}">{"✓" if ok else "✗"}</td>'
        you = f' <span style="color:var(--g);font-size:10px">← вы</span>' if u == username else ''
        adm = '⚡ ' if u == 'admin' else ''
        rows += f"""<tr>
  <td style="{'color:var(--warn)' if u=='admin' else ''}">{adm}{u}{you}</td>
  <td class="center">{level_badge(ul)}</td>
  {cells}
</tr>"""

    # Таблица уровней объектов
    obj_rows = "".join(
        f'<tr><td>{OBJECT_NAMES[j]}</td><td class="center">{j+1}</td><td class="center">{level_badge(OBJECT_LEVELS[j])}</td></tr>'
        for j in range(NUM_OBJECTS)
    )

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Матрица доступа <span>{NUM_OBJECTS}×{NUM_USERS}</span></h1>
    <p>Мандатная модель · Правило: S(субъект) ≥ O(объект) → доступ разрешён</p>
  </div>
  <div class="info-blue">
    <strong>Как читать матрицу:</strong> ✓ = уровень субъекта ≥ уровень объекта,
    ✗ = уровень субъекта &lt; уровень объекта. Числовые коды:
    <code>0=Открытые данные</code> <code>1=Секретно</code> <code>2=Совершенно секретно</code>.
  </div>
  <div class="tover">
    <table class="dtable">
      <thead>
        <tr>
          <th>Субъект</th>
          <th style="text-align:center">Уровень допуска</th>
          {obj_headers}
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="card">
    <div class="card-title">// Уровни объектов (вектор O)</div>
    <div class="tover" style="margin:0">
      <table class="dtable">
        <thead><tr><th>Объект</th><th style="text-align:center">№</th><th style="text-align:center">Уровень конфиденциальности</th></tr></thead>
        <tbody>{obj_rows}</tbody>
      </table>
    </div>
  </div>
  <div class="card">
    <div class="card-title">// Уровни субъектов (вектор S)</div>
    <div class="tover" style="margin:0">
      <table class="dtable">
        <thead><tr><th>Субъект</th><th style="text-align:center">Уровень допуска</th><th style="text-align:center">Код</th></tr></thead>
        <tbody>{"".join(f'<tr><td>{"⚡ " if u=="admin" else ""}{u}</td><td class="center">{level_badge(USER_LEVELS[u])}</td><td class="center" style="color:var(--warn)">{USER_LEVELS[u]}</td></tr>' for u in USERS)}</tbody>
      </table>
    </div>
  </div>
</div>"""
    return page("Матрица — МАМ", content)


# ─────────── THEORY ───────────
@app.route('/theory')
def theory():
    if 'username' not in session:
        return redirect(url_for('index'))

    # Вектор O и S для теории
    vec_o = "".join(
        f'<tr><td>{OBJECT_NAMES[j]}</td><td class="center">{level_badge(OBJECT_LEVELS[j])}</td><td class="center" style="color:var(--warn)">{OBJECT_LEVELS[j]}</td></tr>'
        for j in range(NUM_OBJECTS)
    )
    vec_s = "".join(
        f'<tr><td>{"⚡ " if u=="admin" else ""}{u}</td><td class="center">{level_badge(USER_LEVELS[u])}</td><td class="center" style="color:var(--warn)">{USER_LEVELS[u]}</td></tr>'
        for u in USERS
    )

    qa_data = [
        ("Что такое мандатная модель политики безопасности?",
         "Мандатная (принудительная) модель управления доступом (MAC — Mandatory Access Control) — "
         "политика безопасности, в которой права доступа определяются <strong>не владельцем объекта</strong>, "
         "а централизованно на основе меток безопасности (уровней конфиденциальности). "
         "Субъект не может изменять права доступа — они задаются администратором системы."),
        ("Что такое вектор O и вектор S?",
         "<strong>Вектор O</strong> — массив уровней конфиденциальности объектов системы.<br>"
         "Каждый объект O_j имеет атрибут безопасности из множества L.<br><br>"
         "<strong>Вектор S</strong> — массив уровней допуска субъектов (пользователей).<br>"
         "Каждый субъект S_i имеет уровень допуска из того же множества L.<br><br>"
         "В нашем варианте: L = {«Открытые данные» (0), «Секретно» (1), «Совершенно секретно» (2)}."),
        ("Каково основное правило мандатного доступа?",
         "Субъект S_i получает доступ к объекту O_j тогда и только тогда, когда:<br><br>"
         "<code>уровень_допуска(S_i) ≥ уровень_конфиденциальности(O_j)</code><br><br>"
         "То есть пользователь с уровнем «Секретно» (1) может читать объекты с уровнями "
         "«Открытые данные» (0) и «Секретно» (1), но <strong>не может</strong> получить доступ к объектам "
         "«Совершенно секретно» (2)."),
        ("Чем мандатная модель отличается от дискреционной?",
         "<strong>Дискреционная (DAC):</strong><br>"
         "— Права задаются явно в матрице [субъект × объект]<br>"
         "— Владелец сам управляет правами<br>"
         "— Права можно передавать (grant)<br>"
         "— Гибкая, но менее безопасная<br><br>"
         "<strong>Мандатная (MAC):</strong><br>"
         "— Права определяются уровнями секретности (метками)<br>"
         "— Централизованное управление, субъект не изменяет права<br>"
         "— Нет операции передачи прав<br>"
         "— Жёсткая, высокая степень защиты"),
        ("Как формируется матрица доступа в мандатной модели?",
         "Матрица M[i][j] вычисляется автоматически по правилу:<br><br>"
         "<code>M[i][j] = 1 (разрешён), если S_i ≥ O_j</code><br>"
         "<code>M[i][j] = 0 (запрещён), если S_i &lt; O_j</code><br><br>"
         "В отличие от дискреционной модели, матрица не хранит явные значения прав (0–7), "
         "а вычисляется на лету из векторов O и S."),
        ("Что такое множество атрибутов безопасности L?",
         "L = {«Совершенно секретно», «Секретно», «Открытые данные»} — упорядоченное множество.<br><br>"
         "Для удобства сравнения атрибуты кодируются числами:<br>"
         "<strong>2</strong> = Совершенно секретно (высший уровень)<br>"
         "<strong>1</strong> = Секретно<br>"
         "<strong>0</strong> = Открытые данные (низший уровень)<br><br>"
         "Упорядоченность позволяет использовать операцию сравнения ≥."),
        ("Почему уровни задаются случайно и при чём здесь seed?",
         "По условию задания (п. 1.2 и 1.3) вектора O и S заполняются случайным образом. "
         "Это моделирует реальную систему, где атрибуты безопасности назначаются при инициализации.<br><br>"
         "В учебных целях можно зафиксировать <code>random.seed(N)</code> для воспроизводимости результатов "
         "при повторных запусках — это важно для написания отчёта. Без фиксации seed матрица "
         "будет случайной при каждом запуске."),
        ("Параметры варианта 6 и связь с ЛР №2",
         f"По условию ЛР №3 используются параметры из ЛР №2:<br>"
         f"<strong>Субъектов:</strong> {NUM_USERS}<br>"
         f"<strong>Объектов:</strong> {NUM_OBJECTS}<br>"
         f"<strong>Субъекты:</strong> {', '.join(USERS)}<br><br>"
         "Уровни допуска субъектов (S) и уровни конфиденциальности объектов (O) "
         "задаются случайно из множества L при каждом запуске программы."),
    ]

    qa_html = "".join(
        f"""<div class="qa">
  <div class="qq" onclick="tqa(this)">{i+1}. {q}<span class="arr">▼</span></div>
  <div class="qa-a">{a}</div>
</div>"""
        for i, (q, a) in enumerate(qa_data)
    )

    content = f"""
<div class="wrap">
  <div class="ph">
    <h1>Теория и <span>ответы на вопросы</span></h1>
    <p>Лабораторная работа №3 · Мандатная модель · Вариант 6</p>
  </div>
  <div class="mtabs">
    <button class="mtab on" onclick="swM('theory',this)">Теория</button>
    <button class="mtab" onclick="swM('vectors',this)">Векторы O и S</button>
    <button class="mtab" onclick="swM('qa',this)">Контрольные вопросы</button>
    <button class="mtab" onclick="swM('example',this)">Пример прогонки</button>
  </div>

  <!-- ТЕОРИЯ -->
  <div id="mp-theory" class="mpanel on">
    <div class="card">
      <div class="card-title grad-rgb">Мандатная модель (MAC)</div>
      <div class="card-sub">Mandatory Access Control — принудительное управление доступом</div>
      <p style="font-size:13px;line-height:1.95;color:var(--text)">
        Мандатная политика безопасности основана на <strong style="color:var(--g)">метках безопасности</strong>
        (уровнях конфиденциальности), которые присваиваются как объектам, так и субъектам.
        Доступ определяется автоматически по правилу сравнения уровней — субъект не может
        изменить права доступа самостоятельно.
      </p>
    </div>
    <div class="card">
      <div class="card-title">Ключевые понятия</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px">
        <div style="background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:15px">
          <div style="font-size:10px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:8px">Множество L</div>
          <p style="font-size:12px;line-height:1.85">Упорядоченное множество атрибутов безопасности:<br>
          <span class="lv2">Совершенно секретно</span> = 2<br>
          <span class="lv1">Секретно</span> = 1<br>
          <span class="lv0">Открытые данные</span> = 0</p>
        </div>
        <div style="background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:15px">
          <div style="font-size:10px;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:8px">Правило доступа</div>
          <p style="font-size:12px;line-height:1.85">
          Субъект S_i → Объект O_j<br><br>
          <span style="color:var(--g)">✓</span> если <code>S_i ≥ O_j</code><br>
          <span style="color:var(--r)">✗</span> если <code>S_i &lt; O_j</code>
          </p>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Параметры варианта 6</div>
      <p style="font-size:13px;line-height:2;color:var(--text)">
        Субъектов: <strong style="color:var(--g)">{NUM_USERS}</strong> ·
        Объектов: <strong style="color:var(--g)">{NUM_OBJECTS}</strong><br>
        Субъекты: {', '.join(USERS)}<br>
        admin — уровень <span class="lv2">Совершенно секретно</span> (2) — максимальный допуск
      </p>
    </div>
  </div>

  <!-- ВЕКТОРЫ -->
  <div id="mp-vectors" class="mpanel">
    <div class="card">
      <div class="card-title">Вектор O — уровни конфиденциальности объектов</div>
      <div class="card-sub">Текущие значения (случайно сгенерированы при запуске)</div>
      <div class="tover" style="margin:0">
        <table class="dtable">
          <thead><tr><th>Объект</th><th style="text-align:center">Уровень</th><th style="text-align:center">Код</th></tr></thead>
          <tbody>{vec_o}</tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Вектор S — уровни допуска субъектов</div>
      <div class="card-sub">Текущие значения (случайно сгенерированы при запуске)</div>
      <div class="tover" style="margin:0">
        <table class="dtable">
          <thead><tr><th>Субъект</th><th style="text-align:center">Уровень</th><th style="text-align:center">Код</th></tr></thead>
          <tbody>{vec_s}</tbody>
        </table>
      </div>
    </div>
    <div class="info-blue">
      <strong>Замечание по реализации:</strong> Векторы O и S хранятся как списки Python.
      Проверка доступа: <code>USER_LEVELS[username] &gt;= OBJECT_LEVELS[object_index]</code>.
      Матрица доступа вычисляется динамически — не хранится явно.
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
      <div class="card-sub">Демонстрация работы мандатной модели</div>
      <div class="exbox">
        <p><span class="st">User:</span> admin</p>
        <p><span class="st">Идентификация прошла успешно, добро пожаловать в систему</span></p>
        <p>Уровень допуска: <span class="rs">Совершенно секретно (2)</span></p>
        <br>
        <p>Перечень доступных объектов:</p>
        <p>Объект_1, Объект_2, Объект_3 &nbsp;<span style="color:var(--muted);font-size:10px">(S=2 ≥ любой уровень O)</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">request</span></p>
        <p>К какому объекту хотите получить доступ? <span class="rs">1</span></p>
        <p>Проверка: S(admin)=2 ≥ O(Объект_1)=? → <span class="ok2">Операция прошла успешно</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">quit</span></p>
        <p>Работа пользователя admin завершена. До свидания.</p>
      </div>
      <div class="exbox" style="margin-top:10px">
        <p><span class="st">User:</span> Boris &nbsp;<span style="color:var(--muted);font-size:10px">(уровень: Открытые данные = 0)</span></p>
        <p><span class="st">Идентификация прошла успешно</span></p>
        <br>
        <p>Перечень доступных объектов:</p>
        <p><span style="color:var(--muted)">Только объекты с уровнем 0 (Открытые данные)</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">request</span></p>
        <p>К какому объекту? <span class="rs">Объект с уровнем 0</span></p>
        <p>Проверка: S(Boris)=0 ≥ O=0 → <span class="ok2">Операция прошла успешно</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">request</span></p>
        <p>К какому объекту? <span class="rs">Объект с уровнем 1</span></p>
        <p>Проверка: S(Boris)=0 &lt; O=1 → <span class="er2">Отказ. Недостаточно прав.</span></p>
        <br>
        <p>Жду ваших указаний &gt; <span class="rs">quit</span></p>
        <p>Работа пользователя Boris завершена. До свидания.</p>
      </div>
    </div>
  </div>
</div>

<script>
function swM(name,btn){{
  document.querySelectorAll('.mtab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.mpanel').forEach(p=>p.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('mp-'+name).classList.add('on');
}}
function tqa(el){{
  const a=el.nextElementSibling;
  const open=a.style.display==='block';
  a.style.display=open?'none':'block';
  el.classList.toggle('open',!open);
}}
</script>"""
    return page("Теория — МАМ", content)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
