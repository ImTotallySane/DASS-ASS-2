from typing import Dict, List, Optional

from .models import Car


_VALID_CONDITIONS = {"good", "damaged", "repairing", "retired"}

_cash_balance: int = 0
_cars: Dict[str, Car] = {}
_spare_parts: Dict[str, int] = {}
_tools: Dict[str, int] = {}


def _validate_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")


def _normalize_name(value: str, field_name: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError(f"{field_name} must be non-empty")
    return clean


def _normalize_condition(condition: str) -> str:
    c = (condition or "").strip().lower()
    if c not in _VALID_CONDITIONS:
        raise ValueError(f"invalid condition: {condition}")
    return c


def set_cash_balance(amount: int) -> None:
    global _cash_balance
    _validate_non_negative_int(amount, "amount")
    _cash_balance = amount


def get_cash_balance() -> int:
    return _cash_balance


def adjust_cash(delta: int) -> int:
    global _cash_balance
    if not isinstance(delta, int):
        raise ValueError("delta must be an integer")
    new_balance = _cash_balance + delta
    if new_balance < 0:
        raise ValueError("cash balance cannot go below zero")
    _cash_balance = new_balance
    return _cash_balance


def add_car(car_id: str, model: str, condition: str = "good") -> None:
    cid = _normalize_name(car_id, "car_id")
    model_name = _normalize_name(model, "model")
    if cid in _cars:
        raise ValueError(f"car already exists: {cid}")
    _cars[cid] = Car(
        id=cid,
        model=model_name,
        condition=_normalize_condition(condition),
    )


def get_car(car_id: str) -> Optional[Car]:
    cid = _normalize_name(car_id, "car_id")
    return _cars.get(cid)


def list_cars() -> List[Car]:
    return list(_cars.values())


def update_car_condition(car_id: str, condition: str) -> None:
    cid = _normalize_name(car_id, "car_id")
    car = _cars.get(cid)
    if car is None:
        raise KeyError(f"car not found: {cid}")
    car.condition = _normalize_condition(condition)


def add_spare_part(part_name: str, qty: int = 1) -> None:
    name = _normalize_name(part_name, "part_name")
    _validate_positive_int(qty, "qty")
    _spare_parts[name] = _spare_parts.get(name, 0) + qty


def use_spare_part(part_name: str, qty: int = 1) -> None:
    name = _normalize_name(part_name, "part_name")
    _validate_positive_int(qty, "qty")
    available = _spare_parts.get(name, 0)
    if available < qty:
        raise ValueError(f"not enough spare parts: {name}")
    remaining = available - qty
    if remaining == 0:
        _spare_parts.pop(name, None)
    else:
        _spare_parts[name] = remaining


def get_part_qty(part_name: str) -> int:
    name = _normalize_name(part_name, "part_name")
    return _spare_parts.get(name, 0)


def list_spare_parts() -> Dict[str, int]:
    return dict(_spare_parts)


def add_tool(tool_name: str, qty: int = 1) -> None:
    name = _normalize_name(tool_name, "tool_name")
    _validate_positive_int(qty, "qty")
    _tools[name] = _tools.get(name, 0) + qty


def use_tool(tool_name: str, qty: int = 1) -> None:
    name = _normalize_name(tool_name, "tool_name")
    _validate_positive_int(qty, "qty")
    available = _tools.get(name, 0)
    if available < qty:
        raise ValueError(f"not enough tools: {name}")
    remaining = available - qty
    if remaining == 0:
        _tools.pop(name, None)
    else:
        _tools[name] = remaining


def get_tool_qty(tool_name: str) -> int:
    name = _normalize_name(tool_name, "tool_name")
    return _tools.get(name, 0)


def list_tools() -> Dict[str, int]:
    return dict(_tools)


def clear_inventory() -> None:
    global _cash_balance
    _cash_balance = 0
    _cars.clear()
    _spare_parts.clear()
    _tools.clear()
