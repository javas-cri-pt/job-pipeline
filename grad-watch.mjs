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

// ---- Link-rot: ri-verifica gli URL gia' in grad_watch.json ------------------
// Un program puo' essere "scaduto" senza data in pagina: il segnale piu' affidabile
// e' il link morto (404) o il redirect verso una pagina di ricerca/lista.
// Marca dead:true (NON cancella, NON inventa scadenze). Salta gli aggregatori.
const REDIR_SEARCH = /(\/search|\/results|\/jobs\/?(\?|$)|\/careers\/?(\?|$)|not.?found|404)/i;
async function checkRot(o){
  if (o.domain === 'aggregatore') return { ...o, dead:false };
  try {
    const r = await fetch(o.url, { method:'GET', redirect:'follow',
      headers:{ 'User-Agent':'Mozilla/5.0 job-research' }, signal: AbortSignal.timeout(15000) });
    const finalUrl = r.url || o.url;
    const rot = r.status === 404 || r.status >= 500 ||
                (finalUrl !== o.url && REDIR_SEARCH.test(finalUrl.replace(new URL(o.url).origin,'')));
    return { ...o, dead: rot, rot_status: `${r.status}${finalUrl!==o.url?` ->${finalUrl.slice(0,60)}`:''}` };
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
  writeFileSync(OUT, JSON.stringify(checked, null, 2));
  console.log(`\nScritto data/grad_watch.json (${checked.length} totali). Ora: python3.11 build-job-dashboard.py`);
}
