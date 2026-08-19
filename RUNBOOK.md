# RUNBOOK — come usarla ogni giorno

L'idea: **la macchina scopre e ordina; tu decidi.** Niente parte da solo, niente si candida al posto tuo.

## Il loop settimanale (≈10 minuti)

```bash
cd job-pipeline
node grad-watch.mjs            # aggiorna i graduate program + marca i link morti/scaduti
python3 build-dashboard.py     # rigenera la board
open dashboard.html            # aprila e lavorala   (Windows: start … / Linux: xdg-open …)
```

(Se usi anche uno scanner ATS per riempire `data/pipeline.md` — vedi README → Discovery — lancialo
prima di `build-dashboard.py`.)

## Cosa fai tu nella board (i gesti)

| Tab | Cos'è | La tua mossa |
|---|---|---|
| **To review** | scoperte, non ancora valutate | decidi se ti interessano |
| **Da decidere** ← *parti da qui* | valutate + grad + manuali | apri il link, poi **Avanti →** (ti candidi) o Skip |
| **Applied / Interview / Offer** | ciò che hai mandato | avanzi mano a mano che rispondono |
| badge **N gg / SCADUTO / LINK MORTO** | urgenza | fai prima i "N gg"; ignora gli scaduti |

- **+ Aggiungi** = una candidatura fatta a mano (metti anche la scadenza, se la conosci).
- **Export** = scarica un file `.md` con tutte le candidature e il loro stato.
- Gli spostamenti di stato restano salvati nel **browser** (localStorage) e sopravvivono al rebuild.

## Cadenza consigliata

| Quando | Cosa |
|---|---|
| 1×/settimana | il loop qui sopra |
| ad ogni apertura | guarda i badge scadenza, manda le cose in "N gg" |
| ogni 2-3 settimane | aggiungi qualche azienda nuova a `data/grad_sources.json` |

## Problemi comuni (30 secondi)
- **grad-watch dà 0 su un'azienda** → il loro sito carica i link via JavaScript e il crawler non li
  vede. Resta come voce da controllare a mano; apri il sito tu.
- **la board non cambia** → hai rilanciato `python3 build-dashboard.py` dopo le modifiche?
- **vuoi ripartire da zero** → svuota le chiavi `jobpipe_v1` / `jobpipe_manual_v1` nel localStorage del browser.
