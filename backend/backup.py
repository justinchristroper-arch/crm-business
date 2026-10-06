from fastapi import HTTPException
from pydantic import ValidationError
from backend import schemas as S, services as svc


def import_records(db, actor, payload):
    if payload.get('version') not in (1, 2):
        raise HTTPException(422, 'Versi backup tidak didukung.')
    groups = ['contacts', 'leads', 'deals', 'tasks']
    if any(not isinstance(payload.get(k), list) or len(payload[k]) > 500 for k in groups):
        raise HTTPException(422, 'Backup perlu empat koleksi, maksimal 500 record per koleksi.')
    contact_map, lead_map, deal_map = {}, {}, {}
    count = 0
    converted = []
    try:
        for row in payload['contacts']:
            if row['id'] in contact_map:
                raise ValueError('ID kontak duplikat')
            inp = S.ContactInput(**{k: row.get(k, '') for k in ['name', 'company', 'email', 'phone', 'role']})
            company = svc.resolve_company(db, actor, inp.company, actor.id)
            record = svc.duplicate_contact(db, actor.id, inp.email)
            if record:
                if company.id != record.company_id:
                    raise ValueError('Email terkait perusahaan lain')
            else:
                record = svc.create_record(db, actor, 'contacts', inp)
            contact_map[row['id']] = record.id
            count += 1
        for row in payload['leads']:
            values = {k: row[k] for k in ['name', 'company', 'email', 'source', 'status', 'notes']}
            if values['status'] == 'Dikonversi':
                values['status'] = 'Kualifikasi'
                converted.append(row)
            inp = S.LeadInput(**values)
            if row['id'] in lead_map:
                raise ValueError('ID lead duplikat')
            lead_map[row['id']] = svc.create_record(db, actor, 'leads', inp).id
            count += 1
        reverse = {v: k for k, v in svc.STAGE_LABELS.items()}
        for row in payload['deals']:
            if row['id'] in deal_map:
                raise ValueError('ID deal duplikat')
            contact_id = contact_map[row.get('contact', row.get('contact_id'))]
            inp = S.OpportunityInput(title=row['title'], contact_id=contact_id, value=row['value'],
                                     due=row['due'], stage=row.get('stage_code', reverse[row['stage']]),
                                     notes=row.get('notes', ''), closing_reason=row.get('closing_reason', ''))
            deal_map[row['id']] = svc.create_record(db, actor, 'opportunities', inp).id
            count += 1
        for row in converted:
            result = svc.convert(db, actor, lead_map[row['id']], S.ConvertInput(revision=1, create_opportunity=False))
            if row.get('opportunity_id'):
                opportunity = svc.get_record(db, actor, 'opportunities', deal_map[row['opportunity_id']])
                if opportunity.contact_id != result['contact_id']:
                    raise ValueError('Relasi hasil konversi tidak konsisten')
                lead = svc.get_record(db, actor, 'leads', lead_map[row['id']])
                lead.opportunity_id = opportunity.id
                svc.audit(db, actor, 'leads', lead, 'imported_conversion_link', metadata={'opportunity_id': opportunity.id})
        seen_tasks = set()
        for row in payload['tasks']:
            if row['id'] in seen_tasks:
                raise ValueError('ID tugas duplikat')
            seen_tasks.add(row['id'])
            contact_id = row.get('contact', row.get('contact_id'))
            inp = S.TaskInput(title=row['title'], contact_id=contact_map[contact_id] if contact_id else None,
                              lead_id=lead_map[row['lead_id']] if row.get('lead_id') else None,
                              opportunity_id=deal_map[row['opportunity_id']] if row.get('opportunity_id') else None,
                              date=row['date'], priority=row['priority'], done=row['done'])
            svc.create_record(db, actor, 'tasks', inp)
            count += 1
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise HTTPException(422, 'Backup tidak valid. Tidak ada record yang diimpor; seluruh transaksi dibatalkan.') from exc
    return {'imported': count, 'mode': 'append', 'owner_id': actor.id}
