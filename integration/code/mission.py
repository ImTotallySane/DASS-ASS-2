# Mission Planning module (independent).

from typing import Dict, List, Optional
import uuid


_DEFAULT_ROLE_RULES: Dict[str, List[str]] = {
    "delivery": ["driver"],
    "rescue": [],
    "planning": ["strategist"],
    "repair": ["mechanic"],
}

_missions: Dict[str, Dict] = {}


def _normalize_text(value: str, field_name: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError(f"{field_name} must be non-empty")
    return clean


def _default_roles_for_type(mission_type: str) -> List[str]:
    return _DEFAULT_ROLE_RULES.get(mission_type, [])[:]


def create_mission(
    mission_type: str,
    title: str,
    has_damaged_car: bool = False,
) -> str:
    """Create a mission and return mission id.

    Required roles are always derived from mission type defaults.
    If `has_damaged_car` is True, mechanic requirement is auto-enforced.
    """
    mtype = _normalize_text(mission_type, "mission_type").lower()
    mtitle = _normalize_text(title, "title")

    roles = _default_roles_for_type(mtype)

    if has_damaged_car and "mechanic" not in roles:
        roles.append("mechanic")

    mission_id = uuid.uuid4().hex
    _missions[mission_id] = {
        "id": mission_id,
        "type": mtype,
        "title": mtitle,
        "required_roles": sorted(set(roles)),
        "has_damaged_car": bool(has_damaged_car),
        "status": "planned",
        "assignee_ids": [],
    }
    return mission_id


def list_missions() -> List[Dict]:
    return list(_missions.values())


def get_mission(mission_id: str) -> Optional[Dict]:
    return _missions.get(mission_id)


def assign_mission(mission_id: str, assignee_ids: List[str]) -> Dict:
    """Attach assignee ids to a mission (ids only, no module lookups)."""
    mission = _missions.get(mission_id)
    if mission is None:
        raise KeyError(f"mission not found: {mission_id}")
    if not isinstance(assignee_ids, list):
        raise ValueError("assignee_ids must be a list")

    clean_ids: List[str] = []
    for aid in assignee_ids:
        clean_ids.append(_normalize_text(str(aid), "assignee_id"))

    mission["assignee_ids"] = clean_ids
    return dict(mission)


def evaluate_mission_readiness(mission_id: str, available_roles: List[str]) -> Dict:
    """Evaluate whether mission can start based on provided available roles.

    Returns a structured response with status and reasons.
    """
    mission = _missions.get(mission_id)
    if mission is None:
        raise KeyError(f"mission not found: {mission_id}")
    if not isinstance(available_roles, list):
        raise ValueError("available_roles must be a list of role strings")

    normalized_available = {str(r).strip().lower() for r in available_roles if str(r).strip()}
    required_roles = mission["required_roles"]

    missing = [role for role in required_roles if role not in normalized_available]
    if missing:
        return {
            "mission_id": mission_id,
            "can_start": False,
            "status": "blocked",
            "missing_roles": missing,
            "reason": f"missing required roles: {', '.join(missing)}",
        }

    return {
        "mission_id": mission_id,
        "can_start": True,
        "status": "ready",
        "missing_roles": [],
        "reason": "all required roles are available",
    }


def start_mission(mission_id: str, available_roles: List[str]) -> Dict:
    """Start mission if readiness checks pass; return structured status."""
    mission = _missions.get(mission_id)
    if mission is None:
        raise KeyError(f"mission not found: {mission_id}")
    if mission["status"] == "completed":
        return {
            "mission_id": mission_id,
            "started": False,
            "status": "completed",
            "reason": "mission already completed",
        }

    check = evaluate_mission_readiness(mission_id, available_roles)
    if not check["can_start"]:
        return {
            "mission_id": mission_id,
            "started": False,
            "status": "blocked",
            "reason": check["reason"],
            "missing_roles": check["missing_roles"],
        }

    mission["status"] = "in_progress"
    return {
        "mission_id": mission_id,
        "started": True,
        "status": "in_progress",
        "reason": "mission started",
        "missing_roles": [],
    }


def complete_mission(mission_id: str, outcome: str = "success") -> Dict:
    mission = _missions.get(mission_id)
    if mission is None:
        raise KeyError(f"mission not found: {mission_id}")

    final_outcome = _normalize_text(outcome, "outcome").lower()
    mission["status"] = "completed"
    mission["outcome"] = final_outcome
    return dict(mission)


def clear_missions() -> None:
    _missions.clear()
