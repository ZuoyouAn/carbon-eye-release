"""Avatar, consent, membership and abuse-control checks against disposable SQLite."""
import base64
from datetime import datetime, timedelta
from io import BytesIO
import secrets
import uuid

from PIL import Image, PngImagePlugin
import pytest

from test_website_deployment import full_client
from test_permissions import login
import main as website
from models import User
from social import ChatMessage, ChatMember, ChatThrottle, SocialQuota, UserAvatar, LOBBY


def member(client, name, role='user'):
    credential = secrets.token_urlsafe(24)
    result = client.post('/api/auth/register', json={'username': name, 'password': credential})
    assert result.status_code == 200
    user = result.json()['user']
    if role != 'user':
        with website.SessionLocal() as db:
            db.get(User, user['id']).role = role
            db.commit()
    return login(client, name, credential)


def lobby(client, headers):
    assert client.get('/api/chat/rooms', headers=headers).json()[0]['id'] == LOBBY
    return f'/api/chat/rooms/{LOBBY}'


def send(client, headers, room, text='一条近况', identifier=None):
    return client.post(room + '/messages', headers=headers, json={'content': text, 'client_id': identifier or str(uuid.uuid4())})


def image_data(size=(300, 200)):
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('private-location', 'should-not-survive')
    Image.new('RGB', size, '#acd3e5').save(output, format='PNG', pnginfo=metadata)
    return base64.b64encode(output.getvalue()).decode()


def accepted_direct(client):
    a, ua = member(client, 'alice')
    b, ub = member(client, 'bravo')
    created = client.post('/api/chat/direct', headers=a, json={'user_id': ub['id']})
    assert created.status_code == 200
    room = '/api/chat/rooms/' + created.json()['id']
    assert client.put(room + '/invitation', headers=b, json={'accept': True}).status_code == 200
    return a, ua, b, ub, room


def test_avatar_normalizes_strips_metadata_and_survives_session(full_client):
    headers, user = member(full_client, 'avataruser')
    path = f'/api/users/{user["id"]}/avatar'
    assert full_client.get(path).status_code == 404
    result = full_client.put('/api/me/avatar', headers=headers, json={'image_base64': image_data()})
    assert result.status_code == 200
    response = full_client.get(path)
    assert response.status_code == 200 and response.headers['content-type'] == 'image/webp'
    assert response.headers['x-content-type-options'] == 'nosniff' and len(response.content) < 32768
    decoded = Image.open(BytesIO(response.content))
    assert decoded.size == (128, 128) and decoded.format == 'WEBP'
    assert 'private-location' not in decoded.info and b'should-not-survive' not in response.content
    assert full_client.get(path, headers={'If-None-Match': response.headers['etag']}).status_code == 304
    with website.SessionLocal() as db:
        assert db.get(UserAvatar, user['id']).image == response.content
    assert full_client.delete('/api/me/avatar', headers=headers).status_code == 200
    assert full_client.get(path).status_code == 404


@pytest.mark.parametrize('encoded', ['!!!!', base64.b64encode(b'<svg onload="bad()"/>').decode(), base64.b64encode(b'x' * (256 * 1024 + 1)).decode(), image_data((2500, 2000))], ids=['base64', 'svg', 'file-size', 'pixel-count'])
def test_avatar_rejects_invalid_svg_oversized_and_pixel_bombs(full_client, encoded):
    headers, _ = member(full_client, 'rejectavatar')
    assert full_client.put('/api/me/avatar', headers=headers, json={'image_base64': encoded}).status_code in {400, 422}
    with website.SessionLocal() as db:
        assert db.query(UserAvatar).count() == 0 and db.query(SocialQuota).count() == 0


def test_avatar_cannot_overwrite_other_user_or_expose_deleted_user(full_client):
    a, ua = member(full_client, 'avatara')
    b, ub = member(full_client, 'avatarb')
    data = {'image_base64': image_data()}
    assert full_client.put('/api/me/avatar', json=data).status_code == 401
    assert full_client.put('/api/me/avatar', headers=a, json={**data, 'user_id': ub['id']}).status_code == 422
    assert full_client.put('/api/me/avatar', headers=b, json=data).status_code == 200
    assert full_client.delete(f'/api/users/{ub["id"]}/avatar', headers=a).status_code == 405
    with website.SessionLocal() as db:
        db.get(User, ub['id']).is_deleted = True
        db.commit()
    assert full_client.get(f'/api/users/{ub["id"]}/avatar').status_code == 404


def test_guest_cannot_discover_chat_users_rooms_or_messages(full_client):
    for path in ['/api/chat/rooms', '/api/chat/users?q=root', '/api/chat/blocks', f'/api/chat/rooms/{LOBBY}/messages']:
        assert full_client.get(path).status_code == 401


def test_search_minimum_and_public_fields_only(full_client):
    a, _ = member(full_client, 'finder')
    _, found = member(full_client, 'findtarget')
    assert full_client.get('/api/chat/users?q=f', headers=a).json() == []
    result = full_client.get('/api/chat/users?q=findtarget', headers=a).json()
    assert result[0]['id'] == found['id'] and set(result[0]) == {'id', 'username', 'avatar_path'}
    assert full_client.get('/api/chat/users?q=%', headers=a).json() == []


def test_direct_needs_consent_and_admin_has_no_private_bypass(full_client):
    a, ua = member(full_client, 'alice')
    b, ub = member(full_client, 'bravo')
    admin, _ = login(full_client)
    room = '/api/chat/rooms/' + full_client.post('/api/chat/direct', headers=a, json={'user_id': ub['id']}).json()['id']
    assert send(full_client, a, room).status_code == 403
    for outsider in [b, admin]:
        for suffix in ['/messages', '/members']:
            assert full_client.get(room + suffix, headers=outsider).status_code == 404
    assert full_client.put(room + '/invitation', headers=b, json={'accept': 'yes'}).status_code == 422
    assert full_client.put(room + '/invitation', headers=b, json={'accept': True}).status_code == 200
    text = '<img src=x onerror=alert(1)>只作为文本'
    assert send(full_client, a, room, text).status_code == 200
    history = full_client.get(room + '/messages', headers=b).json()['items']
    assert history[0]['content'] == text
    assert full_client.get(room + '/messages', headers=admin).status_code == 404
    assert full_client.post('/api/chat/direct', headers=b, json={'user_id': ua['id']}).json()['id'] == room.rsplit('/', 1)[1]
    with website.SessionLocal() as db:
        assert db.query(SocialQuota).filter(SocialQuota.scope == f'invite:user:{ua["id"]}').one().used == 1


def test_decline_and_leave_revoke_access_and_prevent_repeat_invites(full_client):
    a, ua, b, ub, room = accepted_direct(full_client)
    assert full_client.delete(room + '/membership', headers=b).status_code == 200
    assert full_client.get(room + '/messages', headers=b).status_code == 404
    assert send(full_client, a, room).status_code == 403
    assert full_client.post('/api/chat/direct', headers=b, json={'user_id': ua['id']}).status_code == 404
    c, uc = member(full_client, 'charlie')
    next_room = '/api/chat/rooms/' + full_client.post('/api/chat/direct', headers=a, json={'user_id': uc['id']}).json()['id']
    assert full_client.put(next_room + '/invitation', headers=c, json={'accept': False}).status_code == 200
    assert full_client.get(next_room + '/messages', headers=c).status_code == 404
    assert send(full_client, a, next_room).status_code == 403
    assert full_client.post('/api/chat/direct', headers=a, json={'user_id': uc['id']}).status_code == 409


def test_bilateral_block_stops_send_search_and_new_invites(full_client):
    a, ua, b, ub, room = accepted_direct(full_client)
    assert full_client.put(f'/api/chat/blocks/{ub["id"]}', headers=a, json={}).status_code == 200
    assert full_client.get('/api/chat/users?q=alice', headers=b).json() == []
    assert send(full_client, a, room).status_code == 403
    assert send(full_client, b, room).status_code == 403
    assert full_client.post('/api/chat/direct', headers=b, json={'user_id': ua['id']}).status_code == 403
    assert full_client.get('/api/chat/rooms', headers=b).json()[1]['blocked'] is True
    assert full_client.get(room + '/messages', headers=b).status_code == 200
    assert full_client.delete(f'/api/chat/blocks/{ub["id"]}', headers=b).status_code == 200
    assert send(full_client, b, room).status_code == 403  # Cannot remove someone else's block.
    assert full_client.delete(f'/api/chat/blocks/{ub["id"]}', headers=a).status_code == 200
    assert send(full_client, b, room).status_code == 200


def test_group_creation_and_invitation_are_role_and_membership_checked(full_client):
    low, ul = member(full_client, 'lowmember')
    owner, uo = member(full_client, 'highmember', 'elevated')
    stranger, _ = member(full_client, 'outsider')
    assert full_client.post('/api/chat/groups', headers=low, json={'name': '小群'}).status_code == 403
    result = full_client.post('/api/chat/groups', headers=owner, json={'name': '探索小队', 'user_ids': [ul['id']]})
    assert result.status_code == 200
    room = '/api/chat/rooms/' + result.json()['id']
    assert send(full_client, owner, room).status_code == 200
    assert full_client.get(room + '/messages', headers=low).status_code == 404
    assert full_client.put(room + '/invitation', headers=low, json={'accept': True}).status_code == 200
    assert len(full_client.get(room + '/messages', headers=low).json()['items']) == 1
    assert full_client.post(room + '/invite', headers=low, json={'user_id': 10}).status_code == 403
    assert full_client.post(room + '/invite', headers=stranger, json={'user_id': 10}).status_code == 404
    assert full_client.post(room + '/invite', headers=owner, json={'user_id': 10}).status_code == 200
    assert full_client.post(room + '/invite', headers=owner, json={'user_id': 10}).status_code == 409


def test_group_size_includes_pending_invitations(full_client):
    owner, _ = member(full_client, 'groupowner', 'elevated')
    ids = [member(full_client, f'member{i}')[1]['id'] for i in range(12)]
    result = full_client.post('/api/chat/groups', headers=owner, json={'name': '满员群', 'user_ids': ids[:11]})
    assert result.status_code == 200
    room = '/api/chat/rooms/' + result.json()['id']
    assert full_client.post(room + '/invite', headers=owner, json={'user_id': ids[11]}).status_code == 400


def test_retraction_owner_only_except_public_moderation(full_client):
    a, ua, b, ub, private = accepted_direct(full_client)
    admin, _ = login(full_client)
    identifier = send(full_client, a, private).json()['id']
    path = private + f'/messages/{identifier}'
    assert full_client.delete(path, headers=b).status_code == 403
    assert full_client.delete(path, headers=admin).status_code == 404
    assert full_client.delete(path, headers=a).status_code == 200
    item = full_client.get(private + '/messages', headers=b).json()['items'][0]
    assert item['is_deleted'] and item['content'] == '' and not item['can_retract']
    with website.SessionLocal() as db:
        db.get(ChatThrottle, ua['id']).last_sent_at -= timedelta(seconds=4)
        db.commit()
    public = lobby(full_client, a)
    identifier = send(full_client, a, public).json()['id']
    assert full_client.delete(public + f'/messages/{identifier}', headers=admin).status_code == 200


def test_message_idempotency_throttle_and_quotas_rollback(full_client):
    headers, user = member(full_client, 'retryuser')
    room = lobby(full_client, headers)
    client_id = str(uuid.uuid4())
    sent = send(full_client, headers, room, identifier=client_id)
    repeated = send(full_client, headers, room, identifier=client_id)
    assert sent.status_code == repeated.status_code == 200
    assert repeated.json() == {'id': sent.json()['id'], 'duplicate': True}
    assert send(full_client, headers, room).status_code == 429
    with website.SessionLocal() as db:
        assert db.query(ChatMessage).count() == 1
        assert {row.used for row in db.query(SocialQuota).filter(SocialQuota.scope.like('message:%'))} == {1}
        quota = db.query(SocialQuota).filter(SocialQuota.scope == f'message:user:{user["id"]}').one()
        quota.used = 200
        db.commit()
    assert send(full_client, headers, room).status_code == 429
    with website.SessionLocal() as db:
        assert db.query(SocialQuota).filter(SocialQuota.scope == 'message:global').one().used == 1


@pytest.mark.parametrize('text', ['   ', 'bad\x00text', 'x' * 1001])
def test_message_invalid_content(full_client, text):
    headers, _ = member(full_client, 'badmessage')
    assert send(full_client, headers, lobby(full_client, headers), text).status_code in {400, 422}


def test_muted_can_read_but_cannot_send_or_invite(full_client):
    headers, user = member(full_client, 'muteduser')
    room = lobby(full_client, headers)
    with website.SessionLocal() as db:
        db.get(User, user['id']).is_muted = True
        db.commit()
    assert full_client.get(room + '/messages', headers=headers).status_code == 200
    assert send(full_client, headers, room).status_code == 403
    assert full_client.post('/api/chat/direct', headers=headers, json={'user_id': 10}).status_code == 403
    assert full_client.post('/api/chat/groups', headers=headers, json={'name': 'bad'}).status_code == 403


def test_muted_recipient_can_still_decline_invitation(full_client):
    sender, _ = member(full_client, 'sender')
    recipient, user = member(full_client, 'recipient')
    room = '/api/chat/rooms/' + full_client.post('/api/chat/direct', headers=sender, json={'user_id': user['id']}).json()['id']
    with website.SessionLocal() as db:
        db.get(User, user['id']).is_muted = True
        db.commit()
    assert full_client.put(room + '/invitation', headers=recipient, json={'accept': True}).status_code == 403
    assert full_client.put(room + '/invitation', headers=recipient, json={'accept': False}).status_code == 200


def test_history_pagination_and_retention_do_not_touch_legacy_content(full_client):
    headers, user = member(full_client, 'historyuser')
    room = lobby(full_client, headers)
    with website.SessionLocal() as db:
        for i in range(60):
            db.add(ChatMessage(room_id=LOBBY, sender_id=user['id'], client_id=str(uuid.uuid4()), content=str(i)))
        db.add(ChatMessage(room_id=LOBBY, sender_id=user['id'], client_id=str(uuid.uuid4()), content='expired', created_at=datetime.utcnow() - timedelta(days=31)))
        db.commit()
    recent = full_client.get(room + '/messages', headers=headers).json()
    assert len(recent['items']) == 50 and recent['has_more'] and recent['items'][0]['content'] == '10'
    older = full_client.get(room + f'/messages?before_id={recent["items"][0]["id"]}', headers=headers).json()
    assert len(older['items']) == 10 and not older['has_more']
    assert send(full_client, headers, room).status_code == 200
    with website.SessionLocal() as db:
        assert not db.query(ChatMessage).filter(ChatMessage.content == 'expired').first()
        assert db.query(website.Novel1).count() == 1 and db.query(website.Profile).count() == 1
