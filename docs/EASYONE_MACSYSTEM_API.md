# EasyOne CRM — MAC SYSTEM

Documento di riferimento per integrazioni MAC AI Assistant.  
Allineato a Bot Ticket MAC SYSTEM (`easyone_client.py`).

**Istanza:** https://e.macsystem.online

## URL di base

| Servizio | URL |
|---|---|
| Portale web CRM | `https://e.macsystem.online` |
| API CRM (anagrafica, ticket) | `https://e.macsystem.online/_api/easyone.crmapi/api` |
| API Eventi (ticket assistenza) | `https://e.macsystem.online/_api/events/api` |

## Variabili ambiente (Hub `.env`)

| Variabile | Descrizione |
|---|---|
| `EASYONE_API_URL` / `EASYONE_BASE_URL` | Base API CRM |
| `EASYONE_EVENTS_URL` / `EASYONE_EVENTS_BASE_URL` | Base API Eventi |
| `EASYONE_CRM_URL` / `EASYONE_PORTAL_URL` | Portale web |
| `EASYONE_TENANT_ID` | GUID tenant organizzazione |
| `EASYONE_NEUTRAL_CUSTOMER_ID` | GUID anagrafica cliente generico |

## Autenticazione

Header su tutte le chiamate API (dopo login):

```
Authorization: Bearer <token>
Accept: application/json
Content-Language: it
```

### Login

`POST {EASYONE_API_URL}/authentication/Login`

```json
{
  "username": "utente_easyone",
  "password": "password",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "loginType": 0
}
```

Risposta: token Bearer (spesso stringa JSON tra virgolette). Validità ~23 ore.

## Anagrafica clienti (People)

`GET {EASYONE_API_URL}/people?take=100&skip=0&searchValue=ROSSI`

Campi utili: `id` (GUID), `description` (ragione sociale), `code` (es. C005008).

## Ticket assistenza

Creazione: `POST {EASYONE_EVENTS_URL}/Event`  
Dettaglio: `GET {EASYONE_API_URL}/tickets/{event_GUID}`  
Info base: `GET {EASYONE_EVENTS_URL}/event/GetEventBasicInfo/{app_ID}`

## Errori frequenti

| Problema | Soluzione |
|---|---|
| 401 / token scaduto | Ripetere `authentication/Login` |
| Cliente non trovato | Cercare con `searchValue` su `/people` |
| Ticket non creato | `customer.id` deve essere GUID da `people.id`, non Tenant ID |

## Sicurezza

- Non inserire credenziali nel codice sorgente.
- Ogni operatore usa il proprio account EasyOne.
- Password solo in `.env` locale o vault aziendale.
