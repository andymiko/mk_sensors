# MK Sensors

Система мониторинга объектов на FastAPI, PostgreSQL, Vue 3, PrimeVue 4, Pinia, Vue Router и MapLibre GL JS.

## Что включено

- регистрация, вход и профиль пользователя;
- JWT-аутентификация и ролевая модель доступа;
- управление пользователями, ролями и разрешениями;
- карта объектов, справочник объектов и журнал показаний;
- территориальные назначения объектов;
- адаптивный layout и светлая/тёмная тема.

Добавлена основа `mk_sensors`: объекты, каналы, события и RBAC с областями
доступа по подразделениям, районам и назначениям объектов. Роли: диспетчер,
техник, руководитель и отдельный администратор. Настройка и API описаны в
[RBAC_SPEC.md](docs/RBAC_SPEC.md).

Новые предметные модули добавляются через отдельные модели, API-router,
Pinia store и Vue-view.

## Быстрый запуск

```bash
cp .env.example .env
# замените SECRET_KEY и параметры PostgreSQL
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload --port 8000
```

Во втором терминале:

```bash
cd frontend
cp .env.example .env.development
npm ci
npm run dev
```

Frontend откроется на `http://localhost:5173`, API — на `http://localhost:8000/api`.

## Первый администратор

После регистрации назначьте пользователю роль `admin`:

```bash
uv run python scripts/promote_user.py admin@example.com
```

Шаблон не создаёт администратора с паролем по умолчанию.
