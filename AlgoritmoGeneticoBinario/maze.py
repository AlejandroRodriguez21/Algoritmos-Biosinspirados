from collections import deque
from dataclasses import dataclass
import random


# Cada movimiento se codifica con exactamente dos bits.
DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))
ARROWS = ("↑", "→", "↓", "←")


@dataclass(frozen=True)
class Maze:
    rows: tuple[str, ...]
    start: tuple[int, int]
    goal: tuple[int, int]

    def __post_init__(self):
        if not self.rows or not self.rows[0]:
            raise ValueError("El laberinto no puede estar vacío.")
        if any(len(row) != self.width for row in self.rows):
            raise ValueError("Las filas deben tener el mismo ancho.")
        if any(cell not in "#." for row in self.rows for cell in row):
            raise ValueError("Usa # para muros y . para pasillos.")
        if not self.is_open(self.start) or not self.is_open(self.goal):
            raise ValueError("La entrada y la salida deben estar en pasillos.")
        if self.start == self.goal:
            raise ValueError("La entrada y la salida deben ser diferentes.")
        if self.start not in self.distances():
            raise ValueError("No existe conexión entre la entrada y la salida.")

    @property
    def width(self):
        return len(self.rows[0])

    @property
    def height(self):
        return len(self.rows)

    def is_open(self, position):
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height and self.rows[y][x] != "#"

    def move(self, position, direction):
        dx, dy = DIRECTIONS[direction]
        candidate = (position[0] + dx, position[1] + dy)
        return candidate if self.is_open(candidate) else position

    def distances(self):
        """BFS calcula distancias para aptitud y verificación, nunca cromosomas."""
        result = {self.goal: 0}
        queue = deque([self.goal])
        while queue:
            position = queue.popleft()
            for direction in range(4):
                neighbor = self.move(position, direction)
                if neighbor not in result:
                    result[neighbor] = result[position] + 1
                    queue.append(neighbor)
        return result


def generate_maze(seed=42, width=19, height=13):
    """DFS aleatorio con aperturas extra: pasillos conectados y rutas alternativas."""
    if width < 5 or height < 5 or width % 2 == 0 or height % 2 == 0:
        raise ValueError("Las dimensiones deben ser impares y al menos 5.")
    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]
    grid[1][1] = "."
    stack = [(1, 1)]
    while stack:
        x, y = stack[-1]
        candidates = []
        for dx, dy in DIRECTIONS:
            nx, ny = x + 2 * dx, y + 2 * dy
            if 0 < nx < width - 1 and 0 < ny < height - 1 and grid[ny][nx] == "#":
                candidates.append((nx, ny, dx, dy))
        if not candidates:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(candidates)
        grid[y + dy][x + dx] = grid[ny][nx] = "."
        stack.append((nx, ny))
    # Abre algunos muros interiores para que existan recorridos de distinta longitud.
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == "#" and (x + y) % 2 == 1 and rng.random() < 0.23:
                grid[y][x] = "."
    return Maze(tuple("".join(row) for row in grid), (1, 1), (width - 2, height - 2))
