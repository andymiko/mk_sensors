"""SQL policies: combine permissions and scope within the same role."""
from sqlalchemy import and_, or_, select

from app.dbapi.models import Channel, Event, Object, Permission, Role, User
from app.dbapi.models.access import (
    district_divisions, user_role_districts, user_role_divisions, user_role_objects,
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
    explicit_objects = select(user_role_objects.c.object_id).where(
        user_role_objects.c.user_id == user_id, user_role_objects.c.role_id == Role.id,
    ).correlate(Role)
    districts = select(user_role_districts.c.district_id).where(
        user_role_districts.c.user_id == user_id, user_role_districts.c.role_id == Role.id,
    ).correlate(Role)
    division_districts = (
        select(district_divisions.c.district_id)
        .join(
            user_role_divisions,
            user_role_divisions.c.division_id == district_divisions.c.division_id,
        )
        .where(user_role_divisions.c.user_id == user_id, user_role_divisions.c.role_id == Role.id)
        .correlate(Role)
    )
    scope = or_(
        and_(Role.code == "technician", Object.district_id.in_(districts), Object.id.in_(explicit_objects)),
        and_(Role.code == "dispatcher", Object.district_id.is_not(None),
             or_(Object.district_id.in_(districts), Object.id.in_(explicit_objects))),
        and_(Role.code == "manager", Object.district_id.in_(division_districts)),
    )
    allowed_role = (
        select(Role.id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .join(role_permissions, role_permissions.c.role_id == Role.id)
        .join(Permission, Permission.id == role_permissions.c.permission_id)
        .where(user_roles.c.user_id == user_id, Permission.code == permission_code, scope)
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
