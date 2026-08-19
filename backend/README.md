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

## Come funziona il "claim-once"
Al primo ingresso il codice viene legato a quel dispositivo e l'app riceve un token; da lì funziona
anche **offline**. Lo stesso codice su un **altro** dispositivo viene rifiutato. È il compromesso che
tiene l'app installabile/offline (un codice revocabile-sempre richiederebbe il server ad ogni apertura).

## Endpoint (per riferimento)
| Metodo | Path | Cosa fa |
|---|---|---|
| POST | `/claim` | `{code, device}` → valida (claim-once), registra apertura, torna un token |
| POST | `/ping` | `{code, device}` → registra un'apertura (conteggio) |
| GET | `/stats?key=…` | cruscotto (protetto da `ADMIN_KEY`) |

## Sicurezza (onesto)
Il gate scoraggia l'uso casuale senza codice. Non è invalicabile: chi clona il repo pubblico può
togliere il gate e girare in locale. Per un vero paywall (quando commercializzerai) l'app andrà servita
**dal Worker** e non da Pages — ma per contare gli utenti e dare accessi mirati, questo basta e avanza.
