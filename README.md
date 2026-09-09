# Misisync

Неофициальное расписание МИСИС: поиск группы, календарные недели, подгруппы.

Python/FastAPI + Vue 3/Nuxt + Docker Compose. Источник данных — live JSON-RPC `edu.misis.ru` (как официальный сайт): каталог групп кэшируется, расписание запрашивается по выбранной группе и неделям.

Базы данных и Excel-импорта нет. Кэш в памяти сокращает повторные обращения к университету: каталог хранится час, неделя группы — 15 минут. После истечения срока данные обновляются при следующем запросе. Если обновление не удалось, последняя версия доступна ещё до часа с предупреждением и временем её получения. После перезапуска кэш пуст; истории изменений и офлайн-доступа после перезапуска нет.

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
| `EDU_STALE_IF_ERROR_SECONDS` | Допустимый срок старых данных после истечения TTL при сбое (3600) |
| `EDU_RETRY_BACKOFF_SECONDS` | Пауза между повторными попытками после сбоя (30) |
| `EDU_MAX_PENDING_REQUESTS` | Максимум различных недель, ожидающих загрузки (64) |
| `EDU_MAX_CONCURRENT_REQUESTS` | Максимум одновременных обращений к университету (4) |
| `NUXT_SCHEDULE_RATE_LIMIT_PER_MINUTE` | Лимит `/api/schedule` на IP в публичном прокси Nuxt (60) |
| `NUXT_TRUST_PROXY` | Доверять `X-Forwarded-For` от внешнего прокси (по умолчанию `false`) |
| `REQUEST_TIMEOUT_SECONDS`, `MAX_DOWNLOAD_BYTES` | Таймаут и лимит размера ответа |
| `NUXT_API_BASE` | Адрес бэкенда для прокси Nuxt |
| `PORT` | Порт фронтенда (3000) |

В Compose наружу открыт только Nuxt; FastAPI доступен внутри сети контейнеров. Лимит посетителей применяется в Nuxt, где виден их IP. Если перед Nuxt стоит внешний reverse proxy, включайте `NUXT_TRUST_PROXY=true` только когда он перезаписывает `X-Forwarded-For`, а прямой доступ к Nuxt закрыт. Иначе все посетители этого прокси разделяют один лимит. Кэш и лимиты локальны одному процессу; несколько экземпляров имеют независимое состояние.

Кнопка «Проверить» повторяет запрос к Misisync и учитывает TTL: она не обходит кэш. «Получено» — время последнего успешного получения расписания у университета; для нескольких недель берётся самое раннее время.

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
