-- Schema D1 (SQLite) per Job Pipeline: codici d'accesso + conteggio aperture.
-- NB: nessun IP, nessun dato di navigazione. Solo codice + device casuale + timestamp.
-- (Anche cosi', in EU codice+timestamp e' dato personale: vedi PRIVACY nel README pubblico.)

CREATE TABLE IF NOT EXISTS codes (
  code       TEXT PRIMARY KEY,          -- es. "JP-7K2M-9QX4"
  label      TEXT,                      -- a chi l'hai dato (nota tua)
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  claimed_at TEXT,                      -- primo uso (claim-once)
  device_id  TEXT,                      -- device che l'ha reclamato per primo
  active     INTEGER NOT NULL DEFAULT 1 -- 0 = disattivato (blocca nuovi claim)
);

CREATE TABLE IF NOT EXISTS opens (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  code      TEXT NOT NULL,
  device_id TEXT,
  ts        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_opens_ts   ON opens(ts);
CREATE INDEX IF NOT EXISTS idx_opens_code ON opens(code);

-- La board sincronizzata: un blob JSON per codice (il codice funge da "username").
-- Contiene i job aggiunti + gli stati. Sincronizzata su tutti i dispositivi dello stesso codice.
CREATE TABLE IF NOT EXISTS boards (
  code       TEXT PRIMARY KEY,
  data       TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
