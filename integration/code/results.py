# Results module.

from typing import Dict, List, Optional

from .models import RaceEntry


_results_by_race: Dict[str, List[Dict]] = {}


def _validate_prize_pool(prize_pool: int) -> None:
    if not isinstance(prize_pool, int) or prize_pool < 0:
        raise ValueError("prize_pool must be a non-negative integer")


def calculate_payouts(ordered_driver_ids: List[str], prize_pool: int) -> Dict[str, int]:
    # Calculate 50/30/20 payouts for top 3 in provided finish order.
    _validate_prize_pool(prize_pool)
    payouts = {driver_id: 0 for driver_id in ordered_driver_ids}
    if not ordered_driver_ids or prize_pool == 0:
        return payouts

    shares = [0.5, 0.3, 0.2]
    for index, share in enumerate(shares):
        if index >= len(ordered_driver_ids):
            break
        payouts[ordered_driver_ids[index]] = int(prize_pool * share)
    return payouts


def record_results(race_id: str, ordered_entries: List[RaceEntry], prize_pool: int) -> List[Dict]:
    # Record final race results in manual finish order.
    if not race_id or not isinstance(race_id, str):
        raise ValueError("race_id must be a non-empty string")
    if not isinstance(ordered_entries, list) or not ordered_entries:
        raise ValueError("ordered_entries must be a non-empty list")
    _validate_prize_pool(prize_pool)

    for entry in ordered_entries:
        if not isinstance(entry, RaceEntry):
            raise ValueError("ordered_entries must contain RaceEntry objects")

    ordered_driver_ids = [entry.driver.id for entry in ordered_entries]
    payouts = calculate_payouts(ordered_driver_ids, prize_pool)

    rows: List[Dict] = []
    for position, entry in enumerate(ordered_entries, start=1):
        rows.append(
            {
                "position": position,
                "driver_id": entry.driver.id,
                "car_id": entry.car.id,
                "payout": payouts.get(entry.driver.id, 0),
            }
        )

    _results_by_race[race_id] = rows
    return rows


def get_results(race_id: str) -> Optional[List[Dict]]:
    # Return recorded results for a race id, or None if absent.
    return _results_by_race.get(race_id)


def list_results() -> Dict[str, List[Dict]]:
    # Return all recorded results keyed by race id.
    return dict(_results_by_race)


def clear_results() -> None:
    _results_by_race.clear()
