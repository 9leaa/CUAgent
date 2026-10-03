"""Read-only source preview. Submitting the saved batch is a separate action."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from agent.daily_report import dump
from backend.config import Settings
from backend.db import database
from backend.manage import load_env
from backend.schedule_runtime import WorkflowCollector
from backend.schemas import BatchSubmission
from backend.workflow_sources import freeze_snapshot


def preview(sessions, *, branch, baseline, due, timezone, output):
    if due.tzinfo is None:
        raise ValueError('timezone-aware cutoff required')
    sources = WorkflowCollector(sessions)({'config': {'branch': branch, 'timezone': timezone},
                                         'dueAt': due, 'lastCommit': baseline})
    body = BatchSubmission.model_validate({'tasks': [dict(s['payload'], inputMode='aggregate')
                                                     for s in sources]}).model_dump(mode='json', exclude_none=True)
    output = Path(output).absolute()
    output.mkdir(mode=0o700)  # Fail if present, including incomplete previous previews.
    records = [freeze_snapshot(source, output / source['workflow']) for source in sources]
    dump(output / 'batch.json', body)
    dump(output / 'preview.json', {'sources': records, 'modelCalls': 0, 'submitted': False})
    return {'sources': records, 'batch': str(output / 'batch.json'), 'submitted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', choices=['harness-migration', 'p5-personal-workflows'], required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--cutoff', type=datetime.fromisoformat, required=True)
    parser.add_argument('--timezone', default='Asia/Shanghai')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(load_env())
    settings = Settings.from_env()
    _, sessions = database(settings.database_url)
    print(json.dumps(preview(sessions, branch=args.branch, baseline=args.baseline, due=args.cutoff,
                             timezone=args.timezone, output=args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
