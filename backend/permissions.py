"""Server-owned role definitions. Unknown roles never receive permissions."""
ROLE_LABELS = {"user": "低权限", "elevated": "高权限", "admin": "管理员"}
ROLE_PERMISSIONS = {
    "user": frozenset({"read", "like", "favorite", "reading_progress", "chat", "avatar"}),
    "elevated": frozenset({"read", "like", "favorite", "reading_progress", "chat", "avatar", "publish"}),
    "admin": frozenset({"read", "like", "favorite", "reading_progress", "chat", "avatar", "publish", "manage_content", "manage_users"}),
}


def permissions_for(role, muted=False):
    permissions = ROLE_PERMISSIONS.get(role, frozenset())
    return sorted(permissions - {"chat", "publish", "manage_content", "manage_users"} if muted else permissions)
