# Деплой на Timeweb Cloud (VPS)

Nginx **лежит в репозитории** (`deploy/nginx/`, `compose.prod.yaml`) и поднимается Docker’ом вместе с приложением. На сервер отдельно nginx ставить не обязательно.

## Один раз на сервере

### 1. Docker

На Ubuntu VPS Timeweb:

```sh
sudo apt update
sudo apt install -y git curl cron
sudo systemctl enable --now cron
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
./deploy/update.sh ПОЛНЫЙ_SHA_ОПУБЛИКОВАННОГО_КОММИТА
```

Открыть `http://schedule.ваш-домен.ru`.

### 5. HTTPS (Let's Encrypt)

Порты **80 и 443** должны быть открыты в фаерволе Timeweb.

```sh
./deploy/issue-cert.sh
```

Скрипт установит cron-задачу продления, получит сертификат и переключит nginx на TLS. Сайт: `https://…`.

Продление автоматически проверяется дважды в сутки через crontab пользователя деплоя. Задача также устанавливается при каждом деплое, если сертификат уже есть. Другие cron-задачи сохраняются; повторная установка не создаёт дублей.

Однократная проверка через тестовый сервер Let's Encrypt:

```sh
./deploy/renew-cert.sh --dry-run
crontab -l
```

Обычный запуск: `./deploy/renew-cert.sh`. После фактического продления проверяется конфигурация nginx и выполняется reload. При ошибке reload остаётся маркер, и следующая попытка повторит перезагрузку. Ошибка Certbot завершает скрипт с ненулевым кодом. Лог: `deploy/certbot/renew.log` (не отслеживается Git). Для уже работающего сервера сначала установите и включите `cron` командами из первого раздела.

Скрипты деплоя, выпуска и продления сертификата используют один `flock` в `.deploy.lock`. Не запускайте в обход них параллельные команды, меняющие production-контейнеры.

---

## Автодеплой из GitHub

Workflow: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — при PR/push выполняет backend-тесты, проверки shell-скриптов, frontend-тесты, проверку типов, ESLint и production-сборку. После успешных проверок push в `main` (или ручной запуск для `main`) допускается к деплою.

По SSH разворачивается точный SHA проверенного коммита. Если `main` уже продвинулся, устаревший деплой пропускается. Новый push не отменяет активный деплой. `update.sh` ждёт здорового состояния контейнеров; ошибка скачивания образов или проверки здоровья завершает workflow с ошибкой. Автоматического отката на предыдущую версию пока нет.

Используется системный OpenSSH с обязательной проверкой ключа хоста. Сторонний SSH Action удалён; оставшиеся официальные Actions закреплены полными commit SHA. В CI минимальные права `contents: read`, production-ключ доступен только шагу деплоя.

### Secrets в GitHub (Settings → Secrets and variables → Actions)

| Secret | Пример |
| --- | --- |
| `DEPLOY_HOST` | `1.2.3.4` или hostname VPS |
| `DEPLOY_USER` | `ubuntu` / `root` |
| `DEPLOY_SSH_KEY` | приватный ключ целиком (`-----BEGIN …`) |
| `DEPLOY_PATH` | `/opt/misisync` |
| `DEPLOY_KNOWN_HOSTS` | Проверенная строка known_hosts для VPS (см. ниже) |

### Проверка ключа сервера (нужна и для существующего деплоя)

В доверенной консоли Timeweb на VPS получите публичный ключ хоста:

```sh
cat /etc/ssh/ssh_host_ed25519_key.pub
```

Создайте GitHub Secret `DEPLOY_KNOWN_HOSTS` в формате `HOST ssh-ed25519 AAAA…`, где `HOST` совпадает с `DEPLOY_HOST`, а ключ скопирован из консоли. Это **публичный ключ сервера**, не приватный ключ пользователя деплоя. При нестандартном SSH-порте используйте `[HOST]:PORT` и задайте repository variable `DEPLOY_PORT` (по умолчанию 22). Непроверенный результат `ssh-keyscan` не заменяет проверку в доверенной консоли.

Без нового секрета workflow остановится до SSH-подключения. При смене VPS/ключа обновите секрет после проверки нового ключа.

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
| Прод | `bash deploy/update.sh` (при первом запуске передайте SHA) → nginx `:80`/`:443` |

Backend наружу не публикуется. `TRUST_PROXY=true` только за nginx из этого compose (он выставляет `X-Forwarded-*`).


## Обновления образов

Nginx обновлён с ветки 1.27 до 1.30.4 и закреплён digest в `compose.prod.yaml`; Certbot закреплён digest в `deploy/common.sh`. При обновлении сверяйте релизы и повторяйте проверку конфигурации. [Официальные предупреждения nginx](https://nginx.org/en/security_advisories.html).

## Готовые образы из GitHub Actions

Push в `develop` не запускает workflow. PR в `main` проверяется; push/merge в `main` повторяет проверки, собирает два linux/amd64 образа в GitHub и публикует их в GHCR с тегом полного SHA коммита. Production больше не собирает исходники. GHCR хранит образы, VPS скачивает сжатые слои и распаковывает их; общие слои переиспользуются.

Перед первым новым деплоем обеспечьте чтение пакетов `ghcr.io/xlasel/misisync-backend` и `ghcr.io/xlasel/misisync-frontend` с сервера. Новые пакеты могут быть private: после первой публикации либо сделайте их public в GitHub Packages (если допустима публикация приложения), либо выполните `docker login ghcr.io` на VPS от пользователя деплоя с отдельным токеном только `read:packages`. Не добавляйте токен в репозиторий. `GITHUB_TOKEN` для публикации выдаётся Actions автоматически. Если первый pull отказал в доступе, текущие контейнеры остаются работать; после настройки доступа повторите workflow.

Для нового VPS: Ubuntu 24.04 x86_64, Docker Compose с поддержкой `!reset`, cron, git, `.env`, доступ к GHCR. Первый запуск из `/opt/misisync`: `bash deploy/update.sh ПОЛНЫЙ_SHA_ОПУБЛИКОВАННОГО_КОММИТА`. Повторный запуск без аргумента использует последний успешный SHA из игнорируемого `deploy/release.env`. Скрипты сертификатов используют то же состояние. На новом IP сначала проверьте источник и приложение, затем переключите DNS и подключите HTTPS. Старый сервер выключайте после проверки нового адреса из внешних сетей.

Текущий и предыдущий успешные SHA сохраняются на VPS. Откат: прочитайте `deploy/previous-release.env` и передайте его SHA в `bash deploy/update.sh SHA`. При неудаче healthcheck автоматического отката нет: проверьте логи и запустите предыдущую версию. Старые SHA-образы только этих двух репозиториев удаляются после успешного деплоя; используемые контейнерами образы Docker не удалит. Старые образы в GHCR этим не удаляются. Логи трёх production-сервисов используют драйвер local: до трёх файлов по 10 МБ на контейнер.

После успешного перехода со сборки на сервере выполните отдельно `docker builder prune` (не во время сборки). Это удаляет неиспользуемый сборочный кэш, не данные работающего приложения. Проверьте результат через `docker system df` и `df -h /`. Старые локальные `misisync-frontend`/`misisync-backend` оставьте до завершения проверки и удалите адресно после неё. Не используйте бездумно `docker system prune -a --volumes`.
