## Hermes Agent — uruchomienie przez Docker Compose

Obczajcie `hermes/docker-compose.yaml`.

### Wymagania

- Docker
- Docker Compose
- wolne porty:
  - `8642` — Hermes Gateway
  - `9119` — Hermes Dashboard
- katalog na trwałe dane Hermesa: `~/.hermes`

### 1. Przygotuj katalog danych Hermesa

Hermes zapisuje tam konfigurację, sesje, skille, crony i pozostałe dane.

Katalog z hosta:

`~/.hermes`

jest montowany w kontenerze jako:

`/opt/data`

### 2. Przygotuj plik `~/.hermes/.env`

Dodaj dane logowania do dashboardu:

```env
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=YOUR_USERNAME
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=YOUR_PASSWORD
HERMES_DASHBOARD_BASIC_AUTH_SECRET=YOUR_SECRET
```

`YOUR_SECRET` powinien być długim, losowym sekretem.

### 3. Sprawdź porty

Docker Compose wystawia:

- `8642:8642` — Gateway
- `9119:9119` — Dashboard

Jeśli któryś port jest już zajęty, zmień port po stronie hosta w `docker-compose.yaml`.

Przykład:

```yaml
ports:
  - "8643:8642"
  - "9119:9119"
```

Wtedy Gateway będzie dostępny na porcie `8643`, ale wewnątrz kontenera nadal działa na `8642`.

### 4. Uruchom Docker Compose

Będąc w katalogu z plikiem `docker-compose.yaml`, uruchom:

```bash
docker compose up -d
```

Docker pobierze obraz Hermesa i uruchomi kontener w tle.

### 5. Sprawdź, czy Hermes działa

```bash
docker compose ps
```

Jeśli potrzebujesz logów:

```bash
docker logs -f hermes
```

### 6. Otwórz dashboard

Jeśli Docker działa lokalnie:

`http://localhost:9119`

Jeśli Docker działa na innym komputerze lub VPS-ie:

`http://IP_SERWERA:9119`

Zaloguj się danymi ustawionymi wcześniej w `~/.hermes/.env`.

### 7. Skonfiguruj model

Po uruchomieniu dashboardu podłącz wybranego providera modelu, np. DeepSeek, OpenAI albo inny obsługiwany backend.

Klucze API i pozostałe dane dostępowe konfiguruj zgodnie z używanym providerem.

### Przydatne komendy

Zatrzymanie:

```bash
docker compose down
```

Ponowne uruchomienie:

```bash
docker compose up -d
```

Aktualizacja obrazu:

```bash
docker compose pull
docker compose up -d
```

### Efekt

Po poprawnym uruchomieniu masz:

`Docker → Hermes Gateway → Hermes Dashboard → przeglądarka na porcie 9119`

Dane Hermesa pozostają zapisane w `~/.hermes`, nawet po ponownym utworzeniu kontenera.