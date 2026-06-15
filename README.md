# MAC AI Assistant

Piattaforma Windows integrata: EasyOne CRM, magazzino, catalogo, PDF, AI e WhatsApp.

**Stack:** Python · FastAPI · PostgreSQL · Qdrant · OpenAI · PySide6

## Avvio rapido

```powershell
cd Projects/tech-distributor-assistant
copy .env.example .env
docker compose up -d
pip install -r requirements.txt
python scripts/init_db.py
python scripts/import_products.py --generate-sample data/samples/prodotti_esempio.xlsx
python scripts/import_products.py data/samples/prodotti_esempio.xlsx
python scripts/seed_compatibility.py
python scripts/import_orders.py --generate-sample data/samples/ordini_esempio.xlsx
python scripts/import_orders.py data/samples/ordini_esempio.xlsx
python scripts/run_hub.py
```

### Client desktop PySide6 (MVP)

```powershell
pip install -r desktop/requirements.txt
python scripts/run_desktop.py
```

Apri `http://localhost:8000` per la UI web legacy e `http://localhost:8000/docs` per l'API.

Documentazione architettura: `docs/MAC_AI_ENTERPRISE_ARCHITECTURE.md`

## Autenticazione EasyOne (Fase 1)

Nessun utente locale: login tramite credenziali EasyOne (o utenti dev in sviluppo).

| Variabile | Default | Descrizione |
|---|---|---|
| `AUTH_REQUIRED` | `false` | Se `true`, tutte le API AI richiedono JWT |
| `EASYONE_AUTH_MODE` | `dev` | `dev` = mock locale, `http` = API EasyOne |
| `EASYONE_MODE` | `local` | `local` = PostgreSQL, `http` = API + fallback |

**Dev login:** `admin` / `admin` (se `DEV_AUTH_USERS` è vuoto).

### Endpoint auth

| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | `/api/auth/login` | Login EasyOne → JWT |
| POST | `/api/auth/refresh` | Rinnova access token |
| POST | `/api/auth/logout` | Invalida sessione |
| GET | `/api/auth/me` | Profilo e permessi sessione |

Per abilitare auth in produzione: `AUTH_REQUIRED=true` e configurare `EASYONE_BASE_URL`.

## MVP 2 — EasyOne live + Setup.exe

### Test integrazione con Mock API EasyOne

```powershell
# Terminal 1 — Mock EasyOne/ERP
python scripts/easyone_mock_api.py

# Terminal 2 — Hub (configurare .env)
# EASYONE_MODE=hybrid
# EASYONE_AUTH_MODE=http
# EASYONE_BASE_URL=http://127.0.0.1:8090
# AUTH_REQUIRED=true
python scripts/run_hub.py

# Terminal 3 — Desktop
python scripts/run_desktop.py
```

Mapping API: `docs/easyone-api-mapping.md`

### Build Setup.exe Windows (distribuzione professionale)

```powershell
pip install -r desktop/requirements.txt
python scripts/build_release.py --clean
```

**Output finale:** `dist/installer/MAC_AI_Assistant_Setup.exe`

Guida completa: [docs/WINDOWS_DEPLOYMENT.md](docs/WINDOWS_DEPLOYMENT.md)

Config post-install: `%APPDATA%\MAC AI Assistant\config.ini`

## Database prodotti

Schema SQL: `database/schema.sql`

Colonne Excel supportate:

| Colonna Excel | Campo database |
|---|---|
| codice_interno | codice interno |
| produttore | produttore |
| descrizione | descrizione |
| categoria | categoria |
| disponibilita | disponibilità |
| prezzo | prezzo |
| link_manuale | link manuale |
| link_scheda_tecnica | link scheda tecnica |

## Endpoint prodotti

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/api/products` | Elenco prodotti con filtri |
| GET | `/api/products/search?q=...` | Ricerca full-text |
| GET | `/api/products/{codice}` | Dettaglio per codice interno |
| POST | `/api/products` | Crea prodotto |
| PUT | `/api/products/{codice}` | Aggiorna prodotto |
| POST | `/api/products/import` | Import Excel (.xlsx) |
| POST | `/api/products/{codice}/compatibility` | Aggiunge collegamento compatibilità |

### Ricerca con compatibilità

`GET /api/products/search?q=router`

Restituisce per ogni prodotto trovato:
- dati prodotto
- **accessories** (accessori compatibili)
- **alternatives** (alternative)
- **spare_parts** (ricambi)
- **complementary** (complementari)

`GET /api/products/{codice}` ha la stessa struttura nel dettaglio singolo.

Tipi compatibilità: `accessory`, `alternative`, `spare_part`, `complementary`

## Raccomandazioni (storico ordini)

Schema: `orders`, `order_lines`, `product_order_stats`, `product_cooccurrence`

Formula correlazione: `(ordini con A e B) / (ordini con A) × 100`

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | `/api/recommendations/{codice}` | Prodotti acquistati insieme + frequenza |
| POST | `/api/recommendations/import` | Import Excel storico ordini |
| POST | `/api/recommendations/recompute` | Ricalcolo correlazioni |

ETL da riga di comando:

```powershell
python scripts/import_orders.py data/samples/ordini_esempio.xlsx
python scripts/import_orders.py --recompute-only
```

Colonne Excel ordini: `numero_ordine`, `data_ordine`, `codice_cliente`, `codice_interno`, `quantita`, `prezzo_unitario`

## Assistente commerciale (chat)

`POST /api/chat/ask`

Per ogni domanda il sistema:
1. Cerca nel **catalogo** prodotti
2. Cerca nei **PDF** indicizzati
3. Verifica **disponibilità** a magazzino
4. Recupera **compatibilità** (accessori, alternative, ricambi, complementari)
5. Analizza **prodotti acquistati insieme** dallo storico ordini

Risposta strutturata con: articolo, disponibilità, descrizione, documentazione, compatibilità, suggerimenti commerciali.
