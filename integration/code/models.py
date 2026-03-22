from dataclasses import dataclass
from typing import Optional


@dataclass
class CrewMember:
    id: str
    name: str
    role: str
    # One role-linked proficiency level from 0..10.
    skill_level: int = 0
    # Personal cash balance for payout tracking.
    money: int = 0


@dataclass
class Car:
    id: str
    model: str
    condition: str = "good"


@dataclass
class RaceEntry:
    driver: CrewMember
    car: Car
    note: Optional[str] = None
