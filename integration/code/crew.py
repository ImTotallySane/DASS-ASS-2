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


def change_rating(member: CrewMember, skill: str, level: int) -> None:
    # Set or update a member's skill rating as 'x/10'.
    if not isinstance(level, int):
        raise ValueError("level must be an integer 0..10")
    if level < 0 or level > 10:
        raise ValueError("level must be between 0 and 10 inclusive")
    if not skill or not isinstance(skill, str):
        raise ValueError("skill name must be a non-empty string")
    member.skills[skill] = f"{level}/10"


def get_skill(member: CrewMember, skill: str) -> Optional[str]:
    """Return the rating string for a skill or None if not set."""
    return member.skills.get(skill)
