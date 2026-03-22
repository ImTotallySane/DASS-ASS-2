# Race Management module

from typing import Dict, List, Optional
import uuid

from .models import Car, CrewMember, RaceEntry

_races: Dict[str, Dict] = {}


def create_race(name: str, prize_pool: int = 0, entries: Optional[List[RaceEntry]] = None) -> str:
    # Create a race record and return its id.

    if not name or not isinstance(name, str):
        raise ValueError("race name must be a non-empty string")
    if not isinstance(prize_pool, int) or prize_pool < 0:
        raise ValueError("prize_pool must be a non-negative integer")
    rid = uuid.uuid4().hex
    _races[rid] = {
        "id": rid,
        "name": name,
        "entries": entries[:] if entries else [],
        "status": "created",
        "prize_pool": prize_pool,
    }
    return rid


def add_entry(race_id: str, driver: CrewMember, car: Car, note: Optional[str] = None) -> None:
    """Add an entrant to an existing race.

    The function does not validate driver roles beyond trusting the caller;
    integration should ensure only valid drivers are passed.
    """
    race = _races.get(race_id)
    if race is None:
        raise KeyError(f"race not found: {race_id}")
    race["entries"].append(RaceEntry(driver=driver, car=car, note=note))


def remove_entry(race_id: str, driver_id: str) -> None:
    race = _races.get(race_id)
    if race is None:
        raise KeyError(f"race not found: {race_id}")
    before = len(race["entries"])
    race["entries"] = [e for e in race["entries"] if e.driver.id != driver_id]
    if len(race["entries"]) == before:
        raise KeyError(f"entry for driver not found: {driver_id}")


def list_races() -> List[Dict]:
    return list(_races.values())


def get_race(race_id: str) -> Optional[Dict]:
    return _races.get(race_id)


def clear_races() -> None:
    _races.clear()
