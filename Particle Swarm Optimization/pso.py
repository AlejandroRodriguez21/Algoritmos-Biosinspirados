import random

# 1. Definir la Función Objetivo (lo que queremos optimizar/minimizar)
# En este caso, la función de la Esfera: f(x, y) = x^2 + y^2
def objective_function(position):
    return sum([x**2 for x in position])

# 2. Clase Partícula
class Particle:
    def __init__(self, bounds):
        # Inicializar posición y velocidad aleatoria dentro de los límites
        self.position = [random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]
        self.velocity = [random.uniform(-1, 1) for _ in range(len(bounds))]
        
        # Mejor posición histórica de esta partícula en particular
        self.best_position = list(self.position)
        self.best_score = float('inf')

# 3. Algoritmo Principal PSO
def pso(objective_function, bounds, num_particles, max_iter):
    # Parámetros clásicos del PSO
    w = 0.5   # Factor de inercia (qué tanto mantiene su dirección actual)
    c1 = 1.5  # Coeficiente cognitivo (qué tanto sigue su propia mejor experiencia)
    c2 = 1.5  # Coeficiente social (qué tanto sigue al líder del enjambre)

    # Crear el enjambre de partículas
    particles = [Particle(bounds) for _ in range(num_particles)]
    
    # Rastrear al mejor de todo el enjambre
    global_best_position = []
    global_best_score = float('inf')

    # Bucle principal de optimización
    for i in range(max_iter):
        for particle in particles:
            # Evaluar la partícula actual
            score = objective_function(particle.position)

            # Actualizar el mejor personal de la partícula
            if score < particle.best_score:
                particle.best_score = score
                particle.best_position = list(particle.position)

            # Actualizar el mejor global del enjambre
            if score < global_best_score:
                global_best_score = score
                global_best_position = list(particle.position)

        # Mover las partículas
        for particle in particles:
            for j in range(len(bounds)):
                r1, r2 = random.random(), random.random()
                
                # Calcular las influencias
                cognitive = c1 * r1 * (particle.best_position[j] - particle.position[j])
                social = c2 * r2 * (global_best_position[j] - particle.position[j])
                
                # Actualizar velocidad y posición
                particle.velocity[j] = w * particle.velocity[j] + cognitive + social
                particle.position[j] += particle.velocity[j]

        # Imprimir progreso cada 10 iteraciones
        if (i + 1) % 10 == 0 or i == 0:
            print(f"Iteración {i+1}: Mejor valor global = {global_best_score:.6f}")

    return global_best_position, global_best_score

# ==========================================
# Ejecución del programa
# ==========================================
if __name__ == "__main__":
    # Configuración del espacio de búsqueda: 2 dimensiones, de -10 a 10
    bounds = [(-10, 10), (-10, 10)] 
    
    # Configuración del enjambre
    num_particles = 30
    max_iter = 50

    print("Iniciando Optimización por Enjambre de Partículas (PSO)...")
    best_pos, best_score = pso(objective_function, bounds, num_particles, max_iter)

    print("\n=== RESULTADO FINAL ===")
    print(f"Posición óptima encontrada: [x: {best_pos[0]:.6f}, y: {best_pos[1]:.6f}]")
    print(f"Valor mínimo de la función: {best_score:.6f}")