"""Poll persisted plans without spawning a second model loop or granting quota."""
import argparse
import json
import time
from sqlalchemy import select
from backend.config import Settings
from backend.db import database
from backend.models import Schedule, utcnow
from backend.schedule_runtime import runtime_service
from backend.service import TaskService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    settings = Settings.from_env()
    _, sessions = database(settings.database_url)
    service = runtime_service(TaskService(sessions, settings))
    previous = {}
    while True:
        with sessions() as db:
            identities = list(db.scalars(select(Schedule.id).where(Schedule.status == 'ACTIVE')
                                         .order_by(Schedule.next_at).limit(100)))
        for identity in identities:
            try:
                result = service.tick(identity)
                record = {k: result[k] for k in ('status', 'id', 'batch_id') if k in result}
            except Exception as error:
                # Unknown commits are inspected on the next poll, never replayed here.
                record = {'status': 'OBSERVATION_ERROR_RECONCILE_ORIGINAL', 'error_type': type(error).__name__}
            if args.once or previous.get(identity) != record:
                print(json.dumps({'schedule': identity, 'observed_at': utcnow().isoformat(), **record}), flush=True)
                previous[identity] = record
        if args.once:
            if not identities: print(json.dumps({'status': 'NO_ACTIVE_PLANS'}), flush=True)
            return
        time.sleep(2)


if __name__ == '__main__':
    main()
