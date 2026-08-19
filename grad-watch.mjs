#!/usr/bin/env node
// grad-watch.mjs — il NOSTRO grad-watch (Cristina).
// Gira su data/grad_sources.json (careers/early-careers di aziende target, tutti i domini
// incl. finanza), estrae i link a graduate/trainee/rotational program e li fonde in
// data/grad_watch.json (dedup per URL). Poi build-job-dashboard.py li mette in dashboard.
//
// Uso:  node grad-watch.mjs            (crawl tutte le fonti)
//       node grad-watch.mjs --dry      (stampa cosa troverebbe, non scrive)
// NB: le query WebSearch (scoperta di nuove aziende) le fa l'agente e le aggiunge a
//     grad_sources.json; questo script fa il crawl deterministico delle fonti note.

import { chromium } from 'playwright';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = join(ROOT, 'data/grad_sources.json');
const OUT = join(ROOT, 'data/grad_watch.json');
const DRY = process.argv.includes('--dry');
const KW = /(graduate|grad(-|\s)?scheme|trainee|traineeship|rotational|early(-|\s)?career|apprentice|neolaurea|programme|program)\b/i;
const NEG = /(privacy|cookie|login|newsletter|press|investor|contact|about-us)\b/i;

function load(p, fallback){ try { return JSON.parse(readFileSync(p,'utf8')) } catch { return fallback } }

const sources = load(SRC, []);
if (!sources.length){ console.error('Nessuna fonte in data/grad_sources.json'); process.exit(1); }
const existing = load(OUT, []);
const seen = new Set(existing.map(o => o.url));
const found = [];

const browser = await chromium.launch();
try {
  const MAXPER = 10; // cap per fonte: evita che una pagina-lista inondi il file
  for (const s of sources){
    if (s.harvest === false) { console.log(`[${s.company}] skip harvest (solo-monitoraggio)`); continue; }
    try {
      const page = await browser.newPage({ userAgent: 'Mozilla/5.0 job-research' });
      await page.goto(s.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1800);
      const origin = new URL(s.url).origin;
      const links = await page.evaluate((o) => Array.from(document.querySelectorAll('a[href]'))
        .map(a => ({ text: (a.textContent||'').replace(/\s+/g,' ').trim().slice(0,90), href: a.href }))
        .filter(l => l.href.startsWith(o)), origin);
      let n = 0;
      for (const l of links){
        const hay = l.text + ' ' + l.href;
        if (!KW.test(hay) || NEG.test(l.href)) continue;
        if (seen.has(l.href) || !l.text) continue;
        if (n >= MAXPER) break;
        seen.add(l.href); n++;
        found.push({ company: s.company, program: l.text, loc: s.loc || 'Europe', url: l.href,
                     note: `grad-watch crawl (${s.domain||'?'}) · verifica scadenza`, domain: s.domain||'?' });
      }
      console.log(`[${s.company}] ${n} program trovati`);
      await page.close();
    } catch (e) {
      console.error(`[${s.company}] errore: ${e.message}`);
    }
  }
} finally {
  await browser.close();
}

// ---- Seminare scadenze: estrai una deadline dalla pagina, CITANDOLA -----------
// Passo in piu' della pipeline. Cerca una data vicino a parole-chiave di scadenza
// (deadline / closing / apply by / scadenza / entro il...). Se non la trova -> null
// (fallback: nessuna scadenza, mai inventata). Vale sia per grad-watch sia, con la
// stessa logica, per la ricerca generale (vedi export in fondo).
const MONTHS = {jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12,
  gen:1,mag:5,giu:6,lug:7,ago:8,set:9,ott:10,dic:12,gennaio:1,febbraio:2,marzo:3,aprile:4,maggio:5,giugno:6,luglio:7,agosto:8,settembre:9,ottobre:10,novembre:11,dicembre:12};
const DL_KW = /(deadline|closing date|closes on|applications? (close|due|deadline)|apply by|last day|scadenz\w*|entro il|termine (ultimo|di presentazione)|candidature entro)/i;
function iso(y,m,d){ y=+y;m=+m;d=+d; if(m<1||m>12||d<1||d>31||y<2024||y>2100) return null;
  return `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
function findDate(s){
  let m;
  if((m=s.match(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/)))            return iso(m[1],m[2],m[3]);
  if((m=s.match(/\b(\d{1,2})[\/.](\d{1,2})[\/.](20\d{2})\b/)))    return iso(m[3],m[2],m[1]); // GG/MM/AAAA
  if((m=s.match(/\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-zàèéìòù]+)\.?,?\s+(20\d{2})\b/))){const mo=MONTHS[m[2].slice(0,3).toLowerCase()]||MONTHS[m[2].toLowerCase()]; if(mo)return iso(m[3],mo,m[1]);}
  if((m=s.match(/\b([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b/))){const mo=MONTHS[m[1].slice(0,3).toLowerCase()]; if(mo)return iso(m[3],mo,m[2]);}
  return null;
}
function extractDeadline(html){
  const text = html.replace(/<script[\s\S]*?<\/script>/gi,' ').replace(/<style[\s\S]*?<\/style>/gi,' ')
                   .replace(/<[^>]+>/g,' ').replace(/&[a-z]+;/g,' ').replace(/\s+/g,' ');
  let best=null;
  const re=new RegExp(DL_KW.source,'gi'); let k;
  while((k=re.exec(text))){
    const win=text.slice(Math.max(0,k.index-30), k.index+140);
    const d=findDate(win);
    if(d){ const q=win.trim().slice(0,120); if(!best||d<best.deadline) best={deadline:d, deadline_quote:q}; }
  }
  return best; // {deadline, deadline_quote} oppure null
}

// ---- Link-rot + seed-deadline: ri-verifica gli URL gia' in grad_watch.json ----
// dead:true su 404/redirect-verso-ricerca (NON cancella). Se la pagina e' viva,
// prova a seminare la scadenza citandola. Salta gli aggregatori.
const REDIR_SEARCH = /(\/search|\/results|\/jobs\/?(\?|$)|\/careers\/?(\?|$)|not.?found|404)/i;
async function checkRot(o){
  if (o.domain === 'aggregatore') return { ...o, dead:false };
  try {
    const r = await fetch(o.url, { method:'GET', redirect:'follow',
      headers:{ 'User-Agent':'Mozilla/5.0 job-research' }, signal: AbortSignal.timeout(15000) });
    const finalUrl = r.url || o.url;
    const rot = r.status === 404 || r.status >= 500 ||
                (finalUrl !== o.url && REDIR_SEARCH.test(finalUrl.replace(new URL(o.url).origin,'')));
    const out = { ...o, dead: rot, rot_status: `${r.status}${finalUrl!==o.url?` ->${finalUrl.slice(0,60)}`:''}` };
    if (!rot && !out.deadline) {   // seed solo se viva e senza scadenza gia' nota
      try { const dl = extractDeadline(await r.text()); if (dl) { out.deadline=dl.deadline; out.deadline_quote=dl.deadline_quote; } }
      catch {}
    }
    return out;
  } catch (e) {
    return { ...o, dead:true, rot_status: `errore: ${e.name||e.message}` };
  }
}

console.log(`\nNuovi program: ${found.length}`);
if (DRY){
  found.slice(0,20).forEach(f => console.log(`  ${f.company} | ${f.program} | ${f.url}`));
} else {
  const merged = existing.concat(found);
  process.stdout.write('Link-rot check');
  const checked = [];
  for (const o of merged){ checked.push(await checkRot(o)); process.stdout.write('.'); }
  const deadN = checked.filter(o => o.dead).length;
  console.log(`\n${deadN} link morti/scaduti marcati (dead:true):`);
  checked.filter(o => o.dead).forEach(o => console.log(`  ⚰ ${o.company} | ${o.program} | ${o.rot_status||''}`));
  const seeded = checked.filter(o => o.deadline);
  console.log(`\n${seeded.length} scadenze seminate dalla pagina (citate):`);
  seeded.forEach(o => console.log(`  ⏳ ${o.company} | ${o.deadline} | "${(o.deadline_quote||'').slice(0,60)}"`));
  writeFileSync(OUT, JSON.stringify(checked, null, 2));
  console.log(`\nScritto data/grad_watch.json (${checked.length} totali). Ora: python3.11 build-job-dashboard.py`);
}
