# -*- coding: utf-8 -*-
"""
ЛР №8 · Вариант 10 · p=13, q=29 · КАТАЛОГ
Автор: Булгаров Марк
Тема: Белый / Синий / Красный
"""
import math
from flask import Flask
app = Flask(__name__)

RU_CODES = {
    'А':1,'Б':2,'В':3,'Г':4,'Д':5,'Е':6,'Ё':7,'Ж':8,'З':9,'И':10,
    'Й':11,'К':12,'Л':13,'М':14,'Н':15,'О':16,'П':17,'Р':18,'С':19,
    'Т':20,'У':21,'Ф':22,'Х':23,'Ц':24,'Ч':25,'Ш':26,'Щ':27,'Ы':28,
    'Ь':29,'Э':30,'Ю':31,'Я':32
}
def lc(ch): return RU_CODES.get(ch.upper(),0)

def compute_hash_steps(word,p,q):
    n=p*q; H=0; steps=[]
    for i,ch in enumerate(word.upper()):
        M=lc(ch); Hp=H; s=Hp+M; Hn=(s*s)%n
        steps.append({'i':i+1,'ch':ch,'M':M,'H_prev':Hp,'sum':s,'sum2':s*s,'H':Hn})
        H=Hn
    return H,steps

def ext_gcd(a,b):
    if b==0: return a,1,0
    g,x,y=ext_gcd(b,a%b); return g,y,x-(a//b)*y
def mod_inv(e,phi): _,x,_=ext_gcd(e,phi); return x%phi
def find_e(phi):
    for e in range(2,phi):
        if math.gcd(e,phi)==1: return e

def fast_pow(base,exp,mod):
    res=1; b=base%mod; e=exp; steps=[]; bits=bin(exp)[2:]
    bit_n=0
    while e>0:
        bit=e&1
        steps.append({'bit_num':bit_n,'bit':bit,'e':e,'b':b,'result_before':res,'multiply':bit==1})
        if bit==1: res=(res*b)%mod
        b=(b*b)%mod; e>>=1; bit_n+=1
    return res,steps,bits

P,Q=13,29; N=P*Q; PHI=(P-1)*(Q-1)
WORD='КАТАЛОГ'; WORD_P='ААТАЛОГ'; WORD_S='АКТАЛОГ'
H,ST=compute_hash_steps(WORD,P,Q)
Hp,STp=compute_hash_steps(WORD_P,P,Q)
Hs,STs=compute_hash_steps(WORD_S,P,Q)
E=find_e(PHI); D=mod_inv(E,PHI)
SIG,SSIG,SBITS=fast_pow(H,D,N)
VER,SVER,VBITS=fast_pow(SIG,E,N)

C1='#1565c0'; C2='#c8152b'; C3='#283593'
COLORS=[C1,C2,C3]
BG='#f8faff'; CARD='#ffffff'; BORDER='#dde6f5'; TEXT='#1a2340'; MUTED='#6b80a8'

CSS=f"""<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Unbounded:wght@700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'JetBrains Mono',monospace;background:{BG};color:{TEXT};min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 55% 40% at 0% 0%,rgba(21,101,192,.08) 0%,transparent 55%),
             radial-gradient(ellipse 45% 35% at 100% 100%,rgba(200,21,43,.06) 0%,transparent 55%);}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 22px;position:relative;z-index:1}}
.hero{{text-align:center;padding:36px 0 26px}}
.hero-sub{{font-size:11px;color:{MUTED};letter-spacing:3px;text-transform:uppercase;margin-bottom:10px}}
.hero h1{{font-family:'Unbounded',sans-serif;font-size:23px;font-weight:900;
  background:linear-gradient(90deg,{C1},{C3},{C2});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero p{{font-size:12px;color:{MUTED};margin-top:8px;line-height:1.7}}
.params{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:26px}}
.param{{background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:15px;text-align:center;box-shadow:0 1px 8px rgba(21,101,192,.06)}}
.param-val{{font-size:24px;font-weight:700;font-family:'Unbounded',sans-serif}}
.param-lbl{{font-size:9px;color:{MUTED};letter-spacing:1.5px;text-transform:uppercase;margin-top:4px}}
.sec-title{{font-family:'Unbounded',sans-serif;font-size:12px;font-weight:700;
  padding:8px 0 6px;margin-bottom:14px;
  border-bottom:2px solid transparent;border-image:linear-gradient(90deg,{C1},{C2}) 1;
  background:linear-gradient(90deg,{C1},{C3},{C2});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.formula-box{{background:#e8f0fe;border:1px solid rgba(21,101,192,.25);border-left:4px solid {C1};
  border-radius:8px;padding:14px 18px;margin-bottom:14px;text-align:center}}
.f-main{{color:{C1};font-size:17px;font-weight:700}}
.f-sub{{color:{MUTED};font-size:11px;margin-top:5px}}
.steps-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-bottom:14px}}
.step-card{{background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:15px;
  position:relative;overflow:hidden;box-shadow:0 1px 6px rgba(21,101,192,.05)}}
.step-card::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:4px}}
.step-card.s0::before{{background:{C1}}}
.step-card.s1::before{{background:{C2}}}
.step-card.s2::before{{background:{C3}}}
.step-num{{font-size:10px;color:{MUTED};letter-spacing:1px;margin-bottom:6px}}
.step-letter{{font-size:24px;font-weight:700;margin-bottom:5px}}
.step-calc{{font-size:12px;line-height:2.1}}
.eq{{color:{C1};font-weight:700}} .op{{color:{C2};font-weight:600}} .res{{color:{C3};font-weight:700;font-size:13px}}
.hash-compare{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px}}
.hash-box{{background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:16px;text-align:center}}
.hash-box .hw{{font-size:13px;font-weight:700;letter-spacing:2px;margin-bottom:7px}}
.hash-box .hv{{font-family:'Unbounded',sans-serif;font-size:32px;font-weight:900;margin-bottom:5px}}
.hash-box .hn{{font-size:10px;color:{MUTED};line-height:1.6}}
.h-orig{{border-color:rgba(21,101,192,.4);background:#e8f0fe}}
.h-ch1{{border-color:rgba(200,21,43,.35);background:#fdecea}}
.h-ch2{{border-color:rgba(40,53,147,.35);background:#ede7f6}}
.rsa-params{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-bottom:18px}}
.rsa-p{{background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:13px;text-align:center}}
.rsa-val{{font-size:20px;font-weight:700}} .rsa-lbl{{font-size:9px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-top:3px}}
.pow-table{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:14px}}
.pow-table th,.pow-table td{{padding:8px 11px;border-bottom:1px solid {BORDER};text-align:center}}
.pow-table th{{color:{MUTED};font-size:10px;letter-spacing:1px;text-transform:uppercase;background:#f0f4ff}}
.pow-table tr:last-child td{{border-bottom:none}}
.active-row{{background:rgba(21,101,192,.06)}} .inactive-row td{{color:#b0bdd0}}
.bit-1{{color:{C1};font-weight:700}} .bit-0{{color:#b0bdd0}}
.result-block{{background:linear-gradient(135deg,#e8f0fe,#fce4ec);border:1px solid rgba(21,101,192,.2);
  border-radius:14px;padding:22px;text-align:center;margin:14px 0}}
.r-label{{font-size:10px;color:{MUTED};letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}}
.r-val{{font-family:'Unbounded',sans-serif;font-size:44px;font-weight:900;
  background:linear-gradient(90deg,{C1},{C3},{C2});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.r-check{{margin-top:10px;font-size:13px}}
.ok{{color:#1b5e20;font-weight:700}} .err{{color:{C2};font-weight:700}}
.bits-row{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px;align-items:center}}
.bits-lbl{{font-size:10px;color:{MUTED};margin-right:6px}}
.bc{{width:27px;height:27px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}}
.b1{{background:rgba(21,101,192,.12);color:{C1};border:1px solid rgba(21,101,192,.3)}}
.b0{{background:#f0f4ff;color:#b0bdd0;border:1px solid {BORDER}}}
.nav-tabs{{display:flex;gap:6px;margin-bottom:22px;flex-wrap:wrap}}
.tab{{padding:7px 15px;font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;
  border:1.5px solid {BORDER};border-radius:6px;cursor:pointer;transition:.2s;color:{MUTED};background:{CARD}}}
.tab:hover,.tab.active{{color:{CARD};border-color:{C1};background:linear-gradient(135deg,{C1},{C3})}}
.tab.tr:hover,.tab.tr.active{{border-color:{C2};background:linear-gradient(135deg,{C2},#b71c1c)}}
.info{{background:#e8f0fe;border:1px solid rgba(21,101,192,.2);border-left:3px solid {C1};
  border-radius:6px;padding:12px 15px;font-size:12px;line-height:1.85;margin-bottom:14px}}
.info strong{{color:{C1}}}
.sec-content{{display:none}} .sec-content.show{{display:block}}
</style>"""

def steps_html(steps):
    cards=[]
    for s in steps:
        cc=f's{(s["i"]-1)%3}'; lc_=COLORS[(s["i"]-1)%3]
        cards.append(f"""<div class="step-card {cc}">
<div class="step-num">ШАГ {s['i']}</div>
<div class="step-letter" style="color:{lc_}">{s['ch']}</div>
<div class="step-calc">
M<sub>{s['i']}</sub>=<span class="op">{s['M']}</span> &nbsp;
H<sub>{s['i']-1}</sub>=<span class="op">{s['H_prev']}</span><br>
{s['H_prev']}+{s['M']}=<span class="eq">{s['sum']}</span><br>
{s['sum']}<sup>2</sup>=<span class="op">{s['sum2']}</span><br>
{s['sum2']} mod {N}=<span class="res">{s['H']}</span>
</div></div>""")
    return '<div class="steps-grid">'+''.join(cards)+'</div>'

def bits_html(bits,label):
    cells=''.join(f'<div class="bc {"b1" if b=="1" else "b0"}">{b}</div>' for b in bits)
    return f'<div class="bits-row"><span class="bits-lbl">{label}:</span>{cells}</div>'

def pow_table_html(steps):
    rows=[]
    for s in steps:
        ac='active-row' if s['bit']==1 else 'inactive-row'
        bc='bit-1' if s['bit']==1 else 'bit-0'
        if s['multiply']:
            prod=(s['result_before']*s['b'])%N
            m=f"{s['result_before']}×{s['b']} mod {N}=<b style='color:{C1}'>{prod}</b>"
        else: m='—'
        rows.append(f"<tr class='{ac}'><td>{s['bit_num']}</td><td class='{bc}'>{s['bit']}</td>"
                    f"<td>{s['e']}</td><td>{s['b']}</td><td>{s['result_before']}</td><td>{m}</td></tr>")
    return (f"<table class='pow-table'><thead><tr>"
            f"<th>Бит №</th><th>Бит</th><th>e</th><th>b²</th><th>result</th><th>Умножение</th>"
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table>")

@app.route('/')
def index():
    codes='  '.join(f'<span style="color:{COLORS[i%3]}">{ch}={lc(ch)}</span>' for i,ch in enumerate(WORD))

    params=f"""<div class="params">
{''.join(f'<div class="param"><div class="param-val" style="color:{c}">{v}</div><div class="param-lbl">{l}</div></div>'
for c,v,l in [(C1,P,'p'),(C2,Q,'q'),(C3,N,'n=p·q'),(C1,PHI,'φ(n)'),(C2,E,'e (откр.)'),(C3,D,'d (закр.)')])}</div>"""

    compare=f"""<div class="hash-compare">
<div class="hash-box h-orig"><div class="hw" style="color:{C1}">{WORD}</div>
  <div class="hv" style="color:{C1}">{H}</div><div class="hn">Оригинал · h(M)={H}</div></div>
<div class="hash-box h-ch1"><div class="hw" style="color:{C2}">{WORD_P}</div>
  <div class="hv" style="color:{C2}">{Hp}</div><div class="hn">К→А (1 буква) · h(M')={Hp} · Δ={abs(H-Hp)}</div></div>
<div class="hash-box h-ch2"><div class="hw" style="color:{C3}">{WORD_S}</div>
  <div class="hv" style="color:{C3}">{Hs}</div><div class="hn">К↔А (перестановка) · h(M'')={Hs} · Δ={abs(H-Hs)}</div></div>
</div>
<div class="info"><strong>Вывод:</strong> h={H}, h'={Hp} (Δ={abs(H-Hp)}), h''={Hs} (Δ={abs(H-Hs)}).
Все три различны {'✓ — лавинный эффект присутствует.' if H!=Hp and H!=Hs and Hp!=Hs else '— не все различны.'}</div>"""

    rsa_info=f"""<div class="info"><strong>e={E}:</strong> НОД({E},{PHI})={math.gcd(E,PHI)} ✓<br>
<strong>d={D}:</strong> {E}·{D}={E*D}={E*D//PHI}·{PHI}+{(E*D)%PHI} → mod {PHI} = <b style="color:{C1}">{(E*D)%PHI}</b>
{'✓' if (E*D)%PHI==1 else '✗'}</div>
<div class="rsa-params">{''.join(f'<div class="rsa-p"><div class="rsa-val" style="color:{c}">{v}</div><div class="rsa-lbl">{l}</div></div>' for c,v,l in [(C1,E,'e открытый'),(C2,D,'d закрытый'),(C3,N,'n модуль'),(C1,H,'H хеш')])}</div>"""

    sig_html=f"""<div class="formula-box"><div class="f-main">S = {H}<sup>{D}</sup> mod {N}</div>
<div class="f-sub">d={D} → двоичный: {SBITS} · Алгоритм Right-to-Left Binary</div></div>
{bits_html(SBITS[::-1],f'd={D}')}
{pow_table_html(SSIG)}
<div class="result-block"><div class="r-label">Подпись S</div>
<div class="r-val">{SIG}</div></div>"""

    ok=f'<span class="ok">✓ V={VER}=H={H} — подпись ВЕРНА</span>' if VER==H else f'<span class="err">✗ НЕВЕРНА</span>'
    ver_html=f"""<div class="formula-box"><div class="f-main">V = {SIG}<sup>{E}</sup> mod {N}</div>
<div class="f-sub">Верификатор сравнивает V с H={H}</div></div>
{bits_html(VBITS[::-1],f'e={E}')}
{pow_table_html(SVER)}
<div class="result-block"><div class="r-label">Верификация V</div>
<div class="r-val">{VER}</div><div class="r-check">{ok}</div></div>"""

    return f"""<!DOCTYPE html><html lang="ru"><head><title>ЛР8 · Вар.10</title>{CSS}</head>
<body><div class="wrap">
<div class="hero"><div class="hero-sub">ЛР №8 · Вариант 10</div>
<h1>Хеш-функция и ЭЦП (RSA)</h1>
<p>КАТАЛОГ · p={P}, q={Q}, n={N}, φ={PHI} · e={E}, d={D}</p></div>
<div class="sec-title">ПАРАМЕТРЫ</div>{params}
<div class="nav-tabs">
<span onclick="show('h1')" class="tab active" id="tab-h1">1. Хеш КАТАЛОГ</span>
<span onclick="show('h2')" class="tab" id="tab-h2">2. M' (К→А)</span>
<span onclick="show('h3')" class="tab" id="tab-h3">3. M'' (К↔А)</span>
<span onclick="show('h4')" class="tab" id="tab-h4">4. Сравнение</span>
<span onclick="show('h5')" class="tab" id="tab-h5">5. RSA-ключи</span>
<span onclick="show('h6')" class="tab tr" id="tab-h6">6. Подпись S</span>
<span onclick="show('h7')" class="tab" id="tab-h7">7. Верификация</span>
</div>
<div id="sec-h1" class="sec-content show">
<div class="sec-title">Хеш КАТАЛОГ · Hᵢ=(Hᵢ₋₁+Mᵢ)² mod {N}</div>
<div class="formula-box"><div class="f-main">Hᵢ=(Hᵢ₋₁+Mᵢ)² mod {N}</div>
<div class="f-sub">H₀=0 · n={P}·{Q}={N}</div></div>
<div class="info"><strong>Коды букв:</strong> {codes}</div>
{steps_html(ST)}
<div class="result-block"><div class="r-label">h(КАТАЛОГ)</div><div class="r-val">{H}</div></div></div>
<div id="sec-h2" class="sec-content">
<div class="sec-title">M' = {WORD_P} · изменена 1 буква К→А (код {lc('К')}→{lc('А')})</div>
<div class="info"><strong>Изменение:</strong> К(код {lc('К')}) → А(код {lc('А')}), разница={abs(lc('К')-lc('А'))}</div>
{steps_html(STp)}
<div class="result-block"><div class="r-label">h(M')=h({WORD_P})</div>
<div class="r-val" style="-webkit-text-fill-color:{C2};color:{C2}">{Hp}</div></div></div>
<div id="sec-h3" class="sec-content">
<div class="sec-title">M'' = {WORD_S} · переставлены К↔А (позиции 0↔1)</div>
<div class="info"><strong>Изменение:</strong> КАТАЛОГ → АКТАЛОГ (К и А поменяны местами)</div>
{steps_html(STs)}
<div class="result-block"><div class="r-label">h(M'')=h({WORD_S})</div>
<div class="r-val" style="-webkit-text-fill-color:{C3};color:{C3}">{Hs}</div></div></div>
<div id="sec-h4" class="sec-content">
<div class="sec-title">СРАВНЕНИЕ ТРЁХ ХЕШ-ОБРАЗОВ</div>{compare}</div>
<div id="sec-h5" class="sec-content">
<div class="sec-title">ГЕНЕРАЦИЯ КЛЮЧЕЙ RSA</div>{rsa_info}</div>
<div id="sec-h6" class="sec-content">
<div class="sec-title">ПОДПИСЬ S = H^d mod n</div>{sig_html}</div>
<div id="sec-h7" class="sec-content">
<div class="sec-title">ВЕРИФИКАЦИЯ V = S^e mod n</div>{ver_html}</div>
</div>
<script>
function show(n){{
  document.querySelectorAll('.sec-content').forEach(s=>s.classList.remove('show'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('sec-'+n).classList.add('show');
  document.getElementById('tab-'+n).classList.add('active');
}}
</script></body></html>"""

if __name__=='__main__':
    print(f"ЛР8 Вар.10 КАТАЛОГ: n={N} φ={PHI} e={E} d={D}")
    print(f"H={H} S={SIG} V={VER} {'✓' if VER==H else '✗'}")
    print("http://127.0.0.1:5000")
    app.run(debug=True)