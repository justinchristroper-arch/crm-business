from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session as DB
from backend import schemas as S, services as svc
from backend.auth import current_user, admin_user, user_view, login, origin_check, hasher, COOKIE
from backend.config import settings
from backend.db import get_db
from backend.models import User, Session, AuditEvent, Config, now

ROOT = Path(__file__).resolve().parents[1]


def create_app():
    app = FastAPI(title='CRM Business API', version='2.0.0', docs_url='/api/docs',
                  openapi_url='/api/openapi.json', redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=settings().allowed_origins,
                       allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                       allow_headers=['Content-Type', 'X-CSRF-Token'])

    @app.middleware('http')
    async def headers(request, call_next):
        try:
            length = int(request.headers.get('content-length', '0') or 0)
        except ValueError:
            return JSONResponse({'detail': 'Content-Length tidak valid.'}, status_code=400)
        if length > 5_000_000:
            return JSONResponse({'detail': 'Payload maksimal 5 MB.'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path == '/api/docs':
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
            )
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({'detail': 'Konflik data: duplikat atau record masih terkait data lain.'}, 409)

    @app.exception_handler(OperationalError)
    async def unavailable(request, exc):
        return JSONResponse({'detail': 'Database tidak tersedia. Silakan coba lagi.'}, 503)

    @app.get('/api/health')
    def health(db: DB = Depends(get_db)):
        # No credentials, table counts, or internal connection details in health responses.
        db.execute(select(1))
        return {'status': 'ok'}

    @app.post('/api/auth/login')
    def login_route(payload: S.Login, request: Request, response: Response, db: DB = Depends(get_db)):
        origin_check(request)
        user, session, token = login(db, payload.email, payload.password, request)
        response.set_cookie(COOKIE, token, httponly=True, secure=settings().cookie_secure,
                            samesite='strict', max_age=8*3600, path='/')
        return {'user': user_view(user), 'csrf': session.csrf}

    @app.get('/api/auth/demo')
    def demo_info():
        return {'available': settings().demo_mode and settings().demo_password == 'PortfolioDemo!2026'}

    @app.get('/api/auth/me')
    def me(request: Request, user: User = Depends(current_user)):
        return {'user': user_view(user), 'csrf': request.state.auth_session.csrf,
                'demo_mode': settings().demo_mode, 'demo_reset': settings().enable_demo_reset}

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response, user: User = Depends(current_user), db: DB = Depends(get_db)):
        request.state.auth_session.revoked = True
        db.commit()
        response.delete_cookie(COOKIE, path='/')
        return {'ok': True}

    @app.get('/api/users')
    def users(user: User = Depends(current_user), db: DB = Depends(get_db)):
        query = select(User).order_by(User.name)
        if user.role == 'sales':
            query = query.where(User.id == user.id)
        elif user.role == 'manager':
            query = query.where(User.team == user.team)
        return [user_view(u) for u in db.scalars(query)]

    def user_audit(db, actor, target, action, old=None, new=None):
        db.add(AuditEvent(actor_id=actor.id, owner_id=target.id, entity_type='users',
                          entity_id=target.id, team=target.team, action=action, old_value=old, new_value=new))

    @app.post('/api/users', status_code=201)
    def create_user(payload: S.UserCreate, actor: User = Depends(admin_user), db: DB = Depends(get_db)):
        target = User(name=payload.name, email=str(payload.email).casefold(), role=payload.role,
                      team=payload.team, password_hash=hasher.hash(payload.password))
        db.add(target)
        db.flush()
        user_audit(db, actor, target, 'user_created', new=user_view(target))
        db.commit()
        return user_view(target)

    @app.patch('/api/users/{id}')
    def update_user(id: str, payload: S.UserUpdate, actor: User = Depends(admin_user), db: DB = Depends(get_db)):
        target = db.scalar(select(User).where(User.id == id).with_for_update())
        if not target:
            raise HTTPException(404, 'Pengguna tidak ditemukan.')
        values = payload.model_dump(exclude_unset=True)
        if not values or any(v is None for v in values.values()):
            raise HTTPException(422, 'Perubahan pengguna tidak valid.')
        if id == actor.id and (values.get('active') is False or values.get('role', 'admin') != 'admin'):
            raise HTTPException(409, 'Admin tidak dapat menonaktifkan atau menurunkan role dirinya sendiri.')
        old = user_view(target)
        if 'password' in values:
            target.password_hash = hasher.hash(values.pop('password'))
        for key, value in values.items():
            setattr(target, key, value)
        for session in db.scalars(select(Session).where(Session.user_id == id)):
            session.revoked = True
        user_audit(db, actor, target, 'user_updated', old, user_view(target))
        db.commit()
        return user_view(target)

    @app.get('/api/config')
    def read_config(user: User = Depends(current_user), db: DB = Depends(get_db)):
        c = svc.config(db)
        return {'workspace': c.workspace, 'risk_days': c.risk_days}

    @app.put('/api/config')
    def update_config(payload: S.ConfigInput, user: User = Depends(admin_user), db: DB = Depends(get_db)):
        c = db.get(Config, 1)
        old = {'workspace': c.workspace, 'risk_days': c.risk_days}
        c.workspace, c.risk_days = payload.workspace, payload.risk_days
        db.add(AuditEvent(actor_id=user.id, owner_id=user.id, entity_type='config', entity_id='1',
                          team=user.team, action='config_updated', old_value=old, new_value=payload.model_dump()))
        db.commit()
        return payload.model_dump()

    @app.get('/api/dashboard')
    def dashboard(days: int = Query(30, ge=1, le=365), user: User = Depends(current_user), db: DB = Depends(get_db)):
        return svc.dashboard(db, user, days)

    @app.get('/api/activities')
    def activities(limit: int = Query(200, ge=1, le=500), user: User = Depends(current_user), db: DB = Depends(get_db)):
        return svc.audit_list(db, user, limit)

    @app.post('/api/activities', status_code=201)
    def followup(payload: S.FollowupInput, user: User = Depends(current_user), db: DB = Depends(get_db)):
        record = svc.get_record(db, user, payload.entity_type, payload.entity_id, lock=True)
        if payload.entity_type == 'opportunities':
            record.last_followup_at = now()
            record.revision += 1
        svc.audit(db, user, payload.entity_type, record, 'followup', metadata={'note': payload.note})
        db.commit()
        return {'ok': True}

    @app.get('/api/workspace')
    def workspace(days: int = Query(30, ge=1, le=365), user: User = Depends(current_user), db: DB = Depends(get_db)):
        # All reads use the same authenticated user and server-side visibility rules.
        c = svc.config(db)
        users = select(User)
        if user.role == 'sales':
            users = users.where(User.id == user.id)
        elif user.role == 'manager':
            users = users.where(User.team == user.team)
        data = {'version': 2, 'workspace': c.workspace, 'risk_days': c.risk_days,
                'user': user_view(user), 'users': [user_view(u) for u in db.scalars(users)],
                'analytics': svc.dashboard(db, user, days), 'activities': svc.audit_list(db, user)}
        for kind in svc.MODELS:
            data['deals' if kind == 'opportunities' else kind] = [svc.serialize(db, r, c.risk_days) for r in svc.visible(db, user, kind)]
        return data

    @app.post('/api/leads/{id}/convert')
    def convert(id: str, payload: S.ConvertInput, user: User = Depends(current_user), db: DB = Depends(get_db)):
        result = svc.convert(db, user, id, payload)
        db.commit()
        return result

    @app.post('/api/opportunities/{id}/stage')
    def stage(id: str, payload: S.StageInput, user: User = Depends(current_user), db: DB = Depends(get_db)):
        record = svc.transition(db, user, id, payload)
        db.commit()
        return svc.serialize(db, record, svc.config(db).risk_days)

    # Typed resource routes: no user-supplied model/table names or arbitrary fields.
    def resource_routes(kind, schema):
        def list_records(user: User = Depends(current_user), db: DB = Depends(get_db)):
            return [svc.serialize(db, r, svc.config(db).risk_days) for r in svc.visible(db, user, kind)]

        def read_record(id: str, user: User = Depends(current_user), db: DB = Depends(get_db)):
            return svc.serialize(db, svc.get_record(db, user, kind, id), svc.config(db).risk_days)

        def create(payload, user: User = Depends(current_user), db: DB = Depends(get_db)):
            record = svc.create_record(db, user, kind, payload)
            db.commit()
            return svc.serialize(db, record, svc.config(db).risk_days)

        def update(id: str, payload, revision: int = Query(..., ge=1), user: User = Depends(current_user), db: DB = Depends(get_db)):
            record = svc.update_record(db, user, kind, id, payload, revision)
            db.commit()
            return svc.serialize(db, record, svc.config(db).risk_days)

        def remove(id: str, revision: int = Query(..., ge=1), user: User = Depends(current_user), db: DB = Depends(get_db)):
            record = svc.get_record(db, user, kind, id, revision, lock=True)
            if kind == 'opportunities':
                raise HTTPException(409, 'Opportunity tetap disimpan untuk riwayat penjualan. Gunakan tahap Gagal dengan alasan.')
            if kind == 'leads' and record.converted_at:
                raise HTTPException(409, 'Lead dikonversi tetap disimpan untuk analitik.')
            svc.audit(db, user, kind, record, 'deleted', old=svc.record_snapshot(record))
            db.delete(record)
            db.commit()
            return {'ok': True}

        def owner(id: str, payload: S.OwnerChange, user: User = Depends(current_user), db: DB = Depends(get_db)):
            record = svc.change_owner(db, user, kind, id, payload)
            db.commit()
            return svc.serialize(db, record, svc.config(db).risk_days)

        create.__annotations__['payload'] = schema
        update.__annotations__['payload'] = schema
        for path, endpoint, methods, status in [('', list_records, ['GET'], 200), ('', create, ['POST'], 201),
                ('/{id}', read_record, ['GET'], 200), ('/{id}', update, ['PUT'], 200),
                ('/{id}', remove, ['DELETE'], 200), ('/{id}/owner', owner, ['POST'], 200)]:
            app.add_api_route('/api/'+kind+path, endpoint, methods=methods, status_code=status,
                              name=f'{kind}_{endpoint.__name__}', tags=[kind])

    for kind, schema in [('companies', S.CompanyInput), ('contacts', S.ContactInput), ('leads', S.LeadInput),
                         ('opportunities', S.OpportunityInput), ('tasks', S.TaskInput)]:
        resource_routes(kind, schema)

    @app.get('/api/backup')
    def backup(user: User = Depends(current_user), db: DB = Depends(get_db)):
        c = svc.config(db)
        result = {'version': 2, 'format': 'crm-business-v2', 'workspace': c.workspace,
                  'exported_at': now().isoformat(), 'risk_days': c.risk_days}
        for kind in svc.MODELS:
            result['deals' if kind == 'opportunities' else kind] = [svc.serialize(db, r, c.risk_days) for r in svc.visible(db, user, kind)]
        # Audit is exported for inspection only and cannot be restored/forged through import.
        result['audit_read_only'] = svc.audit_list(db, user, 500)
        return result

    @app.post('/api/backup/import')
    def import_backup(payload: dict, user: User = Depends(admin_user), db: DB = Depends(get_db)):
        from backend.backup import import_records
        result = import_records(db, user, payload)
        db.commit()
        return result

    @app.post('/api/demo/reset')
    def reset(user: User = Depends(admin_user), db: DB = Depends(get_db)):
        if not settings().demo_mode or not settings().enable_demo_reset:
            raise HTTPException(403, 'Reset demo dinonaktifkan pada lingkungan ini.')
        from backend.seed import reset_demo_records
        reset_demo_records(db, user)
        db.commit()
        return {'ok': True}

    @app.get('/')
    def index():
        return FileResponse(ROOT / 'dist/index.html')

    @app.get('/api/{unknown:path}', include_in_schema=False)
    def unknown(unknown: str):
        raise HTTPException(404, 'Endpoint API tidak ditemukan.')

    app.mount('/', StaticFiles(directory=ROOT/'dist'), name='frontend')
    return app


app = create_app()
