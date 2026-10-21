import unicodedata
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, or_, func, String
from backend.models import Company, Contact, Lead, Opportunity, Task, User, Config, AuditEvent, now
from backend.config import settings
from backend.auth import lock_key

MODELS = {'companies': Company, 'contacts': Contact, 'leads': Lead,
          'opportunities': Opportunity, 'tasks': Task}
STAGE_LABELS = {'New': 'Baru', 'Qualification': 'Kualifikasi', 'Proposal': 'Proposal',
                'Negotiation': 'Negosiasi', 'Won': 'Berhasil', 'Lost': 'Gagal'}


def normalize_name(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def team_ids(db, user):
    return select(User.id).where(User.team == user.team)


def scope(db, user, model):
    if user.role == 'admin':
        return True
    if user.role == 'manager':
        return or_(model.owner_id.in_(team_ids(db, user)), model.assigned_id.in_(team_ids(db, user)))
    return or_(model.owner_id == user.id, model.assigned_id == user.id)


def visible(db, user, kind):
    model = MODELS[kind]
    rows = list(db.scalars(select(model).where(scope(db, user, model)).order_by(model.created_at, model.id)))
    preload_companies(db, rows)
    return rows


def preload_companies(db, rows):
    cache = db.info.setdefault('company_lookup', {})
    ids = {r.company_id for r in rows if isinstance(r, (Contact, Opportunity))}.difference(cache)
    if ids:
        cache.update({r.id: r for r in db.scalars(select(Company).where(Company.id.in_(ids)))})


def page_records(db, user, kind, offset=0, limit=50, query='', status=''):
    model = MODELS[kind]
    conditions = [scope(db, user, model)]
    if query:
        fields = [getattr(model, name) for name in ('name', 'title', 'email', 'company') if hasattr(model, name)]
        escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = '%' + escaped + '%'
        matches = [field.cast(String).ilike(pattern, escape='\\') for field in fields]
        companies = select(Company.id).where(Company.name.ilike(pattern, escape='\\'))
        if kind in ('contacts', 'opportunities'):
            matches.append(model.company_id.in_(companies))
        if kind in ('opportunities', 'tasks'):
            contacts = select(Contact.id).where(or_(Contact.name.ilike(pattern, escape='\\'), Contact.company_id.in_(companies)))
            matches.append(model.contact_id.in_(contacts))
        conditions.append(or_(*matches))
    if status and status != 'Semua':
        if kind == 'opportunities':
            reverse = {label: code for code, label in STAGE_LABELS.items()}
            conditions.append(model.stage == reverse.get(status, status))
        elif kind == 'leads':
            conditions.append(model.status == status)
        elif kind == 'tasks' and status in ('Aktif', 'Selesai'):
            conditions.append(model.done == (status == 'Selesai'))
    total = db.scalar(select(func.count()).select_from(model).where(*conditions))
    rows = list(db.scalars(select(model).where(*conditions).order_by(model.created_at.desc(), model.id)
                          .offset(offset).limit(limit)))
    preload_companies(db, rows)
    return rows, {'offset': offset, 'limit': limit, 'total': total, 'has_more': offset + len(rows) < total}


def get_record(db, user, kind, id, revision=None, lock=False):
    model = MODELS[kind]
    query = select(model).where(model.id == id, scope(db, user, model))
    if lock:
        query = query.with_for_update()
    record = db.scalar(query)
    if not record:
        raise HTTPException(404, 'Data tidak ditemukan atau tidak dapat diakses.')
    if revision is not None and record.revision != revision:
        raise HTTPException(409, 'Data telah berubah. Muat ulang sebelum menyimpan.')
    return record


def resolve_owner(db, actor, owner_id=None, assigned_id=None):
    owner_id = owner_id or actor.id
    if actor.role == 'sales' and (owner_id != actor.id or assigned_id not in (None, actor.id)):
        raise HTTPException(403, 'Sales tidak dapat menetapkan pemilik lain.')
    for id in [owner_id, assigned_id]:
        if id:
            target = db.get(User, id)
            if not target or not target.active:
                raise HTTPException(422, 'Pemilik/assignee harus pengguna aktif.')
            if actor.role == 'manager' and target.team != actor.team:
                raise HTTPException(403, 'Pengguna berada di luar tim Anda.')
    return owner_id, assigned_id


def json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def record_snapshot(record):
    return {c.name: json_value(getattr(record, c.name)) for c in record.__table__.columns
            if c.name not in ('normalized_name', 'normalized_email')}


def audit(db, actor, kind, record, action, old=None, new=None, metadata=None):
    owner = db.get(User, record.owner_id)
    db.add(AuditEvent(actor_id=actor.id, entity_type=kind, entity_id=record.id,
                      owner_id=record.owner_id, assigned_id=record.assigned_id, team=owner.team,
                      action=action, old_value=old, new_value=new,
                      details=metadata or {}))


def resolve_company(db, actor, name, owner, assigned=None):
    normalized = normalize_name(name)
    if not normalized or len(normalized)>200:
        raise HTTPException(422, 'Nama perusahaan setelah normalisasi harus 1-200 karakter.')
    lock_key(db, f'company:{owner}:{normalized}')
    company = db.scalar(select(Company).where(Company.owner_id == owner, Company.normalized_name == normalized))
    if company:
        return company
    company = Company(name=name.strip(), normalized_name=normalized, owner_id=owner, assigned_id=assigned)
    db.add(company)
    db.flush()
    audit(db, actor, 'companies', company, 'created', new=record_snapshot(company))
    return company


def duplicate_contact(db, owner, email, exclude=None):
    normalized = email.strip().casefold() or None
    if not normalized:
        return None
    lock_key(db, f'contact:{owner}:{normalized}')
    query = select(Contact).where(Contact.owner_id == owner, Contact.normalized_email == normalized)
    if exclude:
        query = query.where(Contact.id != exclude)
    return db.scalar(query)


def check_relation(db, actor, kind, id, owner, assigned=None):
    if not id:
        return None
    record = get_record(db, actor, kind, id, lock=True)
    if not {owner, assigned}.difference({None}).issubset({record.owner_id, record.assigned_id}):
        raise HTTPException(422, 'Berikan akses relasi kepada owner dan assignee terlebih dahulu.')
    return record


def validate_relations(db, actor, kind, values, owner, assigned=None):
    if kind == 'contacts':
        check_relation(db, actor, 'companies', values['company_id'], owner, assigned)
    if kind == 'opportunities':
        contact = check_relation(db, actor, 'contacts', values['contact_id'], owner, assigned)
        check_relation(db, actor, 'companies', contact.company_id, owner, assigned)
    if kind == 'leads' and values.get('converted_at'):
        check_relation(db, actor, 'contacts', values['contact_id'], owner, assigned)
        if values.get('opportunity_id'):
            check_relation(db, actor, 'opportunities', values['opportunity_id'], owner, assigned)
    if kind == 'tasks':
        task_relations(db, actor, values, owner, assigned)


def protect_dependants(db, kind, record, owner, assigned):
    """Do not revoke a parent grant that a child still needs; never widen grants implicitly."""
    relations = {
        'companies': [(Contact, 'company_id'), (Opportunity, 'company_id')],
        'contacts': [(Opportunity, 'contact_id'), (Task, 'contact_id'), (Lead, 'contact_id')],
        'opportunities': [(Task, 'opportunity_id'), (Lead, 'opportunity_id')],
        'leads': [(Task, 'lead_id')],
    }
    removed = {record.owner_id, record.assigned_id}.difference({owner, assigned, None})
    for model, field in relations.get(kind, []):
        if removed and db.scalar(select(model.id).where(getattr(model, field) == record.id,
                or_(model.owner_id.in_(removed), model.assigned_id.in_(removed))).limit(1)):
            raise HTTPException(409, 'Akses masih diperlukan record terkait. Ubah assignment record turunan dahulu.')


def close_deal(record, stage, reason):
    if stage == 'Lost' and not reason.strip():
        raise HTTPException(422, 'Alasan penutupan wajib diisi untuk deal Gagal.')
    old_stage = record.stage
    if stage in ('Won', 'Lost'):
        if old_stage != stage or not record.closed_at:
            record.closed_at = now()
        record.closing_reason = reason.strip()
    else:
        record.closed_at = None
        record.closing_reason = ''
    record.stage = stage


def privileged_reason(actor, record, reason, changes):
    if actor.id not in (record.owner_id, record.assigned_id) and changes and not reason.strip():
        raise HTTPException(422, 'Manager/Admin harus mencatat alasan perubahan nilai atau tahap.')


def create_record(db, actor, kind, payload):
    values = payload.model_dump()
    owner, assigned = resolve_owner(db, actor, values.pop('owner_id', None), values.pop('assigned_id', None))
    if kind == 'companies':
        if db.scalar(select(Company).where(Company.owner_id == owner,
                                         Company.normalized_name == normalize_name(values['name']))):
            raise HTTPException(409, 'Perusahaan dengan nama tersebut sudah ada untuk pemilik ini.')
        return resolve_company(db, actor, values['name'], owner, assigned)
    if kind == 'contacts':
        company = resolve_company(db, actor, values.pop('company'), owner, assigned)
        if duplicate_contact(db, owner, values['email']):
            raise HTTPException(409, 'Kontak dengan email tersebut sudah ada untuk pemilik ini.')
        values.update(company_id=company.id, normalized_email=values['email'].casefold() or None)
    if kind == 'opportunities':
        c = check_relation(db, actor, 'contacts', values['contact_id'], owner, assigned)
        check_relation(db, actor, 'companies', c.company_id, owner, assigned)
        values['company_id'] = c.company_id
        values.pop('change_reason')
        if values['stage'] == 'Lost' and not values['closing_reason'].strip():
            raise HTTPException(422, 'Alasan Gagal wajib diisi.')
        values['closed_at'] = now() if values['stage'] in ('Won', 'Lost') else None
        if not values['closed_at']:
            values['closing_reason'] = ''
    if kind == 'tasks':
        task_relations(db, actor, values, owner, assigned)
    if kind == 'contacts':
        validate_relations(db, actor, kind, values, owner, assigned)
    record = MODELS[kind](owner_id=owner, assigned_id=assigned, **values)
    db.add(record)
    db.flush()
    audit(db, actor, kind, record, 'created', new=record_snapshot(record))
    if kind == 'tasks' and record.done:
        complete_followup(db, actor, record)
    return record


def task_relations(db, actor, values, owner, assigned=None):
    for key, kind in [('contact_id', 'contacts'), ('lead_id', 'leads'), ('opportunity_id', 'opportunities')]:
        related = check_relation(db, actor, kind, values.get(key), owner, assigned)
        if related and kind in ('contacts', 'opportunities'):
            validate_relations(db, actor, kind, record_snapshot(related), owner, assigned)
    if values.get('opportunity_id') and values.get('contact_id'):
        deal = get_record(db, actor, 'opportunities', values['opportunity_id'])
        if deal.contact_id != values['contact_id']:
            raise HTTPException(422, 'Kontak tugas tidak cocok dengan opportunity.')


def complete_followup(db, actor, task):
    if task.opportunity_id:
        opportunity = get_record(db, actor, 'opportunities', task.opportunity_id, lock=True)
        opportunity.last_followup_at = now()
        opportunity.revision += 1
        audit(db, actor, 'opportunities', opportunity, 'followup',
              metadata={'task_id': task.id, 'note': task.title})


def update_record(db, actor, kind, id, payload, revision):
    record = get_record(db, actor, kind, id, revision, lock=True)
    values = payload.model_dump()
    # Ownership edits have their own audited command; never trust a generic form.
    if values.get('owner_id') not in (None, record.owner_id) or values.get('assigned_id') not in (None, record.assigned_id):
        raise HTTPException(422, 'Gunakan perintah perubahan owner/assignee.')
    values.pop('owner_id', None)
    values.pop('assigned_id', None)
    old = record_snapshot(record)
    if kind == 'leads' and record.status == 'Dikonversi':
        raise HTTPException(409, 'Lead yang sudah dikonversi tidak dapat diubah. Edit kontak/deal terkait.')
    if kind == 'companies':
        values['normalized_name'] = normalize_name(values['name'])
    if kind == 'contacts':
        company = resolve_company(db, actor, values.pop('company'), record.owner_id, record.assigned_id)
        if duplicate_contact(db, record.owner_id, values['email'], record.id):
            raise HTTPException(409, 'Email kontak sudah digunakan.')
        if company.id != record.company_id and db.scalar(select(Opportunity.id).where(Opportunity.contact_id == id)):
            raise HTTPException(409, 'Kontak terkait deal tidak dapat dipindahkan perusahaan.')
        values.update(company_id=company.id, normalized_email=values['email'].casefold() or None)
    if kind == 'opportunities':
        reason = values.pop('change_reason')
        privileged_reason(actor, record, reason, record.stage != values['stage'] or record.value != values['value']
                          or record.closing_reason != (values['closing_reason'].strip() if values['stage'] in ('Won', 'Lost') else ''))
        c = check_relation(db, actor, 'contacts', values['contact_id'], record.owner_id, record.assigned_id)
        check_relation(db, actor, 'companies', c.company_id, record.owner_id, record.assigned_id)
        values['company_id'] = c.company_id
        close_deal(record, values.pop('stage'), values.pop('closing_reason'))
    if kind == 'tasks':
        task_relations(db, actor, values, record.owner_id, record.assigned_id)
    if kind == 'contacts':
        validate_relations(db, actor, kind, values, record.owner_id, record.assigned_id)
    for key, value in values.items():
        setattr(record, key, value)
    record.revision += 1
    new = record_snapshot(record)
    audit(db, actor, kind, record, 'updated', old=old, new=new,
          metadata={'reason': reason} if kind == 'opportunities' else {})
    if kind == 'opportunities':
        audit_deal_changes(db, actor, record, old, new, reason)
    if kind == 'tasks' and record.done and not old['done']:
        complete_followup(db, actor, record)
    db.flush()
    return record


def audit_deal_changes(db, actor, record, old, new, reason=''):
    for field, action in [('stage', 'stage_changed'), ('value', 'value_changed'),
                          ('closing_reason', 'closing_reason_changed')]:
        changed = Decimal(old[field]) != Decimal(new[field]) if field == 'value' else old[field] != new[field]
        if changed:
            audit(db, actor, 'opportunities', record, action, {field: old[field]}, {field: new[field]},
                  {'reason': reason})
    if old['stage'] in ('Won', 'Lost') and new['stage'] not in ('Won', 'Lost'):
        audit(db, actor, 'opportunities', record, 'reopened', old, new, {'reason': reason})


def transition(db, actor, id, payload):
    record = get_record(db, actor, 'opportunities', id, payload.revision, lock=True)
    effective_reason = payload.closing_reason.strip() if payload.stage in ('Won', 'Lost') else ''
    changed = record.stage != payload.stage or record.closing_reason != effective_reason
    privileged_reason(actor, record, payload.change_reason, changed)
    if not changed:
        return record
    old = record_snapshot(record)
    close_deal(record, payload.stage, payload.closing_reason)
    record.revision += 1
    audit_deal_changes(db, actor, record, old, record_snapshot(record), payload.change_reason)
    db.flush()
    return record


def change_owner(db, actor, kind, id, payload):
    if actor.role == 'sales':
        raise HTTPException(403, 'Perubahan owner hanya untuk Manager/Admin.')
    record = get_record(db, actor, kind, id, payload.revision, lock=True)
    owner, assigned = resolve_owner(db, actor, payload.owner_id, payload.assigned_id)
    if not payload.owner_id:
        raise HTTPException(422, 'Owner wajib diisi.')
    if kind in ('companies', 'contacts') and owner != record.owner_id:
        raise HTTPException(409, 'Pemilik perusahaan/kontak tetap; gunakan assignee untuk kolaborasi.')
    validate_relations(db, actor, kind, record_snapshot(record), owner, assigned)
    protect_dependants(db, kind, record, owner, assigned)
    old = {'owner_id': record.owner_id, 'assigned_id': record.assigned_id}
    record.owner_id, record.assigned_id = owner, assigned
    record.revision += 1
    audit(db, actor, kind, record, 'owner_changed', old,
          {'owner_id': owner, 'assigned_id': assigned}, {'reason': payload.reason})
    db.flush()
    return record


def convert(db, actor, id, payload):
    lead = get_record(db, actor, 'leads', id, payload.revision, lock=True)
    if lead.converted_at:
        raise HTTPException(409, 'Lead sudah dikonversi.')
    if payload.create_opportunity and (not payload.title or not payload.due):
        raise HTTPException(422, 'Judul dan target tanggal diperlukan untuk membuat deal.')
    company = resolve_company(db, actor, lead.company, lead.owner_id, lead.assigned_id)
    check_relation(db, actor, 'companies', company.id, lead.owner_id, lead.assigned_id)
    contact = duplicate_contact(db, lead.owner_id, lead.email)
    if contact and contact.company_id != company.id:
        raise HTTPException(409, 'Email sudah terkait perusahaan lain. Periksa lead sebelum konversi.')
    if contact and actor.role == 'sales' and actor.id not in (contact.owner_id, contact.assigned_id):
        raise HTTPException(409, 'Kontak existing belum ditugaskan kepada Anda. Manager perlu memberi akses terlebih dahulu.')
    if not contact:
        contact = Contact(owner_id=lead.owner_id, assigned_id=lead.assigned_id, name=lead.name,
                          company_id=company.id, email=lead.email, normalized_email=lead.email.casefold() or None,
                          phone=lead.phone, role=lead.role)
        db.add(contact)
        db.flush()
        audit(db, actor, 'contacts', contact, 'created', new=record_snapshot(contact))
    check_relation(db, actor, 'contacts', contact.id, lead.owner_id, lead.assigned_id)
    opportunity = None
    if payload.create_opportunity:
        opportunity = Opportunity(owner_id=lead.owner_id, assigned_id=lead.assigned_id,
                                  company_id=company.id, contact_id=contact.id, title=payload.title,
                                  value=payload.value, stage='New', due=payload.due, notes=lead.notes)
        db.add(opportunity)
        db.flush()
        audit(db, actor, 'opportunities', opportunity, 'created', new=record_snapshot(opportunity))
    old = record_snapshot(lead)
    lead.status, lead.converted_at, lead.contact_id = 'Dikonversi', now(), contact.id
    lead.opportunity_id = opportunity.id if opportunity else None
    lead.revision += 1
    audit(db, actor, 'leads', lead, 'converted', old, record_snapshot(lead))
    db.flush()
    return {'contact_id': contact.id, 'company_id': company.id,
            'opportunity_id': opportunity.id if opportunity else None}


def today():
    return now().astimezone(ZoneInfo(settings().report_timezone)).date()


def at_risk(record, risk_days):
    return record.stage not in ('Won', 'Lost') and now() - (record.last_followup_at or record.created_at) >= timedelta(days=risk_days)


def config(db):
    item = db.get(Config, 1)
    if not item:
        raise HTTPException(503, 'Database belum diinisialisasi. Jalankan migrasi dan seed.')
    return item


def serialize(db, record, risk_days=14):
    result = record_snapshot(record)
    result['created'] = record.created_at.astimezone(ZoneInfo(settings().report_timezone)).date().isoformat()
    if isinstance(record, Contact):
        result['company'] = company_name(db, record.company_id)
    if isinstance(record, Opportunity):
        result.update(contact=record.contact_id, stage=STAGE_LABELS[record.stage], stage_code=record.stage,
                      value=float(record.value), closed=record.closed_at.astimezone(ZoneInfo(settings().report_timezone)).date().isoformat() if record.closed_at else '',
                      at_risk=at_risk(record, risk_days), company=company_name(db, record.company_id))
    if isinstance(record, Task):
        result.update(contact=record.contact_id or '', overdue=not record.done and record.date < today())
    return result


def company_name(db, id):
    cache = db.info.setdefault('company_lookup', {})
    if id not in cache:
        cache[id] = db.get(Company, id)
    return cache[id].name


def audit_list(db, user, limit=200):
    query = select(AuditEvent)
    if user.role == 'sales':
        query = query.where(or_(AuditEvent.owner_id == user.id, AuditEvent.assigned_id == user.id))
    elif user.role == 'manager':
        query = query.where(AuditEvent.team == user.team)
    events = db.scalars(query.order_by(AuditEvent.timestamp.desc(), AuditEvent.id).limit(limit))
    users = {u.id: u.name for u in db.scalars(select(User))}
    return [{'id': e.id, 'actor_id': e.actor_id, 'actor': users.get(e.actor_id, 'Pengguna'),
             'entity_type': e.entity_type, 'entity_id': e.entity_id, 'action': e.action,
             'date': e.timestamp.isoformat(), 'old_value': e.old_value, 'new_value': e.new_value,
             'metadata': e.details, 'text': f'{users.get(e.actor_id, "Pengguna")} · {e.action}: ' +
             str((e.new_value or e.old_value or {}).get('title') or
                 (e.new_value or e.old_value or {}).get('name') or e.details.get('note') or e.entity_type)} for e in events]


def dashboard(db, user, days):
    from backend.analytics import summary
    return summary(db, user, days)
