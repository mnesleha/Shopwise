# Performance Testing s Locust

Tento adresář obsahuje zátěžové testy pro Shopwise API pomocí Locust.

## Spuštění testů

### 1. Příprava prostředí

Před spuštěním testů vypni Sentry, aby ses nevyčerpal kvótu:

**Backend** (`backend/.env.dev`):
```env
SENTRY_ENABLED=false
```

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_SENTRY_ENABLED=false
```

### 2. Spuštění backendu

```bash
sw-run-dev
```

Backend poběží na `http://localhost:8000`

### 3. Spuštění Locust

```bash
cd tests/performance
locust -f locustfile.py --host=http://localhost:8000
```

Pak otevři browser: `http://localhost:8089`

### 4. Parametry testu

V Locust UI nastav:
- **Number of users**: kolik současných uživatelů simulovat (např. 10, 50, 100)
- **Spawn rate**: kolik uživatelů přidat za sekundu (např. 5)
- **Host**: už je nastaveno na `http://localhost:8000`

### 5. Headless režim (bez UI)

Pro automatizované testy můžeš spustit Locust bez webového rozhraní:

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 10 -t 1m
```

Parametry:
- `-u 50`: 50 současných uživatelů
- `-r 10`: přidat 10 uživatelů za sekundu
- `-t 1m`: test běží 1 minutu

## Struktura testů

- `locustfile.py` - základní scénář (browse products, add to cart, checkout)
- `product_load.py` - izolovaný test produktového API
- `checkout_flow.py` - komplexní checkout flow s platbou

## Metriky

Locust měří:
- **Requests/s** - throughput
- **Response time** (min, max, avg, p50, p95, p99)
- **Failures** - procento chybných requestů
- **RPS** - requests per second per endpoint

## Databáze

Locust testy běží proti MySQL (stejně jako Postman testy).
Ujisti se, že máš v `.env.dev` správně nastavenou MySQL connection.

## CI/CD

Locust testy **NEJSOU** součástí běžného CI pipeline (jsou příliš pomalé).
Spouštějí se manuálně před major releases nebo když potřebuješ změřit performance.
