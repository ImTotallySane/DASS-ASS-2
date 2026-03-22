# Crew Management Module

from typing import Optional

from .models import CrewMember


_VALID_ROLES = {"driver", "mechanic", "strategist", "gambler", "other"}


def normalize_role(role: Optional[str]) -> str:
    # Normalize and validate a role.
    if role is None:
        raise ValueError("role must be provided and non-empty")
    r = (role or "").strip().lower()
    if r in _VALID_ROLES:
        return r
    raise ValueError(f"invalid role: {role}")


def change_role(member: CrewMember, new_role: str) -> None:
    # Change the role of the given CrewMember.
    member.role = normalize_role(new_role)


def change_rating(member: CrewMember, level: int) -> None:
    # Set or update the member's role-linked skill level (0..10).
    if not isinstance(level, int):
        raise ValueError("level must be an integer 0..10")
    if level < 0 or level > 10:
        raise ValueError("level must be between 0 and 10 inclusive")
    member.skill_level = level


def get_skill(member: CrewMember) -> str:
    """Return the role-linked skill level as x/10."""
    return f"{member.skill_level}/10"
