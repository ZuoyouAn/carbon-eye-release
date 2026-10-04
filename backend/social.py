"""Persistent avatars and membership-checked chat. No dependency on local disks."""
import base64
import binascii
from datetime import datetime, timedelta
import hashlib
from io import BytesIO
import uuid
import warnings

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, StrictBool
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from database import Base
from models import User
from permissions import permissions_for

LOBBY = 'public-lobby'


class UserAvatar(Base):
    __tablename__ = 'user_avatars'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    image = Column(LargeBinary, nullable=False)
    digest = Column(String(64), nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ChatRoom(Base):
    __tablename__ = 'chat_rooms'
    id = Column(String(36), primary_key=True)
    kind = Column(String(10), nullable=False)
    name = Column(String(40), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    pair_key = Column(String(80), unique=True, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ChatMember(Base):
    __tablename__ = 'chat_members'
    room_id = Column(String(36), ForeignKey('chat_rooms.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    status = Column(String(12), nullable=False)
    invited_by = Column(Integer, ForeignKey('users.id'), nullable=False)


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = (UniqueConstraint('room_id', 'sender_id', 'client_id', name='uq_chat_retry'), Index('ix_chat_room_id', 'room_id', 'id'))
    id = Column(Integer, primary_key=True)
    room_id = Column(String(36), ForeignKey('chat_rooms.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ChatBlock(Base):
    __tablename__ = 'chat_blocks'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    blocked_id = Column(Integer, ForeignKey('users.id'), primary_key=True)


class SocialQuota(Base):
    __tablename__ = 'social_quota'
    day = Column(String(10), primary_key=True)
    scope = Column(String(80), primary_key=True)
    used = Column(Integer, nullable=False, default=0)


class ChatThrottle(Base):
    __tablename__ = 'chat_throttle'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    last_sent_at = Column(DateTime, nullable=False)


class AvatarRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    image_base64: str = Field(max_length=350000, min_length=4)


class TargetRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    user_id: int = Field(gt=0)


class GroupRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    name: str = Field(min_length=1, max_length=40)
    user_ids: list[int] = Field(default_factory=list, max_length=11)


class DecisionRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    accept: StrictBool


class SendRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    content: str = Field(min_length=1, max_length=1000)
    client_id: uuid.UUID


def upsert(db, model, values):
    insert = {'sqlite': sqlite_insert, 'postgresql': pg_insert}.get(db.bind.dialect.name)
    if not insert:
        raise HTTPException(503, '此功能需要持久化PostgreSQL或本地测试SQLite')
    db.execute(insert(model).values(**values).on_conflict_do_nothing())


def quota(db, action, user_id, limit, global_limit):
    day = datetime.utcnow().date().isoformat()
    for scope, maximum in ((action + ':global', global_limit), (f'{action}:user:{user_id}', limit)):
        upsert(db, SocialQuota, {'day': day, 'scope': scope, 'used': 0})
        result = db.execute(update(SocialQuota).where(SocialQuota.day == day, SocialQuota.scope == scope, SocialQuota.used < maximum).values(used=SocialQuota.used + 1))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(429, '今日操作次数已达上限，请明天再试')


def normalize_avatar(encoded):
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 256 * 1024:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw), formats=['JPEG', 'PNG', 'WEBP']) as image:
                if image.width * image.height > 4_000_000 or image.width < 1 or image.height < 1 or getattr(image, 'is_animated', False):
                    raise ValueError()
                image.load()
                normalized = ImageOps.fit(ImageOps.exif_transpose(image).convert('RGB'), (128, 128), method=Image.Resampling.LANCZOS)
                output = BytesIO()
                normalized.save(output, format='WEBP', quality=80)
        result = output.getvalue()
        if len(result) > 32768:
            raise ValueError()
        return result
    except (ValueError, OSError, SyntaxError, binascii.Error, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(400, '请上传有效的静态JPEG、PNG或WebP头像；压缩图片需小于256KB且不超过400万像素。') from None


def person(user):
    return {'id': user.id, 'username': user.username, 'avatar_path': f'/api/users/{user.id}/avatar'}


def blocked(db, a, b):
    return db.query(ChatBlock).filter(or_(
        (ChatBlock.user_id == a) & (ChatBlock.blocked_id == b),
        (ChatBlock.user_id == b) & (ChatBlock.blocked_id == a),
    )).first() is not None


def target_user(db, target_id, actor):
    target = db.query(User).filter(User.id == target_id, User.is_deleted == False).first()
    if not target or target.id == actor.id:
        raise HTTPException(400, '请选择其他正常用户')
    if blocked(db, actor.id, target.id):
        raise HTTPException(403, '你们之间的私聊或邀请已关闭')
    return target


def room_access(db, room_id, user, pending=False, lock=False):
    query = db.query(ChatRoom).filter(ChatRoom.id == room_id)
    room = (query.with_for_update() if lock else query).first()
    if not room:
        raise HTTPException(404, '会话不存在或你无权访问')
    if room.kind == 'public':
        return room, None
    member = db.get(ChatMember, (room_id, user.id))
    if not member or member.status not in (('accepted', 'invited') if pending else ('accepted',)):
        raise HTTPException(404, '会话不存在或你无权访问')
    return room, member


def require_chat(user):
    if 'chat' not in permissions_for(user.role, user.is_muted):
        raise HTTPException(403, '当前账号只能阅读聊天，不能发送或发起邀请')


def message_json(row, user, room):
    message, author = row
    return {'id': message.id, 'sender': person(author), 'content': '' if message.is_deleted else message.content, 'is_deleted': message.is_deleted, 'created_at': message.created_at.isoformat() + 'Z', 'can_retract': not message.is_deleted and (message.sender_id == user.id or (room.kind == 'public' and 'manage_content' in permissions_for(user.role, user.is_muted)))}


def make_router(get_db, get_current_user):
    router = APIRouter(prefix='/api', tags=['space-social'])

    @router.get('/users/{user_id}/avatar')
    def avatar(user_id: int, db=Depends(get_db), if_none_match: str | None = Header(default=None)):
        row = db.query(UserAvatar).join(User, User.id == UserAvatar.user_id).filter(UserAvatar.user_id == user_id, User.is_deleted == False).first()
        if not row:
            raise HTTPException(404, '暂无头像')
        etag = '"' + row.digest + '"'
        headers = {'ETag': etag, 'Cache-Control': 'public, max-age=0, must-revalidate', 'X-Content-Type-Options': 'nosniff'}
        return Response(status_code=304, headers=headers) if if_none_match == etag else Response(content=row.image, media_type='image/webp', headers=headers)

    @router.put('/me/avatar')
    def upload_avatar(data: AvatarRequest, user=Depends(get_current_user), db=Depends(get_db)):
        image = normalize_avatar(data.image_base64)
        quota(db, 'avatar', user.id, 10, 100)
        digest = hashlib.sha256(image).hexdigest()
        row = db.get(UserAvatar, user.id)
        if row:
            row.image, row.digest, row.updated_at = image, digest, datetime.utcnow()
        else:
            db.add(UserAvatar(user_id=user.id, image=image, digest=digest, updated_at=datetime.utcnow()))
        db.commit()
        return {'avatar_path': f'/api/users/{user.id}/avatar', 'version': digest}

    @router.delete('/me/avatar')
    def remove_avatar(user=Depends(get_current_user), db=Depends(get_db)):
        db.execute(delete(UserAvatar).where(UserAvatar.user_id == user.id))
        db.commit()
        return {'message': '头像已移除'}

    @router.get('/chat/users')
    def find_users(q: str = Query(default='', max_length=30), user=Depends(get_current_user), db=Depends(get_db)):
        if len(q.strip()) < 2:
            return []
        users = db.query(User).filter(User.is_deleted == False, User.id != user.id, User.username.contains(q.strip(), autoescape=True)).order_by(User.username).limit(20).all()
        return [person(target) for target in users if not blocked(db, user.id, target.id)]

    @router.get('/chat/rooms')
    def rooms(user=Depends(get_current_user), db=Depends(get_db)):
        if not db.get(ChatRoom, LOBBY):
            upsert(db, ChatRoom, {'id': LOBBY, 'kind': 'public', 'name': 'Space公共大厅'})
            db.commit()
        own = db.query(ChatRoom, ChatMember).join(ChatMember, ChatMember.room_id == ChatRoom.id).filter(ChatMember.user_id == user.id, ChatMember.status.in_(['accepted', 'invited'])).order_by(ChatRoom.created_at.desc()).limit(50).all()
        direct_ids = [room.id for room, _ in own if room.kind == 'direct']
        peers = {}
        if direct_ids:
            participants = db.query(User, ChatMember).join(ChatMember, ChatMember.user_id == User.id).filter(ChatMember.room_id.in_(direct_ids), User.id != user.id).all()
            peers = {membership.room_id: (person, membership) for person, membership in participants}
        block_rows = db.query(ChatBlock).filter(or_(ChatBlock.user_id == user.id, ChatBlock.blocked_id == user.id)).all()
        blocked_ids = {row.blocked_id if row.user_id == user.id else row.user_id for row in block_rows}
        result = [{'id': LOBBY, 'name': 'Space公共大厅', 'kind': 'public', 'status': 'accepted', 'owner_id': None, 'send_state': 'ready'}]
        for room, membership in own:
            name = room.name
            other_id = None
            send_state = 'ready' if membership.status == 'accepted' else 'pending'
            if room.kind == 'direct':
                other, peer_member = peers.get(room.id, (None, None))
                name = other.username if other and not other.is_deleted else '已注销用户'
                other_id = other.id if other else None
                if not other or other.is_deleted or not peer_member or peer_member.status in ('declined', 'left'):
                    send_state = 'closed'
                elif peer_member.status != 'accepted' or membership.status != 'accepted':
                    send_state = 'pending'
                if other_id in blocked_ids:
                    send_state = 'blocked'
            result.append({'id': room.id, 'name': name, 'kind': room.kind, 'status': membership.status, 'owner_id': room.owner_id, 'other_id': other_id, 'blocked': other_id in blocked_ids, 'send_state': send_state})
        return result

    @router.post('/chat/direct')
    def direct(data: TargetRequest, user=Depends(get_current_user), db=Depends(get_db)):
        require_chat(user)
        target = target_user(db, data.user_id, user)
        key = ':'.join(map(str, sorted([user.id, target.id])))
        existing = db.query(ChatRoom).filter(ChatRoom.pair_key == key).first()
        if existing:
            _, member = room_access(db, existing.id, user, pending=True)
            peer = db.get(ChatMember, (existing.id, target.id))
            if not peer or peer.status not in ('accepted', 'invited'):
                raise HTTPException(409, '对方已拒绝或退出，本版本不重复邀请')
            return {'id': existing.id, 'status': member.status}
        quota(db, 'invite', user.id, 5, 100)
        room = ChatRoom(id=str(uuid.uuid4()), kind='direct', name='私聊', owner_id=user.id, pair_key=key)
        try:
            db.add(room)
            db.flush()
            db.add_all([ChatMember(room_id=room.id, user_id=user.id, status='accepted', invited_by=user.id), ChatMember(room_id=room.id, user_id=target.id, status='invited', invited_by=user.id)])
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.query(ChatRoom).filter(ChatRoom.pair_key == key).first()
            if not existing:
                raise HTTPException(409, '邀请冲突，请重试') from None
            _, member = room_access(db, existing.id, user, pending=True)
            return {'id': existing.id, 'status': member.status}
        return {'id': room.id, 'status': 'accepted'}

    @router.post('/chat/groups')
    def group(data: GroupRequest, user=Depends(get_current_user), db=Depends(get_db)):
        require_chat(user)
        if 'publish' not in permissions_for(user.role, user.is_muted):
            raise HTTPException(403, '高权限用户或管理员可以创建小群')
        name = data.name.strip()
        if not name:
            raise HTTPException(400, '群名称不能为空')
        ids = sorted(set(data.user_ids) - {user.id})
        for target in ids:
            target_user(db, target, user)
        quota(db, 'group', user.id, 2, 20)
        quota(db, 'invite', user.id, 5, 100)
        room = ChatRoom(id=str(uuid.uuid4()), kind='group', name=name, owner_id=user.id)
        db.add(room)
        db.flush()
        db.add(ChatMember(room_id=room.id, user_id=user.id, status='accepted', invited_by=user.id))
        for target in ids:
            db.add(ChatMember(room_id=room.id, user_id=target, status='invited', invited_by=user.id))
        db.commit()
        return {'id': room.id}

    @router.post('/chat/rooms/{room_id}/invite')
    def invite(room_id: str, data: TargetRequest, user=Depends(get_current_user), db=Depends(get_db)):
        require_chat(user)
        room, _ = room_access(db, room_id, user, lock=True)
        if room.kind != 'group' or room.owner_id != user.id:
            raise HTTPException(403, '只有群主可以邀请成员')
        target = target_user(db, data.user_id, user)
        count = db.query(ChatMember).filter(ChatMember.room_id == room_id, ChatMember.status.in_(['accepted', 'invited'])).count()
        if count >= 12:
            raise HTTPException(400, '每群最多12人（含待接受邀请）')
        if db.get(ChatMember, (room_id, target.id)):
            raise HTTPException(409, '此用户已参加、已受邀或已退出；本版本不重复邀请')
        quota(db, 'invite', user.id, 5, 100)
        db.add(ChatMember(room_id=room_id, user_id=target.id, status='invited', invited_by=user.id))
        db.commit()
        return {'message': '邀请已发出，对方接受后才能阅读群内消息'}

    @router.put('/chat/rooms/{room_id}/invitation')
    def decide(room_id: str, data: DecisionRequest, user=Depends(get_current_user), db=Depends(get_db)):
        if data.accept:
            require_chat(user)
        room, member = room_access(db, room_id, user, pending=True, lock=True)
        if not member or member.status != 'invited':
            raise HTTPException(400, '没有待处理邀请')
        if data.accept and blocked(db, user.id, member.invited_by):
            raise HTTPException(403, '邀请已关闭')
        member.status = 'accepted' if data.accept else 'declined'
        db.commit()
        return {'status': member.status}

    @router.delete('/chat/rooms/{room_id}/membership')
    def leave(room_id: str, user=Depends(get_current_user), db=Depends(get_db)):
        room, member = room_access(db, room_id, user, pending=True, lock=True)
        if not member or room.kind == 'public':
            raise HTTPException(400, '公共大厅无需退出成员关系')
        member.status = 'left'
        db.commit()
        return {'message': '已退出，不能再读取该会话'}

    @router.get('/chat/rooms/{room_id}/members')
    def members(room_id: str, user=Depends(get_current_user), db=Depends(get_db)):
        room, _ = room_access(db, room_id, user)
        if room.kind == 'public':
            return []
        rows = db.query(User, ChatMember).join(ChatMember, ChatMember.user_id == User.id).filter(ChatMember.room_id == room_id, ChatMember.status.in_(['accepted', 'invited'])).all()
        return [{**person(target), 'status': member.status} for target, member in rows]

    @router.get('/chat/rooms/{room_id}/messages')
    def history(room_id: str, before_id: int = Query(default=0, ge=0), user=Depends(get_current_user), db=Depends(get_db)):
        room, _ = room_access(db, room_id, user)
        query = db.query(ChatMessage, User).join(User, User.id == ChatMessage.sender_id).filter(ChatMessage.room_id == room_id, ChatMessage.created_at >= datetime.utcnow() - timedelta(days=30))
        if before_id:
            query = query.filter(ChatMessage.id < before_id)
        rows = query.order_by(ChatMessage.id.desc()).limit(51).all()
        return {'items': [message_json(row, user, room) for row in reversed(rows[:50])], 'has_more': len(rows) > 50}

    @router.post('/chat/rooms/{room_id}/messages')
    def send(room_id: str, data: SendRequest, user=Depends(get_current_user), db=Depends(get_db)):
        require_chat(user)
        room, _ = room_access(db, room_id, user, lock=True)
        members = db.query(ChatMember).filter(ChatMember.room_id == room_id).all() if room.kind != 'public' else []
        if room.kind == 'direct':
            if len(members) != 2 or any(m.status != 'accepted' for m in members):
                raise HTTPException(403, '对方尚未接受邀请或已退出')
            other_id = next(m.user_id for m in members if m.user_id != user.id)
            target_user(db, other_id, user)
        content = data.content.strip()
        if not content or any(ord(c) < 32 and c not in '\n\t' for c in content):
            raise HTTPException(400, '请输入有效文本消息')
        client_id = str(data.client_id)
        previous = db.query(ChatMessage).filter(ChatMessage.room_id == room_id, ChatMessage.sender_id == user.id, ChatMessage.client_id == client_id).first()
        if previous:
            return {'id': previous.id, 'duplicate': True}
        quota(db, 'message', user.id, 200, 1000)
        now = datetime.utcnow()
        upsert(db, ChatThrottle, {'user_id': user.id, 'last_sent_at': now - timedelta(days=1)})
        result = db.execute(update(ChatThrottle).where(ChatThrottle.user_id == user.id, ChatThrottle.last_sent_at <= now - timedelta(seconds=3)).values(last_sent_at=now))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(429, '请间隔至少3秒发送消息')
        # Only new chat data has a disclosed 30-day retention policy, never legacy posts/messages.
        db.execute(delete(ChatMessage).where(ChatMessage.created_at < now - timedelta(days=30)))
        db.execute(delete(SocialQuota).where(SocialQuota.day < (now - timedelta(days=35)).date().isoformat()))
        row = ChatMessage(room_id=room_id, sender_id=user.id, client_id=client_id, content=content)
        db.add(row)
        db.commit()
        return {'id': row.id, 'duplicate': False}

    @router.delete('/chat/rooms/{room_id}/messages/{message_id}')
    def retract(room_id: str, message_id: int, user=Depends(get_current_user), db=Depends(get_db)):
        room, _ = room_access(db, room_id, user, lock=True)
        row = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.room_id == room_id).first()
        if not row:
            raise HTTPException(404, '消息不存在')
        if row.sender_id != user.id and not (room.kind == 'public' and 'manage_content' in permissions_for(user.role, user.is_muted)):
            raise HTTPException(403, '不能撤回他人的消息')
        row.is_deleted, row.content = True, ''
        db.commit()
        return {'message': '消息已撤回'}

    @router.get('/chat/blocks')
    def blocks(user=Depends(get_current_user), db=Depends(get_db)):
        rows = db.query(User).join(ChatBlock, ChatBlock.blocked_id == User.id).filter(ChatBlock.user_id == user.id).all()
        return [person(target) for target in rows]

    @router.put('/chat/blocks/{target_id}')
    def block(target_id: int, user=Depends(get_current_user), db=Depends(get_db)):
        if target_id == user.id or not db.get(User, target_id):
            raise HTTPException(400, '无效用户')
        # Serialize with direct sends: after this commits no new private message
        # can pass the bilateral block check using an earlier room transaction.
        key = ':'.join(map(str, sorted([user.id, target_id])))
        db.query(ChatRoom).filter(ChatRoom.pair_key == key).with_for_update().first()
        upsert(db, ChatBlock, {'user_id': user.id, 'blocked_id': target_id})
        db.commit()
        return {'message': '已关闭双方的私聊和新邀请；公共群内仍可能遇见对方'}

    @router.delete('/chat/blocks/{target_id}')
    def unblock(target_id: int, user=Depends(get_current_user), db=Depends(get_db)):
        db.execute(delete(ChatBlock).where(ChatBlock.user_id == user.id, ChatBlock.blocked_id == target_id))
        db.commit()
        return {'message': '已解除拉黑'}

    return router
