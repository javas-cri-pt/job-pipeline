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

## Il codice è il tuo account (sync tra dispositivi)

La versione ospitata si apre con un **codice d'accesso**. Il codice funziona da **account**: la tua
board è **salvata sul backend** e **sincronizzata** su tutti i tuoi dispositivi (PC, telefono) che usano
lo stesso codice — fino a 5. La aggiungi da telefono, la ritrovi sul PC.

### Farla riempire dall'AI e ritrovarla nell'app
Il pezzo forte: usi **Claude Code / Codex** in locale per trovare e valutare i lavori (vedi sotto),
poi con **`node push-board.mjs`** mandi la board al tuo account cloud → l'**app installata** (stesso
codice) la scarica e la mostra ovunque.

1. Setup una volta: crea `data/config.json` → `{ "code": "JP-XXXX-XXXX", "api": "https://<tuo-worker>.workers.dev" }`
2. Genera la board: `python3 build-dashboard.py` (scrive `data/board.json`)
3. Sincronizza: `node push-board.mjs` → apri l'app, la trovi lì.

Chi **clona il repo** e non imposta un backend usa l'app **solo in locale**, senza gate e senza sync.

## Privacy

- Con il codice, la tua board (aziende, ruoli, link, stati, scadenze) è **salvata sul backend** legata
  al codice, per poterla sincronizzare tra i tuoi dispositivi. È **privata**: vi si accede solo col
  codice. **Nessun IP, nessun dato di navigazione.**
- I file locali (`data/*.json`, `dashboard.html`, `data/config.json` col tuo codice) sono **gitignored**:
  non finiscono su GitHub. Solo i `*.example.*` fanno parte del repo.
- Nota EU/GDPR: codice, orari e contenuto della board sono dati personali, trattati solo per far
  funzionare l'app. I codici si possono disattivare e i dati cancellare su richiesta.

## Licenza
MIT — vedi [LICENSE](LICENSE). Ispirato al flusso di [career-ops](https://github.com/santifer/career-ops) (MIT).
