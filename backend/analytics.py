"""Scoped SQL aggregates; dashboard cost does not depend on materializing all CRM rows."""
from datetime import timedelta
from sqlalchemy import select, func, Date, and_
from backend.models import Opportunity as D, Lead, Task, Contact, Company, User, now
from backend.config import settings
from backend.services import scope, today, config, STAGE_LABELS


def summary(db, user, days):
    current = today()
    start = current - timedelta(days=days - 1)
    zone = settings().report_timezone
    closed_day = func.timezone(zone, D.closed_at).cast(Date)
    in_window = and_(D.closed_at.is_not(None), closed_day >= start, closed_day <= current)
    won = and_(in_window, D.stage == 'Won')
    active = D.stage.not_in(['Won', 'Lost'])
    def count(where):
        return func.count().filter(where)
    def value(where):
        return func.coalesce(func.sum(D.value).filter(where), 0)
    risk_days = config(db).risk_days
    risk = and_(active, func.coalesce(D.last_followup_at, D.created_at) <= now() - timedelta(days=risk_days))
    stages = ['New', 'Qualification', 'Proposal', 'Negotiation']
    columns = [value(won), count(won), count(in_window), value(active), count(active), count(risk),
               func.avg(func.extract('epoch', D.closed_at - D.created_at) / 86400).filter(won), func.count()]
    for stage in stages:
        columns.extend([count(D.stage == stage), value(D.stage == stage)])
    totals = db.execute(select(*columns).where(scope(db, user, D))).one()
    lead_day = func.timezone(zone, Lead.created_at).cast(Date)
    cohort = and_(lead_day >= start, lead_day <= current)
    lead_counts = db.execute(select(count(cohort), count(and_(cohort, Lead.converted_at.is_not(None))))
                             .select_from(Lead).where(scope(db, user, Lead))).one()
    task_counts = db.execute(select(count(and_(~Task.done, Task.date < current)), count(~Task.done),
                                    count(and_(~Task.done, Task.date == current)), func.count())
                             .select_from(Task).where(scope(db, user, Task))).one()
    result = {
        'won': float(totals[0]), 'wonCount': totals[1], 'closedCount': totals[2],
        'pipeline': float(totals[3]), 'activeCount': totals[4], 'atRiskCount': totals[5],
        'averageSalesCycle': round(float(totals[6]), 1) if totals[6] is not None else 0,
        'dealCount': totals[7], 'winRate': int(totals[1] / totals[2] * 100 + .5) if totals[2] else 0,
        'contactCount': db.scalar(select(func.count()).select_from(Contact).where(scope(db, user, Contact))),
        'companyCount': db.scalar(select(func.count()).select_from(Company).where(scope(db, user, Company))),
        'overdueTasks': task_counts[0], 'activeTasks': task_counts[1], 'todayTasks': task_counts[2], 'taskCount': task_counts[3],
        'conversionRate': round(lead_counts[1] / lead_counts[0] * 100, 1) if lead_counts[0] else 0,
        'stageValues': {STAGE_LABELS[s]: {'count': totals[8 + i * 2], 'value': float(totals[9 + i * 2])}
                        for i, s in enumerate(stages)},
        'sourceCounts': dict(db.execute(select(Lead.source, func.count()).where(scope(db, user, Lead))
                                       .group_by(Lead.source).order_by(Lead.source)).all()),
        'byRep': [], 'months': [], 'days': days, 'today': current.isoformat(),
    }
    month_no = current.year * 12 + current.month - 1
    first = current.replace(year=(month_no - 5) // 12, month=(month_no - 5) % 12 + 1, day=1)
    month = func.to_char(func.timezone(zone, D.closed_at), 'YYYY-MM')
    months = dict(db.execute(select(month, func.sum(D.value)).where(scope(db, user, D), D.stage == 'Won',
                            closed_day >= first).group_by(month)).all())
    result['months'] = [{'month': f'{n // 12}-{n % 12 + 1:02d}',
                         'value': float(months.get(f'{n // 12}-{n % 12 + 1:02d}', 0))}
                        for n in range(month_no - 5, month_no + 1)]
    if user.role in ('manager', 'admin'):
        grouped = {row[0]: row[1:] for row in db.execute(select(D.owner_id, value(active), value(won), count(active))
                                                        .where(scope(db, user, D)).group_by(D.owner_id))}
        reps = select(User).where(User.role == 'sales').order_by(User.name)
        if user.role == 'manager':
            reps = reps.where(User.team == user.team)
        for rep in db.scalars(reps):
            values = grouped.get(rep.id, (0, 0, 0))
            result['byRep'].append({'id': rep.id, 'name': rep.name, 'pipeline': float(values[0]),
                                    'won': float(values[1]), 'open': values[2]})
    return result
