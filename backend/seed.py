"""Explicit synthetic demo setup; never runs in request handlers or automatically at startup."""
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from backend.models import User, Config, Company, Contact, Lead, Opportunity, Task, now
from backend.db import engine
from backend.config import settings
from backend.auth import hasher
from backend.services import resolve_company, audit, record_snapshot, today

DEMO_USERS = [('rep@crm-demo.example', 'Dimas Sales', 'sales', 'Nusantara'),
              ('rep2@crm-demo.example', 'Sarah Sales', 'sales', 'Nusantara'),
              ('manager@crm-demo.example', 'Nadia Manager', 'manager', 'Nusantara'),
              ('admin@crm-demo.example', 'Admin Demo', 'admin', 'Nusantara'),
              ('other@crm-demo.example', 'Sales Tim Bandung', 'sales', 'Bandung')]


def ensure_users(db):
    users = []
    for email, name, role, team in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user and not user.demo:
            raise RuntimeError('Refusing to use a non-demo account as a seed account.')
        if not user:
            user = User(email=email, name=name, role=role, team=team, demo=True,
                        password_hash=hasher.hash(settings().demo_password))
            db.add(user)
            db.flush()
        users.append(user)
    return users


def seed_records(db, users):
    first, second, manager, admin, outsider = users
    contacts = []
    names = [('Dimas Pratama', 'Aksara Digital'), ('Sarah Wijaya', 'Bloom & Co.'),
             ('Rizky Ananda', 'Kopi Senja'), ('Nadia Putri', 'Forma Living'),
             ('Arif Setiawan', 'Ventura Tech'), ('Michelle Tan', 'Studio Rupa'), ('Bima Saputra', 'Langkah Travel')]
    for i, (name, company_name) in enumerate(names):
        owner = first if i < 4 else second
        company = resolve_company(db, admin, company_name, owner.id)
        contact = Contact(owner_id=owner.id, company_id=company.id, name=name,
                          email=f'client{i+1}@example.com', normalized_email=f'client{i+1}@example.com',
                          phone=f'0812 0000 100{i}', role='Business Owner')
        db.add(contact)
        db.flush()
        contacts.append(contact)
        audit(db, admin, 'contacts', contact, 'created', new=record_snapshot(contact), metadata={'synthetic': True})
    outside_company = resolve_company(db, admin, 'Bandung Demo', outsider.id)
    db.add(Contact(owner_id=outsider.id, company_id=outside_company.id, name='Outside Team Contact',
                   email='outside@example.com', normalized_email='outside@example.com'))
    titles = [('Website company profile', 18_000_000, 'Proposal', 0, 20, None),
              ('E-commerce Bloom', 32_000_000, 'Negotiation', 1, 30, None),
              ('Landing page Kopi Senja', 8_500_000, 'Qualification', 2, 10, None),
              ('Katalog interaktif Forma', 24_000_000, 'Proposal', 3, 15, None),
              ('Dashboard internal', 45_000_000, 'New', 4, 3, None),
              ('Portfolio Studio Rupa', 12_000_000, 'Won', 5, 40, 5),
              ('Booking website travel', 28_000_000, 'Won', 6, 50, 12),
              ('Brand microsite', 10_000_000, 'Won', 0, 70, 42),
              ('Website membership', 22_000_000, 'Lost', 4, 55, 18)]
    deals = []
    for title, value, stage, index, age, closed_age in titles:
        c = contacts[index]
        deal = Opportunity(owner_id=c.owner_id, company_id=c.company_id, contact_id=c.id,
                           title=title, value=value, stage=stage, due=today()+timedelta(days=14),
                           created_at=now()-timedelta(days=age),
                           closed_at=now()-timedelta(days=closed_age) if closed_age is not None else None,
                           closing_reason='Anggaran klien ditunda' if stage == 'Lost' else '',
                           notes='Data fiktif untuk demonstrasi portfolio.')
        db.add(deal)
        db.flush()
        deals.append(deal)
        audit(db, admin, 'opportunities', deal, 'created', new=record_snapshot(deal), metadata={'synthetic': True})
    for i, (name, company) in enumerate([('Putri Maharani', 'Lumi Skincare'), ('Andi Nugroho', 'Ruang Kerja'),
                                       ('Fajar Ramadhan', 'Nusa Foods'), ('Clara Dewi', 'Atelier Clara')]):
        lead = Lead(owner_id=first.id if i < 2 else second.id, name=name, company=company,
                    email=f'lead{i}@example.com', source=['Instagram', 'Referral', 'Website', 'LinkedIn'][i],
                    status='Kualifikasi' if i == 2 else 'Baru', notes='Kebutuhan website perusahaan.')
        db.add(lead)
        db.flush()
        audit(db, admin, 'leads', lead, 'created', new=record_snapshot(lead))
    for i, title in enumerate(['Follow-up proposal Aksara', 'Meeting scope e-commerce',
                               'Minta brief dan foto produk', 'Kirim revisi penawaran Forma', 'Discovery call Ventura']):
        c = contacts[i]
        task = Task(owner_id=c.owner_id, contact_id=c.id, opportunity_id=deals[i].id,
                    title=title, date=today()+timedelta(days=[0, 0, 1, -1, 3][i]),
                    priority='Tinggi' if i < 2 else 'Sedang')
        db.add(task)
        db.flush()
        audit(db, admin, 'tasks', task, 'created', new=record_snapshot(task))


def reset_demo_records(db, actor):
    ids = list(db.scalars(select(User.id).where(User.demo)))
    # Audit history and users are deliberately retained. Foreign-key conflicts rollback everything.
    for model in [Task, Lead, Opportunity, Contact, Company]:
        for record in db.scalars(select(model).where(model.owner_id.in_(ids))):
            audit(db, actor, model.__tablename__, record, 'demo_reset_deleted', old=record_snapshot(record))
            db.delete(record)
        db.flush()
    seed_records(db, ensure_users(db))


def main():
    if not settings().demo_mode:
        raise SystemExit('Seed refused: set DEMO_MODE=true in a synthetic demo environment.')
    with sessionmaker(engine(), expire_on_commit=False)() as db:
        if not db.get(Config, 1):
            db.add(Config(id=1))
        users = ensure_users(db)
        if not db.scalar(select(Opportunity.id).limit(1)):
            seed_records(db, users)
        db.commit()
    print('Synthetic demo seed ready (idempotent). No passwords or connection strings printed.')


if __name__ == '__main__':
    main()
