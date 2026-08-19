# Backend — codici d'accesso + conteggio (Cloudflare Worker + D1)

Un piccolo backend che fa **due** cose: valida i codici d'accesso (claim-once) e conta le aperture.
Non vede mai i dati-lavoro degli utenti. Nessun IP salvato. Free-tier Cloudflare più che sufficiente.

Serve un **account Cloudflare** (gratis). Tutti i comandi girano con `npx` — niente da installare.

## Deploy in 7 passi

```bash
cd backend

# 1. login Cloudflare (apre il browser)
npx wrangler login

# 2. crea il database D1
npx wrangler d1 create job-pipeline
#    -> copia il "database_id" che stampa e incollalo in wrangler.toml

# 3. crea le tabelle (sul DB remoto)
npx wrangler d1 execute job-pipeline --remote --file schema.sql

# 4. imposta i due segreti (te li chiede a schermo, non finiscono nel repo)
npx wrangler secret put TOKEN_SECRET     # una frase lunga a caso
npx wrangler secret put ADMIN_KEY        # la password per vedere /stats

# 5. pubblica il Worker
npx wrangler deploy
#    -> ti stampa l'URL, es. https://job-pipeline-api.<tuo-account>.workers.dev

# 6. attiva il gate sul sito: metti quell'URL in ../config.js
#    window.JOBPIPE_API = "https://job-pipeline-api.<tuo-account>.workers.dev";
#    poi commit + push: Pages si aggiorna e la versione online chiede il codice.

# 7. conia i primi codici e inseriscili
node mint-codes.mjs 10 "amici beta"
#    -> ti dà 10 codici e il comando `wrangler d1 execute ...` da lanciare
```

## Uso quotidiano

**Dare accesso a qualcuno** → genera un codice e daglielo:
```bash
node mint-codes.mjs 1 "Marco"      # poi lancia il comando che stampa
```

**Vedere quante persone la usano** → apri nel browser (o `curl`):
```
https://<tuo-worker>.workers.dev/stats?key=LA-TUA-ADMIN_KEY
```
Ti dà: codici totali, quanti reclamati, aperture (7 giorni e totali), utenti attivi, e il dettaglio
per codice (chi apre di più, ultima apertura).

**Disattivare un codice** (blocca nuovi ingressi con quel codice):
```bash
npx wrangler d1 execute job-pipeline --remote --command "UPDATE codes SET active=0 WHERE code='JP-XXXX-XXXX'"
```

## Il codice = account (multi-dispositivo + sync)
Un codice vale su **più dispositivi dello stesso utente** (PC, telefono…), fino a **5**. Al primo
ingresso su un dispositivo l'app riceve un token e da lì funziona anche **offline**. La **board** (i
job, gli stati, le scadenze) è salvata sul backend legata al codice e **sincronizzata** su tutti i
dispositivi con quello stesso codice (last-write-wins). Oltre il 5° dispositivo, il codice viene
rifiutato (freno anti-condivisione).

## Ponte CLI → app
Chi genera la board in locale (con Claude Code/Codex → `python3 build-dashboard.py`) la manda alla
propria app con **`node push-board.mjs`** (vedi README principale): il comando si autentica col codice,
fonde con la board cloud esistente (senza cancellare le aggiunte fatte da app) e la ricarica.

## Endpoint (per riferimento)
| Metodo | Path | Cosa fa |
|---|---|---|
| POST | `/claim` | `{code, device}` → valida (max 5 device/codice), registra apertura, torna un token |
| POST | `/ping` | `{code, device}` → registra un'apertura (conteggio) |
| POST | `/board/get` | `{code, device, token}` → scarica la board sincronizzata del codice |
| POST | `/board/put` | `{code, device, token, data}` → salva la board (last-write-wins) |
| GET | `/stats?key=…` | cruscotto (protetto da `ADMIN_KEY`) |

## Privacy / sicurezza (onesto)
La board è **salvata sul backend** legata al codice, per sincronizzarla tra i tuoi dispositivi: è
privata (accesso solo col codice), nessun IP. Il codice senza password è l'unica chiave: chi lo ha,
entra — quindi distribuiscili con criterio e disattiva quelli compromessi (`active=0`). Per un vero
paywall (quando commercializzerai) l'app andrà servita **dal Worker** e non da Pages.
