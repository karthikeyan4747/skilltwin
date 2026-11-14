"""Grid Game verification: replay a learner's move list on a 5x5 grid with walls."""

from typing import Literal

from pydantic import BaseModel

Move = Literal["up", "down", "left", "right"]
GRID_SIZE = 5
MAX_MOVES = 200
DELTAS: dict[str, tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class GridLevel(BaseModel):
    id: str
    title: str
    start: tuple[int, int]
    goal: tuple[int, int]
    walls: list[tuple[int, int]]
    hint: str


def replay(level: GridLevel, moves: list[Move]) -> bool:
    """True when the moves reach the goal; bumping a wall or the edge leaves you in place."""
    if len(moves) > MAX_MOVES:
        return False
    walls = set(level.walls)
    x, y = level.start
    for move in moves:
        dx, dy = DELTAS[move]
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
            x, y = nx, ny
        if (x, y) == level.goal:
            return True
    return (x, y) == level.goal
