// Job Pipeline API — Cloudflare Worker + D1.
// Fa due cose: valida i codici d'accesso (claim-once) e conta le aperture.
// NON vede i dati-lavoro degli utenti (restano nel loro browser). Nessun IP salvato.
//
// Secrets attesi (via `wrangler secret put`):
//   TOKEN_SECRET  -> firma i token di sblocco
//   ADMIN_KEY     -> protegge /stats
// Binding D1: DB (vedi wrangler.toml)

const ORIGINS = [
  'https://javas-cri-pt.github.io', // GitHub Pages (produzione)
  'http://localhost:8000', 'http://127.0.0.1:8000', // test locale
];
function cors(origin) {
  const allow = ORIGINS.includes(origin) ? origin : ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}
const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json', ...cors(origin) } });

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/[+/=]/g, m => ({ '+': '-', '/': '_', '=': '' }[m]));
}
const token = (secret, code, device) => hmac(secret, `${code}.${device}`).then(s => `${code}.${s}`);

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const origin = req.headers.get('Origin') || '';
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(origin) });

    // --- root: messaggio di salute (e' un'API, non una pagina) ---
    if (url.pathname === '/' && req.method === 'GET')
      return json({ ok: true, service: 'Job Pipeline API', hint: 'API attiva. Usa /claim, /ping, /stats.' }, 200, origin);

    // --- claim: valida un codice (claim-once) e restituisce un token di sblocco ---
    if (url.pathname === '/claim' && req.method === 'POST') {
      const { code, device } = await req.json().catch(() => ({}));
      if (!code || !device) return json({ ok: false, error: 'dati mancanti' }, 400, origin);
      const row = await env.DB.prepare('SELECT * FROM codes WHERE code = ?').bind(code).first();
      if (!row || !row.active) return json({ ok: false, error: 'codice non valido' }, 403, origin);
      // Stesso codice su piu' dispositivi TUOI (PC, telefono...), con un tetto anti-condivisione.
      const CAP = 5;
      const agg = await env.DB.prepare(
        'SELECT COUNT(DISTINCT device_id) n, SUM(CASE WHEN device_id = ? THEN 1 ELSE 0 END) mine FROM opens WHERE code = ?'
      ).bind(device, code).first();
      const known = agg && agg.mine > 0;
      const nDev = (agg && agg.n) || 0;
      if (!known && nDev >= CAP)
        return json({ ok: false, error: 'codice gia\' attivo sul numero massimo di dispositivi' }, 403, origin);
      if (!row.claimed_at)
        await env.DB.prepare('UPDATE codes SET claimed_at = datetime(\'now\'), device_id = ? WHERE code = ?').bind(device, code).run();
      await env.DB.prepare('INSERT INTO opens (code, device_id) VALUES (?, ?)').bind(code, device).run();
      return json({ ok: true, token: await token(env.TOKEN_SECRET, code, device) }, 200, origin);
    }

    // --- ping: registra un'apertura (conteggio). Fire-and-forget dal client. ---
    if (url.pathname === '/ping' && req.method === 'POST') {
      const { code, device } = await req.json().catch(() => ({}));
      if (code && device) await env.DB.prepare('INSERT INTO opens (code, device_id) VALUES (?, ?)').bind(code, device).run();
      return json({ ok: true }, 200, origin);
    }

    // --- stats: cruscotto per te (protetto da ADMIN_KEY) ---
    if (url.pathname === '/stats' && req.method === 'GET') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) return json({ ok: false }, 403, origin);
      const codes = await env.DB.prepare('SELECT COUNT(*) n, SUM(claimed_at IS NOT NULL) claimed FROM codes').first();
      const o7 = await env.DB.prepare("SELECT COUNT(*) n, COUNT(DISTINCT device_id) u FROM opens WHERE ts > datetime('now','-7 days')").first();
      const oall = await env.DB.prepare('SELECT COUNT(*) n, COUNT(DISTINCT device_id) u FROM opens').first();
      const per = await env.DB.prepare(
        "SELECT c.code, c.label, c.claimed_at, COUNT(o.id) opens, MAX(o.ts) last_open " +
        "FROM codes c LEFT JOIN opens o ON o.code = c.code GROUP BY c.code ORDER BY opens DESC").all();
      return json({ ok: true,
        codici: codes.n, reclamati: codes.claimed || 0,
        aperture_7g: o7.n, utenti_attivi_7g: o7.u,
        aperture_totali: oall.n, utenti_totali: oall.u,
        per_codice: per.results }, 200, origin);
    }

    return json({ ok: false, error: 'not found' }, 404, origin);
  },
};
