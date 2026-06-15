# EasyOne API Mapping — MAC AI Assistant

## Mac System (produzione)

Configurazione completa: **`docs/EASYONE_MACSYSTEM_API.md`** e **`.env.macsystem.example`**

```env
EASYONE_API_URL=https://e.macsystem.online/_api/easyone.crmapi/api
EASYONE_EVENTS_URL=https://e.macsystem.online/_api/events/api
EASYONE_CRM_URL=https://e.macsystem.online
EASYONE_TENANT_ID=<GUID-tenant>
EASYONE_PATH_AUTH_LOGIN=/authentication/Login
EASYONE_PATH_CUSTOMERS_SEARCH=/people
```

| Endpoint Hub | EasyOne MAC SYSTEM |
|---|---|
| Login | `POST /authentication/Login` |
| Clienti | `GET /people?take=&skip=&searchValue=` |
| Ticket | `GET /tickets/{event_GUID}` |
| Eventi | `POST {EVENTS_URL}/Event` |
| Agenda / calendario | `GET {EASYONE_API_URL}/calendar/events` (configurabile con `EASYONE_PATH_CALENDAR_EVENTS`) |

## Mock locale (sviluppo)

```powershell
python scripts/easyone_mock_api.py
```

```env
EASYONE_AUTH_MODE=dev
EASYONE_BASE_URL=
AUTH_REQUIRED=false
```

Login test mock: `admin` / `admin`

## Flusso token (desktop → Hub → EasyOne)

1. Desktop → `POST /api/auth/login` (credenziali operatore)
2. Hub → `POST /authentication/Login` su EasyOne
3. Hub salva token in `user_sessions.easyone_access_token`
4. Chiamate CRM usano `Authorization: Bearer` + `Content-Language: it`
