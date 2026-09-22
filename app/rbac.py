"""SQL policies: combine permissions and scope within the same role."""
from sqlalchemy import and_, or_, select

from app.dbapi.models import Channel, Event, Object, Permission, Role, User
from app.dbapi.models.access import (
    division_objects, user_divisions,
)
from app.dbapi.models.associations import role_permissions, user_roles


def _active_user(user_id):
    return select(User.id).where(User.id == user_id, User.is_active.is_(True)).exists()


def _admin(user_id):
    return (
        select(user_roles.c.user_id).join(Role, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user_id, Role.code == "admin").exists()
    )


def object_access_condition(user_id: str, permission_code: str):
    assigned_objects = (
        select(division_objects.c.object_id)
        .join(user_divisions, user_divisions.c.division_id == division_objects.c.division_id)
        .where(user_divisions.c.user_id == user_id)
    )
    allowed_role = (
        select(Role.id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .join(role_permissions, role_permissions.c.role_id == Role.id)
        .join(Permission, Permission.id == role_permissions.c.permission_id)
        .where(
            user_roles.c.user_id == user_id,
            Permission.code == permission_code,
            Object.id.in_(assigned_objects),
        )
        .correlate(Object).exists()
    )
    return and_(_active_user(user_id), or_(_admin(user_id), allowed_role))


def accessible_objects(user_id: str, permission_code: str = "object.view"):
    return select(Object).where(object_access_condition(user_id, permission_code))


def accessible_channels(user_id: str, permission_code: str = "channel.view"):
    object_ids = accessible_objects(user_id, permission_code).with_only_columns(Object.id)
    return select(Channel).where(
        _active_user(user_id), or_(_admin(user_id), Channel.object_id.in_(object_ids)),
    )


def accessible_events(user_id: str, permission_code: str = "event.view"):
    channel_ids = accessible_channels(user_id, permission_code).with_only_columns(Channel.id)
    return select(Event).where(Event.channel_id.in_(channel_ids))
