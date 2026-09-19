# Hermes Agent — uruchomienie przez Docker Compose

Obczajcie `hermes/docker-compose.yaml`.

## Wymagania

- Docker
- Docker Compose
- wolne porty:
  - `8642` — Hermes Gateway
  - `9119` — Hermes Dashboard
- katalog na trwałe dane Hermesa: `~/.hermes`

## 1. Przygotuj katalog danych Hermesa

Hermes zapisuje tam konfigurację, sesje, skille, crony i pozostałe dane.

Katalog z hosta:

`~/.hermes`

jest montowany w kontenerze jako:

`/opt/data`

## 2. Przygotuj plik `~/.hermes/.env`

Dodaj dane logowania do dashboardu:

```env
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=YOUR_USERNAME
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=YOUR_PASSWORD
HERMES_DASHBOARD_BASIC_AUTH_SECRET=YOUR_SECRET
```

`YOUR_SECRET` powinien być długim, losowym sekretem.

Możesz wygenerować go np.:

```bash
openssl rand -base64 32
```

Warto również ograniczyć dostęp do pliku:

```bash
chmod 600 ~/.hermes/.env
```

## 3. Porty

Domyślna konfiguracja publikuje porty wyłącznie na `127.0.0.1`:

- `127.0.0.1:8642:8642` — Gateway
- `127.0.0.1:9119:9119` — Dashboard

Dzięki temu Gateway i Dashboard nie są bezpośrednio wystawione na wszystkie interfejsy sieciowe hosta.

Jeśli któryś port jest już zajęty, możesz zmienić port po stronie hosta.

Przykład:

```yaml
ports:
  - "127.0.0.1:8643:8642"
  - "127.0.0.1:9119:9119"
```

Wtedy Gateway jest dostępny na hoście pod portem `8643`, ale wewnątrz kontenera nadal działa na `8642`.

## 4. Ustaw UID i GID użytkownika

Kontener zapisuje dane do `~/.hermes`.

Żeby pliki utworzone przez Hermesa pozostawały edytowalne przez użytkownika hosta, przed uruchomieniem Compose ustaw:

```bash
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"
```

`docker-compose.yaml` przekazuje te wartości do kontenera jako `HERMES_UID` i `HERMES_GID`.

## 5. Uruchom Docker Compose

Będąc w katalogu z plikiem `docker-compose.yaml`, uruchom:

```bash
docker compose up -d
```

Docker pobierze obraz Hermesa i uruchomi kontener w tle.

## 6. Sprawdź, czy Hermes działa

```bash
docker compose ps
```

Jeśli potrzebujesz logów:

```bash
docker logs -f hermes
```

## 7. Otwórz dashboard

### Docker działa na tym samym komputerze

Otwórz:

`http://localhost:9119`

i zaloguj się danymi ustawionymi w `~/.hermes/.env`.

### Hermes działa na VPS-ie

Dashboard jest związany z `127.0.0.1`, więc nie otwieramy bezpośrednio:

`http://IP_SERWERA:9119`

Zamiast tego możemy utworzyć tunel SSH:

```bash
ssh -L 9119:127.0.0.1:9119 USER@IP_SERWERA
```

Następnie na swoim komputerze otwieramy:

`http://localhost:9119`

Ruch trafia przez SSH do dashboardu działającego na VPS-ie.

Alternatywnie można użyć VPN-a, np. Tailscale, albo poprawnie skonfigurowanego reverse proxy z HTTPS i uwierzytelnieniem.

## 8. Skonfiguruj model

Po uruchomieniu dashboardu podłącz wybranego providera modelu, np. DeepSeek, OpenAI albo inny obsługiwany backend.

Klucze API i pozostałe dane dostępowe konfiguruj zgodnie z używanym providerem.

## Przydatne komendy

Zatrzymanie:

```bash
docker compose down
```

Ponowne uruchomienie:

```bash
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"
docker compose up -d
```

Aktualizacja obrazu:

```bash
docker compose pull
docker compose up -d
```

Podgląd logów:

```bash
docker logs -f hermes
```

## Efekt

Po poprawnym uruchomieniu:

`Docker → Hermes Gateway → Hermes Dashboard → localhost:9119`

Na VPS-ie:

`Laptop → tunel SSH/VPN → VPS → Hermes Dashboard`

Dane Hermesa pozostają zapisane w `~/.hermes`, nawet po ponownym utworzeniu kontenera.