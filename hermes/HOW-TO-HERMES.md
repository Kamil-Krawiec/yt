# Hermes Agent — bezpieczne minimum

Konfiguracja działa dla jednego użytkownika na Linuksie. Dashboard i API są dostępne tylko lokalnie (`127.0.0.1`). Na VPS-ie użyj tunelu SSH — nie wystawiaj portów publicznie.

## 1. Przygotuj dane i sekrety

```bash
install -d -m 700 "$HOME/.hermes"
touch "$HOME/.hermes/.env"
chmod 600 "$HOME/.hermes/.env"
nano "$HOME/.hermes/.env"
```

Wpisz do `.env`:

```dotenv
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=twoj_login
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=dlugie_unikalne_haslo
HERMES_DASHBOARD_BASIC_AUTH_SECRET=LOSOWY_SEKRET_DASHBOARDU

API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_KEY=INNY_LOSOWY_KLUCZ_API
```

Zmień wszystkie przykładowe wartości. Hasło oraz oba sekrety wygeneruj osobno:

```bash
openssl rand -hex 32
```

Klucze modeli, np. `OPENAI_API_KEY`, również zapisuj tylko w `~/.hermes/.env`.

## 2. Uruchom

W katalogu `hermes`:

```bash
export HERMES_UID="$(id -u)"
export HERMES_GID="$(id -g)"

docker compose config --quiet
docker compose up -d
```

Compose przekazuje ten plik do kontenera; API jest jawnie włączone w `docker-compose.yaml`.

## 3. Sprawdź

```bash
docker compose ps
docker compose logs --tail=100 hermes
curl -fsS http://127.0.0.1:8642/health
curl -fsS http://127.0.0.1:9119/api/status
```

Dashboard: `http://127.0.0.1:9119`

W odpowiedzi dashboardu `auth_required` powinno mieć wartość `true`.

## 4. Dostęp do VPS-a

Na swoim komputerze:

```bash
ssh -N \
  -L 9119:127.0.0.1:9119 \
  -L 8642:127.0.0.1:8642 \
  USER@ADRES_VPS
```

Potem otwórz lokalnie `http://127.0.0.1:9119`.

## 5. Backup i aktualizacja

Przed aktualizacją:

```bash
docker compose stop hermes
tar -C "$HOME" -czf "$HOME/hermes-backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" .hermes
chmod 600 "$HOME"/hermes-backup-*.tar.gz
docker compose start hermes
```

Sprawdź nowe wydanie, zmień tag obrazu w `docker-compose.yaml`, a następnie:

```bash
docker compose pull
docker compose up -d
docker compose logs --tail=100 hermes
```

Nie używaj `latest`. W razie problemów przywróć poprzedni tag i uruchom ponownie `docker compose up -d`.

## Najważniejsze zasady

- nie zmieniaj `127.0.0.1` na `0.0.0.0`;
- nie montuj katalogu domowego, kluczy SSH ani `/var/run/docker.sock`;
- nie włączaj YOLO mode;
- instaluj tylko sprawdzone skille i pluginy;
- zatrzymanie: `docker compose down` — dane pozostaną w `~/.hermes`.
