from typing import TypedDict, List

class DocHit(TypedDict):
    point_id: int
    snippet: str
    score: float