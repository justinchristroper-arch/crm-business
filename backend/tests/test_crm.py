from datetime import timedelta
import pytest
from sqlalchemy import select, func, update
from sqlalchemy.exc import DBAPIError
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import Contact, Company, Opportunity, AuditEvent, User, now
from backend.services import today


def contact(client, name='Client', email='client@example.com', company='Studio Test'):
    response = client.post('/api/contacts', json={'name': name, 'company': company, 'email': email})
    assert response.status_code == 201, response.text
    return response.json()


def deal(client, c=None, value='1000000', stage='New', **extra):
    c = c or contact(client)
    payload = {'title': 'Website Demo', 'contact_id': c['id'], 'value': value, 'stage': stage,
               'due': (today()+timedelta(days=7)).isoformat(), **extra}
    response = client.post('/api/opportunities', json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def lead(client, **extra):
    response = client.post('/api/leads', json={'name': 'New Lead', 'company': 'Lead Studio',
                                             'email': 'lead@example.com', **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_authentication_hash_session_logout(clients, db):
    client = clients()
    stored = db.get(User, 'r1')
    assert stored.password_hash.startswith('$argon2id$')
    response = client.get('/api/auth/me')
    assert response.json()['user']['role'] == 'sales'
    assert 'password_hash' not in response.text
    token = client.cookies.get('crm_session')
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/contacts', headers={'Cookie': 'crm_session='+token}).status_code == 401


def test_wrong_password_no_session(clients):
    client = clients()
    client.cookies.clear()
    response = client.post('/api/auth/login', json={'email': 'r1@example.com', 'password': 'bad'})
    assert response.status_code == 401
    assert not client.cookies.get('crm_session')
    assert client.get('/api/workspace').status_code == 401


def test_login_cookie_and_csrf_origin(clients):
    client = clients()
    assert client.post('/api/contacts', json={'name': 'N', 'company': 'C'}, headers={'X-CSRF-Token': ''}).status_code == 403
    assert client.post('/api/contacts', json={'name': 'N', 'company': 'C'}, headers={'Origin': 'https://evil.example'}).status_code == 403
    response = client.post('/api/auth/login', json={'email': 'r1@example.com', 'password': 'PortfolioTest!2026'})
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie


def test_role_reloaded_and_inactive_session(clients, db):
    client = clients()
    db.get(User, 'r1').role = 'manager'
    db.commit()
    assert client.get('/api/auth/me').json()['user']['role'] == 'manager'
    db.get(User, 'r1').active = False
    db.commit()
    assert client.get('/api/dashboard').status_code == 401


def test_rep_cannot_impersonate_owner_or_manage_users(clients):
    client = clients()
    assert client.post('/api/leads', json={'name': 'L', 'company': 'C', 'owner_id': 'r2'}).status_code == 403
    assert client.post('/api/users', json={'name': 'X', 'email': 'x@example.com', 'team': 'Nusantara', 'password': 'VeryLongDemo!2'}).status_code == 403
    assert client.put('/api/config', json={'workspace': 'X', 'risk_days': 1}).status_code == 403


def test_ownership_idor_lists_exports_analytics(clients):
    first, second = clients('r1'), clients('r2')
    d = deal(first)
    assert second.get('/api/opportunities/'+d['id']).status_code == 404
    assert second.post('/api/opportunities/'+d['id']+'/stage', json={'stage': 'Won', 'revision': 1}).status_code == 404
    assert second.get('/api/opportunities').json() == []
    assert second.get('/api/backup').json()['deals'] == []
    assert second.get('/api/dashboard').json()['pipeline'] == 0
    assert second.get('/api/activities').json() == []


def test_manager_team_visibility_and_no_outside_access(clients):
    deal(clients('r1'))
    deal(clients('r2'))
    outside = deal(clients('r3'))
    manager = clients('m1')
    assert len(manager.get('/api/opportunities').json()) == 2
    assert manager.get('/api/opportunities/'+outside['id']).status_code == 404
    assert manager.get('/api/dashboard').json()['pipeline'] == 2_000_000
    assert len(manager.get('/api/dashboard').json()['byRep']) == 2
    assert len(clients('a1').get('/api/opportunities').json()) == 3


def test_normalized_company_and_contact_duplicates_are_owner_scoped(clients):
    client = clients()
    c = contact(client, company='  Studio   TEST  ', email='Mixed@Example.com')
    duplicate = client.post('/api/contacts', json={'name': 'Other', 'company': 'studio test', 'email': 'mixed@example.com'})
    assert duplicate.status_code == 409
    other = contact(client, email='second@example.com', company='studio test')
    assert c['company_id'] == other['company_id']
    assert len(client.get('/api/companies').json()) == 1
    # Privacy boundary: existence of another owner's record is not leaked through duplicate errors.
    assert contact(clients('r2'), email='mixed@example.com')['id'] != c['id']


def test_conversion_transaction_and_repeat_idempotency(clients, db):
    client = clients()
    lead_record = lead(client)
    response = client.post(f"/api/leads/{lead_record['id']}/convert", json={'revision': 1, 'title': 'Lead deal', 'value': 8000,
                          'due': today().isoformat()})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['opportunity_id']
    converted = client.get('/api/leads/'+lead_record['id']).json()
    assert converted['status'] == 'Dikonversi'
    assert converted['contact_id'] == result['contact_id']
    assert client.post(f"/api/leads/{lead_record['id']}/convert", json={'revision': converted['revision'], 'create_opportunity': False}).status_code == 409
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 1


def test_conversion_rolls_back_all_required_steps_on_conflict(clients, db):
    client = clients()
    contact(client, email='lead@example.com', company='Existing Company')
    lead_record = lead(client, company='New Should Rollback')
    before = db.scalar(select(func.count()).select_from(Company))
    audit_count = db.scalar(select(func.count()).select_from(AuditEvent))
    response = client.post(f"/api/leads/{lead_record['id']}/convert", json={'revision': 1, 'create_opportunity': False})
    assert response.status_code == 409
    assert db.scalar(select(func.count()).select_from(Company)) == before
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == audit_count
    assert client.get('/api/leads/'+lead_record['id']).json()['status'] == 'Baru'


def test_conversion_reuses_same_owner_contact(clients, db):
    client = clients()
    c = contact(client, email='lead@example.com', company='Lead Studio')
    lead_record = lead(client)
    response = client.post(f"/api/leads/{lead_record['id']}/convert", json={'revision': 1, 'create_opportunity': False})
    assert response.json()['contact_id'] == c['id']
    assert db.scalar(select(func.count()).select_from(Contact)) == 1


@pytest.mark.parametrize('stage', ['Won', 'Lost'])
def test_closed_stage_sets_timestamp_and_requires_reason(clients, stage):
    client = clients()
    d = deal(client)
    payload = {'stage': stage, 'revision': 1}
    if stage == 'Lost':
        assert client.post(f"/api/opportunities/{d['id']}/stage", json=payload).status_code == 422
        payload['closing_reason'] = 'Budget postponed'
    result = client.post(f"/api/opportunities/{d['id']}/stage", json=payload)
    assert result.status_code == 200
    assert result.json()['closed_at'] is not None
    assert result.json()['stage_code'] == stage


def test_reopen_and_stale_revision(clients):
    client = clients()
    d = deal(client, stage='Won')
    response = client.post(f"/api/opportunities/{d['id']}/stage", json={'stage': 'Proposal', 'revision': 1})
    assert response.json()['closed_at'] is None
    assert response.json()['closing_reason'] == ''
    assert client.get('/api/dashboard').json()['won'] == 0
    assert client.post(f"/api/opportunities/{d['id']}/stage", json={'stage': 'Won', 'revision': 1}).status_code == 409
    actions = [e['action'] for e in client.get('/api/activities').json()]
    assert 'reopened' in actions and 'stage_changed' in actions


def test_manager_must_explain_sales_outcome_change(clients):
    d = deal(clients())
    manager = clients('m1')
    url = f"/api/opportunities/{d['id']}/stage"
    assert manager.post(url, json={'stage': 'Won', 'revision': 1}).status_code == 422
    result = manager.post(url, json={'stage': 'Won', 'revision': 1, 'change_reason': 'Contract reviewed'})
    assert result.status_code == 200
    audit = [e for e in manager.get('/api/activities').json() if e['action'] == 'stage_changed'][0]
    assert audit['actor_id'] == 'm1' and audit['metadata']['reason'] == 'Contract reviewed'


def test_value_changes_and_owner_assignment_are_audited(clients):
    client, manager = clients(), clients('m1')
    lead_record = lead(client)
    response = manager.post(f"/api/leads/{lead_record['id']}/owner", json={'owner_id': 'r2', 'reason': 'Transfer territory', 'revision': 1})
    assert response.status_code == 200
    assert client.get('/api/leads/'+lead_record['id']).status_code == 404
    assert clients('r2').get('/api/leads/'+lead_record['id']).status_code == 200
    d = deal(client)
    result = client.put(f"/api/opportunities/{d['id']}?revision=1", json={'title': d['title'], 'contact_id': d['contact_id'],
                         'value': 2000000, 'due': d['due'], 'stage': 'New'})
    assert result.status_code == 200
    actions = {e['action'] for e in manager.get('/api/activities').json()}
    assert 'owner_changed' in actions and 'value_changed' in actions


def test_task_overdue_completion_clears_risk(clients, db):
    client = clients()
    d = deal(client)
    stored = db.get(Opportunity, d['id'])
    stored.created_at = now()-timedelta(days=15)
    db.commit()
    assert client.get('/api/opportunities/'+d['id']).json()['at_risk']
    payload = {'title': 'Call client', 'date': (today()-timedelta(days=1)).isoformat(),
               'opportunity_id': d['id'], 'priority': 'Tinggi'}
    response = client.post('/api/tasks', json=payload)
    assert response.json()['overdue']
    assert client.get('/api/dashboard').json()['overdueTasks'] == 1
    payload['done'] = True
    result = client.put(f"/api/tasks/{response.json()['id']}?revision=1", json=payload)
    assert result.status_code == 200 and not result.json()['overdue']
    assert not client.get('/api/opportunities/'+d['id']).json()['at_risk']
    assert client.get('/api/dashboard').json()['overdueTasks'] == 0


def test_manual_followup_and_risk_config(clients, db):
    client = clients()
    d = deal(client)
    stored = db.get(Opportunity, d['id'])
    stored.created_at = now()-timedelta(days=5)
    db.commit()
    admin = clients('a1')
    assert admin.put('/api/config', json={'workspace': 'Demo', 'risk_days': 3}).status_code == 200
    assert client.get('/api/dashboard').json()['atRiskCount'] == 1
    assert client.post('/api/activities', json={'entity_type': 'opportunities', 'entity_id': d['id'], 'note': 'Called client'}).status_code == 201
    assert client.get('/api/dashboard').json()['atRiskCount'] == 0


def test_audit_api_and_database_immutable(clients, db):
    client = clients()
    deal(client)
    event = db.scalar(select(AuditEvent))
    assert client.delete('/api/activities/'+event.id).status_code in (404, 405)
    with pytest.raises(DBAPIError):
        db.execute(update(AuditEvent).where(AuditEvent.id == event.id).values(action='tampered'))
    db.rollback()
    assert db.get(AuditEvent, event.id).action != 'tampered'


def test_dashboard_formulas_closed_date_range_and_sales_cycle(clients, db):
    client = clients()
    c = contact(client)
    won = deal(client, c, value='3000000', stage='Won')
    deal(client, c, value='1000000', stage='Lost', closing_reason='No budget')
    deal(client, c, value='4000000')
    stale = deal(client, c, value='9000000', stage='Won')
    db.get(Opportunity, stale['id']).closed_at = now()-timedelta(days=40)
    db.get(Opportunity, won['id']).created_at = now()-timedelta(days=10)
    db.commit()
    result = client.get('/api/dashboard?days=30').json()
    assert result['won'] == 3000000 and result['pipeline'] == 4000000
    assert result['winRate'] == 50 and result['closedCount'] == 2
    assert result['averageSalesCycle'] == 10
    assert client.get('/api/dashboard?days=90').json()['won'] == 12000000


def test_admin_user_management_revokes_sessions(clients):
    client, admin = clients(), clients('a1')
    assert admin.patch('/api/users/r1', json={'active': False}).status_code == 200
    assert client.get('/api/auth/me').status_code == 401
    assert admin.patch('/api/users/a1', json={'active': False}).status_code == 409


def test_bulk_import_transaction_and_admin_only(clients, db):
    rep, admin = clients(), clients('a1')
    invalid = {'version': 1, 'contacts': [{'id': 'old', 'name': 'Backup', 'company': 'Backup Co', 'email': ''}],
               'leads': [], 'deals': [{'id': 'd', 'contact': 'missing'}], 'tasks': []}
    assert rep.post('/api/backup/import', json=invalid).status_code == 403
    assert admin.post('/api/backup/import', json=invalid).status_code == 422
    assert db.scalar(select(func.count()).select_from(Contact)) == 0
    assert db.scalar(select(func.count()).select_from(Company)) == 0


def test_cross_owner_relation_and_closed_delete_protected(clients):
    c = contact(clients('r1'))
    second = clients('r2')
    assert second.post('/api/opportunities', json={'title': 'IDOR', 'contact_id': c['id'], 'value': 10,
                                                 'due': today().isoformat()}).status_code == 404
    first = clients('r1')
    d = deal(first, c)
    assert first.delete(f"/api/opportunities/{d['id']}?revision=1").status_code == 409


def test_direct_auth_requires_session_cookie():
    with TestClient(app) as client:
        assert client.get('/api/dashboard', headers={'Authorization': 'Bearer fake'}).status_code == 401


def test_backup_roundtrip_reconstructs_converted_links_without_forging_audit(clients):
    rep, admin = clients(), clients('a1')
    record = lead(rep)
    result = rep.post(f"/api/leads/{record['id']}/convert", json={
        'revision': 1, 'title': 'Converted demo', 'value': 2500, 'due': today().isoformat()})
    assert result.status_code == 200
    exported = rep.get('/api/backup').json()
    exported['audit_read_only'] = [{'actor_id': 'forged', 'action': 'forged'}]
    restored = admin.post('/api/backup/import', json=exported)
    assert restored.status_code == 200, restored.text
    imported_leads = [r for r in admin.get('/api/leads').json() if r['owner_id'] == 'a1']
    assert len(imported_leads) == 1 and imported_leads[0]['status'] == 'Dikonversi'
    assert imported_leads[0]['opportunity_id']
    assert all(event['actor_id'] != 'forged' for event in admin.get('/api/activities').json())


def test_assignment_grants_explicit_access_and_is_audited(clients):
    rep, manager, other = clients(), clients('m1'), clients('r2')
    record = lead(rep)
    response = manager.post(f"/api/leads/{record['id']}/owner", json={
        'owner_id': 'r1', 'assigned_id': 'r2', 'reason': 'Collaborate', 'revision': 1})
    assert response.status_code == 200
    assert other.get('/api/leads/'+record['id']).status_code == 200
    assert other.post(f"/api/leads/{record['id']}/owner", json={
        'owner_id': 'r2', 'reason': 'Steal', 'revision': 2}).status_code == 403


def test_conversion_rolls_back_when_late_audit_write_fails(clients, db, monkeypatch):
    from backend import services
    client = clients()
    record = lead(client)
    original = services.audit
    def failing_audit(*args, **kwargs):
        if args[4] == 'converted':
            raise RuntimeError('Injected transactional failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(services, 'audit', failing_audit)
    with pytest.raises(RuntimeError, match='Injected'):
        client.post(f"/api/leads/{record['id']}/convert", json={
            'revision': 1, 'title': 'Rollback', 'value': 5000, 'due': today().isoformat()})
    assert db.scalar(select(func.count()).select_from(Contact)) == 0
    assert db.scalar(select(func.count()).select_from(Company)) == 0
    assert db.scalar(select(func.count()).select_from(Opportunity)) == 0
    assert client.get('/api/leads/'+record['id']).json()['status'] == 'Baru'


def test_decimal_formatting_does_not_create_false_value_audit(clients):
    client = clients()
    record = deal(client, value='1000000.00')
    response = client.put(f"/api/opportunities/{record['id']}?revision=1", json={
        'title': record['title'], 'contact_id': record['contact_id'], 'value': '1000000',
        'stage': 'New', 'due': record['due']})
    assert response.status_code == 200
    assert not any(event['action'] == 'value_changed' for event in client.get('/api/activities').json())


def test_configuration_errors_do_not_print_database_secrets():
    from backend.config import Settings
    from pydantic import ValidationError
    secret_url = 'postgresql://test:synthetic-private-password@localhost/disposable'
    with pytest.raises(ValidationError) as result:
        Settings(_env_file=None, database_url=secret_url, jwt_secret='short')
    assert 'synthetic-private-password' not in str(result.value)
