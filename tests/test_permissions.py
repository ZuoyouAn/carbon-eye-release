"""Isolated authorization regression tests; never touch the live database."""
import pytest
import secrets
from test_website_deployment import full_client
import main as website
from models import User, PermissionAudit
from permissions import permissions_for

ADMIN_PASSWORD = "-".join(["test", "admin", "only", "1234"])
MEMBER_PASSWORD = secrets.token_urlsafe(24)


def login(client, username="root", password=ADMIN_PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}, response.json()["user"]


def create_member(client, role="user", username="member"):
    headers, _ = login(client)
    response = client.post("/api/admin/users", headers=headers, json={"username": username, "password": MEMBER_PASSWORD, "role": role, "admin_password": ADMIN_PASSWORD})
    assert response.status_code == 200
    member_headers, user = login(client, username, MEMBER_PASSWORD)
    return headers, member_headers, user


@pytest.mark.parametrize("role", ["user", "elevated", "admin", "owner", "", None])
def test_role_definition_deny_unknown_and_muted(role):
    allowed = permissions_for(role)
    assert ("publish" in allowed) == (role in {"elevated", "admin"})
    assert ("manage_users" in allowed) == (role == "admin")
    assert "publish" not in permissions_for(role, True)
    assert "manage_users" not in permissions_for(role, True)


def test_registration_cannot_choose_role_or_reserved_names(full_client):
    payload = {"username": "member", "password": MEMBER_PASSWORD}
    assert full_client.post("/api/auth/register", json={**payload, "role": "admin"}).status_code == 422
    for username in ["admin", "root", "ADMIN"]:
        assert full_client.post("/api/auth/register", json={**payload, "username": username}).status_code == 400
    registered = full_client.post("/api/auth/register", json=payload).json()["user"]
    assert registered["role"] == "user"
    assert registered["role_label"] == "低权限"
    assert "publish" not in registered["permissions"]


@pytest.mark.parametrize("path,body", [
    ("/api/posts", {"title": "不能发布", "content": "test"}),
    ("/api/messages", {"content": "test"}),
    ("/api/posts/123/comments", {"content": "test"}),
    ("/api/articles/123/comments", {"content": "test"}),
])
def test_guest_and_low_users_cannot_publish(full_client, path, body):
    _, member_headers, _ = create_member(full_client)
    assert full_client.post(path, json=body).status_code == 401
    assert full_client.post(path, headers=member_headers, json=body).status_code == 403


@pytest.mark.parametrize("role", ["elevated", "admin"])
def test_high_and_admin_can_publish_but_only_admin_can_manage(full_client, role):
    admin_headers, headers, user = create_member(full_client, role)
    post = full_client.post("/api/posts", headers=headers, json={"title": "test", "content": "test"})
    assert post.status_code == 200
    post_id = post.json()["post"]["id"]
    assert full_client.post(f"/api/posts/{post_id}/comments", headers=headers, json={"content": "test"}).status_code == 200
    assert full_client.post("/api/messages", headers=headers, json={"content": "test"}).status_code == 200
    article = full_client.post("/api/articles", headers=admin_headers, json={"title": "test", "content": "test"}).json()["article"]
    assert full_client.post(f'/api/articles/{article["id"]}/comments', headers=headers, json={"content": "test"}).status_code == 200
    expected = 200 if role == "admin" else 403
    for path in ["/api/admin/dashboard", "/api/admin/users", "/api/admin/permission-audit"]:
        assert full_client.get(path, headers=headers).status_code == expected
    assert full_client.post("/api/articles", headers=headers, json={"title": "test", "content": "test"}).status_code == expected


def test_low_user_can_favorite_like_and_save_progress(full_client):
    admin, headers, _ = create_member(full_client)
    article = full_client.post("/api/articles", headers=admin, json={"title": "test", "content": "test"}).json()["article"]
    for operation in ["like", "favorite"]:
        assert full_client.post(f'/api/articles/{article["id"]}/{operation}', headers=headers).status_code == 200
    assert full_client.post("/api/novels/8/favorite", headers=headers).status_code == 200
    assert full_client.put("/api/novels/8/progress", headers=headers, json={"progress": 47}).status_code == 200


def test_promotion_and_demotion_revoke_old_sessions_and_are_audited(full_client):
    admin, headers, user = create_member(full_client)
    path = f'/api/admin/users/{user["id"]}/role'
    assert full_client.put(path, headers=headers, json={"role": "admin", "admin_password": MEMBER_PASSWORD}).status_code == 403
    assert full_client.put(path, headers=admin, json={"role": "elevated", "admin_password": "wrong"}).status_code == 403
    assert full_client.put(path, headers=admin, json={"role": "superadmin", "admin_password": ADMIN_PASSWORD}).status_code == 422
    result = full_client.put(path, headers=admin, json={"role": "elevated", "admin_password": ADMIN_PASSWORD})
    assert result.status_code == 200 and result.json()["user"]["role"] == "elevated"
    assert full_client.get("/api/auth/me", headers=headers).status_code == 401
    headers, _ = login(full_client, "member", MEMBER_PASSWORD)
    assert full_client.post("/api/posts", headers=headers, json={"title": "test", "content": "test"}).status_code == 200
    assert full_client.put(path, headers=admin, json={"role": "user", "admin_password": ADMIN_PASSWORD}).status_code == 200
    assert full_client.get("/api/auth/me", headers=headers).status_code == 401
    headers, _ = login(full_client, "member", MEMBER_PASSWORD)
    assert full_client.post("/api/posts", headers=headers, json={"title": "test", "content": "test"}).status_code == 403
    audit = full_client.get("/api/admin/permission-audit", headers=admin).json()["items"]
    assert [(row["old_role"], row["new_role"]) for row in audit[:2]] == [("elevated", "user"), ("user", "elevated")]
    assert "password" not in str(audit)


def test_promoting_admin_requires_strong_password_and_reauthentication(full_client):
    admin, headers, user = create_member(full_client)
    path = f'/api/admin/users/{user["id"]}/role'
    body = {"role": "admin", "admin_password": ADMIN_PASSWORD}
    for password in [None, "123456", "123456789012"]:
        bad = body if password is None else {**body, "new_password": password}
        assert full_client.put(path, headers=admin, json=bad).status_code == 400
    new_password = secrets.token_urlsafe(24)
    assert full_client.put(path, headers=admin, json={**body, "new_password": new_password}).status_code == 200
    assert full_client.get("/api/admin/dashboard", headers=headers).status_code == 401
    assert full_client.post("/api/auth/login", json={"username": "member", "password": MEMBER_PASSWORD}).status_code == 401
    new_headers, _ = login(full_client, "member", new_password)
    assert full_client.get("/api/admin/dashboard", headers=new_headers).status_code == 200
    # A distinct administrator can demote the second admin; root remains.
    assert full_client.put(path, headers=admin, json={"role": "user", "admin_password": ADMIN_PASSWORD}).status_code == 200
    assert full_client.get("/api/auth/me", headers=new_headers).status_code == 401


def test_self_role_change_and_admin_delete_are_forbidden(full_client):
    headers, user = login(full_client)
    path = f'/api/admin/users/{user["id"]}'
    assert full_client.put(path + "/role", headers=headers, json={"role": "user", "admin_password": ADMIN_PASSWORD}).status_code == 403
    assert full_client.delete(path, headers=headers).status_code == 403
    assert full_client.put(path + "/mute", headers=headers, json={}).status_code == 404
    assert full_client.get("/api/admin/dashboard", headers=headers).status_code == 200


def test_role_cannot_be_changed_through_generic_update(full_client):
    admin, _, user = create_member(full_client)
    assert full_client.put(f'/api/admin/users/{user["id"]}', headers=admin, json={"role": "admin"}).status_code == 422
    assert full_client.put(f'/api/admin/users/{user["id"]}/role', headers=admin, json={"role": "admin", "admin_password": ADMIN_PASSWORD, "is_deleted": False}).status_code == 422


def test_mute_revokes_token_and_cannot_be_bypassed_via_messages(full_client):
    admin, headers, user = create_member(full_client, "elevated")
    assert full_client.put(f'/api/admin/users/{user["id"]}/mute', headers=admin, json={}).status_code == 200
    assert full_client.get("/api/auth/me", headers=headers).status_code == 401
    muted_headers, muted = login(full_client, "member", MEMBER_PASSWORD)
    assert "publish" not in muted["permissions"]
    for path, body in [("/api/posts", {"title": "test", "content": "test"}), ("/api/messages", {"content": "test"})]:
        assert full_client.post(path, headers=muted_headers, json=body).status_code == 403
    assert full_client.put(f'/api/admin/users/{user["id"]}/unmute', headers=admin, json={}).status_code == 200
    assert full_client.get("/api/auth/me", headers=muted_headers).status_code == 401


def test_password_change_and_reset_revoke_all_sessions(full_client):
    admin, headers, user = create_member(full_client)
    other_headers, _ = login(full_client, "member", MEMBER_PASSWORD)
    new_password = secrets.token_urlsafe(24)
    assert full_client.put("/api/me/password", headers=headers, json={"old_password": MEMBER_PASSWORD, "new_password": new_password}).status_code == 200
    for session in [headers, other_headers]:
        assert full_client.get("/api/auth/me", headers=session).status_code == 401
    headers, _ = login(full_client, "member", new_password)
    assert full_client.put(f'/api/admin/users/{user["id"]}', headers=admin, json={"password": "reset-test-password"}).status_code == 200
    assert full_client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_creation_requires_confirmation_and_strong_password(full_client):
    headers, _ = login(full_client)
    body = {"username": "admin", "password": "123456", "role": "admin", "admin_password": ADMIN_PASSWORD}
    assert full_client.post("/api/admin/users", headers=headers, json=body).status_code == 400
    body["password"] = "created-admin-test-password"
    assert full_client.post("/api/admin/users", headers=headers, json={**body, "admin_password": "wrong"}).status_code == 403
    assert full_client.post("/api/admin/users", headers=headers, json=body).status_code == 200
    new_headers, new_admin = login(full_client, "admin", body["password"])
    assert new_admin["role"] == "admin"
    assert full_client.get("/api/admin/dashboard", headers=new_headers).status_code == 200


def test_deleted_user_cannot_be_promoted_or_log_in(full_client):
    admin, headers, user = create_member(full_client)
    path = f'/api/admin/users/{user["id"]}'
    assert full_client.delete(path, headers=admin).status_code == 200
    assert full_client.get("/api/auth/me", headers=headers).status_code == 401
    assert full_client.put(path + "/role", headers=admin, json={"role": "elevated", "admin_password": ADMIN_PASSWORD}).status_code == 404
    assert full_client.post("/api/auth/login", json={"username": "member", "password": MEMBER_PASSWORD}).status_code == 401


def test_password_whitespace_preserved_and_legacy_hashes_still_work(full_client):
    password = "  " + secrets.token_urlsafe(24) + "  "
    assert full_client.post("/api/auth/register", json={"username": "spaces", "password": password}).status_code == 200
    assert full_client.post("/api/auth/login", json={"username": "spaces", "password": password}).status_code == 200
    assert full_client.post("/api/auth/login", json={"username": "spaces", "password": password.strip()}).status_code == 401
    assert login(full_client)[1]["username"] == "root"


def test_private_admin_setup_preserves_identity_revokes_sessions_and_is_once_only(full_client, monkeypatch):
    old_headers, original = login(full_client)
    setup_password = secrets.token_urlsafe(24)
    monkeypatch.setenv("ADMIN_SETUP_PASSWORD", setup_password)
    with website.SessionLocal() as db:
        website.initialize_configured_admin(db)
    assert full_client.get("/api/auth/me", headers=old_headers).status_code == 401
    assert full_client.post("/api/auth/login", json={"username": "root", "password": ADMIN_PASSWORD}).status_code == 401
    headers, user = login(full_client, "admin", setup_password)
    assert user["id"] == original["id"]
    new_password = secrets.token_urlsafe(24)
    assert full_client.put("/api/me/password", headers=headers, json={"old_password": setup_password, "new_password": new_password}).status_code == 200
    with website.SessionLocal() as db:
        website.initialize_configured_admin(db)
    assert login(full_client, "admin", new_password)[1]["id"] == original["id"]
    assert full_client.post("/api/auth/login", json={"username": "admin", "password": setup_password}).status_code == 401
    with website.SessionLocal() as db:
        assert db.query(User).count() == 1
        assert db.query(PermissionAudit).filter(PermissionAudit.action == "admin_setup").count() == 1


def test_private_setup_rejects_weak_password_and_does_not_elevate_existing_user(full_client, monkeypatch):
    monkeypatch.setenv("ADMIN_SETUP_PASSWORD", "123456")
    with website.SessionLocal() as db:
        with pytest.raises(RuntimeError, match="至少需要 12"):
            website.initialize_configured_admin(db)
    monkeypatch.setenv("ADMIN_SETUP_PASSWORD", "private-setup-test-password")
    with website.SessionLocal() as db:
        db.add(User(username="admin", password_hash=website.hash_password(MEMBER_PASSWORD), role="user"))
        db.commit()
        with pytest.raises(RuntimeError, match="不会自动提权"):
            website.initialize_configured_admin(db)
