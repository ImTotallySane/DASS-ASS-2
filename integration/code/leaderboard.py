"""Leaderboard display helpers.

This module is read-only and expects the CLI (or integrator) to own and provide
stats dictionaries. No local leaderboard state is stored here.
"""

from typing import Dict, List, Optional


def get_racer_stats(racers_stats: Dict[str, Dict], driver_id: str) -> Optional[Dict]:
    """Return a single racer stats row by driver id."""
    if not racers_stats:
        return None
    row = racers_stats.get(driver_id)
    return dict(row) if row is not None else None


def get_gambler_stats(gamblers_stats: Dict[str, Dict], bettor_id: str) -> Optional[Dict]:
    """Return a single gambler stats row by bettor id."""
    if not gamblers_stats:
        return None
    row = gamblers_stats.get(bettor_id)
    if row is None:
        return None
    result = dict(row)
    # Compute net_profit on read if it is not already present.
    if "net_profit" not in result:
        total_payouts = int(result.get("total_payouts", 0) or 0)
        total_staked = int(result.get("total_staked", 0) or 0)
        result["net_profit"] = total_payouts - total_staked
    return result


def list_racers(racers_stats: Dict[str, Dict]) -> Dict[str, Dict]:
    """Return a shallow copy of all racer stats rows."""
    if not racers_stats:
        return {}
    return {k: dict(v) for k, v in racers_stats.items()}


def list_gamblers(gamblers_stats: Dict[str, Dict]) -> Dict[str, Dict]:
    """Return a shallow copy of all gambler stats rows."""
    if not gamblers_stats:
        return {}
    out: Dict[str, Dict] = {}
    for bettor_id, row in gamblers_stats.items():
        copied = dict(row)
        if "net_profit" not in copied:
            total_payouts = int(copied.get("total_payouts", 0) or 0)
            total_staked = int(copied.get("total_staked", 0) or 0)
            copied["net_profit"] = total_payouts - total_staked
        out[bettor_id] = copied
    return out


def top_racers(racers_stats: Dict[str, Dict], n: int = 10, by: str = "points") -> List[Dict]:
    """Return top N racers sorted descending by the provided key."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if by not in {"points", "wins", "total_earnings"}:
        raise ValueError(f"unsupported sort key: {by}")

    items = list_racers(racers_stats).values()
    ranked = sorted(items, key=lambda r: int(r.get(by, 0) or 0), reverse=True)
    return ranked[:n]


def top_gamblers(gamblers_stats: Dict[str, Dict], n: int = 10, by: str = "net_profit") -> List[Dict]:
    """Return top N gamblers sorted descending by the provided key."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if by not in {"net_profit", "wins", "total_payouts"}:
        raise ValueError(f"unsupported sort key: {by}")

    items = list_gamblers(gamblers_stats).values()
    ranked = sorted(items, key=lambda g: int(g.get(by, 0) or 0), reverse=True)
    return ranked[:n]
