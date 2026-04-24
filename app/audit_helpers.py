from .models import AuditLog, db


def log_action(actor, action, entity_type, entity_id=None, description=''):
    """Record a row in the audit log.

    `actor` may be a user object with a `username` attribute, a plain string, or None.
    """
    if actor is None:
        actor_name = 'system'
    elif isinstance(actor, str):
        actor_name = actor
    else:
        actor_name = getattr(actor, 'username', None) or 'system'

    entry = AuditLog(
        actor=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
