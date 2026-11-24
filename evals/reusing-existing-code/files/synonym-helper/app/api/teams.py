from app.core.identity import canonicalize_account_slug

TEAMS: dict[str, dict] = {}


def create_team(name: str, owner_email: str) -> dict:
    slug = canonicalize_account_slug(name)
    team = {"slug": slug, "name": name.strip(), "owner_email": owner_email.strip().lower()}
    TEAMS[slug] = team
    return team
