"""Explicit local/offline cleanup. Uses no paid scheduler and keeps business audit history."""
import argparse
from datetime import timedelta
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session as DB
from backend.db import engine
from backend.models import Session, LoginAttempt, now


def cleanup(db, apply=False):
    conditions = [(Session, (Session.expires_at <= now()) | Session.revoked),
                  (LoginAttempt, LoginAttempt.updated_at < now() - timedelta(days=7))]
    counts = {}
    for model, condition in conditions:
        counts[model.__tablename__] = db.scalar(select(func.count()).select_from(model).where(condition))
        if apply:
            db.execute(delete(model).where(condition))
    if apply:
        db.commit()
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with DB(engine()) as db:
        print({'applied': args.apply, 'eligible': cleanup(db, args.apply)})
