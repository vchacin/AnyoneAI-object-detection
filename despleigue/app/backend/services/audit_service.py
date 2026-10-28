"""Administrative audit persistence."""
from sqlalchemy.orm import Session

from ..db.models import AuditLog


def record_action(session: Session, *, actor_id: str | None, action: str,
                  entity: str, entity_id: str | None = None,
                  store_id: str | None = None, details: dict | None = None) -> AuditLog:
    entry = AuditLog(actor_id=actor_id, action=action, entity=entity,
                     entity_id=entity_id, store_id=store_id, details=details)
    session.add(entry)
    session.flush()
    return entry
