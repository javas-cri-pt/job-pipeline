# Job Pipeline

Una piccola **board per cercare lavoro**, che gira **sul tuo computer** — niente account, niente
cloud, i tuoi dati non escono da casa tua. Fa tre cose:

1. **Traccia le candidature** in una tabella a stati (Da valutare → Da decidere → Candidato →
   Colloquio → Offerta), con un punteggio di **fit** e la **scadenza** di ognuna.
2. **Sorveglia i graduate program** delle aziende che ti interessano e ti dice quali link sono
   **morti/scaduti**, così non perdi tempo su bandi chiusi.
3. Ti dà una **pagina HTML** ordinata e cercabile che apri con doppio click.

Non serve sapere niente di AI per usarla.

---

## Il modo più facile: installala come app (nessun terminale)

1. Apri il link della board in **Chrome** (o Edge): **https://javas-cri-pt.github.io/job-pipeline/**
2. Nella barra degli indirizzi clicca l'icona **Installa** (⊕ / «Installa Job Pipeline»).
3. Ora hai un'**app sul desktop**. Se la versione online è protetta, inserisci il **codice d'accesso**
   che hai ricevuto (una volta sola). Poi premi **+ Aggiungi** e inserisci i tuoi lavori: azienda,
   ruolo, link, scadenza. I tuoi lavori restano salvati **sul tuo computer** (nel browser).

Funziona anche offline. Questa versione è la board "vuota" da riempire a mano — perfetta per iniziare.
Chi vuole anche la ricerca automatica dei graduate program usa gli script qui sotto.

---

## Cosa ti serve (una volta sola)

- **Python 3** — su Mac è già installato (`python3 --version` per controllare).
- **Node.js** (versione 18+) — da [nodejs.org](https://nodejs.org). Serve solo per il grad-watch.

```bash
# scarica il progetto e entra nella cartella
cd job-pipeline
npm install            # installa il browser che il grad-watch usa (Playwright)
```

---

## Avvio rapido (2 minuti)

```bash
# 1. parti dagli esempi (copiali togliendo ".example")
cp data/pipeline.example.md   data/pipeline.md
cp data/evaluations.example.json data/evaluations.json
cp data/grad_sources.example.json data/grad_sources.json

# 2. genera la board e aprila
python3 build-dashboard.py
open dashboard.html        # su Windows: start dashboard.html ; su Linux: xdg-open
```

Vedi già una board funzionante con dati d'esempio. Ora la rendi tua.

---

## Renderla tua

- **Le tue candidature** → apri `data/evaluations.json` e sostituisci gli esempi con i tuoi lavori.
  Ogni voce ha: azienda, titolo, `fit` (0-5, quanto ti calza), `state`, e se vuoi una `deadline`.
  Oppure, ancora più semplice: nella board clicca **+ Aggiungi** e inseriscili a mano.
- **I graduate program da sorvegliare** → apri `data/grad_sources.json` e metti le aziende che ti
  piacciono (nome + URL della loro pagina "careers/graduate"). Poi:
  ```bash
  node grad-watch.mjs           # cerca i program e marca i link morti
  python3 build-dashboard.py    # rigenera la board
  ```

### Le scadenze (regola importante)
La board mostra un badge **«N gg»** (mancano N giorni), **SCADUTO**, o **LINK MORTO**.
Scrivi una `deadline` **solo se l'hai vista davvero sul sito** — e incolla la frase-fonte in
`deadline_quote`. Meglio nessuna data che una inventata: una scadenza sbagliata ti fa perdere un bando.

---

## Come si usa ogni giorno

Vedi **[RUNBOOK.md](RUNBOOK.md)** — cosa lanciare, ogni quanto, e cosa decidere tu.
In breve: una volta a settimana lanci `grad-watch` + `build-dashboard`, apri la board, e nella tab
**"Da decidere"** premi **Avanti →** sulle cose che ti convincono. Gli spostamenti restano salvati
nel browser anche quando rigeneri la pagina.

---

## Discovery automatica (avanzato, opzionale)

Questo progetto traccia e sorveglia; **non** scandaglia da solo tutti i portali di lavoro.
Se vuoi che le offerte arrivino da sole dagli ATS (Greenhouse, Ashby, …), il file
`data/pipeline.md` può essere generato da uno scanner. Un ottimo motore open-source per quella parte
è **[career-ops](https://github.com/santifer/career-ops)** (MIT): il suo `scan.mjs` produce proprio
quel formato di righe. Questo tool nasce come layer leggero e condivisibile sopra quel tipo di flusso.

---

## Codici d'accesso (versione online)

La versione ospitata può essere protetta da **codici d'accesso**: apri l'app, inserisci il codice che
hai ricevuto, e resti dentro (funziona anche offline dopo il primo ingresso — *claim-once*). Serve a
capire quante persone la usano, in vista di migliorarla. Chi **clona il repo** e gira in locale non ha
nessun gate: l'app è libera finché non imposti un backend (vedi [backend/](backend/)).

## Privacy

- **I tuoi lavori restano sul tuo dispositivo** (nel browser, `localStorage`): non finiscono su nessun
  server. Se pubblichi la tua copia su GitHub, i file dati (`data/*.json`, `data/pipeline.md`,
  `dashboard.html`) sono **gitignored** — solo i `*.example.*` fanno parte del repo.
- Se usi la versione **con codice d'accesso**, l'app invia al backend **solo** il tuo codice e un
  identificativo casuale del dispositivo, per contare le aperture. **Nessun IP, nessun dato di
  navigazione, nessun contenuto delle tue candidature.**
- Nota EU/GDPR: anche codice + orario sono dato personale. Il backend non raccoglie altro; i codici
  possono essere disattivati e i conteggi cancellati su richiesta.

## Licenza
MIT — vedi [LICENSE](LICENSE). Ispirato al flusso di [career-ops](https://github.com/santifer/career-ops) (MIT).
