#!/usr/bin/env node
// push-board.mjs — manda la board generata in locale alla tua app installata (via cloud).
//
// A cosa serve: quando Claude Code / Codex (o tu) generate la board in locale
// (`python3 build-dashboard.py` -> data/board.json), questo comando la carica sul
// backend sotto il TUO codice. L'app installata (stesso codice), su PC e telefono,
// la scarica e la mostra. Il codice fa da "account".
//
// Setup una volta sola: crea data/config.json con
//   { "code": "JP-XXXX-XXXX", "api": "https://job-pipeline-api.<tuo>.workers.dev" }
// (e' gitignored, resta locale). Poi:  node push-board.mjs
//
// Fonde con quello che c'e' gia' sul cloud: non cancella i job aggiunti dall'app
// ne' gli stati che hai spostato; aggiorna/aggiunge quelli generati in locale.

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { randomUUID } from 'node:crypto';

const CFG = 'data/config.json', BOARD = 'data/board.json';
if (!existsSync(CFG)) { console.error(`Manca ${CFG}. Crealo con { "code": "...", "api": "https://...workers.dev" }`); process.exit(1); }
if (!existsSync(BOARD)) { console.error(`Manca ${BOARD}. Prima genera la board:  python3 build-dashboard.py`); process.exit(1); }

const cfg = JSON.parse(readFileSync(CFG, 'utf8'));
if (!cfg.code || !cfg.api) { console.error('config.json deve avere "code" e "api".'); process.exit(1); }
if (!cfg.device) { cfg.device = 'cli-' + randomUUID(); writeFileSync(CFG, JSON.stringify(cfg, null, 2)); }
const api = cfg.api.replace(/\/$/, '');
const local = JSON.parse(readFileSync(BOARD, 'utf8')); // array di offerte

async function post(path, body) {
  const r = await fetch(api + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return { status: r.status, json: await r.json().catch(() => ({})) };
}

// 1. autenticazione: claim del codice -> token
const cl = await post('/claim', { code: cfg.code, device: cfg.device });
if (!cl.json.ok) { console.error(`Codice rifiutato: ${cl.json.error || cl.status}`); process.exit(1); }
const token = cl.json.token;
const auth = { code: cfg.code, device: cfg.device, token };

// 2. leggi la board cloud esistente e fondi (senza perdere aggiunte/stati da app)
const cur = await post('/board/get', auth);
let cloud = { manual: [], over: {} };
try { if (cur.json.data) cloud = JSON.parse(cur.json.data); } catch {}
const localUrls = new Set(local.map(o => o.url));
const kept = (cloud.manual || []).filter(o => !localUrls.has(o.url)); // aggiunte-solo-app che il locale non conosce
const merged = { manual: [...local, ...kept], over: cloud.over || {}, updated_at: Date.now() };

// 3. carica
const put = await post('/board/put', { ...auth, data: JSON.stringify(merged) });
if (put.json.ok) console.log(`OK: caricate ${local.length} offerte (+${kept.length} tenute dall'app). Apri l'app: si sincronizza.`);
else console.error(`Errore nel salvataggio: ${put.json.error || put.status}`);
