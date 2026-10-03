"""Persistent read-only listing and idempotent acknowledgement of local notices."""
from sqlalchemy import select
from backend.models import Notification, Task, utcnow
from backend.service import NotFound


class Inbox:
    def __init__(self, sessions):
        self.sessions = sessions

    def listing(self, after=0, limit=100, unread_only=False):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('INVALID_NOTIFICATION_CURSOR')
        with self.sessions() as db:
            query = select(Notification, Task.status).join(Task, Task.id == Notification.task_id)
            query = query.where(Notification.id > after)
            if unread_only: query = query.where(Notification.read_at.is_(None))
            rows = db.execute(query.order_by(Notification.id).limit(limit)).all()
            items = [{'id': n.id, 'event_id': n.event_id, 'task_id': n.task_id,
                      'status_at_event': n.status, 'current_status': current, 'error_code': n.error_code,
                      'created_at': n.created_at.isoformat(), 'read_at': n.read_at.isoformat() if n.read_at else None,
                      'artifact_urls': ['/tasks/' + n.task_id + '/artifacts/' + name for name in
                                        ('report.json', 'report.md')] if current == n.status == 'SUCCEEDED' else []}
                     for n, current in rows]
        return {'items': items, 'next_cursor': items[-1]['id'] if items else after}

    def mark_read(self, identity):
        with self.sessions.begin() as db:
            item = db.scalar(select(Notification).where(Notification.id == identity).with_for_update())
            if item is None:
                raise NotFound('NOTIFICATION_NOT_FOUND')
            if item.read_at is None:
                item.read_at = utcnow()
            return {'id': item.id, 'read_at': item.read_at.isoformat()}
