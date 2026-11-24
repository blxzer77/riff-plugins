AUDIT_EVENTS: list[dict] = []


def record_audit(actor: str, action: str, target: str) -> None:
    AUDIT_EVENTS.append({"actor": actor, "action": action, "target": target})
