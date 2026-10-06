import unicodedata
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, or_
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
    return list(db.scalars(select(model).where(scope(db, user, model)).order_by(model.created_at)))


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


def check_relation(db, actor, kind, id, owner):
    if not id:
        return None
    record = get_record(db, actor, kind, id)
    if owner not in (record.owner_id, record.assigned_id):
        raise HTTPException(422, 'Relasi harus dapat diakses pemilik record.')
    return record


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
    if kind == 'leads':
        values.pop('phone', None)
        values.pop('role', None)
    if kind == 'opportunities':
        c = check_relation(db, actor, 'contacts', values['contact_id'], owner)
        check_relation(db, actor, 'companies', c.company_id, owner)
        values['company_id'] = c.company_id
        values.pop('change_reason')
        if values['stage'] == 'Lost' and not values['closing_reason'].strip():
            raise HTTPException(422, 'Alasan Gagal wajib diisi.')
        values['closed_at'] = now() if values['stage'] in ('Won', 'Lost') else None
        if not values['closed_at']:
            values['closing_reason'] = ''
    if kind == 'tasks':
        task_relations(db, actor, values, owner)
    record = MODELS[kind](owner_id=owner, assigned_id=assigned, **values)
    db.add(record)
    db.flush()
    audit(db, actor, kind, record, 'created', new=record_snapshot(record))
    if kind == 'tasks' and record.done:
        complete_followup(db, actor, record)
    return record


def task_relations(db, actor, values, owner):
    for key, kind in [('contact_id', 'contacts'), ('lead_id', 'leads'), ('opportunity_id', 'opportunities')]:
        check_relation(db, actor, kind, values.get(key), owner)
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
    if kind == 'leads':
        values.pop('phone', None)
        values.pop('role', None)
    if kind == 'opportunities':
        reason = values.pop('change_reason')
        privileged_reason(actor, record, reason, record.stage != values['stage'] or record.value != values['value'])
        c = check_relation(db, actor, 'contacts', values['contact_id'], record.owner_id)
        check_relation(db, actor, 'companies', c.company_id, record.owner_id)
        values['company_id'] = c.company_id
        close_deal(record, values.pop('stage'), values.pop('closing_reason'))
    if kind == 'tasks':
        task_relations(db, actor, values, record.owner_id)
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
    for field, action in [('stage', 'stage_changed'), ('value', 'value_changed')]:
        changed = Decimal(old[field]) != Decimal(new[field]) if field == 'value' else old[field] != new[field]
        if changed:
            audit(db, actor, 'opportunities', record, action, {field: old[field]}, {field: new[field]},
                  {'reason': reason})
    if old['stage'] in ('Won', 'Lost') and new['stage'] not in ('Won', 'Lost'):
        audit(db, actor, 'opportunities', record, 'reopened', old, new, {'reason': reason})


def transition(db, actor, id, payload):
    record = get_record(db, actor, 'opportunities', id, payload.revision, lock=True)
    privileged_reason(actor, record, payload.change_reason, record.stage != payload.stage)
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
    if kind == 'contacts' and assigned:
        company = db.get(Company, record.company_id)
        if assigned not in (company.owner_id, company.assigned_id):
            raise HTTPException(422, 'Berikan akses perusahaan kepada assignee terlebih dahulu.')
    if kind == 'opportunities':
        c = db.get(Contact, record.contact_id)
        company = db.get(Company, record.company_id)
        if owner not in (c.owner_id, c.assigned_id) or owner not in (company.owner_id, company.assigned_id):
            raise HTTPException(422, 'Berikan akses kontak/perusahaan ke owner baru terlebih dahulu.')
    if kind == 'tasks':
        task_relations(db, actor, record_snapshot(record), owner)
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
    contact = duplicate_contact(db, lead.owner_id, lead.email)
    if contact and contact.company_id != company.id:
        raise HTTPException(409, 'Email sudah terkait perusahaan lain. Periksa lead sebelum konversi.')
    if contact and actor.role == 'sales' and actor.id not in (contact.owner_id, contact.assigned_id):
        raise HTTPException(409, 'Kontak existing belum ditugaskan kepada Anda. Manager perlu memberi akses terlebih dahulu.')
    if not contact:
        contact = Contact(owner_id=lead.owner_id, assigned_id=lead.assigned_id, name=lead.name,
                          company_id=company.id, email=lead.email, normalized_email=lead.email.casefold() or None)
        db.add(contact)
        db.flush()
        audit(db, actor, 'contacts', contact, 'created', new=record_snapshot(contact))
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
        result['company'] = db.get(Company, record.company_id).name
    if isinstance(record, Opportunity):
        result.update(contact=record.contact_id, stage=STAGE_LABELS[record.stage], stage_code=record.stage,
                      value=float(record.value), closed=record.closed_at.astimezone(ZoneInfo(settings().report_timezone)).date().isoformat() if record.closed_at else '',
                      at_risk=at_risk(record, risk_days), company=db.get(Company, record.company_id).name)
    if isinstance(record, Task):
        result.update(contact=record.contact_id or '', overdue=not record.done and record.date < today())
    return result


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
    deals = visible(db, user, 'opportunities')
    leads = visible(db, user, 'leads')
    tasks = visible(db, user, 'tasks')
    contacts = visible(db, user, 'contacts')
    conf = config(db)
    start = today() - timedelta(days=days-1)
    zone = ZoneInfo(settings().report_timezone)
    closed = [d for d in deals if d.closed_at and start <= d.closed_at.astimezone(zone).date() <= today()]
    won = [d for d in closed if d.stage == 'Won']
    active = [d for d in deals if d.stage not in ('Won', 'Lost')]
    def sum_values(rows):
        return float(sum((d.value for d in rows), Decimal(0)))
    denominator = len(closed)
    eligible_leads = [lead for lead in leads if start <= lead.created_at.astimezone(zone).date() <= today()]
    result = {'won': sum_values(won), 'wonCount': len(won), 'closedCount': denominator,
              'pipeline': sum_values(active), 'activeCount': len(active),
              'winRate': int(len(won)/denominator*100+0.5) if denominator else 0,
              'contactCount': len(contacts), 'overdueTasks': sum(not t.done and t.date < today() for t in tasks),
              'atRiskCount': sum(at_risk(d, conf.risk_days) for d in active),
              'conversionRate': round(sum(lead.converted_at is not None for lead in eligible_leads)/len(eligible_leads)*100, 1) if eligible_leads else 0,
              'averageSalesCycle': round(sum((d.closed_at-d.created_at).total_seconds()/86400 for d in won)/len(won), 1) if won else 0,
              'stageValues': {STAGE_LABELS[s]: {'count': sum(d.stage == s for d in active),
                                              'value': sum_values([d for d in active if d.stage == s])}
                              for s in ['New', 'Qualification', 'Proposal', 'Negotiation']},
              'sourceCounts': {s: sum(lead.source == s for lead in leads) for s in sorted({lead.source for lead in leads})},
              'byRep': [], 'months': [], 'days': days, 'today': today().isoformat()}
    # Six calendar months, including the current partial month.
    month_no = today().year*12 + today().month-1
    for n in range(month_no-5, month_no+1):
        key = f'{n//12}-{n%12+1:02d}'
        rows = [d for d in deals if d.stage == 'Won' and d.closed_at and d.closed_at.astimezone(zone).strftime('%Y-%m') == key]
        result['months'].append({'month': key, 'value': sum_values(rows)})
    if user.role in ('manager', 'admin'):
        query = select(User).where(User.role == 'sales')
        if user.role == 'manager':
            query = query.where(User.team == user.team)
        for rep in db.scalars(query):
            result['byRep'].append({'id': rep.id, 'name': rep.name, 'pipeline': sum_values([d for d in active if d.owner_id == rep.id]),
                                    'won': sum_values([d for d in won if d.owner_id == rep.id]),
                                    'open': sum(d.owner_id == rep.id for d in active)})
    return result
