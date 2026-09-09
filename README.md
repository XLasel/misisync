# Misisync

Неофициальное расписание МИСИС: поиск группы, календарные недели, подгруппы.

Python/FastAPI + Vue 3/Nuxt + Docker Compose. Источник данных — live JSON-RPC `edu.misis.ru` (как официальный сайт): каталог групп кэшируется, расписание запрашивается по выбранной группе и неделям.

## Запуск

```sh
cp .env.example .env
docker compose up --build -d
```

Открыть http://localhost:3000. Нужен работающий Docker Engine.

## Настройки

| Переменная | Назначение |
| --- | --- |
| `EDU_API_URL`, `EDU_FILIAL` | JSON-RPC endpoint и филиал (`MOSCOW`) |
| `EDU_GROUPS` | Фильтр имён в каталоге; пусто = все группы филиала |
| `EDU_REQUEST_DELAY_SECONDS` | Пауза перед каждым RPC (по умолчанию 0.25) |
| `EDU_CATALOG_TTL_SECONDS` | TTL кэша списка групп (3600) |
| `EDU_SCHEDULE_TTL_SECONDS` | TTL кэша недели группы (900) |
| `EDU_SCHEDULE_CACHE_MAX_ENTRIES` | Максимум недель в памяти (256) |
| `SCHEDULE_RATE_LIMIT_PER_MINUTE` | Лимит `/api/schedule` на IP в минуту (60) |
| `REQUEST_TIMEOUT_SECONDS`, `MAX_DOWNLOAD_BYTES` | Таймаут и лимит размера ответа |
| `NUXT_API_BASE` | Адрес бэкенда для прокси Nuxt |
| `PORT` | Порт фронтенда (3000) |

## API

- `GET /api/groups`
- `GET /api/schedule?group_id=...&start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/status`
- `GET /api/health`

Контракт и замена бэкенда: [docs/architecture.md](docs/architecture.md). Исследование API: [docs/edu-api-investigation.md](docs/edu-api-investigation.md).

## Локальная разработка

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```sh
cd frontend && npm ci && npm run dev -- --port 3000
```

## HAR replay (без сети)

```sh
PYTHONPATH=backend .venv/bin/python scripts/replay_edu_har.py /path/to/edu.misis.ru.har \
  --group МПИ-26-1-1 --start 2026-09-07 --weeks 4
```

## Проверки

```sh
.venv/bin/pytest backend/tests -q
cd frontend && npm test && npm run typecheck && npm run build
```
