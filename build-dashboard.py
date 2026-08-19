#!/usr/bin/env python3
"""Genera dashboard.html (tracker job, UI a tab+lista, palette calda).

Legge, in ordine e degradando con grazia se un file manca:
  data/pipeline.md            offerte scoperte da scan.mjs (obbligatorio)
  data/evaluations.json       TUOI dati: valutazioni A-G, override, candidature manuali
                              (gitignored; senza, mostra solo le offerte senza punteggi)
  data/grad_watch.json        grad-watch nostro (con deadline/link-rot se presenti)
  data/graduate_program_watch.md   fallback opzionale (export ChatGPT), se presente

Scadenze: ogni offerta puo' avere 'deadline' (ISO YYYY-MM-DD) e 'deadline_quote'.
Il badge SCADUTO / «N gg» / LINK MORTO e' calcolato lato browser sulla data odierna,
cosi' resta corretto ogni volta che apri il file.

Rilancia:  python3.11 build-job-dashboard.py
"""
import re, json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
SHELL = "--shell" in sys.argv   # genera index.html vuoto e installabile (PWA), senza dati personali

def load_json(rel, default):
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception as e: print(f"! {rel}: {e}")
    return default

# ---- 1. offerte scoperte (triage) --------------------------------------------
pipe = os.path.join(ROOT, "data/pipeline.md")
lines = [l for l in open(pipe, encoding="utf-8")] if os.path.exists(pipe) else []
lines = [l for l in lines if l.strip().startswith("- [ ]")]
eu = {"remote","europe"," eu ","italy","italia","germany","deutschland","netherlands","france","spain","españa","sweden","finland","denmark","norway","poland","polska","switzerland","austria","ireland","dublin","berlin","munich","paris","amsterdam","madrid","barcelona","stockholm","lisbon","portugal","london","milan","warsaw","copenhagen","zurich","vienna","brussels","belgium"}
senior = re.compile(r'\b(senior|sr\.?|staff|principal|lead|head|vp|director)\b', re.I)
offt = re.compile(r'\b(marketing|sales|account executive|recruit|talent acquisition|treasury|executive (support|services)|controller|accountant|payroll|people ops|hr )\b', re.I)
rel = re.compile(r'\b(engineer|architect|product|solution|forward deployed|ai|ml|machine learning|data|automation|tpm|technical|program manager|project manager|consultant|analyst|graduate|trainee|developer|research)\b', re.I)
offers = []
for l in lines:
    p = l.split("|")
    if len(p) < 4: continue
    url=p[0].replace("- [ ]","").strip(); co=p[1].strip(); t=p[2].strip(); loc=p[3].strip(); ll=" "+loc.lower()+" "
    if senior.search(t) or offt.search(t) or not rel.search(t) or not any(k in ll for k in eu): continue
    offers.append(dict(url=url, company=co, title=t, loc=loc, fit=None, reasons=[], state="pending", src="ats",
                       deadline=None, dq=None, dead=False))

# ---- 2. layer dati personale (valutazioni A-G, override, manuali) ------------
ev = load_json("data/evaluations.json", {})
OWNER = ev.get("owner", "")
EVAL = {e["match"]: e for e in ev.get("evaluations", [])}
for o in offers:
    for k, e in EVAL.items():
        if o["title"].startswith(k):
            o["fit"]=e.get("fit"); o["state"]=e.get("state","evaluated"); o["reasons"]=e.get("reasons",[])
            o["deadline"]=e.get("deadline"); o["dq"]=e.get("deadline_quote"); break
for ov in ev.get("overrides", []):
    for o in offers:
        if o["company"]==ov.get("company") and o["title"]==ov.get("title"):
            o["fit"]=ov.get("fit"); o["state"]=ov.get("state"); o["reasons"]=ov.get("reasons",[])
for m in ev.get("manual", []):
    offers.append(dict(url=m["url"], company=m.get("company","?"), title=m.get("title","?"), loc=m.get("loc","—"),
                       fit=m.get("fit"), state=m.get("state","evaluated"), src="manual", reasons=m.get("reasons",[]),
                       deadline=m.get("deadline"), dq=m.get("deadline_quote"), dead=False))

# ---- 3. grad-watch (con deadline + link-rot se il crawler li ha scritti) -----
grad_seen=set()
for g in load_json("data/grad_watch.json", []):
    if g["url"] in grad_seen: continue
    grad_seen.add(g["url"])
    rs=["grad-watch", g.get("note","verifica scadenza")]
    offers.append(dict(url=g["url"], company=g["company"], title=g["program"], loc=g.get("loc","Europe"),
                       fit=None, state="evaluated", src="grad", reasons=rs,
                       deadline=g.get("deadline"), dq=g.get("deadline_quote"), dead=bool(g.get("dead"))))

# fallback opzionale: export ChatGPT come data/graduate_program_watch.md
gmd = os.path.join(ROOT, "data/graduate_program_watch.md")
if os.path.exists(gmd):
    for l in open(gmd, encoding="utf-8").read().splitlines():
        m=re.search(r'\]\((https?://[^\s)]+)', l)
        if not m: continue
        url=m.group(1)
        if url in grad_seen: continue
        grad_seen.add(url)
        company=l[2:15].strip().rstrip("-").strip(); program=l[15:34].strip().rstrip("-").strip() or "Graduate Program"
        loc=l[34:49].strip() or "Europe"; deadline=l[49:67].strip()
        offers.append(dict(url=url, company=company, title=program, loc=loc, fit=None, state="evaluated", src="grad",
                           reasons=["grad-watch (ChatGPT)", (f"scadenza: {deadline}" if deadline else "verifica")],
                           deadline=None, dq=deadline or None, dead=False))

# ---- 4. render ---------------------------------------------------------------
if SHELL:
    offers = []; OWNER = ""   # guscio pubblico: nessun dato personale, si riempie via "+ Aggiungi"
data = json.dumps(offers, ensure_ascii=False)
STATES = [("pending","To review"),("evaluated","Da decidere"),("applied","Applied"),("responded","Responded"),("interview","Interview"),("offer","Offer"),("hired","Hired"),("skip","Skip"),("rejected","Rejected"),("discarded","Discarded")]
opts = "".join(f'<option value="{s}">{l}</option>' for s,l in STATES)
title_line = ("la tua board · aggiungi i tuoi job con «+ Aggiungi»" if SHELL
              else (f"{OWNER} · fit + stato + scadenze + avanzamento" if OWNER else "fit + stato + scadenze + avanzamento"))

H = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Job Pipeline</title>
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#2a3a44"><link rel="apple-touch-icon" href="icons/icon-192.png">__CONFIGJS__<style>
:root{--ink:#221d17;--soft:#4f4636;--muted:#8a7d64;--accent:#2a3a44;--camel:#c3a789;--brown:#5c503f;--bg:#ece5d9;--card:#f9f5ef;--rule:#dbd0be;--need:#b07a3e;--cream:#e8e0d4;--warn:#b07a3e;--exp:#9a4b3c;}
:root{--serif:"Charter","Iowan Old Style",Georgia,serif;--sans:"Avenir Next","Segoe UI",system-ui,-apple-system,sans-serif;}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ink:#e9e1d4;--soft:#c3b7a2;--muted:#9a8d76;--accent:#c3a789;--slate:#25313a;--camel:#c3a789;--brown:#8a7458;--bg:#100d0b;--card:#1b242d;--rule:#2f3b46;--need:#d29a55;--cream:#100d0b;--warn:#d29a55;--exp:#d97a68;}}
*{box-sizing:border-box;margin:0;padding:0}html,body{background:var(--bg)}
body{font-family:var(--sans);color:var(--ink);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:34px 26px 80px}
h1{font-family:var(--serif);font-size:38px;letter-spacing:-.015em}.sub{color:var(--brown);font-weight:600;margin-top:4px;font-size:15px}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:22px 0 6px}
input,select,button{font:inherit;font-size:14.5px;padding:9px 13px;border:1px solid var(--rule);border-radius:10px;background:var(--card);color:var(--ink)}
input{flex:1;min-width:180px}button{cursor:pointer;font-weight:600}
button.pri{background:var(--accent);color:var(--cream);border-color:var(--accent)}
.addbox{display:none;gap:9px;flex-wrap:wrap;margin:11px 0 0;padding:15px;border:1px dashed var(--rule);border-radius:12px;background:var(--card)}.addbox.on{display:flex}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0 8px}
.tab{padding:10px 16px;border:1px solid var(--rule);border-radius:24px;background:var(--card);cursor:pointer;font-weight:600;color:var(--soft);font-size:14px;transition:all .12s}
.tab .n{font-weight:800;margin-left:7px;opacity:.7}
.tab:hover{border-color:var(--camel)}
.tab.on{background:var(--accent);color:var(--cream);border-color:var(--accent)}
.tab.park{color:var(--muted)}.tab.park.on{background:var(--brown);border-color:var(--brown);color:var(--cream)}
.hint{color:var(--muted);font-size:13px;margin:2px 0 16px}
.list{display:flex;flex-direction:column;gap:11px}
.row{display:flex;gap:18px;align-items:flex-start;background:var(--card);border:1px solid var(--rule);border-radius:13px;padding:15px 18px}
.row.need{border-left:4px solid var(--need)}
.row.gone{opacity:.5}
.main{flex:1;min-width:0}
.co{font-weight:700;font-size:14.5px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.rl{margin:3px 0}.rl a{color:var(--ink);text-decoration:none;font-weight:600;font-size:15.5px}.rl a:hover{color:var(--brown)}
.loc{color:var(--muted);font-size:12.5px}
.rs{margin:7px 0 0;padding-left:16px;color:var(--soft);font-size:13.5px}.rs li{margin:2px 0}
.fit{font-weight:800;font-size:12px;padding:2px 9px;border-radius:20px}.f45,.f5{background:var(--accent);color:var(--cream)}.f4{background:#7c6636;color:#f4ecdd}.f3{background:var(--camel);color:#2a2016}.f2{background:var(--brown);color:#f0e7d8}.fn{background:var(--rule);color:var(--muted)}
.tag{font-size:9.5px;font-weight:800;padding:2px 7px;border-radius:5px;letter-spacing:.04em}.tag.manual{background:#7a4fd6;color:#fff}.tag.grad{background:var(--camel);color:#2a2016}
.dl{font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;letter-spacing:.02em;border:1px solid transparent}
.dl.warn{background:var(--warn);color:#fff}.dl.exp{background:var(--exp);color:#fff}.dl.dead{background:transparent;border-color:var(--exp);color:var(--exp)}.dl.ok{background:transparent;border-color:var(--rule);color:var(--muted)}
.side{display:flex;flex-direction:column;gap:7px;flex:0 0 178px}
.side select{padding:6px 9px;font-size:12.5px}.side .go{display:flex;gap:6px}
.adv{flex:1;padding:6px;font-size:12.5px;background:var(--accent);color:var(--cream);border-color:var(--accent)}
.rm{padding:6px 10px;font-size:12.5px;background:transparent;border-color:var(--rule);color:var(--muted)}
.empty{color:var(--muted);padding:30px;text-align:center;border:1px dashed var(--rule);border-radius:13px}
@media(max-width:640px){.row{flex-direction:column}.side{flex-basis:auto;width:100%}}
__GATECSS__
</style></head><body>__GATE__<div class="wrap">
<h1>Job Pipeline</h1><div class="sub">__SUB__</div>
<div class="bar">
<input id="q" placeholder="Cerca ruolo / azienda / paese…">
<select id="co"><option value="">Tutte le aziende</option></select>
<select id="mf"><option value="0">Fit: tutti</option><option value="4">≥4</option><option value="3">≥3</option></select>
<button class="pri" id="toggleadd">+ Aggiungi</button><button id="export">⤓ Export</button>
</div>
<div class="addbox" id="addbox">
<input id="a_url" placeholder="URL annuncio *" style="flex:2;min-width:240px">
<input id="a_co" placeholder="Azienda *"><input id="a_role" placeholder="Ruolo *"><input id="a_loc" placeholder="Location">
<input id="a_dl" placeholder="Scadenza (AAAA-MM-GG)" style="min-width:150px">
<select id="a_state">__OPTS__</select><button class="pri" id="a_add">Aggiungi</button>
</div>
<div class="tabs" id="tabs"></div>
<div class="hint" id="hint"></div>
<div class="list" id="list"></div>
</div>
<script>
const EMBED=__DATA__, STATES=__ST__, NEED=new Set(["evaluated","responded","interview"]), OPTS=`__OPTS__`;
const PARK=new Set(["skip","rejected","discarded"]);
const LS="jobpipe_v1", MLS="jobpipe_manual_v1";
function jload(k){try{return JSON.parse(localStorage.getItem(k))||(k===MLS?[]:{})}catch(e){return k===MLS?[]:{}}}
function jsave(k,v){localStorage.setItem(k,JSON.stringify(v))}
let over=jload(LS), manual=jload(MLS), active="evaluated";
function allData(){const seen=new Set(EMBED.map(o=>o.url));const m=manual.filter(o=>!seen.has(o.url));const d=[...EMBED,...m];d.forEach(o=>{if(over[o.url])o.state=over[o.url]});return d}
let DATA=allData();
const q=document.getElementById('q'),co=document.getElementById('co'),mf=document.getElementById('mf'),tabs=document.getElementById('tabs'),list=document.getElementById('list'),hint=document.getElementById('hint');
function fillco(){co.innerHTML='<option value="">Tutte le aziende</option>';[...new Set(DATA.map(o=>o.company))].sort().forEach(c=>{const op=document.createElement('option');op.textContent=c;co.appendChild(op)})}
function fcls(f){if(f===null||f===undefined)return'fn';if(f>=4.5)return'f45';if(f>=4)return'f4';if(f>=3)return'f3';return'f2'}
// giorni alla scadenza sulla data ODIERNA (ricalcolato ad ogni apertura)
function days(iso){if(!iso)return null;const d=new Date(iso+'T23:59:59');if(isNaN(d))return null;return Math.ceil((d-new Date())/86400000)}
function dlbadge(o){
  if(o.dead)return{cls:'dead',txt:'LINK MORTO',gone:true,ord:1e9};
  const n=days(o.deadline);
  if(n===null)return null;
  if(n<0)return{cls:'exp',txt:'SCADUTO',gone:true,ord:1e8-n};
  if(n<=21)return{cls:'warn',txt:n+' gg',gone:false,ord:n};
  return{cls:'ok',txt:o.deadline,gone:false,ord:n};
}
function setState(url,st){over[url]=st;jsave(LS,over);const o=DATA.find(x=>x.url===url);if(o)o.state=st;render()}
function delManual(url){manual=manual.filter(o=>o.url!==url);jsave(MLS,manual);delete over[url];jsave(LS,over);DATA=allData();fillco();render()}
function tagof(o){return o.src==='manual'?'<span class="tag manual">MANUALE</span>':o.src==='grad'?'<span class="tag grad">GRAD</span>':''}
function filtered(){return DATA.filter(o=>{if(co.value&&o.company!==co.value)return false;if(+mf.value&&(o.fit===null||o.fit<+mf.value))return false;return (o.company+' '+o.title+' '+o.loc).toLowerCase().includes(q.value.toLowerCase())})}
function isGone(o){const b=dlbadge(o);return !!(b&&b.gone)}   // scaduto o link morto
function render(){
 const fd=filtered();
 const goneN=fd.filter(isGone).length;
 let html=STATES.map(([s,l])=>{const n=fd.filter(o=>o.state===s&&!isGone(o)).length;return `<button class="tab${PARK.has(s)?' park':''}${s===active?' on':''}" data-s="${s}">${l}<span class="n">${n}</span></button>`}).join('');
 html+=`<button class="tab park${active==='expired'?' on':''}" data-s="expired">⏳ Scaduti<span class="n">${goneN}</span></button>`;
 tabs.innerHTML=html;
 tabs.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{active=b.dataset.s;render()});
 let rows = active==='expired' ? fd.filter(isGone) : fd.filter(o=>o.state===active&&!isGone(o));
 // ordina: scadenze imminenti prime, scaduti/morti in fondo
 rows.forEach(o=>{const b=dlbadge(o);o._ord=b?b.ord:5e7;});
 rows.sort((a,b)=>a._ord-b._ord);
 const lbl = active==='expired' ? 'Scaduti' : (STATES.find(x=>x[0]===active)||['',''])[1];
 hint.textContent = active==='expired' ? 'Bandi con scadenza passata o link morto — messi da parte per non intralciare. Puoi archiviarli (Discarded) o riaprirli se sbagliano.' : (active==='evaluated' ? 'Le tue da decidere (valutate A-G, grad-watch, candidature manuali). Bordo arancione = serve la tua azione · badge scadenza in alto.' : (active==='pending'?'Scoperte e triate, non ancora valutate A-G.':''));
 if(!rows.length){list.innerHTML=`<div class="empty">Nessun job in "${lbl}".</div>`;return}
 list.innerHTML='';
 rows.forEach(o=>{
   const rs=o.reasons&&o.reasons.length?`<ul class="rs">${o.reasons.map(r=>`<li>${r}</li>`).join('')}</ul>`:'';
   const fit=(o.fit===null||o.fit===undefined)?'<span class="fit fn">—</span>':`<span class="fit ${fcls(o.fit)}">${o.fit}</span>`;
   const b=dlbadge(o);
   const dl=b?`<span class="dl ${b.cls}"${o.dq?` title="${String(o.dq).replace(/"/g,'&quot;')}"`:''}>${b.txt}</span>`:'';
   const idx=STATES.findIndex(x=>x[0]===o.state), nxt=(idx>=0&&idx<6)?STATES[idx+1][0]:null;
   const el=document.createElement('div');el.className='row'+(NEED.has(o.state)?' need':'')+(b&&b.gone?' gone':'');
   el.innerHTML=`<div class="main"><div class="co">${o.company} ${fit} ${dl} ${tagof(o)}</div><div class="rl"><a href="${o.url}" target="_blank">${o.title}</a></div><div class="loc">${o.loc}</div>${rs}</div>
   <div class="side"><select>${OPTS}</select><div class="go">${nxt?`<button class="adv">Avanti →</button>`:''}${o.src==='manual'?`<button class="rm">✕</button>`:''}</div></div>`;
   const sel=el.querySelector('select');sel.value=o.state;sel.onchange=()=>setState(o.url,sel.value);
   if(nxt)el.querySelector('.adv').onclick=()=>setState(o.url,nxt);
   if(o.src==='manual')el.querySelector('.rm').onclick=()=>{if(confirm('Rimuovere?'))delManual(o.url)};
   list.appendChild(el);
 });
}
[q,co,mf].forEach(e=>e.addEventListener('input',render));
document.getElementById('toggleadd').onclick=()=>document.getElementById('addbox').classList.toggle('on');
document.getElementById('a_add').onclick=()=>{const url=a_url.value.trim(),c=a_co.value.trim(),r=a_role.value.trim();
 if(!url||!c||!r){alert('URL, Azienda e Ruolo obbligatori');return} if(DATA.some(o=>o.url===url)){alert('URL già presente');return}
 const st=a_state.value,dl=a_dl.value.trim()||null; manual.push({url,company:c,title:r,loc:a_loc.value.trim()||'—',fit:null,reasons:['aggiunta manualmente'],state:st,src:'manual',deadline:dl,dq:dl?'inserita a mano':null,dead:false});
 jsave(MLS,manual);['a_url','a_co','a_role','a_loc','a_dl'].forEach(id=>document.getElementById(id).value='');active=st;DATA=allData();fillco();render()};
document.getElementById('export').onclick=()=>{const rows=DATA.filter(o=>o.state!=='pending').map(o=>`| ${o.company} | ${o.title} | ${o.state} | ${o.fit??''} | ${o.deadline??''} | ${o.loc} | ${o.url} |`);
 const md="# applications.md (export)\n\n| Company | Role | Status | Fit | Deadline | Location | URL |\n|---|---|---|---|---|---|---|\n"+rows.join("\n");
 const b=new Blob([md],{type:'text/markdown'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='applications-export.md';a.click()};
fillco();render();
if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}))}
__GATEJS__
</script></body></html>"""
# --- gate d'accesso (solo nella shell pubblica; la board locale non lo ha) ------
GATECSS = GATE = GATEJS = CONFIGJS = ""
if SHELL:
    CONFIGJS = '<script src="config.js"></script>'
    GATECSS = ("#gate{display:none;position:fixed;inset:0;z-index:9999;background:var(--bg);align-items:center;justify-content:center;padding:20px}"
      ".gatebox{background:var(--card);border:1px solid var(--rule);border-radius:16px;padding:32px 28px;max-width:380px;width:100%;text-align:center}"
      ".gatebox h2{font-family:var(--serif);font-size:26px;margin-bottom:6px}.gatebox p{color:var(--soft);font-size:14px;margin-bottom:16px}"
      ".gatebox input{width:100%;text-align:center;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px}"
      ".gatebox button{width:100%;background:var(--accent);color:var(--cream);border-color:var(--accent);padding:11px}"
      ".gerr{color:var(--exp);font-size:13px;min-height:18px;margin-top:10px}.gnote{color:var(--muted);font-size:11.5px;margin-top:16px;line-height:1.4}"
      # --- tutorial ---
      "#tut{display:none;position:fixed;inset:0;z-index:10000;background:rgba(16,13,11,.55);align-items:center;justify-content:center;padding:18px}"
      ".tutbox{position:relative;background:var(--card);border:1px solid var(--rule);border-radius:16px;max-width:540px;width:100%;max-height:88vh;display:flex;flex-direction:column;padding:26px 26px 20px}"
      ".tutbox h2{font-family:var(--serif);font-size:24px;margin-bottom:4px;padding-right:28px}"
      ".tutbody{overflow-y:auto;margin:8px 0 4px}"
      ".tutbody h3{font-size:15px;margin:16px 0 5px;color:var(--accent)}"
      ".tutbody p{color:var(--soft);font-size:14px;line-height:1.55;margin:5px 0}"
      ".tutbody ol,.tutbody ul{color:var(--soft);font-size:14px;line-height:1.55;margin:5px 0 5px 18px}.tutbody li{margin:4px 0}"
      ".tutbody code{background:var(--bg);border:1px solid var(--rule);border-radius:6px;padding:1px 6px;font-size:12.5px;font-family:ui-monospace,Menlo,monospace;color:var(--ink);word-break:break-all}"
      ".tutbox b{color:var(--ink)}"
      ".tutx{position:absolute;top:12px;right:14px;width:auto;background:none;border:none;color:var(--muted);font-size:24px;line-height:1;cursor:pointer;padding:0}"
      ".tutok{margin-top:12px;width:100%;background:var(--accent);color:var(--cream);border-color:var(--accent);padding:11px}"
      ".tuthelp{position:fixed;bottom:18px;right:18px;z-index:900;width:42px;height:42px;border-radius:50%;background:var(--accent);color:var(--cream);border:none;font-size:20px;font-weight:800;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.22)}")
    GATE = ('<div id="gate"><div class="gatebox"><h2>Job Pipeline</h2><p>Inserisci il codice d\'accesso per entrare.</p>'
      '<input id="gcode" placeholder="JP-XXXX-XXXX" autocomplete="off" spellcheck="false">'
      '<button id="gbtn">Entra</button><div id="gerr" class="gerr"></div>'
      '<div class="gnote">I tuoi lavori restano sul tuo dispositivo. Inviamo solo il codice e un conteggio di aperture, senza IP.</div></div></div>'
      # --- tutorial primo avvio ---
      '<div id="tut"><div class="tutbox"><button id="tutx" class="tutx">&times;</button>'
      '<h2>Benvenutə nella tua Job Pipeline</h2>'
      '<div class="tutbody">'
      '<p>Questa è la tua <b>bacheca personale</b> per cercare lavoro senza perdere il filo. Ogni offerta è una scheda con uno <b>stato</b> e, se la conosci, una <b>scadenza</b>. Tutto resta sul tuo dispositivo.</p>'
      '<h3>1 · Aggiungi un lavoro</h3>'
      '<p>Premi <b>+ Aggiungi</b> in alto: incolla il link dell\'annuncio, l\'azienda, il ruolo e (se c\'è) la scadenza. Comparirà nella lista sotto “Da decidere”.</p>'
      '<h3>2 · Fallo avanzare</h3>'
      '<p>Quando ti candidi premi <b>Avanti →</b> (passa a “Candidato”), poi lo sposti mano a mano: Colloquio, Offerta. I badge <b>«N gg»</b> / <b>SCADUTO</b> ti dicono cosa scade; gli scaduti finiscono nella tab <b>⏳ Scaduti</b>.</p>'
      '<h3>3 · Hai Claude Code o Codex? Fai lavorare l\'AI 🤖</h3>'
      '<p><b>Claude Code</b> e <b>Codex</b> sono assistenti che girano nel <b>terminale</b> del tuo computer: sanno leggere il web e scrivere file. Con loro l\'app fa molto di più — <b>ti trova</b> le offerte e i graduate program e <b>li valuta</b> per il tuo profilo. Non serve saper programmare: parli a parole tue.</p>'
      '<ol>'
      '<li>Installa Claude Code (o Codex) seguendo la loro guida ufficiale.</li>'
      '<li>Scarica il progetto: apri il Terminale e incolla<br><code>git clone https://github.com/javas-cri-pt/job-pipeline</code></li>'
      '<li>Entra nella cartella (<code>cd job-pipeline</code>) e avvia l\'assistente (scrivi <code>claude</code> oppure <code>codex</code>).</li>'
      '<li>Chiedigli, a parole tue, per esempio:<ul>'
      '<li>«Trovami graduate program in Europa nel tech e mettili nella board.»</li>'
      '<li>«Leggi questo annuncio &lt;incolla-il-link&gt; e dimmi se fa per me, poi aggiungilo con un voto.»</li>'
      '<li>«Aggiorna le scadenze e segna quelli scaduti.»</li></ul></li>'
      '<li>Ti rigenera una board completa (<code>dashboard.html</code>). I dettagli sono nel file <b>RUNBOOK.md</b> dentro il progetto.</li>'
      '</ol>'
      '<h3>4 · Privacy</h3>'
      '<p>I tuoi lavori restano <b>sul tuo dispositivo</b>, nel browser. Buona ricerca! 🍀</p>'
      '</div><button id="tutok" class="tutok">Ho capito, iniziamo</button></div></div>'
      '<button id="tuthelp" class="tuthelp" title="Rivedi la guida">?</button>')
    GATEJS = r"""(function(){var API=(window.JOBPIPE_API||'').replace(/\/$/,'');var TOK='jobpipe_token';
var DEV=localStorage.getItem('jobpipe_device');if(!DEV){DEV=(crypto.randomUUID?crypto.randomUUID():String(Math.random()).slice(2));localStorage.setItem('jobpipe_device',DEV);}
// --- tutorial primo avvio ---
function showTut(){var t=document.getElementById('tut');if(t)t.style.display='flex';}
function closeTut(){var t=document.getElementById('tut');if(t)t.style.display='none';localStorage.setItem('jobpipe_onboarded','1');}
function tutOnce(){if(!localStorage.getItem('jobpipe_onboarded'))showTut();}
['tutx','tutok'].forEach(function(id){var b=document.getElementById(id);if(b)b.onclick=closeTut;});
var th=document.getElementById('tuthelp');if(th)th.onclick=showTut;
function unlock(){var g=document.getElementById('gate');if(g)g.style.display='none';tutOnce();}
function ping(code){if(API&&code){fetch(API+'/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,device:DEV})}).catch(function(){});}}
if(!API){unlock();return;}
var t=localStorage.getItem(TOK);
if(t){unlock();ping(t.split('.')[0]);return;}
var g=document.getElementById('gate');if(g)g.style.display='flex';
var btn=document.getElementById('gbtn'),inp=document.getElementById('gcode'),err=document.getElementById('gerr');
async function submit(){var code=(inp.value||'').trim().toUpperCase();if(!code){err.textContent='Metti il codice.';return;}err.textContent='Verifico...';
 try{var r=await fetch(API+'/claim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,device:DEV})});var d=await r.json();
  if(d.ok){localStorage.setItem(TOK,d.token);unlock();}else{err.textContent=d.error||'Codice non valido.';}}
 catch(e){err.textContent='Errore di rete, riprova.';}}
btn.onclick=submit;inp.addEventListener('keydown',function(e){if(e.key==='Enter')submit();});
})();"""

H = (H.replace("__DATA__", data)
      .replace("__ST__", json.dumps([[s,l] for s,l in STATES]))
      .replace("__SUB__", title_line)
      .replace("__CONFIGJS__", CONFIGJS)
      .replace("__GATECSS__", GATECSS)
      .replace("__GATE__", GATE)
      .replace("__GATEJS__", GATEJS)
      .replace("__OPTS__", opts))
outfile = "index.html" if SHELL else "dashboard.html"
open(os.path.join(ROOT,outfile),"w",encoding="utf-8").write(H)
ng = sum(1 for o in offers if o["src"]=="grad")
nd = sum(1 for o in offers if o.get("deadline") or o.get("dead"))
print(f"{outfile} · {len(offers)} card ({ng} grad, {nd} con scadenza/link-rot) · {len(H)} bytes")
