# -*- coding: utf-8 -*-
"""
Лабораторная работа №8
Хеш-функция и электронная цифровая подпись (RSA)
Вариант 6: p=11, q=29, фамилия БУЛГАРОВ
Автор: Булгаров Марк Александрович
"""

import math
from flask import Flask

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════
#  МАТЕМАТИЧЕСКИЙ ДВИЖОК
# ══════════════════════════════════════════════════════════════════════

# Таблица кодов букв (А=1..Я=32, без Ъ)
RU_CODES = {
    'А':1,'Б':2,'В':3,'Г':4,'Д':5,'Е':6,'Ё':7,'Ж':8,'З':9,'И':10,
    'Й':11,'К':12,'Л':13,'М':14,'Н':15,'О':16,'П':17,'Р':18,'С':19,
    'Т':20,'У':21,'Ф':22,'Х':23,'Ц':24,'Ч':25,'Ш':26,'Щ':27,'Ы':28,
    'Ь':29,'Э':30,'Ю':31,'Я':32
}

def letter_code(ch):
    return RU_CODES.get(ch.upper(), 0)

def hash_step(H_prev, M_i, n):
    """H_i = (H_{i-1} + M_i)^2 mod n"""
    s = H_prev + M_i
    return (s * s) % n

def compute_hash_all(word, p, q):
    """Вычисляет хеш с сохранением всех шагов."""
    n = p * q
    steps = []
    H = 0  # H_0 = 0
    for i, ch in enumerate(word.upper()):
        M_i = letter_code(ch)
        H_prev = H
        s = H_prev + M_i
        H_new = (s * s) % n
        steps.append({
            'i': i + 1,
            'ch': ch,
            'M': M_i,
            'H_prev': H_prev,
            'sum': s,
            'sum2': s * s,
            'H': H_new,
        })
        H = H_new
    return H, steps

def gcd_extended(a, b):
    """Расширенный алгоритм Евклида. Возвращает (gcd, x, y)."""
    if b == 0:
        return a, 1, 0
    g, x1, y1 = gcd_extended(b, a % b)
    return g, y1, x1 - (a // b) * y1

def mod_inverse(e, phi):
    """Обратный элемент: d такой что e*d ≡ 1 (mod phi)."""
    g, x, _ = gcd_extended(e, phi)
    if g != 1:
        return None
    return x % phi

def find_e(phi_n):
    """Находим e: 1 < e < phi, gcd(e,phi)=1."""
    for e in range(2, phi_n):
        if math.gcd(e, phi_n) == 1:
            return e
    return None

def fast_pow_mod_steps(base, exp, mod):
    """
    Алгоритм быстрого возведения в степень по модулю (Right-to-Left).
    Возвращает (result, steps_list).
    """
    steps = []
    result = 1
    b = base % mod
    e = exp
    bit_num = 0
    bits = bin(exp)[2:]  # строка битов

    while e > 0:
        bit = e & 1
        steps.append({
            'bit_num': bit_num,
            'bit': bit,
            'e': e,
            'b': b,
            'result_before': result,
            'multiply': bit == 1,
        })
        if bit == 1:
            result = (result * b) % mod
        b = (b * b) % mod
        e >>= 1
        bit_num += 1

    return result, steps, bits

# ══════════════════════════════════════════════════════════════════════
#  ВЫЧИСЛЕНИЯ ДЛЯ ВАРИАНТА 6
# ══════════════════════════════════════════════════════════════════════

P, Q = 11, 29
N = P * Q                    # 319
PHI = (P - 1) * (Q - 1)     # 280
WORD = "БУЛГАРОВ"
WORD_PRIME  = "ВУЛГАРОВ"    # одна буква изменена Б→В
WORD_SWAP   = "УЛБГАРОВ"    # две буквы переставлены Б↔У

H_orig,  STEPS_orig  = compute_hash_all(WORD,       P, Q)
H_prime, STEPS_prime = compute_hash_all(WORD_PRIME, P, Q)
H_swap,  STEPS_swap  = compute_hash_all(WORD_SWAP,  P, Q)

E = find_e(PHI)
D = mod_inverse(E, PHI)

# Подпись S = H^d mod n
SIG, SIG_STEPS, SIG_BITS = fast_pow_mod_steps(H_orig, D, N)
# Верификация V = S^e mod n (должна совпасть с H_orig)
VER, VER_STEPS, VER_BITS = fast_pow_mod_steps(SIG,    E, N)

# ══════════════════════════════════════════════════════════════════════
#  СТИЛИ
# ══════════════════════════════════════════════════════════════════════

CSS = """
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
    radial-gradient(ellipse 60% 40% at 10% 0%,  rgba(255,77,109,.10) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 90% 100%, rgba(59,130,246,.10) 0%,transparent 60%),
    radial-gradient(ellipse 40% 30% at 50%  50%, rgba(0,212,170,.06) 0%,transparent 70%);}
.wrap{max-width:1000px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}
.hero{text-align:center;padding:40px 0 32px}
.hero-sub{font-size:11px;color:var(--muted);letter-spacing:3px;text-transform:uppercase;margin-bottom:12px}
.hero h1{font-family:'Unbounded',sans-serif;font-size:26px;font-weight:900;line-height:1.2;
  background:linear-gradient(90deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero p{font-size:12px;color:var(--muted);margin-top:10px;line-height:1.7}
/* ПАРАМЕТРЫ */
.params{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:28px}
.param{background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:16px;text-align:center}
.param-val{font-size:26px;font-weight:700;font-family:'Unbounded',sans-serif}
.param-lbl{font-size:9px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:5px}
/* СЕКЦИИ */
.section{margin-bottom:32px}
.sec-title{font-family:'Unbounded',sans-serif;font-size:13px;font-weight:700;
  padding:10px 0 8px;margin-bottom:16px;
  border-bottom:1px solid var(--border);
  background:linear-gradient(90deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
/* ФОРМУЛА КАРТОЧКА */
.formula-box{background:#0d1320;border:1px solid var(--border);border-radius:8px;
  padding:16px 20px;margin-bottom:16px;text-align:center;
  font-size:16px;letter-spacing:1px}
.formula-box .f-main{color:var(--g);font-size:18px;font-weight:700}
.formula-box .f-sub{color:var(--muted);font-size:11px;margin-top:6px}
/* ШАГ ХЕША */
.steps-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.step-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;
  position:relative;overflow:hidden}
.step-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px}
.step-card.s-r::before{background:var(--r)}
.step-card.s-g::before{background:var(--g)}
.step-card.s-b::before{background:var(--b)}
.step-num{font-size:10px;color:var(--muted);letter-spacing:1px;margin-bottom:8px}
.step-letter{font-size:28px;font-weight:700;margin-bottom:6px}
.step-calc{font-size:12px;line-height:2;color:var(--text)}
.step-calc .eq{color:var(--g);font-weight:700}
.step-calc .op{color:var(--warn)}
.step-calc .res{color:var(--b);font-weight:700;font-size:14px}
/* СРАВНЕНИЕ ХЕШЕЙ */
.hash-compare{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px}
.hash-box{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;text-align:center}
.hash-box .h-word{font-size:13px;font-weight:700;letter-spacing:2px;margin-bottom:8px}
.hash-box .h-val{font-family:'Unbounded',sans-serif;font-size:32px;font-weight:900;margin-bottom:6px}
.hash-box .h-note{font-size:10px;color:var(--muted);line-height:1.6}
.hash-box.changed{border-color:rgba(255,77,109,.4);background:rgba(255,77,109,.05)}
.hash-box.orig{border-color:rgba(0,212,170,.4);background:rgba(0,212,170,.05)}
/* RSA ПАРАМЕТРЫ */
.rsa-params{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:20px}
.rsa-p{background:var(--card);border:1px solid var(--border);border-radius:10px;
  padding:14px;text-align:center}
.rsa-p-val{font-size:22px;font-weight:700;color:var(--g)}
.rsa-p-lbl{font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-top:4px}
/* АЛГОРИТМ БЫСТРОГО ВОЗВЕДЕНИЯ */
.pow-table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:16px}
.pow-table th,.pow-table td{padding:9px 12px;border-bottom:1px solid var(--border);text-align:center}
.pow-table th{color:var(--muted);font-size:10px;letter-spacing:1px;text-transform:uppercase;
  background:#0d1320}
.pow-table tr:last-child td{border-bottom:none}
.pow-table .active-row td{background:rgba(0,212,170,.07)}
.pow-table .inactive-row td{color:var(--muted)}
.bit-1{color:var(--g);font-weight:700}
.bit-0{color:var(--muted)}
/* РЕЗУЛЬТАТ */
.result-block{background:#0d1320;border:1px solid var(--border);border-radius:12px;
  padding:24px;text-align:center;margin:16px 0}
.result-block .r-label{font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-bottom:10px}
.result-block .r-val{font-family:'Unbounded',sans-serif;font-size:42px;font-weight:900;
  background:linear-gradient(90deg,var(--r),var(--g),var(--b));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.result-block .r-check{margin-top:12px;font-size:13px}
.ok{color:var(--g)}
.err{color:var(--r)}
/* БИТОВАЯ СТРОКА */
.bits-row{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:14px;align-items:center}
.bit-cell{width:28px;height:28px;border-radius:4px;display:flex;align-items:center;
  justify-content:center;font-size:13px;font-weight:700}
.bit-cell.b1{background:rgba(0,212,170,.15);color:var(--g);border:1px solid rgba(0,212,170,.3)}
.bit-cell.b0{background:#0d1320;color:var(--muted);border:1px solid var(--border)}
.bits-label{font-size:10px;color:var(--muted);margin-right:6px}
/* НАВИГАЦИЯ */
.nav-tabs{display:flex;gap:6px;margin-bottom:28px;flex-wrap:wrap}
.tab{padding:8px 18px;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  border:1px solid var(--border);border-radius:6px;cursor:pointer;transition:.2s;text-decoration:none;
  color:var(--muted)}
.tab:hover,.tab.active{color:var(--text);border-color:var(--g);background:rgba(0,212,170,.08)}
.tab.t-r{color:var(--r)}.tab.t-r:hover,.tab.t-r.active{border-color:var(--r);background:rgba(255,77,109,.08)}
.tab.t-g{color:var(--g)}.tab.t-g:hover,.tab.t-g.active{border-color:var(--g);background:rgba(0,212,170,.08)}
.tab.t-b{color:var(--b)}.tab.t-b:hover,.tab.t-b.active{border-color:var(--b);background:rgba(59,130,246,.08)}
/* ВЕРИФИКАЦИЯ */
.verify-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px}
.verify-row .vr-label{font-size:11px;color:var(--muted);letter-spacing:1px;min-width:120px}
.verify-row .vr-val{font-size:18px;font-weight:700}
/* СЕКЦИЯ СКРЫТАЯ */
.sec-content{display:none}
.sec-content.show{display:block}
/* INFO BOX */
.info{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.2);border-radius:8px;
  padding:13px 16px;font-size:12px;line-height:1.85;color:#93c5fd;margin-bottom:16px}
.info strong{color:#60a5fa}
</style>"""

# ══════════════════════════════════════════════════════════════════════
#  ГЕНЕРАТОРЫ HTML-БЛОКОВ
# ══════════════════════════════════════════════════════════════════════

def color_class(i):
    return ['s-r','s-g','s-b'][i % 3]

def letter_color(i):
    return ['var(--r)','var(--g)','var(--b)'][i % 3]

def render_hash_steps(steps):
    cards = []
    for s in steps:
        cc = color_class(s['i'] - 1)
        lc = letter_color(s['i'] - 1)
        cards.append(f"""
<div class="step-card {cc}">
  <div class="step-num">ШАГ {s['i']}</div>
  <div class="step-letter" style="color:{lc}">{s['ch']}</div>
  <div class="step-calc">
    Код M<sub>{s['i']}</sub> = <span class="op">{s['M']}</span><br>
    H<sub>{s['i']-1}</sub> = <span class="op">{s['H_prev']}</span><br>
    H<sub>{s['i']-1}</sub> + M<sub>{s['i']}</sub> = {s['H_prev']} + {s['M']} = <span class="eq">{s['sum']}</span><br>
    ({s['sum']})<sup>2</sup> = <span class="op">{s['sum2']}</span><br>
    <span class="op">{s['sum2']}</span> mod {N} = <span class="res">{s['H']}</span>
  </div>
</div>""")
    return '<div class="steps-grid">' + ''.join(cards) + '</div>'


def render_bits(bits_str, label):
    cells = []
    for b in bits_str:
        cls = 'b1' if b == '1' else 'b0'
        cells.append(f'<div class="bit-cell {cls}">{b}</div>')
    return f'<div class="bits-row"><span class="bits-label">{label}:</span>{"".join(cells)}</div>'


def render_pow_table(steps, base, mod, result):
    rows = []
    for s in steps:
        active = 'active-row' if s['bit'] == 1 else 'inactive-row'
        bit_cls = 'bit-1' if s['bit'] == 1 else 'bit-0'
        mult_html = f'{s["result_before"]} × {s["b"]} mod {mod} = <b style="color:var(--g)">{(s["result_before"]*s["b"])%mod}</b>' if s['multiply'] else '—'
        rows.append(f"""<tr class="{active}">
  <td>{s['bit_num']}</td>
  <td class="{bit_cls}">{s['bit']}</td>
  <td>{s['e']}</td>
  <td>{s['b']}</td>
  <td>{s['result_before']}</td>
  <td>{mult_html}</td>
</tr>""")
    return f"""<table class="pow-table">
<thead><tr>
  <th>Бит №</th><th>Бит</th><th>e (текущий)</th>
  <th>b (основание²)</th><th>result до</th><th>Умножение (если бит=1)</th>
</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>"""


# ══════════════════════════════════════════════════════════════════════
#  ОСНОВНАЯ СТРАНИЦА
# ══════════════════════════════════════════════════════════════════════

@app.route('/')
def index():

    # ── Блок 1: Параметры ──────────────────────────────────────────────
    params_html = f"""
<div class="params">
  <div class="param"><div class="param-val" style="color:var(--r)">{P}</div><div class="param-lbl">p (простое)</div></div>
  <div class="param"><div class="param-val" style="color:var(--g)">{Q}</div><div class="param-lbl">q (простое)</div></div>
  <div class="param"><div class="param-val" style="color:var(--b)">{N}</div><div class="param-lbl">n = p·q</div></div>
  <div class="param"><div class="param-val" style="color:var(--warn)">{PHI}</div><div class="param-lbl">φ(n) = (p-1)(q-1)</div></div>
  <div class="param"><div class="param-val" style="color:var(--r)">{E}</div><div class="param-lbl">e (откр. ключ)</div></div>
  <div class="param"><div class="param-val" style="color:var(--g)">{D}</div><div class="param-lbl">d (закр. ключ)</div></div>
</div>"""

    # ── Блок 2: Хеш оригинала ─────────────────────────────────────────
    codes_row = "  ".join([f'<span style="color:{letter_color(i)}">{ch}={letter_code(ch)}</span>'
                            for i, ch in enumerate(WORD)])

    hash_steps_html = render_hash_steps(STEPS_orig)

    # ── Блок 3: Сравнение хешей ───────────────────────────────────────
    diff_note_prime = f"Изменена 1-я буква: Б→В (код {letter_code('Б')}→{letter_code('В')})"
    diff_note_swap  = f"Переставлены буквы 1↔2: Б↔У"

    hash_compare = f"""
<div class="hash-compare">
  <div class="hash-box orig">
    <div class="h-word" style="color:var(--g)">{WORD}</div>
    <div class="h-val" style="color:var(--g)">{H_orig}</div>
    <div class="h-note">Оригинал<br>h(M) = {H_orig}</div>
  </div>
  <div class="hash-box changed">
    <div class="h-word" style="color:var(--r)">{WORD_PRIME}</div>
    <div class="h-val" style="color:var(--r)">{H_prime}</div>
    <div class="h-note">Изменена 1 буква<br>h(M') = {H_prime}<br>
    <span style="color:var(--warn)">Δ = {abs(H_orig-H_prime)}</span></div>
  </div>
  <div class="hash-box changed">
    <div class="h-word" style="color:var(--b)">{WORD_SWAP}</div>
    <div class="h-val" style="color:var(--b)">{H_swap}</div>
    <div class="h-note">Перестановка 2 букв<br>h(M'') = {H_swap}<br>
    <span style="color:var(--warn)">Δ = {abs(H_orig-H_swap)}</span></div>
  </div>
</div>
<div class="info">
  <strong>Вывод о лавинном эффекте:</strong><br>
  h(БУЛГАРОВ) = <b style="color:var(--g)">{H_orig}</b>&nbsp; h(ВУЛГАРОВ) = <b style="color:var(--r)">{H_prime}</b>&nbsp; h(УЛБГАРОВ) = <b style="color:var(--b)">{H_swap}</b><br>
  Изменение одного символа изменяет хеш с {H_orig} на {H_prime} — значения {'совпадают ⚠' if H_orig==H_prime else 'различаются ✓'}.
  Перестановка двух символов даёт хеш {H_swap} — {'совпадает ⚠' if H_orig==H_swap else 'различается ✓'}.
  Хеш-функция {'не обладает' if H_orig==H_prime or H_orig==H_swap else 'обладает'} лавинным эффектом на данных примерах.
</div>"""

    # ── Блок 4: RSA-параметры ──────────────────────────────────────────
    rsa_params_html = f"""
<div class="info">
  <strong>Алгоритм выбора e:</strong> перебираем числа от 2 до φ(n)={PHI},
  выбираем первое e такое что НОД(e, φ(n))=1.<br>
  e={E}: НОД({E},{PHI}) = {math.gcd(E,PHI)} ✓<br>
  <strong>Алгоритм нахождения d:</strong> расширенный алгоритм Евклида.
  Находим d такое что e·d ≡ 1 (mod φ(n)).<br>
  {E}·{D} = {E*D} = {E*D // PHI}·{PHI} + {(E*D)%PHI}
  → {E*D}mod{PHI} = <b style="color:var(--g)">{(E*D)%PHI}</b>
  {'✓ d верно' if (E*D)%PHI==1 else '✗ ошибка'}
</div>
<div class="rsa-params">
  <div class="rsa-p"><div class="rsa-p-val" style="color:var(--r)">{E}</div><div class="rsa-p-lbl">e — открытый ключ</div></div>
  <div class="rsa-p"><div class="rsa-p-val" style="color:var(--g)">{D}</div><div class="rsa-p-lbl">d — закрытый ключ</div></div>
  <div class="rsa-p"><div class="rsa-p-val" style="color:var(--b)">{N}</div><div class="rsa-p-lbl">n — модуль</div></div>
  <div class="rsa-p"><div class="rsa-p-val" style="color:var(--warn)">{H_orig}</div><div class="rsa-p-lbl">H — хеш (подписываем)</div></div>
</div>"""

    # ── Блок 5: Подпись S = H^d mod n ─────────────────────────────────
    sig_bits_html  = render_bits(SIG_BITS[::-1], f'd={D} в двоичной')
    sig_table_html = render_pow_table(SIG_STEPS, H_orig, N, SIG)

    sig_html = f"""
<div class="formula-box">
  <div class="f-main">S = H<sup>d</sup> mod n = {H_orig}<sup>{D}</sup> mod {N}</div>
  <div class="f-sub">Вычисляется алгоритмом быстрого возведения в степень по модулю (Right-to-Left Binary)</div>
</div>
<div class="info">
  <strong>Алгоритм:</strong> разбиваем показатель d={D} в двоичный вид,
  обрабатываем биты справа налево.
  Если текущий бит = 1 → умножаем result на текущее основание (mod n).
  Затем возводим основание в квадрат (mod n). Переходим к следующему биту.
</div>
{sig_bits_html}
{sig_table_html}
<div class="result-block">
  <div class="r-label">Электронная подпись S = {H_orig}<sup>{D}</sup> mod {N}</div>
  <div class="r-val">{SIG}</div>
</div>"""

    # ── Блок 6: Верификация V = S^e mod n ─────────────────────────────
    ver_bits_html  = render_bits(VER_BITS[::-1], f'e={E} в двоичной')
    ver_table_html = render_pow_table(VER_STEPS, SIG, N, VER)

    ok_str = f'<span class="ok">✓ {VER} = {H_orig} — подпись ВЕРНА</span>' if VER == H_orig \
             else f'<span class="err">✗ {VER} ≠ {H_orig} — подпись НЕВЕРНА</span>'

    ver_html = f"""
<div class="formula-box">
  <div class="f-main">V = S<sup>e</sup> mod n = {SIG}<sup>{E}</sup> mod {N}</div>
  <div class="f-sub">Верификатор вычисляет V и сравнивает с исходным хешем H</div>
</div>
{ver_bits_html}
{ver_table_html}
<div class="result-block">
  <div class="r-label">Верифицированное значение V</div>
  <div class="r-val">{VER}</div>
  <div class="r-check">{ok_str}</div>
</div>"""

    # ── ИТОГОВАЯ СТРАНИЦА ──────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="ru"><head><title>ЛР8 — Хеш и ЭЦП | Булгаров</title>{CSS}</head>
<body>
<div class="wrap">

  <!-- HERO -->
  <div class="hero">
    <div class="hero-sub">Лабораторная работа №8 · Вариант 6</div>
    <h1>Хеш-функция и ЭЦП (RSA)</h1>
    <p>Фамилия: <b style="color:var(--g)">БУЛГАРОВ</b> &nbsp;·&nbsp;
       p={P}, q={Q}, n={N}, φ(n)={PHI}<br>
       e={E} (открытый ключ) &nbsp;·&nbsp; d={D} (закрытый ключ)</p>
  </div>

  <!-- ПАРАМЕТРЫ -->
  <div class="section">
    <div class="sec-title">ПАРАМЕТРЫ ВАРИАНТА</div>
    {params_html}
  </div>

  <!-- НАВИГАЦИЯ -->
  <div class="nav-tabs">
    <span onclick="show('hash')"    class="tab t-r active" id="tab-hash">1. Хеш БУЛГАРОВ</span>
    <span onclick="show('prime')"   class="tab t-g"        id="tab-prime">2. Хеш M' (1 буква)</span>
    <span onclick="show('swap')"    class="tab t-b"        id="tab-swap">3. Хеш M'' (перестановка)</span>
    <span onclick="show('compare')" class="tab"            id="tab-compare">4. Сравнение хешей</span>
    <span onclick="show('rsa')"     class="tab t-r"        id="tab-rsa">5. RSA-ключи</span>
    <span onclick="show('sign')"    class="tab t-g"        id="tab-sign">6. Подпись S</span>
    <span onclick="show('verify')"  class="tab t-b"        id="tab-verify">7. Верификация</span>
  </div>

  <!-- СЕКЦИЯ 1: Хеш оригинала -->
  <div id="sec-hash" class="sec-content show">
    <div class="sec-title">ШАГ 1 — Хеш-образ фамилии БУЛГАРОВ</div>
    <div class="formula-box">
      <div class="f-main">H<sub>i</sub> = (H<sub>i-1</sub> + M<sub>i</sub>)<sup>2</sup> mod n</div>
      <div class="f-sub">где n = p·q = {P}·{Q} = {N}, H<sub>0</sub> = 0</div>
    </div>
    <div class="info">
      <strong>Коды букв фамилии:</strong><br>
      {codes_row}
    </div>
    {hash_steps_html}
    <div class="result-block">
      <div class="r-label">Итоговый хеш h(БУЛГАРОВ)</div>
      <div class="r-val">{H_orig}</div>
    </div>
  </div>

  <!-- СЕКЦИЯ 2: Хеш M' -->
  <div id="sec-prime" class="sec-content">
    <div class="sec-title">ШАГ 2 — Хеш M' = {WORD_PRIME} (изменена 1 буква: Б→В)</div>
    <div class="info">
      <strong>Изменение:</strong> первая буква Б (код {letter_code('Б')}) заменена на В (код {letter_code('В')}).
      Остальные буквы без изменений.
    </div>
    {render_hash_steps(STEPS_prime)}
    <div class="result-block">
      <div class="r-label">h(M') = h({WORD_PRIME})</div>
      <div class="r-val" style="background:linear-gradient(90deg,var(--r),var(--warn));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent">{H_prime}</div>
    </div>
  </div>

  <!-- СЕКЦИЯ 3: Хеш M'' -->
  <div id="sec-swap" class="sec-content">
    <div class="sec-title">ШАГ 3 — Хеш M'' = {WORD_SWAP} (переставлены буквы 1↔2)</div>
    <div class="info">
      <strong>Изменение:</strong> буквы Б и У поменяны местами: БУЛГАРОВ → УЛБГАРОВ.
      Порядок букв нарушен, содержание — то же.
    </div>
    {render_hash_steps(STEPS_swap)}
    <div class="result-block">
      <div class="r-label">h(M'') = h({WORD_SWAP})</div>
      <div class="r-val" style="background:linear-gradient(90deg,var(--b),var(--g));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent">{H_swap}</div>
    </div>
  </div>

  <!-- СЕКЦИЯ 4: Сравнение -->
  <div id="sec-compare" class="sec-content">
    <div class="sec-title">СРАВНЕНИЕ ТРЁХ ХЕШ-ОБРАЗОВ</div>
    {hash_compare}
    <!-- Подробные шаги рядом -->
    <div class="info" style="margin-top:12px">
      <strong>M' (1 буква изменена):</strong> {diff_note_prime}<br>
      <strong>M'' (перестановка):</strong> {diff_note_swap}
    </div>
  </div>

  <!-- СЕКЦИЯ 5: RSA ключи -->
  <div id="sec-rsa" class="sec-content">
    <div class="sec-title">ШАГ 4 — Генерация ключей RSA</div>
    {rsa_params_html}
  </div>

  <!-- СЕКЦИЯ 6: Подпись -->
  <div id="sec-sign" class="sec-content">
    <div class="sec-title">ШАГ 5 — Вычисление подписи S = H<sup>d</sup> mod n</div>
    {sig_html}
  </div>

  <!-- СЕКЦИЯ 7: Верификация -->
  <div id="sec-verify" class="sec-content">
    <div class="sec-title">ШАГ 6 — Верификация подписи V = S<sup>e</sup> mod n</div>
    {ver_html}
  </div>

</div><!-- /wrap -->

<script>
function show(name){{
  document.querySelectorAll('.sec-content').forEach(s=>s.classList.remove('show'));
  document.querySelectorAll('.nav-tabs .tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('sec-'+name).classList.add('show');
  document.getElementById('tab-'+name).classList.add('active');
}}
</script>
</body></html>"""


if __name__ == '__main__':
    print(f"\n{'='*55}")
    print(f"  ЛР №8 — Хеш + ЭЦП RSA")
    print(f"  Вариант 6: p={P}, q={Q}, n={N}, φ(n)={PHI}")
    print(f"  e={E}, d={D}")
    print(f"  Фамилия: БУЛГАРОВ → H={H_orig}")
    print(f"  Подпись: S={SIG}")
    print(f"  Верификация: V={VER} {'✓' if VER==H_orig else '✗'}")
    print(f"  http://127.0.0.1:5000")
    print(f"{'='*55}\n")
    app.run(debug=True)
