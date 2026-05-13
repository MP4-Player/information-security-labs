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
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Unbounded:wght@700;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#07090f; --card:#0f1621; --border:#1a2236;
  --text:#e2e8f0; --muted:#55677d;
  --r:#ff4d6d; --g:#00d4aa; --b:#3b82f6; --warn:#f59e0b;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'JetBrains Mono',monospace;background:var(--bg);color:var(--text);min-height:100vh}
body::before{content:'';position:fixed;inset:0;pointer-events:none;
  background:
    radial-gradient(ellipse 60% 40% at 10% 0%,   rgba(255,77,109,.10) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 90% 100%,  rgba(59,130,246,.10) 0%,transparent 60%),
    radial-gradient(ellipse 40% 30% at 50%  50%,  rgba(0,212,170,.06) 0%,transparent 70%);}
nav{position:sticky;top:0;z-index:99;background:rgba(7,9,15,.95);border-bottom:1px solid var(--border);
    backdrop-filter:blur(14px);padding:13px 28px;display:flex;align-items:center;justify-content:space-between}
.brand{font-family:'Unbounded',sans-serif;font-size:12px;
  background:linear-gradient(90deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.nav-links{display:flex;gap:4px}
.nl{padding:5px 13px;font-size:11px;letter-spacing:1px;text-transform:uppercase;
  color:var(--muted);text-decoration:none;border:1px solid transparent;border-radius:4px;transition:.2s}
.nl:hover{color:var(--text);border-color:var(--border)}
.nl.red:hover{color:var(--r);border-color:rgba(255,77,109,.3)}
.chip{display:flex;align-items:center;gap:7px;background:var(--card);border:1px solid var(--border);
  border-radius:20px;padding:5px 13px;font-size:12px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--g);animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.wrap{max-width:860px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:22px;margin-bottom:16px}
.grad-rgb{background:linear-gradient(90deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.ph h1{font-family:'Unbounded',sans-serif;font-size:19px;font-weight:700;margin-bottom:6px}
.ph h1 span{color:var(--g)}
.ph p{font-size:11px;color:var(--muted);line-height:1.75}
.info-blue{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);border-radius:8px;
  padding:14px 18px;font-size:12px;line-height:1.85;color:#93c5fd;margin-bottom:16px}
.info-blue strong{color:#60a5fa}
.info-warn{background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.25);border-radius:8px;
  padding:12px 16px;font-size:12px;line-height:1.85;color:#fcd34d;margin-bottom:16px}
.info-ok{background:rgba(0,212,170,.07);border:1px solid rgba(0,212,170,.25);border-radius:8px;
  padding:12px 16px;font-size:12px;line-height:1.85;color:#6ee7d0;margin-bottom:16px}
.btn{padding:10px 22px;border:none;border-radius:6px;font-family:'JetBrains Mono',monospace;
  font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:.2s}
.btn-g{background:var(--g);color:#07090f}
.btn-g:hover{background:#00f5c4;box-shadow:0 4px 18px rgba(0,212,170,.3);transform:translateY(-1px)}
.btn-g:disabled{background:#1e3a35;color:#2a5a50;cursor:not-allowed;transform:none}
.btn-r{background:var(--r);color:#fff}
.btn-r:hover{background:#ff6b85}
.btn-gray{background:var(--border);color:var(--text);margin-right:8px}
.btn-gray:hover{background:#273346}
select,input[type=text]{padding:9px 13px;background:#111827;border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;
  transition:.2s;width:100%}
select:focus,input:focus{outline:none;border-color:var(--g)}
select option{background:#1e293b}
.fgroup{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.flabel{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--muted)}
.result{margin-top:14px;padding:15px;border-radius:7px;font-size:13px;line-height:1.8}
.result.ok{background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.25);color:#6ee7d0}
.result.err{background:rgba(255,77,109,.08);border:1px solid rgba(255,77,109,.25);color:#fca5a5}
/* LOGIN */
.login-body{min-height:100vh;display:flex;align-items:center;justify-content:center}
.lw{width:500px;position:relative;z-index:1}
.badge{display:inline-flex;align-items:center;gap:7px;background:rgba(0,212,170,.09);
  border:1px solid rgba(0,212,170,.25);border-radius:4px;padding:4px 12px;font-size:10px;
  color:var(--g);letter-spacing:2px;text-transform:uppercase;margin-bottom:18px}
.badge::before{content:'';width:6px;height:6px;background:var(--g);border-radius:50%;animation:blink 2s infinite}
.lh1{font-family:'Unbounded',sans-serif;font-size:24px;font-weight:900;line-height:1.2;margin-bottom:7px}
.lsub{font-size:11px;color:var(--muted);margin-bottom:24px;line-height:1.7}
.lsub span{color:var(--warn)}
.err-box{display:flex;align-items:center;gap:9px;background:rgba(255,77,109,.09);
  border:1px solid rgba(255,77,109,.28);border-radius:6px;padding:11px 15px;
  font-size:13px;color:#fca5a5;margin-bottom:14px}
.sec{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);
  display:flex;align-items:center;gap:10px;margin-bottom:12px}
.sec::after{content:'';flex:1;height:1px;background:var(--border)}
/* GRID CANVAS WRAPPER */
.canvas-wrap{
  display:flex;flex-direction:column;align-items:center;gap:12px;margin:16px 0;
}
#gk-canvas{
  border-radius:12px;
  border:2px solid var(--border);
  background:#0a0f1a;
  cursor:crosshair;
  touch-action:none;
  display:block;
}
.status-row{display:flex;align-items:center;justify-content:space-between;width:360px}
.pts-count{font-size:12px;color:var(--muted)}
.pts-count span{color:var(--g);font-weight:700}
/* USERS TABLE */
.utbl{width:100%;border-collapse:collapse;font-size:12px}
.utbl th,.utbl td{padding:10px 12px;border-bottom:1px solid var(--border);text-align:left}
.utbl th{color:var(--muted);font-size:10px;letter-spacing:1px;text-transform:uppercase}
.utbl tr:last-child td{border-bottom:none}
/* ATTEMPTS DOTS */
.att-row{display:flex;gap:6px;margin:8px 0}
.att-d{width:10px;height:10px;border-radius:50%;background:var(--border)}
.att-d.used{background:var(--r)}
.att-d.ok{background:var(--g)}
</style>"""

def nav_html(u=""):
    chip = f'<div class="chip"><div class="dot"></div>{u}</div>' if u else ''
    ls = [("/dashboard","Главная",""),("/register","Регистрация",""),
          ("/users","Пользователи",""),("/logout","Выход","red")]
    lh = "".join(f'<a href="{h}" class="nl {c}">{l}</a>' for h,l,c in ls)
    return f'<nav><div class="brand">ГК · Графический ключ</div><div class="nav-links">{lh}</div>{chip}</nav>'

def page(title, content, login=False, user=""):
    bc  = "login-body" if login else ""
    nav = "" if login else nav_html(user)
    return f"""<!DOCTYPE html>
<html lang="ru"><head><title>{title}</title>{BASE_STYLE}</head>
<body class="{bc}">{nav}{content}</body></html>"""

# ─── Canvas JS (общий для регистрации и авторизации) ─────────────────────────
def canvas_js(mode: str, username: str = "", min_pts: int = MIN_POINTS) -> str:
    """
    mode: 'register' | 'auth'
    Рисует сетку 3×3, позволяет провести паттерн.
    Линия градиентная: красный → зелёный → синий.
    Умная логика: автовставка промежуточных точек.
    """
    return f"""
<script>
(function(){{
const MODE      = '{mode}';
const USERNAME  = {json.dumps(username)};
const MIN_PTS   = {min_pts};
const canvas    = document.getElementById('gk-canvas');
const ctx       = canvas.getContext('2d');
const SIZE      = 360;
canvas.width    = SIZE;
canvas.height   = SIZE;

// Центры 9 точек в пикселях
const COLS = 3, ROWS = 3;
const PAD  = 60;
const STEP = (SIZE - PAD*2) / (COLS-1);
const pts  = [];
for(let r=0;r<ROWS;r++) for(let c=0;c<COLS;c++)
  pts.push({{x: PAD + c*STEP, y: PAD + r*STEP, idx: r*COLS+c}});

// Цвета градиента по прогрессу t∈[0,1]: красный→зелёный→синий
function gradColor(t){{
  let r,g,b;
  if(t < 0.5){{
    const s = t/0.5;
    r = Math.round(255*(1-s));
    g = Math.round(212*s);
    b = Math.round(109*(1-s));
  }} else {{
    const s = (t-0.5)/0.5;
    r = Math.round(0);
    g = Math.round(212*(1-s));
    b = Math.round(59 + 197*s);
  }}
  return `rgb(${{r}},${{g}},${{b}})`;
}}

// Состояние
let pattern  = [];   // индексы нажатых точек (расширенные)
let rawPts   = [];   // индексы в порядке касания (до расширения)
let dragging = false;
let cursorX  = 0, cursorY = 0;
let regAttempts = [];  // для регистрации: несколько вводов

// Промежуточная точка между двумя точками
function betweenIdx(a, b){{
  const ax=pts[a].x, ay=pts[a].y;
  const bx=pts[b].x, by=pts[b].y;
  const mx=(ax+bx)/2, my=(ay+by)/2;
  for(let i=0;i<pts.length;i++){{
    if(Math.abs(pts[i].x-mx)<1 && Math.abs(pts[i].y-my)<1) return i;
  }}
  return -1;
}}

// Расширение паттерна
function expand(raw){{
  const result=[], visited=new Set();
  for(const pt of raw){{
    if(visited.has(pt)) continue;
    if(result.length){{
      const mid = betweenIdx(result[result.length-1], pt);
      if(mid!==-1 && !visited.has(mid)){{ result.push(mid); visited.add(mid); }}
    }}
    result.push(pt); visited.add(pt);
  }}
  return result;
}}

// Ближайшая незадействованная точка в радиусе r
function nearest(x, y, r){{
  let best=-1, bd=Infinity;
  for(const p of pts){{
    if(pattern.includes(p.idx)) continue;
    const d=Math.hypot(p.x-x, p.y-y);
    if(d<r && d<bd){{ bd=d; best=p.idx; }}
  }}
  return best;
}}

// ── РИСОВАНИЕ ───────────────────────────────────────────────────────────────
function draw(){{
  ctx.clearRect(0,0,SIZE,SIZE);
  const n = pattern.length;
  const total = n + (dragging ? 1 : 0) - 1;

  // Линии между точками паттерна
  for(let i=1;i<n;i++){{
    const a=pts[pattern[i-1]], b=pts[pattern[i]];
    const t0=(i-1)/Math.max(total,1), t1=i/Math.max(total,1);
    const grad = ctx.createLinearGradient(a.x,a.y,b.x,b.y);
    grad.addColorStop(0, gradColor(t0));
    grad.addColorStop(1, gradColor(t1));
    ctx.beginPath();
    ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
    ctx.strokeStyle = grad;
    ctx.lineWidth   = 4;
    ctx.lineCap     = 'round';
    ctx.shadowColor = gradColor((t0+t1)/2);
    ctx.shadowBlur  = 8;
    ctx.stroke();
    ctx.shadowBlur  = 0;
  }}

  // Линия к курсору (во время рисования)
  if(dragging && n>0){{
    const last = pts[pattern[n-1]];
    const t0 = (n-1)/Math.max(total,1);
    ctx.beginPath();
    ctx.moveTo(last.x,last.y); ctx.lineTo(cursorX,cursorY);
    ctx.strokeStyle = gradColor(t0);
    ctx.lineWidth   = 3;
    ctx.setLineDash([6,4]);
    ctx.stroke();
    ctx.setLineDash([]);
  }}

  // Точки сетки
  for(const p of pts){{
    const active  = pattern.includes(p.idx);
    const order   = pattern.indexOf(p.idx);
    const t       = active && total>0 ? order/total : 0;

    // Внешнее кольцо
    ctx.beginPath();
    ctx.arc(p.x, p.y, active ? 18 : 14, 0, Math.PI*2);
    ctx.strokeStyle = active ? gradColor(t) : '#1e293b';
    ctx.lineWidth   = active ? 2.5 : 1.5;
    if(active){{ ctx.shadowColor=gradColor(t); ctx.shadowBlur=12; }}
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Внутренний круг
    ctx.beginPath();
    ctx.arc(p.x, p.y, active ? 8 : 5, 0, Math.PI*2);
    ctx.fillStyle = active ? gradColor(t) : '#2a3a50';
    ctx.fill();

    // Номер точки (порядок)
    if(active){{
      ctx.font      = 'bold 10px JetBrains Mono,monospace';
      ctx.fillStyle = '#07090f';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(order+1, p.x, p.y);
    }}
  }}

  // Счётчик точек
  const el = document.getElementById('pt-count');
  if(el) el.textContent = pattern.length;
}}

// ── СОБЫТИЯ ──────────────────────────────────────────────────────────────────
function getPos(e){{
  const r = canvas.getBoundingClientRect();
  const cl = e.touches ? e.touches[0] : e;
  return {{x: (cl.clientX - r.left)*(SIZE/r.width),
           y: (cl.clientY - r.top)*(SIZE/r.height)}};
}}

function onStart(e){{
  e.preventDefault();
  const {{x,y}} = getPos(e);
  pattern=[]; rawPts=[];
  dragging=true;
  const hit=nearest(x,y,30);
  if(hit!==-1){{ rawPts.push(hit); pattern=expand(rawPts); }}
  cursorX=x; cursorY=y;
  draw();
}}

function onMove(e){{
  if(!dragging) return;
  e.preventDefault();
  const {{x,y}} = getPos(e);
  cursorX=x; cursorY=y;
  const hit=nearest(x,y,28);
  if(hit!==-1 && !rawPts.includes(hit)){{
    rawPts.push(hit);
    pattern=expand(rawPts);
  }}
  draw();
}}

function onEnd(e){{
  if(!dragging) return;
  dragging=false;
  draw();
  if(pattern.length >= MIN_PTS) handleComplete();
  else {{
    showMsg('Проведите через минимум '+MIN_PTS+' точки', false);
    setTimeout(()=>{{ pattern=[]; rawPts=[]; draw(); }}, 1200);
  }}
}}

canvas.addEventListener('mousedown',  onStart);
canvas.addEventListener('mousemove',  onMove);
canvas.addEventListener('mouseup',    onEnd);
canvas.addEventListener('mouseleave', onEnd);
canvas.addEventListener('touchstart', onStart, {{passive:false}});
canvas.addEventListener('touchmove',  onMove,  {{passive:false}});
canvas.addEventListener('touchend',   onEnd);

function showMsg(text, ok){{
  const el = document.getElementById('gk-result');
  if(!el) return;
  el.className = 'result '+(ok?'ok':'err');
  el.textContent = (ok?'✓ ':'✗ ') + text;
  el.style.display='block';
}}

function resetCanvas(){{
  pattern=[]; rawPts=[]; dragging=false; draw();
  const el=document.getElementById('gk-result');
  if(el) el.style.display='none';
}}

// ── ОБРАБОТКА ЗАВЕРШЁННОГО ПАТТЕРНА ──────────────────────────────────────────
{_handle_complete_js(mode)}

draw(); // начальная отрисовка
window._resetCanvas = resetCanvas;
}})();
</script>"""


def _handle_complete_js(mode: str) -> str:
    if mode == 'register':
        return """
function handleComplete(){
  // Читаем username динамически в момент отправки — не из константы
  const uname = (typeof window._regUsername !== 'undefined' && window._regUsername)
                ? window._regUsername : USERNAME;
  if(!uname){
    showMsg('Имя пользователя не задано', false);
    setTimeout(()=>{ pattern=[]; rawPts=[]; draw(); }, 1400);
    return;
  }
  fetch('/api/reg_attempt',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username: uname, pattern: pattern})
  }).then(r=>r.json()).then(d=>{
    showMsg(d.message, d.success||d.pending);
    updateProgress(d.attempt, d.total_needed);
    if(d.success){ setTimeout(()=>window.location.href='/', 2000); return; }
    setTimeout(()=>{ pattern=[]; rawPts=[]; draw(); }, 1400);
  });
}
function updateProgress(done, need){
  const bar=document.getElementById('reg-bar');
  if(!bar) return;
  bar.innerHTML='';
  for(let i=0;i<need;i++){
    const d=document.createElement('div');
    d.className='att-d'+(i<done?' ok':'');
    bar.appendChild(d);
  }
}
"""
    else:
        return f"""
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
  const max={MAX_ATTEMPTS};
  for(let i=0;i<max;i++){{
    const d=document.createElement('div');
    d.className='att-d'+(i<(max-left)?' used':'');
    bar.appendChild(d);
  }}
}}
"""


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
      <div style="background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:14px;text-align:center">
        <div style="font-family:'Unbounded',sans-serif;font-size:24px;color:var(--g)">{info.get('pattern_len','?')}</div>
        <div style="font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-top:4px">Длина паттерна</div>
      </div>
      <div style="background:#0d1320;border:1px solid var(--border);border-radius:7px;padding:14px;text-align:center">
        <div style="font-size:13px;color:var(--text)">{info.get('registered','—')}</div>
        <div style="font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-top:4px">Дата регистрации</div>
      </div>
    </div>
    <div style="margin-top:12px;padding:10px 14px;background:#0d1320;border:1px solid var(--border);border-radius:6px;font-size:11px;color:var(--muted);word-break:break-all">
      SHA-256: <span style="color:var(--b)">{info.get('hash','—')[:32]}…</span>
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
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Свободный рисунок: <span>{username}</span></h1>
    <p>Нарисуйте ваш рисунок так же, как при регистрации.</p>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div style="display:flex;gap:8px;margin-bottom:20px">
    <a href="/auth" style="text-decoration:none;flex:1">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;
           padding:12px;text-align:center;font-size:12px;color:var(--muted)">
        ⬡ Сетка 3×3
      </div>
    </a>
    <div style="background:rgba(0,212,170,.08);border:1px solid var(--g);border-radius:8px;
         padding:12px;text-align:center;font-size:12px;color:var(--g);flex:1">
        ✏ Свободный рисунок ←
    </div>
  </div>

  <div class="info-blue">
    <strong>Алгоритм:</strong> рисунок нормализуется в квадрат [0,1]×[0,1]
    и ресэмплируется в {DRAW_SAMPLE_N} равноудалённых точек.
    Сравнение по среднему евклидову расстоянию (порог {DRAW_THRESHOLD}).
    Линия рисуется градиентом красный→зелёный→синий.
  </div>

  <div class="card" style="text-align:center">
    <div class="sec">// Нарисуйте ваш рисунок</div>
    <div class="canvas-wrap">
      <canvas id="draw-canvas" width="400" height="340"
        style="border-radius:10px;border:2px solid var(--border);
               background:#08101e;cursor:crosshair;touch-action:none;display:block">
      </canvas>
      <div class="status-row" style="width:400px">
        <div class="pts-count">Точек: <span id="pt-cnt">0</span></div>
        <div style="font-size:11px;color:var(--muted)">
          Попыток осталось: <span id="att-left">{left}</span>
        </div>
      </div>
      <div id="att-bar" class="att-row">{att_dots}</div>
    </div>
    <button class="btn btn-gray" onclick="resetDraw()">↺ Сброс</button>
    <button class="btn btn-g" id="submit-btn" onclick="submitDraw()" disabled style="margin-left:8px">
      → Проверить
    </button>
    <a href="/"><button class="btn btn-r" type="button" style="margin-left:8px">Отмена</button></a>
    <div id="draw-result" class="result" style="display:none"></div>
  </div>
</div>

{_draw_canvas_js('auth', username)}"""
    return page(f"Рисунок — {username}", content, user=username)


# ─── Страница: свободный рисунок (регистрация) ────────────────────────────────
@app.route('/draw_register')
def draw_register():
    session.pop('draw_reg_pts', None)

    content = f"""
<div class="wrap">
  <div class="ph" style="margin-bottom:20px">
    <h1>Регистрация: <span>свободный рисунок</span></h1>
    <p>Введите имя и нарисуйте рисунок {REG_NEEDED} раза одинаково.</p>
  </div>

  <!-- ВКЛАДКИ РЕЖИМОВ -->
  <div style="display:flex;gap:8px;margin-bottom:20px">
    <a href="/register" style="text-decoration:none;flex:1">
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;
           padding:12px;text-align:center;font-size:12px;color:var(--muted)">
        ⬡ Сетка 3×3
      </div>
    </a>
    <div style="background:rgba(0,212,170,.08);border:1px solid var(--g);border-radius:8px;
         padding:12px;text-align:center;font-size:12px;color:var(--g);flex:1">
        ✏ Свободный рисунок ←
    </div>
  </div>

  <div class="info-warn">
    ⚠ Нарисуйте <strong>одинаковый рисунок {REG_NEEDED} раза</strong>.
    Не нужно быть точным до пикселя — алгоритм нормализует и ресэмплирует рисунок.
    Порог сравнения: {DRAW_THRESHOLD} (0 = идеально, 1 = совершенно разные).
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
    <div class="sec">// Шаг 2 — Нарисуйте рисунок</div>
    <div class="canvas-wrap">
      <canvas id="draw-canvas" width="400" height="340"
        style="border-radius:10px;border:2px solid var(--border);
               background:#08101e;cursor:crosshair;touch-action:none;display:block">
      </canvas>
      <div class="status-row" style="width:400px">
        <div class="pts-count">Точек: <span id="pt-cnt">0</span></div>
        <div id="reg-bar" class="att-row"></div>
      </div>
    </div>
    <button class="btn btn-gray" onclick="resetDraw()">↺ Сброс</button>
    <button class="btn btn-g" id="submit-btn" onclick="submitDraw()" disabled style="margin-left:8px">
      → Записать попытку
    </button>
    <div id="draw-result" class="result" style="display:none"></div>
  </div>
</div>

<script>
let drUsername = '';
function checkName(){{
  const val = document.getElementById('uname-inp').value.trim();
  const err = document.getElementById('name-err');
  if(!val || val.length<2){{ err.textContent='Имя слишком короткое'; err.style.display='block'; return; }}
  if(!/^[a-zA-Z0-9_]+$/.test(val)){{ err.textContent='Только латиница, цифры и _'; err.style.display='block'; return; }}
  err.style.display='none';
  fetch('/api/check_user',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{username:val}})}}).then(r=>r.json()).then(d=>{{
    if(d.exists){{ err.textContent='Пользователь уже существует'; err.style.display='block'; return; }}
    drUsername = val;
    document.getElementById('step-name').style.display='none';
    document.getElementById('step-draw').style.display='block';
  }});
}}
document.getElementById('uname-inp').addEventListener('keypress',e=>{{ if(e.key==='Enter') checkName(); }});
</script>
{_draw_canvas_js('register', '__DR_USER__')}"""
    return page("Регистрация рисунок — ГК", content)


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

// Фоновая сетка (тонкие линии)
function drawBg(){{
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle = 'rgba(30,41,59,0.6)';
  ctx.lineWidth   = 0.5;
  for(let x=0;x<W;x+=40){{ ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke(); }}
  for(let y=0;y<H;y+=40){{ ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke(); }}
}}

// Цвет по прогрессу пути 0..1 (красный→зелёный→синий)
function gradColor(t){{
  let r,g,b;
  if(t<0.5){{
    const s=t/0.5; r=Math.round(255*(1-s)); g=Math.round(212*s); b=Math.round(109*(1-s));
  }}else{{
    const s=(t-0.5)/0.5; r=0; g=Math.round(212*(1-s)); b=Math.round(59+197*s);
  }}
  return `rgb(${{r}},${{g}},${{b}})`;
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

  let acc = 0; // накопленная длина до текущего сегмента
  for(let si=0; si<segments.length; si++){{
    const seg = segments[si];
    if(seg.length < 2) continue;
    let segAcc = 0;
    for(let i=1;i<seg.length;i++){{
      const a=seg[i-1], b=seg[i];
      const d=Math.hypot(b.x-a.x,b.y-a.y);
      const t0=(acc+segAcc)/grand, t1=(acc+segAcc+d)/grand;
      const grad=ctx.createLinearGradient(a.x,a.y,b.x,b.y);
      grad.addColorStop(0, gradColor(t0));
      grad.addColorStop(1, gradColor(t1));
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
      ctx.strokeStyle=grad; ctx.lineWidth=3.5; ctx.lineCap='round'; ctx.lineJoin='round';
      ctx.shadowColor=gradColor((t0+t1)/2); ctx.shadowBlur=6;
      ctx.stroke(); ctx.shadowBlur=0;
      segAcc+=d;
    }}
    // Точка начала каждого сегмента (кроме продолжения)
    const sp=seg[0];
    const t=acc/grand;
    ctx.beginPath(); ctx.arc(sp.x,sp.y,4,0,Math.PI*2);
    ctx.fillStyle=gradColor(t); ctx.fill();
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