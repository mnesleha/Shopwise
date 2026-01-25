# Locust Testing Guide - Odpovědi na časté otázky

## 1. Payment Payload

**Správný formát:**
```json
{
  "order_id": 123,
  "result": "success"  // nebo "fail"
}
```

**POZOR:**
- ❌ `"payment_method"` - NENÍ součástí payloadu
- ❌ `"result": "failure"` - ŠPATNĚ, má být `"fail"`
- ✅ `"result": "success"` nebo `"result": "fail"` - SPRÁVNĚ

## 2. Product Search

Všechny testy obsahují search varianty:

```python
# Základní search
GET /api/v1/products/?search=MOUSE

# V testech:
- locustfile.py -> ShopwiseUser.search_products()
- product_load.py -> ProductSearcher.search_products()
```

Testované search terms: `MOUSE`, `KEYBOARD`, `HEADSET`, `MONITOR`, `LAPTOP`, `CABLE`

## 3. Guest Flow

**Kompletní guest checkout flow** v `locustfile.py`:

```python
class GuestUser(HttpUser):
    """
    Testuje anonymous/guest uživatele:
    1. Browse products (bez loginu)
    2. Add to cart (backend vrátí cart token v cookie)
    3. Checkout (vytvoří guest order)
    4. Payment (s order_id)
    5. Access guest order (s guest_access_token)
    """
```

**Guest vs Authenticated flow:**
- Guest: Cookie/header `X-Cart-Token` identifikuje košík
- Authenticated: Session cookie po loginu

## 4. Auth varianty - Session vs JWT

### Session Auth (Výchozí)
```python
class ShopwiseUser(HttpUser):
    def on_start(self):
        # Login vytvoří session cookie
        self.client.post("/api/v1/auth/login/", json={...})
        # Cookie se automaticky používá pro další requesty
```

**Používá:**
- `ShopwiseUser` - session auth
- `HeavyShopperUser` - session auth
- `GuestUser` - žádný auth (anonymous)

### JWT Auth (Bearer Token)
```python
class JWTAuthUser(HttpUser):
    def on_start(self):
        # Login vrátí access_token a refresh_token
        response = self.client.post("/api/v1/auth/login/", json={...})
        tokens = response.json()
        
        # Nastav Authorization header
        self.client.headers.update({
            "Authorization": f"Bearer {tokens['access']}"
        })
```

**Testuje:**
- Bearer token authentication
- Token refresh flow (`/api/v1/auth/refresh/`)
- `/api/v1/auth/me/` endpoint s JWT

## 5. Error handling - Co když test spadne?

### Locust NESPADNE celý při chybném payloadu

**Co se stane:**
```python
# Chybný payload
response = self.client.post("/api/v1/payments/", json={
    "order": 123,  # WRONG - should be "order_id"
    "result": "failure"  # WRONG - should be "fail"
})

# Locust zaznamená:
# - Response: 400 Bad Request
# - Failure count: +1
# - Response time: např. 45ms
# - Nikdy NESPADNE celý test!
```

**Kde vidíš chyby:**

1. **Web UI** (`http://localhost:8089`):
   - Tab "Failures" - seznam všech failed requestů
   - Tab "Charts" - failure rate %
   - Tab "Exceptions" - Python exceptions (pokud nastaly)

2. **Console output:**
   ```
   [2026-01-24 10:30:15,123] INFO/locust.runners: Hatching and swarming 10 users...
   POST /api/v1/payments/: 400 Bad Request
   ```

3. **Headless mode** (`--headless`):
   ```bash
   Name                          # reqs  # fails  Avg   Min   Max
   POST /api/v1/payments/        100     100      45    30    200
   ```

**Typy selhání:**

- **HTTP Error (400, 404, 500)** - Locust to počítá jako failure
- **Connection Error** - Locust to počítá jako failure
- **Timeout** - Configurable, default 30s
- **Python Exception** - Locust zachytí a reportuje, test pokračuje

**Jak debugovat:**

```python
# Přidej debugging do testu
response = self.client.post("/api/v1/payments/", json={...})

if response.status_code != 201:
    print(f"Payment failed: {response.status_code}")
    print(f"Response: {response.text}")
```

**Best practices:**

1. **Před spuštěním performance testů:**
   - Ověř payloady v Postman nebo pytest
   - Ujisti se, že seed data existují (customer_2, products 1-100)
   
2. **První test run:**
   - Začni s 1 uživatelem
   - Zkontroluj Failures tab
   - Oprav chybné payloady
   
3. **Production-like test:**
   - Vypni Sentry (`SENTRY_ENABLED=false`)
   - Spusť s reálným počtem uživatelů (50-100)
   - Sleduj response times a failure rate

## Summary

✅ **Payment:** `{"order_id": 123, "result": "success"}`  
✅ **Search:** Testováno v `ShopwiseUser` a `ProductSearcher`  
✅ **Guest flow:** `GuestUser` class  
✅ **Auth:** Session (`ShopwiseUser`), JWT (`JWTAuthUser`), Anonymous (`GuestUser`)  
✅ **Error handling:** Locust nikdy nespadne, zobrazí failures v UI/console
