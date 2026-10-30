import unittest

from genetic import Config, GeneticSolver
from main import result_data
from maze import Maze, generate_maze


def encode(moves):
    return tuple(bit for move in moves for bit in (move >> 1, move & 1))


class GeneticTests(unittest.TestCase):
    def setUp(self):
        self.maze = Maze(("#####", "#...#", "#####"), (1, 1), (3, 1))
        self.solver = GeneticSolver(self.maze, Config(population=20, steps=6, generations=15))

    def test_two_bits_per_move_and_stop_at_exit(self):
        individual = self.solver.evaluate(encode([1, 1, 3, 3, 0, 0]))
        self.assertTrue(individual.solved)
        self.assertEqual(individual.moves, (1, 1))
        self.assertEqual(individual.path, ((1, 1), (2, 1), (3, 1)))

    def test_wall_collision_consumes_step(self):
        individual = self.solver.evaluate(encode([0, 1, 1, 0, 0, 0]))
        self.assertTrue(individual.solved)
        self.assertEqual(individual.used_steps, 3)
        self.assertEqual(individual.collisions, 1)
        self.assertEqual(individual.path[:2], ((1, 1), (1, 1)))

    def test_best_prefix_is_retained(self):
        individual = self.solver.evaluate(encode([1, 3, 0, 0, 0, 0]))
        self.assertFalse(individual.solved)
        self.assertEqual(individual.distance, 1)
        self.assertEqual(individual.used_steps, 1)
        self.assertEqual(individual.path[-1], (2, 1))

    def test_fitness_prefers_success_then_fewer_steps(self):
        quick = self.solver.evaluate(encode([1, 1, 0, 0, 0, 0]))
        slow = self.solver.evaluate(encode([0, 0, 0, 0, 1, 1]))
        partial = self.solver.evaluate(encode([1, 0, 0, 0, 0, 0]))
        self.assertGreater(quick.fitness, slow.fitness)
        self.assertGreater(slow.fitness, partial.fitness)

    def test_repair_removes_loops_and_collisions(self):
        original = self.solver.evaluate(encode([0, 1, 3, 1, 1, 0]))
        repaired = self.solver.evaluate(self.solver.repair_prefix(original))
        self.assertEqual(repaired.used_steps, 2)
        self.assertEqual(repaired.collisions, 0)
        self.assertTrue(repaired.solved)
        self.assertEqual(len(repaired.genome), 12)

    def test_elitism_and_binary_population(self):
        solver = GeneticSolver(generate_maze(2), Config(population=30, steps=80, generations=15))
        previous = solver.best.fitness
        while not solver.finished:
            solver.step()
            self.assertGreaterEqual(solver.best.fitness, previous)
            previous = solver.best.fitness
            self.assertEqual(len(solver.population), 30)
            for individual in solver.population:
                self.assertEqual(len(individual.genome), 160)
                self.assertLessEqual(set(individual.genome), {0, 1})

    def test_seed_reproduces_evolution(self):
        config = Config(population=30, generations=6, steps=90, seed=5)
        first = GeneticSolver(generate_maze(2), config)
        second = GeneticSolver(generate_maze(2), config)
        self.assertEqual(first.run(), second.run())
        self.assertEqual(first.history, second.history)

    def test_default_finds_verified_optimum(self):
        solver = GeneticSolver(generate_maze(), Config())
        best = solver.run()
        self.assertTrue(solver.optimal)
        position = solver.maze.start
        for move, expected in zip(best.moves, best.path[1:]):
            position = solver.maze.move(position, move)
            self.assertEqual(position, expected)
        self.assertEqual(position, solver.maze.goal)
        self.assertEqual(best.used_steps, solver.optimal_steps)

    def test_generation_limit_without_solution(self):
        solver = GeneticSolver(generate_maze(2), Config(population=20, steps=1, generations=3))
        solver.run()
        self.assertTrue(solver.finished)
        self.assertFalse(solver.best.solved)
        self.assertEqual(solver.generation, 3)

    def test_maze_generation_and_validation(self):
        for seed in range(10):
            maze = generate_maze(seed)
            self.assertIn(maze.start, maze.distances())
            self.assertEqual(maze, generate_maze(seed))
        with self.assertRaises(ValueError):
            Maze(("#####", "#.#.#", "#####"), (1, 1), (3, 1))
        with self.assertRaises(ValueError):
            Config(population=1)
        with self.assertRaises(ValueError):
            Config(mutation=float("nan"))

    def test_export_matches_individual(self):
        best = self.solver.run()
        data = result_data(self.maze, self.solver.config, best, self.solver.generation, 2)
        self.assertEqual(len(data["bits_del_recorrido"]), best.used_steps * 2)
        self.assertEqual(len(data["cromosoma"]), 12)
        self.assertEqual(data["salida_alcanzada"], best.solved)


if __name__ == "__main__":
    unittest.main()
