from sqlalchemy import event, select, func
import pytest
from backend.models import AuditEvent
from backend.tests.test_crm import contact, deal, lead
from backend.services import today


@pytest.mark.parametrize('endpoint', ['stage', 'put'])
@pytest.mark.parametrize('stage', ['Lost', 'Won'])
def test_closing_reason_requires_explanation_and_creates_audit(clients, endpoint, stage):
    rep, manager = clients(), clients('m1')
    d = deal(rep, stage=stage, closing_reason='Original reason')
    body = {'stage': stage, 'closing_reason': 'Customer confirmed correction'}
    if endpoint == 'stage':
        body['revision'] = d['revision']
        def send(payload):
            return manager.post('/api/opportunities/' + d['id'] + '/stage', json=payload)
    else:
        body.update(title=d['title'], contact_id=d['contact_id'], value=str(d['value']), due=d['due'])
        def send(payload):
            return manager.put('/api/opportunities/' + d['id'] + '?revision=1', json=payload)
    assert send(body).status_code == 422
    response = send({**body, 'change_reason': 'Corrected after review'})
    assert response.status_code == 200
    events = [e for e in manager.get('/api/activities').json() if e['action'] == 'closing_reason_changed']
    assert len(events) == 1
    assert events[0]['old_value']['closing_reason'] == 'Original reason'
    assert events[0]['new_value']['closing_reason'] == body['closing_reason']
    assert events[0]['metadata']['reason'] == 'Corrected after review'


def test_unchanged_stage_is_noop_and_stale_revision_still_rejected(clients, db):
    rep = clients()
    d = deal(rep, stage='Lost', closing_reason='No budget')
    count = db.scalar(select(func.count()).select_from(AuditEvent))
    response = rep.post('/api/opportunities/' + d['id'] + '/stage', json={
        'stage': 'Lost', 'closing_reason': 'No budget', 'revision': d['revision']})
    assert response.status_code == 200 and response.json()['revision'] == d['revision']
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == count
    assert rep.post('/api/opportunities/' + d['id'] + '/stage', json={
        'stage': 'Lost', 'closing_reason': 'No budget', 'revision': 99}).status_code == 409


def assign(manager, kind, record, assignee):
    return manager.post(f"/api/{kind}/{record['id']}/owner", json={
        'owner_id': 'r1', 'assigned_id': assignee, 'revision': record['revision'], 'reason': 'Collaboration'})


def test_assignment_rejects_missing_relations_then_assignee_can_work(clients):
    rep, manager, other = clients(), clients('m1'), clients('r2')
    c = contact(rep)
    d = deal(rep, c)
    task = rep.post('/api/tasks', json={'title': 'Follow-up', 'date': today().isoformat(),
        'contact_id': c['id'], 'opportunity_id': d['id']}).json()
    assert assign(manager, 'opportunities', d, 'r2').status_code == 422
    assert assign(manager, 'tasks', task, 'r2').status_code == 422
    assert other.get('/api/opportunities/' + d['id']).status_code == 404
    company = rep.get('/api/companies/' + c['company_id']).json()
    shared_company = assign(manager, 'companies', company, 'r2').json()
    shared_contact = assign(manager, 'contacts', c, 'r2').json()
    shared_deal = assign(manager, 'opportunities', d, 'r2').json()
    shared_task = assign(manager, 'tasks', task, 'r2').json()
    assert other.get('/api/contacts/' + c['id']).status_code == 200
    response = other.put(f"/api/opportunities/{d['id']}?revision={shared_deal['revision']}", json={
        'title': 'Updated by assignee', 'contact_id': c['id'], 'value': str(d['value']),
        'stage': d['stage_code'], 'due': d['due']})
    assert response.status_code == 200
    assert other.put(f"/api/tasks/{task['id']}?revision={shared_task['revision']}", json={
        'title': task['title'], 'date': task['date'], 'contact_id': c['id'],
        'opportunity_id': d['id'], 'done': True}).status_code == 200
    assert assign(manager, 'companies', shared_company, None).status_code == 409
    assert assign(manager, 'contacts', shared_contact, None).status_code == 409


def test_lead_details_survive_conversion_and_backup_roundtrip(clients):
    rep, admin = clients(), clients('a1')
    original = lead(rep, phone='081234567890', role='Procurement')
    assert original['phone'] == '081234567890' and original['role'] == 'Procurement'
    body = {k: original[k] for k in ['name', 'company', 'email', 'phone', 'role', 'source', 'status', 'notes']}
    body['phone'] = '089876543210'
    updated = rep.put('/api/leads/' + original['id'] + '?revision=1', json=body).json()
    result = rep.post('/api/leads/' + original['id'] + '/convert', json={
        'revision': updated['revision'], 'title': 'Conversion', 'due': today().isoformat()}).json()
    converted = rep.get('/api/contacts/' + result['contact_id']).json()
    assert converted['phone'] == body['phone'] and converted['role'] == body['role']
    assert admin.post('/api/backup/import', json=rep.get('/api/backup').json()).status_code == 200
    restored = [r for r in admin.get('/api/leads').json() if r['owner_id'] == 'a1'][0]
    assert restored['phone'] == body['phone'] and restored['role'] == body['role']


def test_workspace_company_queries_do_not_grow_per_deal(clients, db):
    rep = clients()
    c = contact(rep)
    for n in range(20):
        deal(rep, c, value=str(1000 + n))
    statements = []
    def track(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    engine = db.get_bind()
    event.listen(engine, 'before_cursor_execute', track)
    try:
        assert rep.get('/api/workspace').status_code == 200
    finally:
        event.remove(engine, 'before_cursor_execute', track)
    assert len(statements) >= 10
    assert not any('FROM companies' in s and 'companies.id =' in s for s in statements)
    # Aggregate, page count, page rows, relation batch, and lookup batch: constant cost.
    assert sum('FROM companies' in s and 'JOIN' not in s for s in statements) <= 5


def test_pagination_search_scope_and_metrics_are_independent(clients):
    rep, other = clients(), clients('r2')
    c = contact(rep, company='Searchable Studio')
    for n in range(7):
        deal(rep, c, value='1000', title=f'Page deal {n}')
    first = rep.get('/api/opportunities/page?limit=3&q=Searchable').json()
    second = rep.get('/api/opportunities/page?limit=3&offset=3&q=Searchable').json()
    assert first['total'] == 7 and first['has_more']
    assert not {r['id'] for r in first['items']}.intersection(r['id'] for r in second['items'])
    assert other.get('/api/opportunities/page?q=Searchable').json()['total'] == 0
    page = rep.get('/api/workspace?view=opportunities&limit=3&offset=3').json()
    assert len(page['deals']) == 3 and page['pagination']['deals']['total'] == 7
    assert page['analytics']['pipeline'] == 7000 and page['analytics']['activeCount'] == 7
    assert rep.get('/api/opportunities/page?limit=101').status_code == 422


def test_demo_accounts_are_rejected_when_demo_mode_is_disabled(clients, monkeypatch):
    from backend.config import settings
    rep = clients()
    monkeypatch.setattr(settings(), 'demo_mode', False)
    assert rep.get('/api/auth/me').status_code == 401
    assert rep.post('/api/auth/login', json={'email': 'r1@example.com', 'password': 'PortfolioTest!2026'}).status_code == 401


def test_validation_errors_do_not_echo_passwords(clients):
    client = clients()
    password = 'NeverEchoThisPassword' * 20
    response = client.post('/api/auth/login', json={'email': 'r1@example.com', 'password': password})
    assert response.status_code == 422 and password not in response.text
    assert response.headers.get('X-Request-ID')


def test_sessions_are_bounded_and_expired_sessions_are_cleaned(clients, db):
    from datetime import timedelta
    from backend.models import Session, now
    from scripts.maintenance import cleanup
    for _ in range(7):
        clients()
    assert db.scalar(select(func.count()).select_from(Session)) == 5
    expired = db.scalar(select(Session))
    expired.expires_at = now() - timedelta(days=1)
    db.commit()
    assert cleanup(db)['auth_sessions'] == 1
    cleanup(db, apply=True)
    assert db.scalar(select(func.count()).select_from(Session)) == 4
