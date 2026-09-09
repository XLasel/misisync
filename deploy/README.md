# Деплой на Timeweb Cloud (VPS)

Nginx **лежит в репозитории** (`deploy/nginx/`, `compose.prod.yaml`) и поднимается Docker’ом вместе с приложением. На сервер отдельно nginx ставить не обязательно.

## Один раз на сервере

### 1. Docker

На Ubuntu VPS Timeweb:

```sh
sudo apt update
sudo apt install -y git curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# выйти из SSH и зайти снова
docker compose version
```

### 2. Клон и `.env`

```sh
sudo mkdir -p /opt/misisync
sudo chown "$USER":"$USER" /opt/misisync
git clone git@github.com:YOUR_ORG/misisync.git /opt/misisync
cd /opt/misisync
cp .env.example .env
nano .env
```

Обязательно для прода:

```env
DOMAIN=schedule.ваш-домен.ru
TRUST_PROXY=true
API_BASE=http://backend:8000
```

### 3. DNS

В панели домена: **A-запись** `schedule.ваш-домен.ru` → публичный IP сервера Timeweb. Подождать распространения DNS.

### 4. Первый запуск (HTTP)

```sh
chmod +x deploy/*.sh
./deploy/update.sh
```

Открыть `http://schedule.ваш-домен.ru`.

### 5. HTTPS (Let's Encrypt)

Порты **80 и 443** должны быть открыты в фаерволе Timeweb.

```sh
./deploy/issue-cert.sh
```

Скрипт получит сертификат и подменит nginx-шаблон на TLS. Сайт: `https://…`.

Обновление сертификата позже — снова `./deploy/issue-cert.sh` или cron с `certbot renew` + `docker compose … up -d nginx`.

---

## Автодеплой из GitHub

Workflow: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — при пуше в `main` (и вручную) SSH на сервер → `git reset --hard origin/main` → `./deploy/update.sh`.

### Secrets в GitHub (Settings → Secrets and variables → Actions)

| Secret | Пример |
| --- | --- |
| `DEPLOY_HOST` | `1.2.3.4` или hostname VPS |
| `DEPLOY_USER` | `ubuntu` / `root` |
| `DEPLOY_SSH_KEY` | приватный ключ целиком (`-----BEGIN …`) |
| `DEPLOY_PATH` | `/opt/misisync` |

### SSH-ключ для деплоя

На своём Mac:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/misisync_deploy -N ""
ssh-copy-id -i ~/.ssh/misisync_deploy.pub USER@SERVER
```

В GitHub Secrets → `DEPLOY_SSH_KEY` = содержимое `~/.ssh/misisync_deploy` (приватный).

На сервере репозиторий должен уметь `git fetch` (deploy key GitHub read-only или HTTPS + token). Для приватного repo удобнее **Deploy key** (read-only) в настройках репозитория GitHub, публичный ключ на сервере в `~/.ssh/`.

### Проверка

Actions → Deploy to Timeweb → должен стать зелёным после пуша в `main`.

---

## Локально vs прод

| | Команда |
| --- | --- |
| Локально | `docker compose up --build -d` → `:3000` |
| Прод | `docker compose -f compose.yaml -f compose.prod.yaml up --build -d` → nginx `:80`/`:443` |

Backend наружу не публикуется. `TRUST_PROXY=true` только за nginx из этого compose (он выставляет `X-Forwarded-*`).
