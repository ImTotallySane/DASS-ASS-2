from typing import Dict, List, Optional
import uuid

from .models import CrewMember

_VALID_ROLES = {"driver", "mechanic", "strategist", "gambler", "other"}

_members: Dict[str, CrewMember] = {}


def normalize_role(role: Optional[str]) -> str:
    # Normalize and validate a role.
    if role is None:
        raise ValueError("role must be provided and non-empty")
    r = (role or "").strip().lower()
    if r in _VALID_ROLES:
        return r
    raise ValueError(f"invalid role: {role}")


def register_member(name: str, role: str = "other") -> str:
    # Register a crew member and return their id.

    name = (name or "").strip()
    if not name:
        raise ValueError("name must be non-empty")
    role = normalize_role(role)
    member_id = uuid.uuid4().hex
    member = CrewMember(id=member_id, name=name, role=role)
    _members[member_id] = member
    return member_id


def get_member(member_id: str) -> Optional[CrewMember]:
    return _members.get(member_id)


def list_members() -> List[CrewMember]:
    return list(_members.values())


def clear_members() -> None:
    """clear in-memory members (test helper)."""
    _members.clear()
