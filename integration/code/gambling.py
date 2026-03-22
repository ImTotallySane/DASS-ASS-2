# Gambling module (independent).

from typing import Dict, List, Optional

from .models import CrewMember


_bets_by_race: Dict[str, List[Dict]] = {}


def _normalize_id(value: str, field_name: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError(f"{field_name} must be non-empty")
    return clean


def _validate_amount(amount: int) -> None:
    if not isinstance(amount, int):
        raise ValueError("amount must be an integer")
    if amount <= 0:
        raise ValueError("amount must be greater than 0")


def _race_bets(race_id: str) -> List[Dict]:
    return _bets_by_race.setdefault(race_id, [])


def place_bet(race_id: str, bettor: CrewMember, racer_id: str, amount: int) -> Dict:
    """Place a bet for one racer in one race.

    Constraints:
    - bettor must have role 'gambler'
    - only one total bettor can bet on a given racer in a race
    """
    rid = _normalize_id(race_id, "race_id")
    target_racer = _normalize_id(racer_id, "racer_id")
    _validate_amount(amount)

    if not isinstance(bettor, CrewMember):
        raise ValueError("bettor must be a CrewMember")
    if bettor.role.strip().lower() != "gambler":
        raise ValueError("only bettors with role 'gambler' can place bets")

    bets = _race_bets(rid)
    existing_on_racer = next((b for b in bets if b["racer_id"] == target_racer), None)
    if existing_on_racer is not None:
        raise ValueError(f"a bet already exists for racer: {target_racer}")

    bet = {
        "race_id": rid,
        "bettor_id": bettor.id,
        "bettor_name": bettor.name,
        "racer_id": target_racer,
        "amount": amount,
        "status": "open",
    }
    bets.append(bet)
    return dict(bet)


def list_bets(race_id: str) -> List[Dict]:
    rid = _normalize_id(race_id, "race_id")
    return [dict(b) for b in _bets_by_race.get(rid, [])]


def get_bet_for_racer(race_id: str, racer_id: str) -> Optional[Dict]:
    rid = _normalize_id(race_id, "race_id")
    target_racer = _normalize_id(racer_id, "racer_id")
    bet = next((b for b in _bets_by_race.get(rid, []) if b["racer_id"] == target_racer), None)
    if bet is None:
        return None
    return dict(bet)


def total_pool(race_id: str) -> int:
    rid = _normalize_id(race_id, "race_id")
    return sum(b["amount"] for b in _bets_by_race.get(rid, []))


def settle_bets(race_id: str, winning_racer_id: str) -> Dict:
    """Settle race bets and return payout information.

    Winner gets entire pool.
    Since one-bet-per-racer is enforced, winner is either one bettor or none.
    """
    rid = _normalize_id(race_id, "race_id")
    winner_racer = _normalize_id(winning_racer_id, "winning_racer_id")

    bets = _bets_by_race.get(rid, [])
    pool = sum(b["amount"] for b in bets)
    winner_bet = next((b for b in bets if b["racer_id"] == winner_racer), None)

    settled_rows: List[Dict] = []
    for bet in bets:
        is_winner = winner_bet is not None and bet is winner_bet
        settled_rows.append(
            {
                "bettor_id": bet["bettor_id"],
                "racer_id": bet["racer_id"],
                "amount": bet["amount"],
                "won": bool(is_winner),
                "payout": pool if is_winner else 0,
            }
        )
        bet["status"] = "settled"

    return {
        "race_id": rid,
        "winning_racer_id": winner_racer,
        "pool": pool,
        "winner_bettor_id": winner_bet["bettor_id"] if winner_bet else None,
        "winner_payout": pool if winner_bet else 0,
        "results": settled_rows,
    }


def clear_bets(race_id: Optional[str] = None) -> None:
    if race_id is None:
        _bets_by_race.clear()
        return
    rid = _normalize_id(race_id, "race_id")
    _bets_by_race.pop(rid, None)
