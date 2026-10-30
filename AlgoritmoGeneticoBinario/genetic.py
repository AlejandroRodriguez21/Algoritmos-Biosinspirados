"""Algoritmo genético binario independiente de la interfaz gráfica."""

from dataclasses import dataclass
import random

from maze import Maze, DIRECTIONS


@dataclass(frozen=True)
class Config:
    population: int = 180
    generations: int = 500
    steps: int = 160
    mutation: float = 0.015
    crossover: float = 0.85
    seed: int = 42

    def __post_init__(self):
        if not 20 <= self.population <= 1000:
            raise ValueError("La población debe estar entre 20 y 1000.")
        if not 1 <= self.generations <= 10000:
            raise ValueError("Las generaciones deben estar entre 1 y 10000.")
        if not 1 <= self.steps <= 2000:
            raise ValueError("Los pasos deben estar entre 1 y 2000.")
        if not 0 <= self.mutation <= 1 or not 0 <= self.crossover <= 1:
            raise ValueError("Las probabilidades deben estar entre 0 y 1.")


@dataclass(frozen=True)
class Individual:
    genome: tuple[int, ...]
    fitness: int
    distance: int
    used_steps: int
    path: tuple[tuple[int, int], ...]
    collisions: int

    @property
    def solved(self):
        return self.distance == 0

    @property
    def moves(self):
        return tuple(2 * self.genome[i] + self.genome[i + 1]
                     for i in range(0, 2 * self.used_steps, 2))


class GeneticSolver:
    def __init__(self, maze: Maze, config: Config):
        self.maze = maze
        self.config = config
        self.rng = random.Random(config.seed)
        self.distances = maze.distances()
        self.optimal_steps = self.distances[maze.start]
        self.generation = 0
        self.stagnation = 0
        self.history = []
        self.population = [self.evaluate(self.random_genome()) for _ in range(config.population)]
        self.population.sort(key=lambda item: item.fitness, reverse=True)
        self.best = self.population[0]
        self.record()

    def random_genome(self):
        return tuple(self.rng.getrandbits(1) for _ in range(self.config.steps * 2))

    def evaluate(self, genome):
        """Puntúa el mejor prefijo: acercamiento primero, menos pasos después.

        Si choca, el agente permanece en su celda y consume una instrucción.
        Se detiene al alcanzar la salida. Los genes posteriores quedan inactivos.
        """
        position = self.maze.start
        path = [position]
        best_distance = self.optimal_steps
        best_step = 0
        collisions = best_collisions = 0
        for step in range(self.config.steps):
            direction = genome[2 * step] * 2 + genome[2 * step + 1]
            next_position = self.maze.move(position, direction)
            collisions += next_position == position
            position = next_position
            path.append(position)
            distance = self.distances.get(position, self.maze.width * self.maze.height)
            if distance < best_distance:
                best_distance, best_step, best_collisions = distance, step + 1, collisions
            if distance == 0:
                break
        fitness = ((self.optimal_steps - best_distance) * (self.config.steps + 1)
                   + self.config.steps - best_step)
        return Individual(tuple(genome), fitness, best_distance, best_step,
                          tuple(path[:best_step + 1]), best_collisions)

    @property
    def optimal(self):
        return self.best.solved and self.best.used_steps == self.optimal_steps

    @property
    def finished(self):
        return self.optimal or self.generation >= self.config.generations

    def tournament(self):
        return max(self.rng.sample(self.population, 4), key=lambda item: item.fitness)

    def repair_prefix(self, individual):
        """Elimina choques y ciclos del recorrido ya descubierto y extiende al azar.

        No consulta distancias ni construye una ruta con BFS. Solo reutiliza
        celdas que este individuo ya visitó, como operador de reparación.
        """
        route = [self.maze.start]
        indices = {self.maze.start: 0}
        for position in individual.path[1:]:
            if position in indices:
                index = indices[position]
                for removed in route[index + 1:]:
                    del indices[removed]
                del route[index + 1:]
            else:
                indices[position] = len(route)
                route.append(position)
        bits = []
        for previous, current in zip(route, route[1:]):
            delta = (current[0] - previous[0], current[1] - previous[1])
            direction = DIRECTIONS.index(delta)
            bits.extend((direction >> 1, direction & 1))
        bits.extend(self.rng.getrandbits(1) for _ in range(2 * self.config.steps - len(bits)))
        return bits

    def step(self):
        if self.finished:
            return self.best
        elite_count = max(2, self.config.population // 20)
        next_population = self.population[:elite_count]
        # Aumenta la exploración cuando la mejor aptitud deja de mejorar.
        mutation = min(1.0, self.config.mutation * (1 + self.stagnation / 30))
        while len(next_population) < self.config.population:
            parent = self.tournament()
            if self.rng.random() < 0.3:
                child = self.repair_prefix(parent)
            else:
                child = list(parent.genome)
                if self.rng.random() < self.config.crossover:
                    other = self.tournament()
                    cut = self.rng.randrange(1, len(child))
                    child[cut:] = other.genome[cut:]
                for index in range(len(child)):
                    if self.rng.random() < mutation:
                        child[index] ^= 1
            next_population.append(self.evaluate(child))
        next_population.sort(key=lambda item: item.fitness, reverse=True)
        self.population = next_population
        if self.population[0].fitness > self.best.fitness:
            self.best = self.population[0]
            self.stagnation = 0
        else:
            self.stagnation += 1
        self.generation += 1
        self.record()
        return self.best

    def record(self):
        self.history.append((self.best.fitness,
                             sum(item.fitness for item in self.population) / len(self.population)))

    def run(self):
        while not self.finished:
            self.step()
        return self.best
