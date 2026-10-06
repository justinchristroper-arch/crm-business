from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

Stage = Literal['New', 'Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Login(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Strict):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: Literal['sales', 'manager', 'admin'] = 'sales'
    team: str = Field(min_length=1, max_length=80)


class UserUpdate(Strict):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal['sales', 'manager', 'admin'] | None = None
    team: str | None = Field(default=None, min_length=1, max_length=80)
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


class Ownership(Strict):
    owner_id: str | None = None
    assigned_id: str | None = None


class CompanyInput(Ownership):
    name: str = Field(min_length=1, max_length=200)


class ContactInput(Ownership):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=80)
    role: str = Field(default='', max_length=120)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        if value:
            from pydantic import TypeAdapter
            return str(TypeAdapter(EmailStr).validate_python(value)).casefold()
        return ''


class LeadInput(ContactInput):
    source: Literal['Website', 'Instagram', 'LinkedIn', 'Referral', 'Event', 'Lainnya'] = 'Website'
    status: Literal['Baru', 'Dihubungi', 'Kualifikasi', 'Tidak cocok'] = 'Baru'
    notes: str = Field(default='', max_length=5000)


class OpportunityInput(Ownership):
    title: str = Field(min_length=1, max_length=200)
    contact_id: str
    value: Decimal = Field(ge=0, le=1000000000000, decimal_places=2)
    stage: Stage = 'New'
    due: date
    notes: str = Field(default='', max_length=5000)
    closing_reason: str = Field(default='', max_length=2000)
    change_reason: str = Field(default='', max_length=2000)


class StageInput(Strict):
    stage: Stage
    closing_reason: str = Field(default='', max_length=2000)
    change_reason: str = Field(default='', max_length=2000)
    revision: int = Field(ge=1)


class RevisionInput(Strict):
    revision: int = Field(ge=1)


class OwnerChange(RevisionInput, Ownership):
    reason: str = Field(min_length=1, max_length=2000)


class ConvertInput(RevisionInput):
    create_opportunity: bool = True
    title: str = Field(default='', max_length=200)
    value: Decimal = Field(default=0, ge=0, le=1000000000000, decimal_places=2)
    due: date | None = None


class TaskInput(Ownership):
    title: str = Field(min_length=1, max_length=200)
    contact_id: str | None = None
    lead_id: str | None = None
    opportunity_id: str | None = None
    date: date
    priority: Literal['Rendah', 'Sedang', 'Tinggi'] = 'Sedang'
    done: bool = False


class FollowupInput(Strict):
    entity_type: Literal['leads', 'contacts', 'opportunities']
    entity_id: str
    note: str = Field(min_length=1, max_length=5000)


class ConfigInput(Strict):
    workspace: str = Field(min_length=1, max_length=80)
    risk_days: int = Field(ge=1, le=365)
