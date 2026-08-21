#!/usr/bin/env python3
"""Genera dashboard.html (tracker job). UI: oceanic, sidebar stati + cards-grid.
BACKEND/DATI INVARIATI: stesse chiavi localStorage (jobpipe_v1/manual/star/token),
stesso formato board {manual,over,stars,updated_at}, stessi endpoint /claim /board /ping.

Legge, degradando con grazia se un file manca:
  data/pipeline.md · data/evaluations.json · data/grad_watch.json · data/graduate_program_watch.md
Rilancia:  python3.11 build-job-dashboard.py   (--shell = index.html PWA vuoto)
"""
import re, json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
SHELL = "--shell" in sys.argv

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
            o["deadline"]=e.get("deadline"); o["dq"]=e.get("deadline_quote")
            o["star"]=e.get("star",False); o["gap"]=e.get("gap",False); break
for ov in ev.get("overrides", []):
    for o in offers:
        if o["company"]==ov.get("company") and o["title"]==ov.get("title"):
            o["fit"]=ov.get("fit"); o["state"]=ov.get("state"); o["reasons"]=ov.get("reasons",[])
for m in ev.get("manual", []):
    offers.append(dict(url=m["url"], company=m.get("company","?"), title=m.get("title","?"), loc=m.get("loc","—"),
                       fit=m.get("fit"), state=m.get("state","evaluated"), src="manual", reasons=m.get("reasons",[]),
                       deadline=m.get("deadline"), dq=m.get("deadline_quote"), dead=False,
                       star=m.get("star",False), gap=m.get("gap",False)))

# ---- 3. grad-watch -----------------------------------------------------------
grad_seen=set()
for g in load_json("data/grad_watch.json", []):
    if g["url"] in grad_seen: continue
    grad_seen.add(g["url"])
    rs=["grad-watch", g.get("note","verifica scadenza")]
    offers.append(dict(url=g["url"], company=g["company"], title=g["program"], loc=g.get("loc","Europe"),
                       fit=None, state="evaluated", src="grad", reasons=rs,
                       deadline=g.get("deadline"), dq=g.get("deadline_quote"), dead=bool(g.get("dead"))))
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
    offers = []; OWNER = ""
for o in offers:
    o.setdefault("star", False); o.setdefault("gap", False)
data = json.dumps(offers, ensure_ascii=False)

# stati: (id, label, colore) — id INVARIATI (compatibilita' dati)
STATE_DEF = [("pending","To review","#005f73"),("evaluated","Da decidere","#0a9396"),
             ("applied","Applied","#3f9a86"),("responded","Responded","#c9a227"),
             ("interview","Interview","#ee9b00"),("offer","Offer","#ca6702"),
             ("hired","Hired","#bb3e03"),("skip","Skip","#ae2012"),
             ("rejected","Rejected","#9b2226"),("discarded","Discarded","#6b7280")]
opts = "".join(f'<option value="{s}">{l}</option>' for s,l,c in STATE_DEF)
STDEF = json.dumps([[s,l,c] for s,l,c in STATE_DEF])

H = r"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Job Pipeline</title>
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#005f73"><link rel="icon" type="image/png" href="icons/icon-192.png"><link rel="apple-touch-icon" href="icons/icon-192.png">__CONFIGJS__<style>
:root{--p-void:#001219;--p-deep:#005f73;--p-teal:#0a9396;--p-mint:#94d2bd;--p-sand:#e9d8a6;--p-gold:#ee9b00;--p-orange:#ca6702;--p-rust:#bb3e03;--p-red:#ae2012;--p-wine:#9b2226;
--bg-page:#ece5d9;--bg-surface:#e6ded0;--bg-card:#f9f5ef;--border:rgba(0,18,25,0.09);--text:#221d17;--text-2:#4f4636;--text-3:#8a7d64;
--radius-sm:6px;--radius-md:8px;--radius-lg:10px;--radius-xl:12px;--sp1:4px;--sp2:8px;--sp3:12px;--sp4:16px;--sp5:20px;--sp6:24px;--trans:140ms ease-out;}
@media(prefers-color-scheme:dark){:root{--bg-page:#100d0b;--bg-surface:#1a140f;--bg-card:#201a14;--border:rgba(233,216,166,0.09);--text:#e9e1d4;--text-2:#c3b7a2;--text-3:#9a8d76;}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg-page);color:var(--text);line-height:1.45;-webkit-font-smoothing:antialiased;height:100vh;overflow:hidden}
.app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:230px;flex-shrink:0;display:flex;flex-direction:column;border-right:1px solid var(--border);background:var(--bg-surface);padding:var(--sp4) 0;overflow-y:auto}
.sidebar-brand{display:flex;align-items:center;gap:var(--sp3);padding:0 var(--sp4) var(--sp4);font-size:18px;font-weight:600;letter-spacing:-.3px;border-bottom:1px solid var(--border);margin-bottom:var(--sp3);color:var(--text)}
.status-list{display:flex;flex-direction:column;gap:2px;padding:0 var(--sp3)}
.status-item{display:flex;align-items:center;gap:var(--sp3);padding:7px var(--sp3);border-radius:var(--radius-md);border:1px solid transparent;background:transparent;color:var(--text-2);font-size:13px;cursor:pointer;transition:all var(--trans);text-align:left;width:100%;font-family:inherit}
.status-item:hover{background:var(--bg-card);color:var(--text)}
.status-item.active{background:var(--bg-card);color:var(--text);border-color:var(--border);font-weight:500}
.status-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.status-label{flex:1}
.status-count{font-size:11px;font-weight:500;padding:1px 7px;border-radius:999px;background:var(--bg-page);color:var(--text-3)}
.status-item.active .status-count{background:var(--bg-surface);color:var(--text-2)}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;align-items:center;gap:var(--sp3);padding:var(--sp4) var(--sp5);border-bottom:1px solid var(--border);flex-shrink:0;flex-wrap:wrap}
.search-box{display:flex;align-items:center;gap:var(--sp2);flex:1;min-width:200px;max-width:380px;padding:7px var(--sp3);border-radius:var(--radius-lg);border:1px solid var(--border);background:var(--bg-card)}
.search-box input{border:none;outline:none;background:transparent;font-size:14px;color:var(--text);width:100%;font-family:inherit}
.search-box input::placeholder{color:var(--text-3)}
.btn-icon{width:34px;height:34px;border-radius:var(--radius-md);border:1px solid var(--border);background:var(--bg-card);color:var(--text-2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:all var(--trans);font-size:16px}
.btn-icon:hover{background:var(--bg-surface);color:var(--text)}
.btn-primary{display:inline-flex;align-items:center;gap:6px;padding:7px var(--sp4);border-radius:var(--radius-lg);border:1px solid var(--p-deep);background:var(--p-deep);color:#fff;font-size:14px;font-weight:500;cursor:pointer;font-family:inherit;transition:opacity var(--trans)}
.btn-primary:hover{opacity:.88}
.tags-bar{display:flex;align-items:center;gap:var(--sp2);padding:var(--sp3) var(--sp5);flex-shrink:0;flex-wrap:wrap}
.chip{padding:4px var(--sp3);border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text-2);font-size:12px;cursor:pointer;font-family:inherit;transition:all var(--trans)}
.chip:hover{border-color:var(--text-3);color:var(--text)}
.chip.active{background:var(--text);color:var(--bg-page);border-color:var(--text)}
.cards-scroll{flex:1;overflow-y:auto;padding:var(--sp4) var(--sp5) var(--sp5)}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:var(--sp3)}
.card{background:var(--bg-card);border-radius:var(--radius-lg);border:1px solid var(--border);padding:var(--sp4);cursor:pointer;position:relative;transition:transform var(--trans),box-shadow var(--trans),border-color var(--trans)}
.card:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,18,25,0.06)}
.card.gone{opacity:.5}
.card-actions{position:absolute;top:8px;right:8px;display:flex;gap:4px;opacity:0;transition:opacity var(--trans)}
.card:hover .card-actions{opacity:1}
.card-actions button{width:26px;height:26px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-surface);color:var(--text-2);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;font-size:13px}
.card-actions button:hover{background:var(--bg-card);color:var(--text)}
.card-actions .on{color:var(--p-gold);border-color:var(--p-gold)}
.card-company{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--text-3);margin-bottom:3px;padding-right:70px}
.card-role{font-size:15px;font-weight:600;color:var(--text);line-height:1.3;margin-bottom:var(--sp3)}
.card-tags{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:var(--sp3)}
.card-tag{font-size:11px;padding:3px 9px;border-radius:999px;background:var(--bg-surface);color:var(--text-2);font-weight:500}
.card-tag.fit{color:#fff;font-weight:700}
.card-tag.dl-warn{background:var(--p-gold);color:#001219;font-weight:700}
.card-tag.dl-exp{background:var(--p-red);color:#fff;font-weight:700}
.card-tag.dl-dead{background:transparent;border:1px solid var(--p-red);color:var(--p-red);font-weight:700}
.card-tag.dl-ok{background:transparent;border:1px solid var(--border);color:var(--text-3)}
.card-tag.gap{background:var(--p-orange);color:#fff;font-weight:700}
.card-tag.src-m{background:#6d5ac0;color:#fff}
.card-tag.src-g{background:var(--p-teal);color:#001219}
.card-reasons{font-size:12px;color:var(--text-3);margin:0 0 12px;line-height:1.45;list-style:none}
.card-reasons li{position:relative;padding-left:14px;margin:2px 0}
.card-reasons li::before{content:"";position:absolute;left:3px;top:.5em;width:4px;height:4px;border-radius:50%;background:var(--text-3)}
.card-meta{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--text-3);padding-top:var(--sp3);border-top:1px solid var(--border)}
.move-menu{position:absolute;right:8px;top:38px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:4px;z-index:30;display:flex;flex-direction:column;gap:2px;box-shadow:0 8px 28px rgba(0,18,25,0.10);min-width:170px}
.move-menu button{text-align:left;padding:6px 10px;border-radius:var(--radius-sm);border:none;background:transparent;color:var(--text-2);font-size:12px;cursor:pointer;font-family:inherit;display:flex;align-items:center;gap:8px}
.move-menu button:hover{background:var(--bg-surface);color:var(--text)}
.move-menu .mm-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.empty{grid-column:1/-1;color:var(--text-3);padding:44px;text-align:center;border:1px dashed var(--border);border-radius:var(--radius-lg)}
.cards-grid.list{display:flex;flex-direction:column;gap:var(--sp2)}
.cards-grid.list .card{display:flex;align-items:center;gap:var(--sp3);padding:9px var(--sp4)}
.cards-grid.list .card:hover{transform:none;box-shadow:none;border-color:var(--p-teal)}
.cards-grid.list .card-reasons{display:none}
.cards-grid.list .card-company{margin:0;padding:0;width:128px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cards-grid.list .card-role{margin:0;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13.5px}
.cards-grid.list .card-tags{margin:0;flex-shrink:0;flex-wrap:nowrap}
.cards-grid.list .card-meta{margin:0;padding:0;border:0;flex-shrink:0;width:118px;justify-content:flex-end;gap:8px}
.cards-grid.list .card-meta span:first-child{display:none}
.cards-grid.list .card-actions{position:static;opacity:1;order:6;flex-shrink:0}
@media(max-width:600px){.cards-grid.list .card-company{width:92px}.cards-grid.list .card-meta{width:auto}}
.hint{padding:0 var(--sp5) var(--sp2);font-size:12px;color:var(--text-3)}
.modal-overlay{position:fixed;inset:0;z-index:100;background:rgba(0,18,25,0.35);display:none;align-items:center;justify-content:center;padding:var(--sp4);backdrop-filter:blur(2px)}
.modal{width:100%;max-width:440px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-xl);padding:var(--sp5);display:flex;flex-direction:column;gap:var(--sp4)}
.modal-header{display:flex;align-items:center;justify-content:space-between}.modal-header h3{font-size:17px;font-weight:600}
.form-body{display:flex;flex-direction:column;gap:var(--sp3)}
.form-body label{font-size:12px;font-weight:500;color:var(--text-2);display:flex;flex-direction:column;gap:5px;text-transform:uppercase;letter-spacing:.3px}
.form-body input,.form-body select{padding:9px var(--sp3);border-radius:var(--radius-lg);border:1px solid var(--border);background:var(--bg-page);color:var(--text);font-size:14px;outline:none;font-family:inherit;text-transform:none;letter-spacing:0}
.form-body input:focus,.form-body select:focus{border-color:var(--p-teal)}
.modal-footer{display:flex;justify-content:flex-end;gap:var(--sp2)}
.btn-secondary{padding:7px var(--sp4);border-radius:var(--radius-lg);border:1px solid var(--border);background:transparent;color:var(--text-2);font-size:14px;cursor:pointer;font-family:inherit}
.btn-secondary:hover{background:var(--bg-surface)}
@media(max-width:768px){.sidebar{width:200px}.cards-grid{grid-template-columns:1fr}}
@media(max-width:600px){.app{flex-direction:column}.sidebar{width:100%;flex-direction:row;padding:var(--sp3) var(--sp4);border-right:none;border-bottom:1px solid var(--border);overflow-x:auto;gap:var(--sp2)}.sidebar-brand{display:none}.status-list{flex-direction:row;padding:0}.status-item{white-space:nowrap}}
__GATECSS__
</style></head><body>__GATE__
<div class="app">
  <aside class="sidebar">
    <div class="sidebar-brand"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="color:var(--p-teal);flex-shrink:0"><path d="M4 4h16v2H4zm0 5h10v2H4zm0 5h16v2H4z" fill="currentColor"/></svg>Job Pipeline</div>
    <nav class="status-list" id="statusList"></nav>
  </aside>
  <main class="main">
    <header class="topbar">
      <div class="search-box"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="color:var(--text-3);flex-shrink:0"><path d="M11.5 3a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zm0 15.2a6.7 6.7 0 1 1 0-13.4 6.7 6.7 0 0 1 0 13.4z" fill="currentColor"/><path d="m16.84 18.11 3.02 3.03a1.27 1.27 0 1 1-1.8 1.8l-3.02-3.02a8.57 8.57 0 0 0 1.8-1.8z" fill="currentColor"/></svg><input type="text" id="searchInput" placeholder="Cerca azienda o ruolo…"></div>
      <button class="btn-icon" id="themeToggle" title="Tema"><svg id="iconSun" width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-8a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM11 2h2v2h-2zm0 18h2v2h-2zM2 11h2v2H2zm18 0h2v2h-2zM4.93 4.93l1.41 1.41L4.93 7.76 3.52 6.34zm12.73 12.73 1.41 1.41-1.41 1.41-1.41-1.41zm0-12.73 1.41-1.41 1.41 1.41-1.41 1.41zM4.93 17.66l1.41 1.41-1.41 1.41-1.41-1.41z" fill="currentColor"/></svg><svg id="iconMoon" width="16" height="16" viewBox="0 0 24 24" fill="none" style="display:none"><path d="M12 3a9 9 0 1 0 9 9c0-.46-.04-.92-.1-1.36a5.39 5.39 0 0 1-4.4 2.26 5.4 5.4 0 0 1-3.14-9.8c-.44-.06-.9-.1-1.36-.1z" fill="currentColor"/></svg></button>
      <button class="btn-icon" id="exportBtn" title="Export">⤓</button>
      <button class="btn-icon" id="viewToggle" title="Vista lista / card">☰</button>
      <button class="btn-icon" id="widgetBtn" title="Widget desktop (card singola)">▭</button>
      <button class="btn-primary" id="addJobBtn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 6a1 1 0 0 1 1 1v4h4a1 1 0 1 1 0 2h-4v4a1 1 0 1 1-2 0v-4H7a1 1 0 1 1 0-2h4V7a1 1 0 0 1 1-1z" fill="currentColor"/></svg><span>Nuova</span></button>
    </header>
    <div class="tags-bar" id="tagsBar">
      <button class="chip active" data-tag="all">Tutte</button>
      <button class="chip" data-tag="star">⭐ Preferiti</button>
      <button class="chip" data-tag="fit4">Fit ≥4</button>
      <button class="chip" data-tag="fit3">Fit ≥3</button>
    </div>
    <div class="hint" id="hint"></div>
    <div class="cards-scroll"><div class="cards-grid" id="cardsGrid"></div></div>
  </main>
</div>
<div class="modal-overlay" id="modal"><div class="modal">
  <div class="modal-header"><h3 id="modalTitle">Nuova posizione</h3><button class="btn-icon" id="closeModal">✕</button></div>
  <div class="form-body">
    <label>Azienda<input type="text" id="fCompany" placeholder="es. Revolut"></label>
    <label>Ruolo<input type="text" id="fRole" placeholder="es. Product Owner (Technical)"></label>
    <label>URL annuncio<input type="text" id="fUrl" placeholder="https://…"></label>
    <label>Location<input type="text" id="fLoc" placeholder="es. Milano / Remote"></label>
    <label>Scadenza<input type="text" id="fDl" placeholder="AAAA-MM-GG (opzionale)"></label>
    <label>Stato<select id="fStatus"></select></label>
  </div>
  <div class="modal-footer"><button class="btn-secondary" id="cancelBtn">Annulla</button><button class="btn-primary" id="saveBtn">Salva</button></div>
</div></div>
<script>
const EMBED=__DATA__, STDEF=__STDEF__;
const PARK=new Set(["skip","rejected","discarded"]);
const LS="jobpipe_v1", MLS="jobpipe_manual_v1", SKEY="jobpipe_star_v1";
function jload(k){try{return JSON.parse(localStorage.getItem(k))||((k===MLS||k===SKEY)?[]:{})}catch(e){return (k===MLS||k===SKEY)?[]:{}}}
function jsave(k,v){localStorage.setItem(k,JSON.stringify(v))}
let over=jload(LS), manual=jload(MLS), stars=jload(SKEY);
let active="evaluated", filterMode="all", searchQuery="", editingUrl=null, viewMode=localStorage.getItem('jobpipe_view')||'card';
const $=id=>document.getElementById(id);
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}
function isStar(o){return stars.indexOf(o.company)>=0}
function toggleStar(co){const i=stars.indexOf(co);if(i>=0)stars.splice(i,1);else stars.push(co);jsave(SKEY,stars);render();}
function seedDreams(){var ch=false;DATA.forEach(function(o){if(o.star&&stars.indexOf(o.company)<0){stars.push(o.company);ch=true;}});if(ch)jsave(SKEY,stars);}
function allData(){const seen=new Set(EMBED.map(o=>o.url));const m=manual.filter(o=>!seen.has(o.url));const d=[...EMBED,...m];d.forEach(o=>{if(over[o.url])o.state=over[o.url]});return d}
let DATA=allData();seedDreams();
function fillco(){}
function colorOf(st){const d=STDEF.find(x=>x[0]===st);return d?d[2]:'#6b7280'}
function labelOf(st){const d=STDEF.find(x=>x[0]===st);return d?d[1]:st}
function days(iso){if(!iso)return null;const d=new Date(iso+'T23:59:59');if(isNaN(d))return null;return Math.ceil((d-new Date())/86400000)}
function dlbadge(o){if(o.dead)return{cls:'dl-dead',txt:'LINK MORTO',gone:true,ord:1e9};const n=days(o.deadline);if(n===null)return null;if(n<0)return{cls:'dl-exp',txt:'SCADUTO',gone:true,ord:1e8-n};if(n<=21)return{cls:'dl-warn',txt:n+' gg',gone:false,ord:n};return{cls:'dl-ok',txt:o.deadline,gone:false,ord:n}}
function isGone(o){const b=dlbadge(o);return !!(b&&b.gone)}
function fitStyle(f){const bg=f>=4.5?'var(--p-teal)':f>=4?'var(--p-deep)':f>=3?'var(--p-gold)':'var(--p-rust)';const tc=(f>=3&&f<4)?'#001219':'#fff';return `background:${bg};color:${tc}`}
function setState(url,st){over[url]=st;jsave(LS,over);const o=DATA.find(x=>x.url===url);if(o)o.state=st;render()}
function delManual(url){manual=manual.filter(o=>o.url!==url);jsave(MLS,manual);delete over[url];jsave(LS,over);DATA=allData();render()}
function filtered(){return DATA.filter(o=>{
  if(filterMode==='star'&&!isStar(o))return false;
  if(filterMode==='fit4'&&(o.fit==null||o.fit<4))return false;
  if(filterMode==='fit3'&&(o.fit==null||o.fit<3))return false;
  return (o.company+' '+o.title+' '+o.loc).toLowerCase().includes(searchQuery.toLowerCase());
})}
function renderSidebar(){
  const fd=filtered(); let html='';
  function item(id,label,color,n){return `<button class="status-item${active===id?' active':''}" data-s="${id}"><span class="status-dot" style="background:${color}"></span><span class="status-label">${label}</span><span class="status-count">${n}</span></button>`}
  html+=item('all','Tutte','#001219',fd.filter(o=>!isGone(o)).length);
  STDEF.forEach(([id,label,color])=>{html+=item(id,label,color,fd.filter(o=>o.state===id&&!isGone(o)).length)});
  html+=item('expired','⏳ Scaduti','#ee9b00',fd.filter(isGone).length);
  $('statusList').innerHTML=html;
  $('statusList').querySelectorAll('.status-item').forEach(b=>b.onclick=()=>{active=b.dataset.s;render()});
}
function renderCards(){
  const grid=$('cardsGrid'), fd=filtered();
  grid.className='cards-grid'+(viewMode==='list'?' list':'');
  let rows = active==='expired'?fd.filter(isGone):active==='all'?fd.filter(o=>!isGone(o)):fd.filter(o=>o.state===active&&!isGone(o));
  rows.forEach(o=>{const b=dlbadge(o);o._ord=b?b.ord:5e7});rows.sort((a,b)=>a._ord-b._ord);
  $('hint').textContent = active==='expired'?'Bandi scaduti o con link morto, messi da parte.':active==='evaluated'?'Le tue da decidere. Clicca una scheda per spostarla di stato.':'';
  if(!rows.length){grid.innerHTML='<div class="empty">Nessun job qui.</div>';return}
  grid.innerHTML='';
  rows.forEach(o=>{
    const b=dlbadge(o), st=isStar(o), col=colorOf(o.state);
    const tags=[];
    if(o.fit!=null)tags.push(`<span class="card-tag fit" style="${fitStyle(o.fit)}">fit ${o.fit}</span>`);
    if(b)tags.push(`<span class="card-tag ${b.cls}"${o.dq?` title="${esc(o.dq)}"`:''}>${b.txt}</span>`);
    if(o.gap)tags.push('<span class="card-tag gap">CONOSCENZE DA INTEGRARE</span>');
    if(o.src==='manual')tags.push('<span class="card-tag src-m">MANUALE</span>');else if(o.src==='grad')tags.push('<span class="card-tag src-g">GRAD</span>');
    const reasons=o.reasons&&o.reasons.length?`<ul class="card-reasons">${o.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>`:'';
    const card=document.createElement('div');card.className='card'+(b&&b.gone?' gone':'');card.style.borderColor=col;
    card.innerHTML=`<div class="card-actions">
        <button class="ca-star${st?' on':''}" title="Preferito (dream)">${st?'★':'☆'}</button>
        <button class="ca-open" title="Apri annuncio">↗</button>
        ${o.src==='manual'?'<button class="ca-edit" title="Modifica">✎</button><button class="ca-del" title="Elimina">🗑</button>':''}
      </div>
      <div class="card-company">${st?'★ ':''}${esc(o.company)}</div>
      <div class="card-role">${esc(o.title)}</div>
      <div class="card-tags">${tags.join('')}</div>${reasons}
      <div class="card-meta"><span>${esc(o.loc)}</span><span style="color:${col};font-weight:600">${esc(labelOf(o.state))}</span></div>`;
    card.querySelector('.ca-star').onclick=e=>{e.stopPropagation();toggleStar(o.company)};
    card.querySelector('.ca-open').onclick=e=>{e.stopPropagation();window.open(o.url,'_blank')};
    const ce=card.querySelector('.ca-edit');if(ce)ce.onclick=e=>{e.stopPropagation();openEdit(o)};
    const cd=card.querySelector('.ca-del');if(cd)cd.onclick=e=>{e.stopPropagation();if(confirm('Rimuovere?'))delManual(o.url)};
    card.addEventListener('click',()=>showMoveMenu(o,card));
    grid.appendChild(card);
  });
}
function render(){renderSidebar();renderCards();}
function showMoveMenu(o,card){
  const ex=card.querySelector('.move-menu');if(ex){ex.remove();return}
  const menu=document.createElement('div');menu.className='move-menu';
  STDEF.forEach(([id,label,color])=>{const btn=document.createElement('button');btn.innerHTML=`<span class="mm-dot" style="background:${color}"></span>${label}`;btn.onclick=e=>{e.stopPropagation();setState(o.url,id)};menu.appendChild(btn)});
  card.appendChild(menu);
  setTimeout(()=>{const close=e=>{if(!menu.contains(e.target)){menu.remove();document.removeEventListener('click',close)}};document.addEventListener('click',close)},0);
}
// modal
function openModal(edit){$('modalTitle').textContent=edit?'Modifica posizione':'Nuova posizione';$('modal').style.display='flex'}
function closeModal(){$('modal').style.display='none';editingUrl=null}
function openAdd(){editingUrl=null;['fCompany','fRole','fUrl','fLoc','fDl'].forEach(i=>$(i).value='');$('fStatus').value='evaluated';openModal(false)}
function openEdit(o){editingUrl=o.url;$('fCompany').value=o.company;$('fRole').value=o.title;$('fUrl').value=o.url;$('fLoc').value=o.loc==='—'?'':o.loc;$('fDl').value=o.deadline||'';$('fStatus').value=o.state;openModal(true)}
STDEF.forEach(([id,label])=>{const op=document.createElement('option');op.value=id;op.textContent=label;$('fStatus').appendChild(op)});
$('saveBtn').onclick=()=>{
  const c=$('fCompany').value.trim(),r=$('fRole').value.trim(),url=$('fUrl').value.trim(),loc=$('fLoc').value.trim(),dl=$('fDl').value.trim()||null,st=$('fStatus').value;
  if(!c||!r||!url){alert('Compila azienda, ruolo e URL');return}
  if(editingUrl){const j=manual.find(x=>x.url===editingUrl);if(j){j.company=c;j.title=r;j.loc=loc||'—';j.deadline=dl;j.dq=dl?'inserita a mano':null;j.state=st;j.url=url}jsave(MLS,manual);over[url]=st;jsave(LS,over);}
  else{if(DATA.some(o=>o.url===url)){alert('URL già presente');return}manual.push({url,company:c,title:r,loc:loc||'—',fit:null,reasons:['aggiunta manualmente'],state:st,src:'manual',deadline:dl,dq:dl?'inserita a mano':null,dead:false,star:false,gap:false});jsave(MLS,manual);}
  active=st;DATA=allData();seedDreams();closeModal();render();
};
$('addJobBtn').onclick=openAdd;$('closeModal').onclick=closeModal;$('cancelBtn').onclick=closeModal;
$('widgetBtn').onclick=()=>window.open('widget.html','jobwidget','width=460,height=660');
function updateViewBtn(){$('viewToggle').textContent=viewMode==='list'?'▦':'☰';$('viewToggle').title=viewMode==='list'?'Vista card':'Vista lista';}
updateViewBtn();
$('viewToggle').onclick=()=>{viewMode=viewMode==='list'?'card':'list';localStorage.setItem('jobpipe_view',viewMode);updateViewBtn();render();};
$('searchInput').addEventListener('input',e=>{searchQuery=e.target.value;render()});
$('tagsBar').addEventListener('click',e=>{if(!e.target.classList.contains('chip'))return;document.querySelectorAll('#tagsBar .chip').forEach(c=>c.classList.remove('active'));e.target.classList.add('active');filterMode=e.target.dataset.tag;render()});
$('exportBtn').onclick=()=>{const rows=DATA.filter(o=>o.state!=='pending').map(o=>`| ${o.company} | ${o.title} | ${o.state} | ${o.fit??''} | ${o.deadline??''} | ${o.loc} | ${o.url} |`);
 const md="# applications.md (export)\n\n| Company | Role | Status | Fit | Deadline | Location | URL |\n|---|---|---|---|---|---|---|\n"+rows.join("\n");
 const bl=new Blob([md],{type:'text/markdown'});const a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download='applications-export.md';a.click()};
// theme
function applyTheme(dark){const r=document.documentElement;
 r.style.setProperty('--bg-page',dark?'#100d0b':'#ece5d9');r.style.setProperty('--bg-surface',dark?'#1a140f':'#e6ded0');r.style.setProperty('--bg-card',dark?'#201a14':'#f9f5ef');
 r.style.setProperty('--border',dark?'rgba(233,216,166,0.09)':'rgba(0,18,25,0.09)');r.style.setProperty('--text',dark?'#e9e1d4':'#221d17');r.style.setProperty('--text-2',dark?'#c3b7a2':'#4f4636');r.style.setProperty('--text-3',dark?'#9a8d76':'#8a7d64');
 $('iconSun').style.display=dark?'none':'block';$('iconMoon').style.display=dark?'block':'none';}
let themeDark=localStorage.getItem('jobpipe_theme')==='dark'||(localStorage.getItem('jobpipe_theme')===null&&window.matchMedia('(prefers-color-scheme: dark)').matches);
applyTheme(themeDark);
$('themeToggle').onclick=()=>{themeDark=!themeDark;localStorage.setItem('jobpipe_theme',themeDark?'dark':'light');applyTheme(themeDark)};
render();
if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}))}
__GATEJS__
</script></body></html>"""

# --- gate + tutorial (solo shell pubblica) ------------------------------------
GATECSS = GATE = GATEJS = CONFIGJS = ""
if SHELL:
    CONFIGJS = '<script src="config.js"></script>'
    GATECSS = ("#gate{display:none;position:fixed;inset:0;z-index:9999;background:var(--bg-page);align-items:center;justify-content:center;padding:20px}"
      ".gatebox{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:32px 28px;max-width:380px;width:100%;text-align:center}"
      ".gatebox h2{font-size:24px;margin-bottom:6px;color:var(--text)}.gatebox p{color:var(--text-2);font-size:14px;margin-bottom:16px}"
      ".gatebox input{width:100%;text-align:center;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg-page);color:var(--text);font-family:inherit;font-size:15px}"
      ".gatebox button{width:100%;background:var(--p-deep);color:#fff;border:none;padding:11px;border-radius:10px;cursor:pointer;font-family:inherit;font-size:15px;font-weight:500}"
      ".gerr{color:var(--p-red);font-size:13px;min-height:18px;margin-top:10px}.gnote{color:var(--text-3);font-size:11.5px;margin-top:16px;line-height:1.4}"
      "#tut{display:none;position:fixed;inset:0;z-index:10000;background:rgba(0,18,25,.55);align-items:center;justify-content:center;padding:18px}"
      ".tutbox{position:relative;background:var(--bg-card);border:1px solid var(--border);border-radius:16px;max-width:540px;width:100%;max-height:88vh;display:flex;flex-direction:column;padding:26px 26px 20px;color:var(--text)}"
      ".tutbox h2{font-size:22px;margin-bottom:4px;padding-right:28px}"
      ".tutbody{overflow-y:auto;margin:8px 0 4px}.tutbody h3{font-size:15px;margin:16px 0 5px;color:var(--p-teal)}"
      ".tutbody p{color:var(--text-2);font-size:14px;line-height:1.55;margin:5px 0}"
      ".tutbody ol,.tutbody ul{color:var(--text-2);font-size:14px;line-height:1.55;margin:5px 0 5px 18px}.tutbody li{margin:4px 0}"
      ".tutbody code{background:var(--bg-surface);border:1px solid var(--border);border-radius:6px;padding:1px 6px;font-size:12.5px;font-family:ui-monospace,Menlo,monospace;color:var(--text);word-break:break-all}"
      ".tutbox b{color:var(--text)}"
      ".tutx{position:absolute;top:12px;right:14px;width:auto;background:none;border:none;color:var(--text-3);font-size:24px;line-height:1;cursor:pointer;padding:0}"
      ".tutok{margin-top:12px;width:100%;background:var(--p-deep);color:#fff;border:none;padding:11px;border-radius:10px;cursor:pointer;font-family:inherit;font-size:15px}"
      ".tuthelp{position:fixed;bottom:18px;right:18px;z-index:900;width:42px;height:42px;border-radius:50%;background:var(--p-deep);color:#fff;border:none;font-size:20px;font-weight:800;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.22)}")
    GATE = ('<div id="gate"><div class="gatebox"><h2>Job Pipeline</h2><p>Inserisci il codice d\'accesso per entrare.</p>'
      '<input id="gcode" placeholder="JP-XXXX-XXXX" autocomplete="off" spellcheck="false">'
      '<button id="gbtn">Entra</button><div id="gerr" class="gerr"></div>'
      '<div class="gnote">Il codice è il tuo account: la board è sincronizzata sui tuoi dispositivi (PC, telefono). Nessun IP raccolto.</div></div></div>'
      '<div id="tut"><div class="tutbox"><button id="tutx" class="tutx">&times;</button>'
      '<h2>Benvenutə nella tua Job Pipeline</h2><div class="tutbody">'
      '<p>Questa è la tua <b>bacheca personale</b> per cercare lavoro senza perdere il filo. Ogni offerta è una scheda con uno <b>stato</b> e, se la conosci, una <b>scadenza</b>.</p>'
      '<h3>1 · Aggiungi un lavoro</h3><p>Premi <b>Nuova</b> in alto: incolla link, azienda, ruolo e (se c\'è) la scadenza.</p>'
      '<h3>2 · Spostalo di stato</h3><p><b>Clicca una scheda</b> per aprire il menù e cambiarle stato (Candidato, Colloquio, Offerta…). I badge <b>«N gg» / SCADUTO</b> ti dicono cosa scade.</p>'
      '<h3>3 · Hai Claude Code o Codex? Fai lavorare l\'AI 🤖</h3>'
      '<p><b>Claude Code</b> e <b>Codex</b> girano nel <b>terminale</b> e sanno leggere il web e scrivere file: <b>ti trovano</b> le offerte e i graduate program e <b>li valutano</b>. Non serve saper programmare.</p>'
      '<ol><li>Installa Claude Code (o Codex).</li>'
      '<li>Scarica il progetto: <code>git clone https://github.com/javas-cri-pt/job-pipeline</code></li>'
      '<li>Entra (<code>cd job-pipeline</code>) e avvia <code>claude</code> o <code>codex</code>.</li>'
      '<li>Chiedi a parole tue: «Trovami graduate program in Europa e mettili nella board», «Leggi questo annuncio e dimmi se fa per me».</li>'
      '<li>Poi <code>node push-board.mjs</code> manda la board a questa app (PC + telefono). Dettagli nel <b>RUNBOOK.md</b>.</li></ol>'
      '<h3>4 · Il codice è il tuo account</h3><p>La board è <b>sincronizzata</b> ovunque usi lo stesso codice. Buona ricerca! 🍀</p>'
      '</div><button id="tutok" class="tutok">Ho capito, iniziamo</button></div></div>'
      '<button id="tuthelp" class="tuthelp" title="Rivedi la guida">?</button>')
    GATEJS = r"""(function(){var API=(window.JOBPIPE_API||'').replace(/\/$/,'');var TOK='jobpipe_token';
var DEV=localStorage.getItem('jobpipe_device');if(!DEV){DEV=(crypto.randomUUID?crypto.randomUUID():String(Math.random()).slice(2));localStorage.setItem('jobpipe_device',DEV);}
function showTut(){var t=document.getElementById('tut');if(t)t.style.display='flex';}
function closeTut(){var t=document.getElementById('tut');if(t)t.style.display='none';localStorage.setItem('jobpipe_onboarded','1');}
function tutOnce(){if(!localStorage.getItem('jobpipe_onboarded'))showTut();}
['tutx','tutok'].forEach(function(id){var b=document.getElementById(id);if(b)b.onclick=closeTut;});
var th=document.getElementById('tuthelp');if(th)th.onclick=showTut;
function logout(){if(!confirm('Esci e cambia codice? La board resta salvata sul tuo account (codice); qui viene solo scollegata.'))return;
 ['jobpipe_token','jobpipe_manual_v1','jobpipe_v1','jobpipe_updated','jobpipe_onboarded'].forEach(function(k){localStorage.removeItem(k)});location.reload();}
if(API){var _bar=document.querySelector('.topbar');if(_bar){var _lo=document.createElement('button');_lo.textContent='Esci';_lo.title='Cambia codice';_lo.className='btn-secondary';_lo.onclick=logout;_bar.appendChild(_lo);}}
var UPD='jobpipe_updated',pushT=null,applying=false;
function _auth(x){var tk=localStorage.getItem(TOK)||'';return Object.assign({code:tk.split('.')[0],device:DEV,token:tk},x||{});}
function pushBoard(){if(!API||!localStorage.getItem(TOK))return;var now=Date.now();localStorage.setItem(UPD,now);
 fetch(API+'/board/put',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_auth({data:JSON.stringify({manual:manual,over:over,stars:stars,updated_at:now})}))}).catch(function(){});}
function schedulePush(){clearTimeout(pushT);pushT=setTimeout(pushBoard,700);}
async function pullBoard(){if(!API||!localStorage.getItem(TOK))return;
 try{var r=await fetch(API+'/board/get',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_auth())});var d=await r.json();if(!d.ok)return;
  var localU=+(localStorage.getItem(UPD)||0);
  if(d.data){var srv=JSON.parse(d.data);var srvU=+(srv.updated_at||0);
   if(srvU>localU){applying=true;jsave(MLS,srv.manual||[]);jsave(LS,srv.over||{});jsave(SKEY,srv.stars||[]);localStorage.setItem(UPD,srvU);applying=false;
    manual=jload(MLS);over=jload(LS);stars=jload(SKEY);DATA=allData();seedDreams();render();}
   else if(localU>srvU){pushBoard();}}
  else{if((manual&&manual.length)||Object.keys(over||{}).length)pushBoard();}
 }catch(e){}}
function syncInit(){if(!API||!localStorage.getItem(TOK))return;
 var _js=jsave;jsave=function(k,v){_js(k,v);if(!applying&&(k===LS||k===MLS||k===SKEY))schedulePush();};
 pullBoard();window.addEventListener('focus',pullBoard);}
function unlock(){var g=document.getElementById('gate');if(g)g.style.display='none';tutOnce();syncInit();}
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

H = (H.replace("__DATA__", data).replace("__STDEF__", STDEF)
      .replace("__CONFIGJS__", CONFIGJS).replace("__GATECSS__", GATECSS)
      .replace("__GATE__", GATE).replace("__GATEJS__", GATEJS))
outfile = "index.html" if SHELL else "dashboard.html"
open(os.path.join(ROOT,outfile),"w",encoding="utf-8").write(H)
if not SHELL:
    open(os.path.join(ROOT,"data/board.json"),"w",encoding="utf-8").write(json.dumps(offers, ensure_ascii=False))

# ---- widget.html: card singola + dot-filtro + swipe (condivide dati/sync) -----
WIDGET = r"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Job Widget</title>
<link rel="manifest" href="widget.webmanifest"><meta name="theme-color" content="#ece5d9"><link rel="icon" type="image/png" href="icons/icon-192.png"><link rel="apple-touch-icon" href="icons/icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Job Widget">__CONFIGJS__<style>
:root{--p-deep:#005f73;--p-teal:#0a9396;--p-gold:#ee9b00;--p-orange:#ca6702;--p-rust:#bb3e03;--p-red:#ae2012;
--bg-page:#ece5d9;--bg-surface:#e6ded0;--bg-card:#f9f5ef;--border:rgba(0,18,25,0.09);--text:#221d17;--text-2:#4f4636;--text-3:#8a7d64;}
@media(prefers-color-scheme:dark){:root{--bg-page:#100d0b;--bg-surface:#1a140f;--bg-card:#201a14;--border:rgba(233,216,166,0.09);--text:#e9e1d4;--text-2:#c3b7a2;--text-3:#9a8d76;}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg-page);color:var(--text);height:100vh;overflow:hidden;-webkit-font-smoothing:antialiased}
.wrap{max-width:440px;margin:0 auto;height:100vh;display:flex;flex-direction:column;padding:14px 16px 16px;gap:11px}
.whead{display:flex;align-items:center;justify-content:space-between}.wtitle{font-weight:600;font-size:15px}
.wopen{color:var(--p-deep);text-decoration:none;font-size:12px;font-weight:600}
.dots{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;padding:2px 0}
.dot{width:15px;height:15px;border-radius:50%;border:none;cursor:pointer;opacity:.45;transition:all .12s;padding:0}
.dot:hover{opacity:.8}.dot.active{opacity:1;box-shadow:0 0 0 2px var(--bg-page),0 0 0 4px var(--text)}
.stage{flex:1;display:flex;align-items:center;justify-content:center;touch-action:pan-y;user-select:none;overflow:hidden}
.wcard{width:100%;background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:8px}
.wcompany{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:var(--text-3)}
.wrole{font-size:19px;font-weight:700;line-height:1.25}
.wtags{display:flex;flex-wrap:wrap;gap:5px;margin:2px 0}
.wtag{font-size:11px;padding:3px 9px;border-radius:999px;background:var(--bg-surface);color:var(--text-2);font-weight:500}
.wtag.fit{color:#fff;font-weight:700}.wtag.dl-warn{background:var(--p-gold);color:#001219;font-weight:700}.wtag.dl-exp{background:var(--p-red);color:#fff;font-weight:700}.wtag.dl-dead{background:transparent;border:1px solid var(--p-red);color:var(--p-red);font-weight:700}.wtag.dl-ok{background:transparent;border:1px solid var(--border);color:var(--text-3)}.wtag.gap{background:var(--p-orange);color:#fff;font-weight:700}.wtag.src-m{background:#6d5ac0;color:#fff}.wtag.src-g{background:var(--p-teal);color:#001219}
.wreasons{list-style:none;font-size:13px;color:var(--text-2);line-height:1.5;margin:2px 0}
.wreasons li{position:relative;padding-left:15px;margin:3px 0}.wreasons li::before{content:"";position:absolute;left:3px;top:.6em;width:4px;height:4px;border-radius:50%;background:var(--text-3)}
.wmeta{display:flex;justify-content:space-between;font-size:12.5px;color:var(--text-3);border-top:1px solid var(--border);padding-top:10px;margin-top:2px}
.wfoot{display:flex;align-items:center;gap:8px;margin-top:6px}
.wfoot select{flex:1;padding:8px 10px;border-radius:10px;border:1px solid var(--border);background:var(--bg-page);color:var(--text);font-family:inherit;font-size:13px}
.wstar{width:38px;height:38px;border-radius:10px;border:1px solid var(--border);background:var(--bg-card);cursor:pointer;font-size:16px;color:var(--text-3)}.wstar.on{color:#e0a53a;border-color:#e0a53a}
.wapri{width:38px;height:38px;border-radius:10px;border:1px solid var(--border);background:var(--bg-card);cursor:pointer;font-size:15px;color:var(--text-2);display:inline-flex;align-items:center;justify-content:center;text-decoration:none}
.nav{display:flex;align-items:center;justify-content:space-between;gap:10px}
.navbtn{width:46px;height:40px;border-radius:10px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-2);font-size:18px;cursor:pointer}.navbtn:hover{background:var(--bg-surface);color:var(--text)}
.pos{font-size:12px;color:var(--text-3);font-variant-numeric:tabular-nums}
.wmsg{color:var(--text-3);text-align:center;padding:26px;font-size:14px;line-height:1.5}
</style></head><body>
<div class="wrap">
  <div class="whead"><span class="wtitle">Job Pipeline</span><a class="wopen" href="./" title="Apri l'app completa">↗ app</a></div>
  <div class="dots" id="dots"></div>
  <div class="stage" id="stage"></div>
  <div class="nav"><button class="navbtn" id="prev">‹</button><span class="pos" id="pos"></span><button class="navbtn" id="next">›</button></div>
</div>
<script>
const EMBED=__DATA__, STDEF=__STDEF__;
const API=(window.JOBPIPE_API||'').replace(/\/$/,''),TOK='jobpipe_token',UPD='jobpipe_updated';
const LS="jobpipe_v1",MLS="jobpipe_manual_v1",SKEY="jobpipe_star_v1";
function jload(k){try{return JSON.parse(localStorage.getItem(k))||((k===MLS||k===SKEY)?[]:{})}catch(e){return (k===MLS||k===SKEY)?[]:{}}}
function jsave(k,v){localStorage.setItem(k,JSON.stringify(v))}
let over=jload(LS),manual=jload(MLS),stars=jload(SKEY),active='all',idx=0;
const $=id=>document.getElementById(id);
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}
function allData(){const seen=new Set(EMBED.map(o=>o.url));const m=manual.filter(o=>!seen.has(o.url));const d=[...EMBED,...m];d.forEach(o=>{if(over[o.url])o.state=over[o.url]});return d}
function isStar(o){return stars.indexOf(o.company)>=0}
function colorOf(s){const d=STDEF.find(x=>x[0]===s);return d?d[2]:'#6b7280'}
function labelOf(s){const d=STDEF.find(x=>x[0]===s);return d?d[1]:s}
function days(iso){if(!iso)return null;const d=new Date(iso+'T23:59:59');if(isNaN(d))return null;return Math.ceil((d-new Date())/86400000)}
function dlbadge(o){if(o.dead)return{cls:'dl-dead',txt:'LINK MORTO',gone:true};const n=days(o.deadline);if(n===null)return null;if(n<0)return{cls:'dl-exp',txt:'SCADUTO',gone:true};if(n<=21)return{cls:'dl-warn',txt:n+' gg',gone:false};return{cls:'dl-ok',txt:o.deadline,gone:false}}
function isGone(o){const b=dlbadge(o);return !!(b&&b.gone)}
function fitStyle(f){const bg=f>=4.5?'var(--p-teal)':f>=4?'var(--p-deep)':f>=3?'var(--p-gold)':'var(--p-rust)';const tc=(f>=3&&f<4)?'#001219':'#fff';return `background:${bg};color:${tc}`}
function pool(){const d=allData();return active==='expired'?d.filter(isGone):active==='all'?d.filter(o=>!isGone(o)):d.filter(o=>o.state===active&&!isGone(o))}
function push(){if(!API||!localStorage.getItem(TOK))return;var now=Date.now();localStorage.setItem(UPD,now);var tk=localStorage.getItem(TOK),dev=localStorage.getItem('jobpipe_device')||'';
 fetch(API+'/board/put',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:tk.split('.')[0],device:dev,token:tk,data:JSON.stringify({manual:manual,over:over,stars:stars,updated_at:now})})}).catch(function(){});}
async function pull(){if(!API||!localStorage.getItem(TOK))return;try{var tk=localStorage.getItem(TOK),dev=localStorage.getItem('jobpipe_device')||'';
 var r=await fetch(API+'/board/get',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:tk.split('.')[0],device:dev,token:tk})});var d=await r.json();if(!d.ok||!d.data)return;
 var srv=JSON.parse(d.data),localU=+(localStorage.getItem(UPD)||0);if((srv.updated_at||0)>localU){jsave(MLS,srv.manual||[]);jsave(LS,srv.over||{});jsave(SKEY,srv.stars||[]);localStorage.setItem(UPD,srv.updated_at||0);over=jload(LS);manual=jload(MLS);stars=jload(SKEY);render();}}catch(e){}}
function setState(url,st){over[url]=st;jsave(LS,over);push();render();}
function toggleStar(co){const i=stars.indexOf(co);if(i>=0)stars.splice(i,1);else stars.push(co);jsave(SKEY,stars);push();render();}
function renderDots(){const d=allData();const defs=[['all','Tutte','#221d17']].concat(STDEF).concat([['expired','⏳ Scaduti','#ee9b00']]);
 $('dots').innerHTML=defs.map(([id,label,color])=>{const n=id==='all'?d.filter(o=>!isGone(o)).length:id==='expired'?d.filter(isGone).length:d.filter(o=>o.state===id&&!isGone(o)).length;
  return `<button class="dot${active===id?' active':''}" data-s="${id}" title="${label} (${n})" style="background:${color}"></button>`}).join('');
 $('dots').querySelectorAll('.dot').forEach(b=>b.onclick=()=>{active=b.dataset.s;idx=0;render()});}
function renderCard(){
 if(API&&!localStorage.getItem(TOK)){$('stage').innerHTML='<div class="wmsg">Apri prima l\'app e accedi col tuo codice.<br><a class="wopen" href="./">↗ apri l\'app</a></div>';$('pos').textContent='';return;}
 const p=pool();if(!p.length){$('stage').innerHTML='<div class="wmsg">Nessun job in questo stato.</div>';$('pos').textContent='';return;}
 if(idx>=p.length)idx=0;if(idx<0)idx=p.length-1;
 const o=p[idx],b=dlbadge(o),st=isStar(o),col=colorOf(o.state);
 const tags=[];if(o.fit!=null)tags.push(`<span class="wtag fit" style="${fitStyle(o.fit)}">fit ${o.fit}</span>`);
 if(b)tags.push(`<span class="wtag ${b.cls}">${b.txt}</span>`);if(o.gap)tags.push('<span class="wtag gap">CONOSCENZE DA INTEGRARE</span>');
 if(o.src==='manual')tags.push('<span class="wtag src-m">MANUALE</span>');else if(o.src==='grad')tags.push('<span class="wtag src-g">GRAD</span>');
 const reasons=o.reasons&&o.reasons.length?`<ul class="wreasons">${o.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>`:'';
 const opt=STDEF.map(([id,label])=>`<option value="${id}"${id===o.state?' selected':''}>${label}</option>`).join('');
 $('stage').innerHTML=`<div class="wcard" style="border-color:${col}">
   <div class="wcompany">${st?'★ ':''}${esc(o.company)}</div>
   <div class="wrole">${esc(o.title)}</div>
   <div class="wtags">${tags.join('')}</div>${reasons}
   <div class="wmeta"><span>${esc(o.loc)}</span><span style="color:${col};font-weight:600">${esc(labelOf(o.state))}</span></div>
   <div class="wfoot"><button class="wstar${st?' on':''}" id="wstar" title="Preferito">${st?'★':'☆'}</button><select id="wstate">${opt}</select><a class="wapri" href="${esc(o.url)}" target="_blank" title="Apri annuncio">↗</a></div>
 </div>`;
 $('pos').textContent=`${idx+1} / ${p.length}`;
 $('wstar').onclick=()=>toggleStar(o.company);
 $('wstate').onchange=e=>setState(o.url,e.target.value);
}
function render(){renderDots();renderCard();}
function next(){const p=pool();if(p.length){idx=(idx+1)%p.length;renderCard();}}
function prev(){const p=pool();if(p.length){idx=(idx-1+p.length)%p.length;renderCard();}}
$('next').onclick=next;$('prev').onclick=prev;
window.addEventListener('keydown',e=>{if(e.key==='ArrowRight')next();else if(e.key==='ArrowLeft')prev();});
var sx=null;const stage=$('stage');
stage.addEventListener('pointerdown',e=>{sx=e.clientX});
stage.addEventListener('pointerup',e=>{if(sx===null)return;var dx=e.clientX-sx;sx=null;if(dx<-40)next();else if(dx>40)prev();});
render();pull();window.addEventListener('focus',pull);
if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}))}
</script></body></html>"""
WIDGET = WIDGET.replace("__DATA__", data).replace("__STDEF__", STDEF).replace("__CONFIGJS__", CONFIGJS)
open(os.path.join(ROOT,"widget.html"),"w",encoding="utf-8").write(WIDGET)

ng = sum(1 for o in offers if o["src"]=="grad")
nd = sum(1 for o in offers if o.get("deadline") or o.get("dead"))
print(f"{outfile} · {len(offers)} card ({ng} grad, {nd} con scadenza/link-rot) · {len(H)} bytes")
