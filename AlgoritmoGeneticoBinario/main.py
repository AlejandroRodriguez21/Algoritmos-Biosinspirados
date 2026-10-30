"""Ejecuta este archivo para abrir el laboratorio visual de evolución."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from genetic import Config, GeneticSolver
from maze import ARROWS, generate_maze


BACKGROUND = "#f2f5fa"
INK = "#172b46"
MUTED = "#65768e"
BLUE = "#2563eb"
GREEN = "#13a889"


def result_data(maze, config, best, generation, optimal_steps):
    return {
        "laberinto": list(maze.rows), "entrada": maze.start, "salida": maze.goal,
        "configuracion": asdict(config), "generacion": generation,
        "salida_alcanzada": best.solved,
        "optimo_comprobado": best.solved and best.used_steps == optimal_steps,
        "minimo_teorico_pasos": optimal_steps, "pasos_ejecutados": best.used_steps,
        "distancia_restante": best.distance, "choques": best.collisions,
        "aptitud": best.fitness, "cromosoma": "".join(map(str, best.genome)),
        "bits_del_recorrido": "".join(map(str, best.genome[:best.used_steps * 2])),
        "codificacion": {"00": "arriba", "01": "derecha", "10": "abajo", "11": "izquierda"},
        "movimientos": [ARROWS[move] for move in best.moves], "recorrido": best.path,
        "nota": "BFS solo aporta distancias a la aptitud y comprueba la longitud mínima. "
                "La secuencia procede de la población genética y su reparación de ciclos.",
    }


class Application:
    def __init__(self, root):
        self.root = root
        root.title("Laberinto evolutivo · Algoritmo genético binario")
        root.geometry(f"{min(1180, root.winfo_screenwidth() - 80)}x{min(850, root.winfo_screenheight() - 100)}")
        root.minsize(960, 650)
        root.configure(bg=BACKGROUND)
        self.maze_seed = 42
        self.maze = generate_maze(self.maze_seed)
        self.best = None
        self.config = None
        self.generation = 0
        self.optimal_steps = self.maze.distances()[self.maze.start]
        self.history = []
        self.messages = queue.SimpleQueue()
        self.cancel = threading.Event()
        self.gate = threading.Event()
        self.run_id = 0
        self.running = self.paused = False
        self.animation_id = None
        self.animation_index = None
        self.entries = {}
        self.build_ui()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(60, self.poll)

    def label(self, parent, text, size=10, color=INK, bold=False, **kwargs):
        return tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else "normal"),
                        bg=parent.cget("bg"), fg=color, **kwargs)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 5))
        style.configure("Primary.TButton", background=BLUE, foreground="white")
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#a6bbeb")])
        style.configure("TEntry", padding=5)
        header = tk.Frame(self.root, bg=INK, padx=24, pady=12)
        header.pack(fill="x")
        self.label(header, "LABORATORIO DE EVOLUCIÓN", 9, "#80b9ff", True).pack(anchor="w")
        self.label(header, "Un genoma. Miles de rutas posibles.", 22, "white", True).pack(anchor="w")
        self.label(header, "Observa cómo una población de secuencias binarias aprende a llegar a la salida.",
                   11, "#c0cede").pack(anchor="w", pady=(3, 0))
        body = tk.Frame(self.root, bg=BACKGROUND, padx=18, pady=16)
        body.pack(fill="both", expand=True)
        sidebar_box = tk.Frame(body, bg="white")
        sidebar_box.pack(side="left", fill="y", padx=(0, 16))
        sidebar_canvas = tk.Canvas(sidebar_box, width=290, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar_box, orient="vertical", command=sidebar_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        sidebar_canvas.pack(side="left", fill="y", expand=True)
        sidebar_canvas.configure(yscrollcommand=scrollbar.set)
        sidebar = tk.Frame(sidebar_canvas, bg="white", padx=14, pady=12)
        sidebar_window = sidebar_canvas.create_window(0, 0, window=sidebar, anchor="nw")
        sidebar.bind("<Configure>", lambda event: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_canvas.bind("<Configure>", lambda event: sidebar_canvas.itemconfigure(sidebar_window, width=event.width))
        self.label(sidebar, "01 / CONFIGURACIÓN", 12, INK, True).pack(anchor="w", pady=(0, 8))
        fields = (("population", "Individuos", "180"), ("generations", "Máximo de generaciones", "500"),
                  ("steps", "Movimientos por cromosoma", "160"),
                  ("mutation", "Mutación por bit (0–1)", "0.015"),
                  ("crossover", "Probabilidad de cruce (0–1)", "0.85"),
                  ("seed", "Semilla del algoritmo", "42"))
        form = tk.Frame(sidebar, bg="white")
        form.pack(fill="x")
        for index, (name, title, default) in enumerate(fields):
            field = tk.Frame(form, bg="white")
            field.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 5), pady=3)
            form.columnconfigure(index % 2, weight=1, uniform="fields")
            self.label(field, title, 9, MUTED, wraplength=118, height=2, anchor="w", justify="left").pack(anchor="w")
            entry = ttk.Entry(field, width=12)
            entry.insert(0, default)
            entry.pack(fill="x")
            self.entries[name] = entry
        self.start_button = ttk.Button(sidebar, text="▶  Iniciar evolución", style="Primary.TButton", command=self.start)
        self.start_button.pack(fill="x", pady=(12, 6))
        self.pause_button = ttk.Button(sidebar, text="Pausar", command=self.pause, state="disabled")
        self.pause_button.pack(fill="x", pady=3)
        ttk.Button(sidebar, text="Reiniciar", command=self.reset).pack(fill="x", pady=3)
        ttk.Button(sidebar, text="Nuevo laberinto", command=self.new_maze).pack(fill="x", pady=3)
        self.replay_button = ttk.Button(sidebar, text="Reproducir mejor ruta", command=self.replay, state="disabled")
        self.replay_button.pack(fill="x", pady=(12, 3))
        self.export_button = ttk.Button(sidebar, text="Guardar resultado JSON", command=self.export, state="disabled")
        self.export_button.pack(fill="x", pady=3)
        self.label(sidebar, "EL CROMOSOMA", 10, INK, True).pack(anchor="w", pady=(18, 5))
        self.label(sidebar, "00 ↑    01 →    10 ↓    11 ←", 11, BLUE, True).pack(anchor="w")
        self.label(sidebar, "Cada par de bits es una instrucción.\nUn choque consume un paso.\nLa evolución conserva las mejores rutas.",
                   9, MUTED, justify="left").pack(anchor="w", pady=(6, 0))

        content = tk.Frame(body, bg=BACKGROUND)
        content.pack(side="left", fill="both", expand=True)
        cards = tk.Frame(content, bg=BACKGROUND)
        cards.pack(fill="x")
        self.metrics = {}
        for index, (key, title, initial) in enumerate((
            ("generation", "GENERACIÓN", "0 / 500"), ("distance", "DISTANCIA A SALIDA", "—"),
            ("steps", "PASOS DE LA RUTA", "—"), ("optimal", "MÍNIMO TEÓRICO", str(self.optimal_steps)))):
            card = tk.Frame(cards, bg="white", padx=12, pady=10)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 6 if index < 3 else 0))
            cards.columnconfigure(index, weight=1)
            self.label(card, title, 8, MUTED, True).pack(anchor="w")
            value = self.label(card, initial, 19, BLUE, True)
            value.pack(anchor="w")
            self.metrics[key] = value
        board = tk.Frame(content, bg="white", padx=12, pady=10)
        board.pack(fill="both", expand=True, pady=(12, 0))
        self.label(board, "02 / EXPLORACIÓN DEL LABERINTO", 11, INK, True).pack(anchor="w")
        self.canvas = tk.Canvas(board, bg="white", highlightthickness=0, height=300)
        self.canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas.bind("<Configure>", lambda event: self.draw_maze())
        self.label(board, "E · Entrada     S · Salida     Azul · Mejor recorrido     Naranja · Agente", 9, MUTED).pack(anchor="w")
        self.status = self.label(content, "Listo. Presiona «Iniciar evolución» para crear la primera población.",
                                 10, INK, anchor="w", justify="left", wraplength=760)
        self.status.pack(fill="x", pady=10)
        chart_box = tk.Frame(content, bg="white", padx=12, pady=10)
        chart_box.pack(fill="x")
        self.label(chart_box, "03 / APTITUD POR GENERACIÓN", 11, INK, True).pack(anchor="w")
        self.chart = tk.Canvas(chart_box, height=95, bg="white", highlightthickness=0)
        self.chart.pack(fill="x")
        self.chart.bind("<Configure>", lambda event: self.draw_chart())
        self.label(chart_box, "Azul: mejor individuo · Verde: promedio · Mayor aptitud es mejor", 9, MUTED).pack(anchor="w")
        self.sequence = tk.Text(content, height=3, wrap="word", font=("Consolas", 10),
                                relief="flat", bg="#e6edf7", fg=INK, padx=10, pady=8)
        self.sequence.pack(fill="x", pady=(10, 0))
        self.set_sequence("Aquí aparecerán los bits y los movimientos del mejor recorrido.")

    def set_sequence(self, text):
        self.sequence.configure(state="normal")
        self.sequence.delete("1.0", "end")
        self.sequence.insert("1.0", text)
        self.sequence.configure(state="disabled")

    def read_config(self):
        values = {key: entry.get().strip() for key, entry in self.entries.items()}
        try:
            return Config(**{key: float(value.replace(",", ".")) if key in ("mutation", "crossover") else int(value)
                             for key, value in values.items()})
        except (ValueError, OverflowError) as error:
            raise ValueError("Revisa los parámetros numéricos.\n" + str(error)) from error

    def start(self):
        try:
            config = self.read_config()
            if config.steps < self.optimal_steps:
                raise ValueError(f"Este laberinto necesita al menos {self.optimal_steps} movimientos por cromosoma.")
        except ValueError as error:
            messagebox.showerror("Configuración inválida", str(error), parent=self.root)
            return
        self.reset()
        self.config = config
        self.running = True
        self.gate.set()
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        for entry in self.entries.values():
            entry.configure(state="disabled")
        self.status.configure(text="Creando población binaria aleatoria…")
        threading.Thread(target=self.evolve, args=(self.run_id, self.maze, config, self.cancel, self.gate),
                         daemon=True).start()

    def evolve(self, run_id, maze, config, cancel, gate):
        # El hilo de cálculo solo escribe en la cola; Tkinter vive en el hilo principal.
        try:
            solver = GeneticSolver(maze, config)
            self.messages.put((run_id, "progress", (solver.best, 0, solver.history[-1], solver.finished)))
            while not solver.finished and not cancel.is_set():
                if not gate.wait(0.1):
                    continue
                if cancel.is_set():
                    return
                solver.step()
                self.messages.put((run_id, "progress", (solver.best, solver.generation, solver.history[-1], solver.finished)))
                # Breve intervalo para que la evolución sea visible, interrumpible al reiniciar.
                if cancel.wait(0.12):
                    return
        except Exception as error:
            self.messages.put((run_id, "error", str(error)))

    def poll(self):
        try:
            while True:
                run_id, kind, payload = self.messages.get_nowait()
                if run_id != self.run_id:
                    continue
                if kind == "error":
                    self.finish_controls()
                    self.status.configure(text="No se pudo completar la ejecución.")
                    messagebox.showerror("Error de ejecución", payload, parent=self.root)
                    continue
                self.best, self.generation, point, finished = payload
                self.history.append(point)
                self.update_result(finished)
        except queue.Empty:
            pass
        self.root.after(60, self.poll)

    def finish_controls(self):
        self.running = self.paused = False
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pausar")
        for entry in self.entries.values():
            entry.configure(state="normal")

    def update_result(self, finished):
        best = self.best
        self.metrics["generation"].configure(text=f"{self.generation} / {self.config.generations}")
        self.metrics["distance"].configure(text=str(best.distance))
        self.metrics["steps"].configure(text=str(best.used_steps))
        bits = " ".join("".join(map(str, best.genome[i:i + 2])) for i in range(0, best.used_steps * 2, 2))
        self.set_sequence(f"BITS  {bits or '—'}\nRUTA  {' '.join(ARROWS[move] for move in best.moves) or '—'}")
        optimal = best.solved and best.used_steps == self.optimal_steps
        if optimal:
            text = f"Óptimo comprobado: salida alcanzada en {best.used_steps} pasos, sin superar el mínimo teórico."
        elif finished and best.solved:
            text = f"Límite alcanzado. Mejor solución: {best.used_steps} pasos; mínimo teórico: {self.optimal_steps}."
        elif finished:
            text = "Límite alcanzado sin llegar a la salida. Prueba más generaciones, más pasos u otra semilla."
        elif best.solved:
            text = f"Salida encontrada en {best.used_steps} pasos. La evolución sigue buscando una ruta más corta."
        else:
            text = f"Evolucionando… mejor prefijo a {best.distance} celdas de la salida. Choques: {best.collisions}."
        self.status.configure(text=("En pausa. " if self.paused else "") + text)
        self.draw_maze()
        self.draw_chart()
        self.export_button.configure(state="normal")
        if finished:
            self.finish_controls()
            self.replay_button.configure(state="normal")
            self.replay()

    def pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if self.paused:
            self.gate.clear()
            self.status.configure(text="En pausa. Puedes continuar o reiniciar la evolución.")
        else:
            self.gate.set()
            self.status.configure(text="Continuando la evolución…")
        self.pause_button.configure(text="Continuar" if self.paused else "Pausar")

    def stop_animation(self):
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
        self.animation_id = self.animation_index = None

    def reset(self):
        self.cancel.set()
        self.gate.set()
        self.run_id += 1
        self.cancel, self.gate = threading.Event(), threading.Event()
        self.stop_animation()
        self.best = None
        self.history = []
        self.generation = 0
        self.finish_controls()
        self.replay_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        for key in ("distance", "steps"):
            self.metrics[key].configure(text="—")
        self.metrics["generation"].configure(text="0")
        self.metrics["optimal"].configure(text=str(self.optimal_steps))
        self.status.configure(text=f"Listo. Laberinto con semilla {self.maze_seed}; mínimo teórico: {self.optimal_steps} pasos.")
        self.set_sequence("Aquí aparecerán los bits y los movimientos del mejor recorrido.")
        self.draw_maze()
        self.draw_chart()

    def new_maze(self):
        self.maze_seed += 1
        self.maze = generate_maze(self.maze_seed)
        self.optimal_steps = self.maze.distances()[self.maze.start]
        self.reset()

    def draw_maze(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        cell = min((width - 10) / self.maze.width, (height - 10) / self.maze.height)
        if cell <= 0:
            return
        ox, oy = (width - cell * self.maze.width) / 2, (height - cell * self.maze.height) / 2

        def center(position):
            return ox + (position[0] + 0.5) * cell, oy + (position[1] + 0.5) * cell

        for y, row in enumerate(self.maze.rows):
            for x, value in enumerate(row):
                x1, y1 = ox + x * cell, oy + y * cell
                canvas.create_rectangle(x1, y1, x1 + cell, y1 + cell,
                                        fill=INK if value == "#" else "#f1f5fc", outline="white", width=1)
        path = self.best.path if self.best else (self.maze.start,)
        visible = path if self.animation_index is None else path[:self.animation_index + 1]
        if len(visible) > 1:
            coords = [coordinate for position in visible for coordinate in center(position)]
            canvas.create_line(*coords, fill="#639bff", width=max(3, cell * 0.24), capstyle="round", joinstyle="round")
        for position, text, color in ((self.maze.start, "E", BLUE), (self.maze.goal, "S", GREEN)):
            cx, cy = center(position)
            radius = cell * 0.42
            canvas.create_rectangle(cx - radius, cy - radius, cx + radius, cy + radius, fill=color, outline="")
            canvas.create_text(cx, cy, text=text, fill="white", font=("Segoe UI", max(8, int(cell * 0.45)), "bold"))
        cx, cy = center(visible[-1])
        radius = cell * 0.22
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#ffb344", outline="white", width=2)

    def draw_chart(self):
        canvas = self.chart
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 80:
            return
        left, right, top, bottom = 48, width - 12, 12, height - 18
        if not self.history:
            canvas.create_text(width / 2, height / 2, text="La gráfica aparecerá al iniciar.", fill=MUTED)
            return
        minimum = min(point[1] for point in self.history)
        maximum = max(point[0] for point in self.history)
        span = max(1, maximum - minimum)
        for value, y in ((maximum, top), (minimum, bottom)):
            canvas.create_line(left, y, right, y, fill="#e6edf7")
            canvas.create_text(left - 6, y, text=f"{value:.0f}", anchor="e", fill=MUTED, font=("Segoe UI", 8))
        for column, color in ((1, GREEN), (0, BLUE)):
            coords = []
            for index, point in enumerate(self.history):
                coords.extend((left + (right - left) * index / max(1, len(self.history) - 1),
                               bottom - (point[column] - minimum) / span * (bottom - top)))
            if len(coords) >= 4:
                canvas.create_line(*coords, fill=color, width=2)
            else:
                x, y = coords
                canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
        canvas.create_text(left, height - 5, text="0", fill=MUTED, font=("Segoe UI", 8))
        canvas.create_text(right, height - 5, text=str(self.generation), fill=MUTED, font=("Segoe UI", 8))

    def replay(self):
        if not self.best or self.running:
            return
        self.stop_animation()
        self.animation_index = 0

        def tick():
            self.draw_maze()
            if self.animation_index < len(self.best.path) - 1:
                self.animation_index += 1
                self.animation_id = self.root.after(110, tick)
            else:
                self.animation_id = None
        tick()

    def export(self):
        if self.best is None:
            return
        filename = filedialog.asksaveasfilename(parent=self.root, title="Guardar resultado",
                                              defaultextension=".json", initialfile="resultado_laberinto.json",
                                              filetypes=[("Resultado JSON", "*.json")])
        if filename:
            try:
                data = result_data(self.maze, self.config, self.best, self.generation, self.optimal_steps)
                Path(filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self.status.configure(text=f"Resultado guardado en {filename}")
            except OSError as error:
                messagebox.showerror("No se pudo guardar", str(error), parent=self.root)

    def close(self):
        self.cancel.set()
        self.gate.set()
        self.stop_animation()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Algoritmo genético binario para un laberinto 2D.")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana")
    parser.add_argument("--seed", type=int, default=42, help="Semilla del laberinto y del algoritmo en modo consola")
    parser.add_argument("--generations", type=int, default=500, help="Límite de generaciones en modo consola")
    parser.add_argument("--export", type=Path, help="Guardar JSON en modo consola")
    args = parser.parse_args()
    if args.headless:
        maze = generate_maze(args.seed)
        config = Config(seed=args.seed, generations=args.generations)
        solver = GeneticSolver(maze, config)
        best = solver.run()
        data = result_data(maze, config, best, solver.generation, solver.optimal_steps)
        if args.export:
            args.export.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Salida alcanzada: {best.solved} | Optimo comprobado: {solver.optimal}")
        print(f"Generacion: {solver.generation} | Pasos: {best.used_steps} | Minimo: {solver.optimal_steps}")
        print("Bits: " + data["bits_del_recorrido"])
    else:
        root = tk.Tk()
        Application(root)
        root.mainloop()


if __name__ == "__main__":
    main()
