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
STUDY = json.dumps(load_json("data/study_plan.json", {}).get("topics", []), ensure_ascii=False)

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
--bg-page:#ece5d9;--bg-surface:#e6ded0;--bg-card:#f9f5ef;--border:rgba(0,18,25,0.09);--text:#221d17;--text-2:#4f4636;--text-3:#6f6247;
--radius-sm:6px;--radius-md:8px;--radius-lg:10px;--radius-xl:12px;--sp1:4px;--sp2:8px;--sp3:12px;--sp4:16px;--sp5:20px;--sp6:24px;--trans:150ms ease-out;--ease:cubic-bezier(.22,1,.36,1);--z-menu:60;}
@media(prefers-color-scheme:dark){:root{--bg-page:#100d0b;--bg-surface:#1a140f;--bg-card:#201a14;--border:rgba(233,216,166,0.09);--text:#e9e1d4;--text-2:#c3b7a2;--text-3:#9a8d76;}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg-page);color:var(--text);line-height:1.45;-webkit-font-smoothing:antialiased;height:100vh;overflow:hidden}
.app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:230px;flex-shrink:0;display:flex;flex-direction:column;border-right:1px solid var(--border);background:var(--bg-surface);padding:var(--sp4) 0;overflow-y:auto}
.sidebar-brand{display:flex;align-items:center;gap:var(--sp3);padding:0 var(--sp4) var(--sp4);font-size:18px;font-weight:600;letter-spacing:-.3px;border-bottom:1px solid var(--border);margin-bottom:var(--sp3);color:var(--text)}
.study-panel{margin-top:auto;padding:var(--sp3) var(--sp3) var(--sp2);border-top:1px solid var(--border)}
.study-panel h4{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--text-3);margin:2px 0 6px;padding:0 6px}
.study-item{border-radius:8px}
.study-item>summary{list-style:none;cursor:pointer;padding:5px 6px;border-radius:8px;display:flex;align-items:center;gap:7px;color:var(--text-2);font-weight:500;font-size:12.5px}
.study-item>summary::-webkit-details-marker{display:none}
.study-item>summary:hover{background:var(--bg-card)}
.study-item[open]>summary{color:var(--text)}
.study-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.study-body{padding:1px 8px 8px 20px;color:var(--text-3);font-size:11.5px;line-height:1.5}
.study-body .why{margin-bottom:5px}
.study-body b{color:var(--text-2);font-weight:600}
.study-roles{display:flex;flex-wrap:wrap;gap:3px;margin-top:6px}
.study-roles span{font-size:9.5px;background:var(--bg-card);border:1px solid var(--border);border-radius:20px;padding:1px 6px;color:var(--text-3)}
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
.tb-right{display:flex;align-items:center;gap:var(--sp2);margin-left:auto}
.btn-icon{width:34px;height:34px;border-radius:var(--radius-md);border:1px solid var(--border);background:var(--bg-card);color:var(--text-2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:background var(--trans),color var(--trans),transform var(--trans),border-color var(--trans);font-size:16px}
.btn-icon svg{width:16px;height:16px}
.btn-icon:hover{background:var(--bg-surface);color:var(--text);border-color:var(--text-3)}
.btn-icon:active{transform:scale(.92)}
.btn-primary{display:inline-flex;align-items:center;gap:6px;padding:7px var(--sp4);border-radius:var(--radius-lg);border:1px solid var(--p-deep);background:var(--p-deep);color:#fff;font-size:14px;font-weight:500;cursor:pointer;font-family:inherit;transition:background var(--trans),transform var(--trans),box-shadow var(--trans)}
.btn-primary svg{width:15px;height:15px}
.btn-primary:hover{background:var(--p-teal);box-shadow:0 3px 10px rgba(10,147,150,.28)}
.btn-primary:active{transform:translateY(1px);box-shadow:none}
.btn-icon:focus-visible,.btn-primary:focus-visible,.chip:focus-visible,.avatar:focus-visible{outline:2px solid var(--p-teal);outline-offset:2px}
.avatar{width:34px;height:34px;border-radius:50%;border:none;padding:0;cursor:pointer;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:13px;letter-spacing:.01em;line-height:1;box-shadow:0 1px 3px rgba(0,18,25,.22),inset 0 1px 1px rgba(255,255,255,.35),inset 0 -3px 6px rgba(0,18,25,.18);transition:transform var(--trans),box-shadow var(--trans);text-shadow:0 1px 2px rgba(0,18,25,.35)}
.avatar:hover{transform:translateY(-1px);box-shadow:0 5px 14px rgba(0,18,25,.24),inset 0 1px 1px rgba(255,255,255,.4),inset 0 -3px 6px rgba(0,18,25,.18)}
.avatar:active{transform:scale(.95)}
.av-menu{position:fixed;z-index:var(--z-menu);min-width:196px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:5px;box-shadow:0 14px 38px rgba(0,18,25,.18);display:none;flex-direction:column;gap:1px;transform-origin:top right;animation:menuIn .16s var(--ease)}
.av-menu.open{display:flex}
.av-head{padding:8px 10px 7px;border-bottom:1px solid var(--border);margin-bottom:3px;display:flex;flex-direction:column;gap:2px}
.av-head b{font-size:13px;color:var(--text);font-weight:600;line-height:1.2}
.av-head span{font-size:11px;color:var(--text-3);font-variant-numeric:tabular-nums}
.av-menu button{display:flex;align-items:center;gap:9px;text-align:left;padding:8px 10px;border:none;background:transparent;color:var(--text-2);font-size:13px;cursor:pointer;font-family:inherit;border-radius:var(--radius-sm);transition:background var(--trans),color var(--trans)}
.av-menu button:hover{background:var(--bg-surface);color:var(--text)}
.av-menu button svg{width:16px;height:16px;flex-shrink:0;opacity:.75}
.pf-tabs{display:flex;gap:4px;background:var(--bg-page);border:1px solid var(--border);border-radius:var(--radius-lg);padding:4px}
.pf-tab{flex:1;padding:7px 10px;border:none;background:transparent;color:var(--text-2);font-size:13px;font-weight:500;border-radius:var(--radius-md);cursor:pointer;font-family:inherit;transition:background var(--trans),color var(--trans),box-shadow var(--trans)}
.pf-tab:hover{color:var(--text)}
.pf-tab.active{background:var(--bg-card);color:var(--text);box-shadow:0 1px 3px rgba(0,18,25,.10)}
.pf-panel{display:flex;flex-direction:column;gap:var(--sp3)}
.tags-bar{display:flex;align-items:center;gap:var(--sp2);padding:var(--sp3) var(--sp5);flex-shrink:0;flex-wrap:wrap}
.chip{padding:4px var(--sp3);border-radius:999px;border:1px solid var(--border);background:transparent;color:var(--text-2);font-size:12px;cursor:pointer;font-family:inherit;transition:all var(--trans)}
.chip:hover{border-color:var(--text-3);color:var(--text)}
.chip.active{background:var(--text);color:var(--bg-page);border-color:var(--text)}
.tags-bar.cats{padding-top:0;padding-bottom:var(--sp3);gap:6px}
.chip.cat{font-size:11.5px;padding:3px 10px}
.chip.cat.active{background:var(--p-teal);color:#001219;border-color:var(--p-teal)}
.chip .cn{opacity:.55;font-variant-numeric:tabular-nums;font-size:10px;margin-left:2px}
.chip.cat.active .cn{opacity:.8}
.cards-scroll{flex:1;overflow-y:auto;padding:var(--sp4) var(--sp5) var(--sp5)}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:var(--sp3)}
.card{background:var(--bg-card);border-radius:var(--radius-lg);border:1px solid var(--border);padding:var(--sp4);cursor:pointer;position:relative;transition:transform var(--trans),box-shadow var(--trans),border-color var(--trans)}
.card:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,18,25,0.06)}
.card.gone{opacity:.5}
.card-actions{position:absolute;top:8px;right:8px;display:flex;gap:4px;opacity:0;transition:opacity var(--trans)}
.card:hover .card-actions{opacity:1}
.card-actions button{width:26px;height:26px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-surface);color:var(--text-2);display:inline-flex;align-items:center;justify-content:center;cursor:pointer;font-size:13px}
.card-actions button:hover{background:var(--bg-card);color:var(--text)}
.card-actions button svg{width:14px;height:14px}
.card-actions button:active{transform:scale(.9)}
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
.cards-grid.list .card{display:flex;align-items:center;gap:var(--sp3);padding:9px var(--sp4);border-color:var(--border)!important}
.cards-grid.list .card:hover{transform:none;box-shadow:none;border-color:var(--text-3)!important}
.cards-grid.list .card-reasons{display:none}
.cards-grid.list .card-company{margin:0;padding:0;width:128px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cards-grid.list .card-role{margin:0;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13.5px}
.cards-grid.list .card-tags{margin:0;flex-shrink:0;flex-wrap:nowrap}
.cards-grid.list .card-meta{margin:0;padding:0;border:0;flex-shrink:0;width:118px;justify-content:flex-end;gap:8px}
.cards-grid.list .card-meta span:first-child{display:none}
.cards-grid.list .card-actions{position:static;opacity:1;order:6;flex-shrink:0}
@media(max-width:600px){.cards-grid.list .card-company{width:92px}.cards-grid.list .card-meta{width:auto}}
.hint{padding:0 var(--sp5) var(--sp2);font-size:12px;color:var(--text-3)}
.modal-overlay{position:fixed;inset:0;z-index:100;background:rgba(0,18,25,0.35);display:none;align-items:center;justify-content:center;padding:var(--sp4);backdrop-filter:blur(3px);animation:overlayIn .18s ease-out}
.modal{width:100%;max-width:440px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-xl);padding:var(--sp5);display:flex;flex-direction:column;gap:var(--sp4);box-shadow:0 20px 60px rgba(0,18,25,.22);animation:modalIn .24s var(--ease)}
@keyframes overlayIn{from{opacity:0}to{opacity:1}}
@keyframes modalIn{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
@keyframes menuIn{from{opacity:0;transform:translateY(-4px) scale(.97)}to{opacity:1;transform:none}}
.modal-header{display:flex;align-items:center;justify-content:space-between}.modal-header h3{font-size:17px;font-weight:600}
.form-body{display:flex;flex-direction:column;gap:var(--sp3)}
.form-body label{font-size:12px;font-weight:500;color:var(--text-2);display:flex;flex-direction:column;gap:5px;text-transform:uppercase;letter-spacing:.3px}
.form-body input,.form-body select,.form-body textarea{padding:9px var(--sp3);border-radius:var(--radius-lg);border:1px solid var(--border);background:var(--bg-page);color:var(--text);font-size:14px;outline:none;font-family:inherit;text-transform:none;letter-spacing:0;transition:border-color var(--trans),box-shadow var(--trans)}
.form-body textarea{resize:vertical;line-height:1.5}
.form-body input:focus,.form-body select:focus,.form-body textarea:focus{border-color:var(--p-teal);box-shadow:0 0 0 3px rgba(10,147,150,.14)}
.modal-footer{display:flex;justify-content:flex-end;gap:var(--sp2)}
.btn-secondary{padding:7px var(--sp4);border-radius:var(--radius-lg);border:1px solid var(--border);background:transparent;color:var(--text-2);font-size:14px;cursor:pointer;font-family:inherit}
.btn-secondary:hover{background:var(--bg-surface)}
.modal.eng{max-width:520px}
.eng-body{display:flex;flex-direction:column;gap:var(--sp3);font-size:13.5px;color:var(--text-2);line-height:1.5}
.eng-body p{margin:0}
.eng-step{display:flex;gap:var(--sp3);align-items:flex-start}
.eng-n{flex-shrink:0;width:22px;height:22px;border-radius:50%;background:var(--p-teal);color:#001219;font-weight:700;font-size:12px;display:inline-flex;align-items:center;justify-content:center}
.eng-code{display:flex;align-items:center;gap:8px;margin-top:5px;background:var(--bg-page);border:1px solid var(--border);border-radius:var(--radius-md);padding:7px 10px}
.eng-code code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--text);flex:1;overflow-x:auto;white-space:nowrap}
.eng-copy{flex-shrink:0;border:1px solid var(--border);background:var(--bg-card);color:var(--text-2);border-radius:var(--radius-sm);padding:3px 9px;font-size:11.5px;cursor:pointer;font-family:inherit}
.eng-copy:hover{background:var(--bg-surface);color:var(--text)}
.eng-hint{font-size:11.5px;color:var(--text-3)}
.eng-foot{display:flex;gap:var(--sp2);flex-wrap:wrap;margin-top:2px}
.eng-foot a{text-decoration:none}
.eng-note{font-size:11px;color:var(--text-3)}
@media(max-width:768px){.sidebar{width:200px}.cards-grid{grid-template-columns:1fr}}
@media(max-width:600px){.app{flex-direction:column}.sidebar{width:100%;flex-direction:row;padding:var(--sp3) var(--sp4);border-right:none;border-bottom:1px solid var(--border);overflow-x:auto;gap:var(--sp2)}.sidebar-brand{display:none}.status-list{flex-direction:row;padding:0}.status-item{white-space:nowrap}}
@media(max-width:600px){.topbar{gap:var(--sp2);padding:var(--sp3) var(--sp4)}.search-box{max-width:none}.tb-right{gap:6px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}.card:hover,.avatar:hover,.btn-primary:hover{transform:none}}
__GATECSS__
</style></head><body>__GATE__
<div class="app">
  <aside class="sidebar">
    <div class="sidebar-brand"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="color:var(--p-teal);flex-shrink:0"><path d="M4 4h16v2H4zm0 5h10v2H4zm0 5h16v2H4z" fill="currentColor"/></svg>Job Pipeline</div>
    <nav class="status-list" id="statusList"></nav>
    <div class="study-panel" id="studyPanel"></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <div class="search-box"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-3);flex-shrink:0"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.2-4.2"/></svg><input type="text" id="searchInput" placeholder="Cerca azienda o ruolo…"></div>
      <div class="tb-right">
      <button class="btn-icon" id="themeToggle" title="Tema chiaro / scuro"><svg id="iconSun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg id="iconMoon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:none"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></button>
      <button class="btn-icon" id="exportBtn" title="Esporta (Markdown)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v11"/><path d="M8 10.5l4 4 4-4"/><path d="M5 20h14"/></svg></button>
      <button class="btn-icon" id="viewToggle" title="Vista lista"><svg id="iconList" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg><svg id="iconGrid" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:none"><rect x="3.5" y="3.5" width="7" height="7" rx="1.4"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.4"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.4"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.4"/></svg></button>
      <button class="btn-icon" id="widgetBtn" title="Widget desktop (card singola)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6"/><path d="M20 4l-8.5 8.5"/><path d="M18 13.5V18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4.5"/></svg></button>
      <button class="btn-icon" id="engineBtn" title="Motore AI avanzato (opzionale, in locale)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.7 4.6 4.6 1.7-4.6 1.7L12 15.6l-1.7-4.6L5.7 9.3l4.6-1.7z"/><path d="M18 14.4l.65 1.75 1.75.65-1.75.65L18 19.9l-.65-1.75-1.75-.65 1.75-.65z"/></svg></button>
      <button class="btn-primary" id="addJobBtn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg><span>Nuova</span></button>
      </div>
    </header>
    <div class="tags-bar" id="tagsBar">
      <button class="chip active" data-tag="all">Tutte</button>
      <button class="chip" data-tag="star">⭐ Preferiti</button>
      <button class="chip" data-tag="fit4">Fit ≥4</button>
      <button class="chip" data-tag="fit3">Fit ≥3</button>
    </div>
    <div class="tags-bar cats" id="catBar"></div>
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
<div class="modal-overlay" id="engineModal"><div class="modal eng">
  <div class="modal-header"><h3>Motore AI</h3><button class="btn-icon" id="closeEngine">✕</button></div>
  <div class="eng-body" id="engBody"></div>
</div></div>
<script>
const EMBED=__DATA__, STDEF=__STDEF__, STUDY=__STUDY__;
const PARK=new Set(["skip","rejected","discarded"]);
const LS="jobpipe_v1", MLS="jobpipe_manual_v1", SKEY="jobpipe_star_v1";
function jload(k){try{return JSON.parse(localStorage.getItem(k))||((k===MLS||k===SKEY)?[]:{})}catch(e){return (k===MLS||k===SKEY)?[]:{}}}
function jsave(k,v){localStorage.setItem(k,JSON.stringify(v))}
let over=jload(LS), manual=jload(MLS), stars=jload(SKEY);
let active="evaluated", filterMode="all", searchQuery="", editingUrl=null, viewMode=localStorage.getItem('jobpipe_view')||'card', catFilter="all";
const _IK='viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';
const IC={
  starOn:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3.4l2.55 5.17 5.7.83-4.12 4.02.97 5.68L12 16.42 6.9 19.1l.97-5.68L3.75 9.4l5.7-.83z"/></svg>',
  star:'<svg '+_IK+'><path d="M12 3.4l2.55 5.17 5.7.83-4.12 4.02.97 5.68L12 16.42 6.9 19.1l.97-5.68L3.75 9.4l5.7-.83z"/></svg>',
  open:'<svg '+_IK+'><path d="M8 6.5h9.5V16"/><path d="M17.5 6.5L7 17"/></svg>',
  edit:'<svg '+_IK+'><path d="M4 20h4L18.5 9.5a1.98 1.98 0 0 0-2.8-2.8L5 17.2z"/><path d="M13.4 6.6l4 4"/></svg>',
  del:'<svg '+_IK+'><path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l.9 12.5h9.2L17.5 7"/></svg>'
};
const CATS=["Spazio","AI","Energia","Fintech","Dev & Infra","Altro"];
function catOf(o){if(o.cat)return o.cat;const s=((o.company||'')+' '+(o.title||'')+' '+(o.loc||'')).toLowerCase();
 if(/space|spazio|aerospace|satellit|orbital|thales alenia|leonardo|argotec|altec|tyvak|terran|aiko|\besa\b|spacex|\basi\b|avio|d-orbit|kayser|sitael|euspa/.test(s))return"Spazio";
 if(/\bai\b|machine learning|\bml\b|\bllm\b|genai|elevenlabs|cohere|synthesia|bland|mistral|hugging|anthropic|openai|deepmind/.test(s))return"AI";
 if(/equinor|energy|energia|renewable|\btesla\b|solar|\bwind\b|oil|gas/.test(s))return"Energia";
 if(/revolut|fintech|\bbank\b|payment|trading|neobank/.test(s))return"Fintech";
 if(/supabase|lovable|vercel|database|devtools|developer tools|\binfra\b|platform|kubernetes/.test(s))return"Dev & Infra";
 return"Altro";}
function inCat(o){return catFilter==='all'||catOf(o)===catFilter}
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
function renderCats(){
  const base=filtered();
  const defs=[['all','Tutte']].concat(CATS.map(c=>[c,c]));
  $('catBar').innerHTML=defs.map(([id,label])=>{const n=id==='all'?base.length:base.filter(o=>catOf(o)===id).length;
   if(id!=='all'&&n===0)return '';
   return `<button class="chip cat${catFilter===id?' active':''}" data-cat="${id}">${label} <span class="cn">${n}</span></button>`}).join('');
  $('catBar').querySelectorAll('.chip').forEach(b=>b.onclick=()=>{catFilter=b.dataset.cat;render()});
}
function renderSidebar(){
  const fd=filtered().filter(inCat); let html='';
  function item(id,label,color,n){return `<button class="status-item${active===id?' active':''}" data-s="${id}"><span class="status-dot" style="background:${color}"></span><span class="status-label">${label}</span><span class="status-count">${n}</span></button>`}
  html+=item('all','Tutte','#001219',fd.filter(o=>!isGone(o)).length);
  STDEF.forEach(([id,label,color])=>{html+=item(id,label,color,fd.filter(o=>o.state===id&&!isGone(o)).length)});
  html+=item('expired','⏳ Scaduti','#ee9b00',fd.filter(isGone).length);
  $('statusList').innerHTML=html;
  $('statusList').querySelectorAll('.status-item').forEach(b=>b.onclick=()=>{active=b.dataset.s;render()});
  renderStudy();
}
function renderStudy(){
  const el=$('studyPanel'); if(!el||el.children.length) return;
  const pc={high:'var(--p-orange)',med:'var(--p-gold)',low:'var(--p-teal)'};
  let h='<h4>📚 Cosa studiare</h4>';
  STUDY.forEach(t=>{const dot=pc[t.priority]||'var(--text-3)';
    h+=`<details class="study-item"><summary><span class="study-dot" style="background:${dot}"></span>${esc(t.topic)}</summary>`+
       `<div class="study-body"><div class="why">${esc(t.why||'')}</div>`+
       (t.exercise?`<div><b>Esercizio:</b> ${esc(t.exercise)}</div>`:'')+
       (t.project?`<div><b>Progetto:</b> ${esc(t.project)}</div>`:'')+
       `<div class="study-roles">${(t.roles||[]).map(r=>`<span>${esc(r)}</span>`).join('')}</div></div></details>`;});
  el.innerHTML=h;
}
function renderCards(){
  const grid=$('cardsGrid'), fd=filtered().filter(inCat);
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
        <button class="ca-star${st?' on':''}" title="Preferito (dream)">${st?IC.starOn:IC.star}</button>
        <button class="ca-open" title="Apri annuncio">${IC.open}</button>
        ${o.src==='manual'?'<button class="ca-edit" title="Modifica">'+IC.edit+'</button><button class="ca-del" title="Elimina">'+IC.del+'</button>':''}
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
function render(){renderCats();renderSidebar();renderCards();}
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
function updateViewBtn(){var l=$('iconList'),g=$('iconGrid');if(l&&g){l.style.display=viewMode==='list'?'none':'';g.style.display=viewMode==='list'?'':'none';}$('viewToggle').title=viewMode==='list'?'Vista card':'Vista lista';}
updateViewBtn();
$('viewToggle').onclick=()=>{viewMode=viewMode==='list'?'card':'list';localStorage.setItem('jobpipe_view',viewMode);updateViewBtn();render();};
const ENG_CMD='git clone https://github.com/javas-cri-pt/career-ops';
const ENG_DL='https://github.com/javas-cri-pt/career-ops/archive/refs/heads/main.zip';
$('engBody').innerHTML=
 '<p>Questa app è la tua <b>board</b>. Per il mio <b>stesso flusso</b> (ricerca automatica di annunci e <b>graduate program</b> + <b>CV/cover su misura</b>), fai girare in locale il motore <b>career-ops</b> — la <b>mia versione</b>, con la board già integrata — col tuo AI CLI (Claude Code, Codex, Gemini…). Gira sul <b>tuo</b> computer, coi tuoi dati.</p>'
 +'<div class="eng-step"><span class="eng-n">1</span><div><b>Scarica il motore</b> (serve git + Node 18+):<div class="eng-code"><code id="engCmd">'+ENG_CMD+'</code><button class="eng-copy" id="engCopy">Copia</button></div></div></div>'
 +'<div class="eng-step"><span class="eng-n">2</span><div><b>Entra, installa, apri il tuo AI CLI</b>:<div class="eng-code"><code>cd career-ops, npm install, poi: claude</code></div><span class="eng-hint">oppure codex, gemini, opencode…</span></div></div>'
 +'<div class="eng-step"><span class="eng-n">3</span><div><b>Ti fa lui le domande</b> (CV, ruoli, «vuoi la board + graduate program?»). Dagli il <b>codice</b> che ti ho dato: da lì ogni lavoro che trova <b>finisce qui nella board</b>, in automatico.</div></div>'
 +'<div class="eng-foot"><a class="btn-primary" href="https://github.com/javas-cri-pt/career-ops" target="_blank" rel="noopener">Vai al repo</a><a class="btn-secondary" href="'+ENG_DL+'">Scarica ZIP</a></div>'
 +'<p class="eng-note">Fork open-source (MIT) del career-ops di Santiago Fernández de Valderrama, adattato con la board. Nessun dato personale incluso.</p>';
$('engineBtn').onclick=()=>{$('engineModal').style.display='flex'};
$('closeEngine').onclick=()=>{$('engineModal').style.display='none'};
$('engineModal').onclick=e=>{if(e.target.id==='engineModal')$('engineModal').style.display='none'};
$('engCopy').onclick=()=>{navigator.clipboard.writeText(ENG_CMD).then(()=>{const b=$('engCopy');b.textContent='Copiato';setTimeout(()=>b.textContent='Copia',1400)}).catch(()=>{})};
$('searchInput').addEventListener('input',e=>{searchQuery=e.target.value;render()});
$('tagsBar').addEventListener('click',e=>{if(!e.target.classList.contains('chip'))return;document.querySelectorAll('#tagsBar .chip').forEach(c=>c.classList.remove('active'));e.target.classList.add('active');filterMode=e.target.dataset.tag;render()});
$('exportBtn').onclick=()=>{const rows=DATA.filter(o=>o.state!=='pending').map(o=>`| ${o.company} | ${o.title} | ${o.state} | ${o.fit??''} | ${o.deadline??''} | ${o.loc} | ${o.url} |`);
 const md="# applications.md (export)\n\n| Company | Role | Status | Fit | Deadline | Location | URL |\n|---|---|---|---|---|---|---|\n"+rows.join("\n");
 const bl=new Blob([md],{type:'text/markdown'});const a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download='applications-export.md';a.click()};
// theme
function applyTheme(dark){const r=document.documentElement;
 r.style.setProperty('--bg-page',dark?'#100d0b':'#ece5d9');r.style.setProperty('--bg-surface',dark?'#1a140f':'#e6ded0');r.style.setProperty('--bg-card',dark?'#201a14':'#f9f5ef');
 r.style.setProperty('--border',dark?'rgba(233,216,166,0.09)':'rgba(0,18,25,0.09)');r.style.setProperty('--text',dark?'#e9e1d4':'#221d17');r.style.setProperty('--text-2',dark?'#c3b7a2':'#4f4636');r.style.setProperty('--text-3',dark?'#9a8d76':'#6f6247');
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
      '<h3>3 · Vuoi scraping automatico + CV su misura?</h3>'
      '<p>Premi il tasto <b>Motore AI</b> (l\'icona a stelline, in alto a destra). Fai girare in locale il motore <b>career-ops</b> col tuo AI CLI (<b>Claude Code</b>, <b>Codex</b>, Gemini…): <b>ti trova</b> annunci e <b>graduate program</b>, li <b>valuta</b>, genera <b>CV/cover su misura</b> e <b>sincronizza tutto qui nella board</b>. Gira sul <b>tuo</b> computer, coi tuoi dati. Non serve saper programmare.</p>'
      '<ol><li>Installa il tuo AI CLI (Claude Code o Codex), <b>git</b> e <b>Node 18+</b>.</li>'
      '<li>Scarica il motore: <code>git clone https://github.com/javas-cri-pt/career-ops</code></li>'
      '<li><code>cd career-ops</code>, <code>npm install</code>, poi avvia <code>claude</code> (o <code>codex</code>).</li>'
      '<li>Rispondi alle sue domande e dagli il <b>codice</b> che ti ho dato: da lì i lavori che trova <b>compaiono qui</b>. Poi chiedi a parole tue: «Trovami graduate program in Europa e valutali».</li></ol>'
      '<p style="font-size:13px;color:var(--text-3)">I lavori trovati dal motore <b>si sincronizzano</b> in questa board (stesso codice), su telefono e PC.</p>'
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
/* Esci ora vive nel menu dell'avatar (initProfile) */
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
function initProfile(){
 if(!API||!localStorage.getItem(TOK))return;
 var bar=document.querySelector('.topbar');if(!bar||document.getElementById('avatarBtn'))return;
 var code=(localStorage.getItem(TOK)||'').split('.')[0]||'';
 var hh=2166136261;for(var _i=0;_i<code.length;_i++){hh^=code.charCodeAt(_i);hh=(hh*16777619)>>>0;}
 var hue1=hh%360,hue2=(hue1+128+(Math.floor(hh/360)%80))%360;
 var grad='linear-gradient(140deg,hsl('+hue1+' 58% 54%),hsl('+hue2+' 62% 42%))';
 var av=document.createElement('button');av.id='avatarBtn';av.className='avatar';av.title='Il mio profilo';av.setAttribute('aria-label','Il mio profilo');av.style.background=grad;
 function setMono(nm){nm=(nm||'').trim();if(nm){av.textContent=nm.charAt(0).toUpperCase();var an=document.getElementById('avName');if(an)an.textContent=nm;localStorage.setItem('jobpipe_pname',nm);}}
 av.textContent=((localStorage.getItem('jobpipe_pname')||'').trim().charAt(0)||'').toUpperCase();
 (bar.querySelector('.tb-right')||bar).appendChild(av);
 var menu=document.createElement('div');menu.className='av-menu';menu.id='avMenu';
 menu.innerHTML='<div class="av-head"><b id="avName">'+(localStorage.getItem('jobpipe_pname')||'Il mio account')+'</b><span>'+code+'</span></div>'
  +'<button id="avProfile"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8.4" r="3.6"/><path d="M4.5 20c0-3.4 3.2-5.6 7.5-5.6s7.5 2.2 7.5 5.6"/></svg>Il mio profilo</button>'
  +'<button id="avLogout"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5V4.2A1.2 1.2 0 0 0 13.8 3H6.2A1.2 1.2 0 0 0 5 4.2v15.6A1.2 1.2 0 0 0 6.2 21h7.6a1.2 1.2 0 0 0 1.2-1.2V19"/><path d="M19 12H9.5M16 9l3 3-3 3"/></svg>Esci</button>';
 document.body.appendChild(menu);
 function closeMenu(){menu.classList.remove('open');document.removeEventListener('click',onDoc);}
 function onDoc(e){if(!menu.contains(e.target)&&e.target!==av)closeMenu();}
 av.onclick=function(e){e.stopPropagation();if(menu.classList.contains('open')){closeMenu();return;}var r=av.getBoundingClientRect();menu.style.top=(r.bottom+8)+'px';menu.style.right=Math.max(8,window.innerWidth-r.right)+'px';menu.classList.add('open');setTimeout(function(){document.addEventListener('click',onDoc);},0);};
 window.addEventListener('resize',closeMenu);
 document.getElementById('avLogout').onclick=function(){closeMenu();logout();};
 if(!av.textContent){fetch(API+'/profile/get',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_auth())}).then(function(r){return r.json();}).then(function(d){try{var p=(d&&d.data)?JSON.parse(d.data):{};setMono((p.contact||{}).name);}catch(e){}}).catch(function(){});}
 var ROLES=['AI / Builder / FDE','Product Manager','Project / Program Manager','Solutions / Pre-sales','Innovation / Strategy','Data / ML','Software Engineering','Spazio / Aerospace','Altro'];
 var LAYOUTS=[['serif','Classico serif'],['twocol','Moderno due colonne'],['compact','Compatto una pagina'],['tech','Tech minimale']];
 var rolehd='style="font-size:12px;font-weight:500;color:var(--text-2);text-transform:uppercase;letter-spacing:.3px"';
 var ov=document.createElement('div');ov.className='modal-overlay';ov.id='profileModal';
 ov.innerHTML='<div class="modal" style="max-width:560px;max-height:90vh;overflow-y:auto">'
  +'<div class="modal-header"><h3>Il mio profilo</h3><button class="btn-icon" id="pfClose">✕</button></div>'
  +'<div class="pf-tabs"><button class="pf-tab active" data-t="0">Anagrafica</button><button class="pf-tab" data-t="1">Ricerca</button><button class="pf-tab" data-t="2">CV</button></div>'
  +'<div class="form-body">'
  +'<div class="pf-panel" data-p="0">'
  +'<label>Nome<input id="pf_name"></label><label>Email<input id="pf_email"></label>'
  +'<label>LinkedIn<input id="pf_linkedin"></label><label>GitHub<input id="pf_github"></label><label>Citta<input id="pf_city"></label>'
  +'</div>'
  +'<div class="pf-panel" data-p="1" style="display:none">'
  +'<div '+rolehd+'>Famiglie di ruolo</div>'
  +'<div id="pf_roles" style="display:flex;flex-wrap:wrap;gap:8px">'+ROLES.map(function(r){return '<label style="display:flex;gap:5px;align-items:center;font-size:12px;text-transform:none;letter-spacing:0"><input type="checkbox" value="'+r+'" style="width:auto"> '+r+'</label>'}).join('')+'</div>'
  +'<label>Sedi / modalita<input id="pf_loc" placeholder="es. remote EU, Torino, ibrido"></label>'
  +'<label>Seniority<select id="pf_sen"><option>stage</option><option>junior</option><option>junior-mid</option><option>mid</option><option>qualsiasi</option></select></label>'
  +'<label>Keyword<input id="pf_kw" placeholder="es. RAG, agenti, fintech, spazio"></label>'
  +'<label>Settori da evitare<input id="pf_avoid"></label>'
  +'<label>Autorizzazione al lavoro<input id="pf_auth" placeholder="es. UE"></label>'
  +'<label>Lingue<input id="pf_lang" placeholder="es. IT madrelingua, EN C1, DE B1"></label>'
  +'</div>'
  +'<div class="pf-panel" data-p="2" style="display:none">'
  +'<label>Layout CV<select id="pf_layout">'+LAYOUTS.map(function(l){return '<option value="'+l[0]+'">'+l[1]+'</option>'}).join('')+'</select></label>'
  +'<label>Colore accento<input id="pf_accent" placeholder="es. teal, blu, coral, #22417a"></label>'
  +'<label>Lingua CV<select id="pf_cvlang"><option value="it">Italiano</option><option value="en">English</option></select></label>'
  +'<label>Il tuo CV / dati (incolla)<textarea id="pf_cv" rows="6" style="font-family:inherit;text-transform:none"></textarea></label>'
  +'</div>'
  +'</div>'
  +'<div class="modal-footer"><span id="pf_status" style="font-size:12px;color:var(--text-3);margin-right:auto"></span><button class="btn-secondary" id="pfCancel">Chiudi</button><button class="btn-primary" id="pfSave">Salva</button></div></div>';
 document.body.appendChild(ov);
 var _tabs=ov.querySelectorAll('.pf-tab'),_panels=ov.querySelectorAll('.pf-panel');
 _tabs.forEach(function(t){t.onclick=function(){_tabs.forEach(function(x){x.classList.remove('active')});t.classList.add('active');_panels.forEach(function(p){p.style.display=(p.getAttribute('data-p')===t.getAttribute('data-t'))?'':'none';});};});
 function sv(id,v){var e=document.getElementById(id);if(e)e.value=(v==null?'':v);}
 function gv(id){var e=document.getElementById(id);return e?e.value:'';}
 async function load(){try{var r=await fetch(API+'/profile/get',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_auth())});var d=await r.json();var p=(d&&d.data)?JSON.parse(d.data):{};var c=p.contact||{},s=p.search||{},cv=p.cv||{};
  sv('pf_name',c.name);sv('pf_email',c.email);sv('pf_linkedin',c.linkedin);sv('pf_github',c.github);sv('pf_city',c.city);setMono(c.name);
  sv('pf_loc',s.loc);sv('pf_kw',(s.keywords||[]).join(', '));sv('pf_avoid',s.avoid);sv('pf_auth',s.work_auth);sv('pf_lang',s.languages);
  if(s.seniority)document.getElementById('pf_sen').value=s.seniority;
  (s.roles||[]).forEach(function(r){var cb=document.querySelector('#pf_roles input[value="'+r+'"]');if(cb)cb.checked=true;});
  if(cv.layout)document.getElementById('pf_layout').value=cv.layout;if(cv.lang)document.getElementById('pf_cvlang').value=cv.lang;sv('pf_accent',cv.accent);sv('pf_cv',cv.text);
 }catch(e){}}
 async function save(){var st=document.getElementById('pf_status');st.textContent='Salvo...';
  var roles=[].slice.call(document.querySelectorAll('#pf_roles input:checked')).map(function(x){return x.value});
  var body={contact:{name:gv('pf_name'),email:gv('pf_email'),linkedin:gv('pf_linkedin'),github:gv('pf_github'),city:gv('pf_city')},
   search:{roles:roles,loc:gv('pf_loc'),seniority:gv('pf_sen'),keywords:gv('pf_kw').split(',').map(function(x){return x.trim()}).filter(Boolean),avoid:gv('pf_avoid'),work_auth:gv('pf_auth'),languages:gv('pf_lang')},
   cv:{layout:gv('pf_layout'),accent:gv('pf_accent'),lang:gv('pf_cvlang'),text:gv('pf_cv')},updated_at:Date.now()};
  try{var r=await fetch(API+'/profile/put',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_auth({data:JSON.stringify(body)}))});var d=await r.json();st.textContent=d.ok?'Salvato ✓':'Errore';if(d.ok)setMono(gv('pf_name'));setTimeout(function(){st.textContent=''},1600);}catch(e){st.textContent='Errore di rete';}}
 document.getElementById('avProfile').onclick=function(){closeMenu();ov.style.display='flex';load();};
 document.getElementById('pfClose').onclick=function(){ov.style.display='none';};
 document.getElementById('pfCancel').onclick=function(){ov.style.display='none';};
 ov.onclick=function(e){if(e.target===ov)ov.style.display='none';};
 document.getElementById('pfSave').onclick=save;
}
function unlock(){var g=document.getElementById('gate');if(g)g.style.display='none';tutOnce();syncInit();initProfile();}
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

H = (H.replace("__DATA__", data).replace("__STDEF__", STDEF).replace("__STUDY__", STUDY)
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
--bg-page:#ece5d9;--bg-surface:#e6ded0;--bg-card:#f9f5ef;--border:rgba(0,18,25,0.09);--text:#221d17;--text-2:#4f4636;--text-3:#6f6247;}
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
