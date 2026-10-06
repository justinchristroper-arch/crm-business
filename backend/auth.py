import hashlib
import hmac
import secrets
from datetime import timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session as DB
from backend.config import settings
from backend.db import get_db
from backend.models import User, Session, LoginAttempt, now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash('not-a-user-' + secrets.token_hex(12))
COOKIE = 'crm_session'


def lock_key(db, key):
    number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': number})


def origin_check(request):
    origin = request.headers.get('origin')
    if origin and origin.rstrip('/') not in settings().allowed_origins:
        raise HTTPException(403, 'Origin tidak diizinkan.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Permintaan lintas situs ditolak.')


def login(db, email, password, request):
    email = str(email).casefold().strip()
    key = hashlib.sha256((email + ':' + request.client.host).encode()).hexdigest()
    lock_key(db, 'login:' + key)
    attempt = db.get(LoginAttempt, key)
    current = now()
    if attempt and attempt.blocked_until and attempt.blocked_until > current:
        raise HTTPException(429, 'Terlalu banyak percobaan. Coba lagi setelah 15 menit.')
    user = db.scalar(select(User).where(User.email == email))
    valid = False
    try:
        valid = hasher.verify(user.password_hash if user else DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        pass
    if not user or not valid or not user.active:
        if not attempt:
            attempt = LoginAttempt(key=key, attempts=0)
            db.add(attempt)
        if attempt.updated_at and current - attempt.updated_at > timedelta(minutes=15):
            attempt.attempts = 0
        attempt.attempts += 1
        attempt.updated_at = current
        attempt.blocked_until = current + timedelta(minutes=15) if attempt.attempts >= 8 else None
        db.commit()
        raise HTTPException(401, 'Email atau password salah.')
    if attempt:
        db.delete(attempt)
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(password)
    session = Session(user_id=user.id, csrf=secrets.token_urlsafe(32), expires_at=current + timedelta(hours=8))
    db.add(session)
    db.flush()
    token = jwt.encode({'sub': user.id, 'jti': session.id, 'iat': current,
                        'exp': session.expires_at, 'iss': 'crm-business', 'aud': 'crm-web'},
                       settings().jwt_secret, algorithm='HS256')
    db.commit()
    return user, session, token


def current_user(request: Request, db: DB = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    try:
        claims = jwt.decode(token or '', settings().jwt_secret, algorithms=['HS256'],
                            issuer='crm-business', audience='crm-web',
                            options={'require': ['exp', 'iat', 'sub', 'jti']})
    except jwt.InvalidTokenError:
        raise HTTPException(401, 'Silakan masuk kembali.') from None
    session = db.get(Session, claims['jti'])
    user = db.get(User, claims['sub'])
    if not session or session.revoked or session.expires_at <= now() or not user or not user.active:
        raise HTTPException(401, 'Sesi tidak aktif.')
    if session.user_id != user.id:
        raise HTTPException(401, 'Sesi tidak valid.')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin_check(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf):
            raise HTTPException(403, 'Token CSRF tidak valid. Muat ulang halaman.')
    request.state.auth_session = session
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Hanya Admin yang dapat melakukan tindakan ini.')
    return user


def user_view(user):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role,
            'team': user.team, 'active': user.active, 'demo': user.demo}
