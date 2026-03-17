from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CrewMember:
    id: str
    name: str
    role: str
    # skill levels are stored as x/10, essentially a rating
    skills: Dict[str, str] = field(default_factory=dict)
