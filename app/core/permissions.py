from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"


class Permission(str, Enum):
    MANAGE_ROLES = "manage_roles"
    MANAGE_MODULES = "manage_modules"
    MANAGE_MUSIC = "manage_music"
    MANAGE_MODERATION = "manage_moderation"
    WARN_USERS = "warn_users"
    KICK_USERS = "kick_users"
    BAN_USERS = "ban_users"
    MUTE_USERS = "mute_users"
    PURGE_MESSAGES = "purge_messages"
    VIEW_MOD_LOGS = "view_mod_logs"
    DELETE_MESSAGES = "delete_messages"
    MANAGE_COMMUNITY = "manage_community"
    MANAGE_WELCOME = "manage_welcome"
    MANAGE_GIVEAWAYS = "manage_giveaways"
    MANAGE_ECONOMY = "manage_economy"
    MANAGE_AI = "manage_ai"
    VIEW_ADMIN_LOGS = "view_admin_logs"


ALL_PERMISSIONS = frozenset(Permission)


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: ALL_PERMISSIONS,
    Role.ADMIN: ALL_PERMISSIONS,
    Role.MODERATOR: frozenset(
        {
            Permission.MANAGE_MODERATION,
            Permission.WARN_USERS,
            Permission.MUTE_USERS,
            Permission.PURGE_MESSAGES,
            Permission.VIEW_MOD_LOGS,
            Permission.DELETE_MESSAGES,
            Permission.VIEW_ADMIN_LOGS,
        }
    ),
    Role.MEMBER: frozenset(),
}
