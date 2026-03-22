from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CrewMember:
    id: str
    name: str
    role: str
    # skill levels are stored as x/10, essentially a rating
    skills: Dict[str, str] = field(default_factory=dict)


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
