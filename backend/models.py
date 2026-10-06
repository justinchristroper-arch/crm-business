from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Numeric, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('sales','manager','admin')", name='user_role'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='sales')
    team: Mapped[str] = mapped_column(String(80), default='Nusantara')
    active: Mapped[bool] = mapped_column(default=True)
    demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Session(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    csrf: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime]
    revoked: Mapped[bool] = mapped_column(default=False)


class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(default=0)
    blocked_until: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(default=now)


class Config(Base):
    __tablename__ = 'crm_config'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    workspace: Mapped[str] = mapped_column(String(80), default='Nusantara Studio')
    risk_days: Mapped[int] = mapped_column(default=14)
    __table_args__ = (CheckConstraint('risk_days >= 1 AND risk_days <= 365', name='risk_days_range'),)


class Owned:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    assigned_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)
    revision: Mapped[int] = mapped_column(default=1)


class Company(Owned, Base):
    __tablename__ = 'companies'
    __table_args__ = (UniqueConstraint('owner_id', 'normalized_name', name='company_owner_name'),)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200))


class Contact(Owned, Base):
    __tablename__ = 'contacts'
    __table_args__ = (UniqueConstraint('owner_id', 'normalized_email', name='contact_owner_email'),)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(254), default='')
    normalized_email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(80), default='')
    role: Mapped[str] = mapped_column(String(120), default='')


class Lead(Owned, Base):
    __tablename__ = 'leads'
    __table_args__ = (CheckConstraint("status IN ('Baru','Dihubungi','Kualifikasi','Dikonversi','Tidak cocok')",
                                    name='lead_status'),)
    name: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(254), default='')
    source: Mapped[str] = mapped_column(String(40), default='Website')
    status: Mapped[str] = mapped_column(String(30), default='Baru')
    notes: Mapped[str] = mapped_column(Text, default='')
    converted_at: Mapped[datetime | None]
    contact_id: Mapped[str | None] = mapped_column(ForeignKey('contacts.id'))
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey('opportunities.id', use_alter=True,
                                                               name='lead_opportunity_fk'))


class Opportunity(Owned, Base):
    __tablename__ = 'opportunities'
    __table_args__ = (
        CheckConstraint("stage IN ('New','Qualification','Proposal','Negotiation','Won','Lost')", name='deal_stage'),
        CheckConstraint('value >= 0 AND value <= 1000000000000', name='deal_value'),
        CheckConstraint("(stage IN ('Won','Lost') AND closed_at IS NOT NULL) OR "
                        "(stage NOT IN ('Won','Lost') AND closed_at IS NULL)", name='deal_closed'),
        CheckConstraint("stage != 'Lost' OR length(trim(closing_reason)) > 0", name='lost_reason'),
    )
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), index=True)
    contact_id: Mapped[str] = mapped_column(ForeignKey('contacts.id'), index=True)
    title: Mapped[str] = mapped_column(String(200))
    value: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    stage: Mapped[str] = mapped_column(String(30), default='New')
    due: Mapped[date]
    closed_at: Mapped[datetime | None]
    closing_reason: Mapped[str] = mapped_column(Text, default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    last_followup_at: Mapped[datetime | None]


class Task(Owned, Base):
    __tablename__ = 'tasks'
    __table_args__ = (CheckConstraint("priority IN ('Rendah','Sedang','Tinggi')", name='task_priority'),)
    title: Mapped[str] = mapped_column(String(200))
    contact_id: Mapped[str | None] = mapped_column(ForeignKey('contacts.id'), index=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey('leads.id'), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey('opportunities.id'), index=True)
    date: Mapped[date]
    priority: Mapped[str] = mapped_column(String(20), default='Sedang')
    done: Mapped[bool] = mapped_column(default=False)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    assigned_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    team: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(60))
    timestamp: Mapped[datetime] = mapped_column(default=now, index=True)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
