# CRUD предметных данных

Репозитории экспортируются из `app.dbapi.models`:

| Таблица | Репозиторий | Методы |
|---|---|---|
| `divisions` | `Divisions` | `insert_new_division`, `get_division_by_id`, `get_division_by_code`, `get_divisions_page`, `update_division_by_id`, `delete_division_by_id` |
| `districts` | `Districts` | `insert_new_district`, `get_district_by_id`, `get_district_by_code`, `get_districts_page`, `update_district_by_id`, `delete_district_by_id` |
| `objects` | `Objects` | `insert_new_object`, `get_object_by_id`, `get_objects_page`, `update_object_by_id`, `delete_object_by_id` |
| `channels` | `Channels` | `insert_new_channel`, `get_channel_by_id`, `get_channels_page`, `update_channel_by_id`, `delete_channel_by_id` |
| `events` | `Events` | `insert_new_event`, `get_event_by_id`, `get_events_page`, `update_event_by_id`, `delete_event_by_id` |

Каждый метод принимает необязательную async-сессию `db`. Без неё репозиторий
создаёт собственную сессию. Операции записи фиксируют транзакцию, а при ошибке
выполняют rollback. Конфликты уникальности и внешних ключей возвращаются как
исключения SQLAlchemy, чтобы вызывающий API или загрузчик выбрал нужную реакцию.

Методы `get_*_page` возвращают `(items, total)`, принимают `offset` и `limit`.
Допустимый `limit` — от 1 до 1000. Аналитические выборки следует реализовывать
отдельными запросами с агрегацией в PostgreSQL, а не чтением всех страниц CRUD.

Частичные обновления меняют только переданные аргументы. Для nullable-полей
явное значение `None` записывает SQL `NULL`; пропущенный аргумент сохраняет
текущее значение.

Пример:

```python
from app.dbapi.models import Channels, Objects

obj = await Objects.insert_new_object(
    id=100,
    hierarchy_level=1,
    object_type="building",
    dispatch_name="Объект 100",
    district_id=district_id,
    db=session,
)

channel = await Channels.insert_new_channel(
    id=200,
    object_id=obj.id,
    sensor_type="temperature",
    sensor_name="Температура подачи",
    db=session,
)

await Channels.update_channel_by_id(channel.id, sensor_name=None, db=session)
items, total = await Channels.get_channels_page(offset=0, limit=100, db=session)
```

Удаление возвращает `True`, если запись была удалена, и `False`, если ID уже
отсутствовал. Зависимые записи не удаляются неявно: ограничения внешних ключей
защищают объект с каналами, канал с событиями и используемые территории.
