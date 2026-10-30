import random
import math

# 1. Definir la Función Objetivo (Antígeno)
# Buscamos el mínimo de f(x, y) = x^2 + y^2
def objective_function(position):
    return sum([x**2 for x in position])

# 2. Clase Anticuerpo (Posible solución)
class Antibody:
    def __init__(self, bounds, position=None):
        # Si no se da una posición, se genera aleatoriamente
        if position is None:
            self.position = [random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]
        else:
            self.position = list(position)
            
        self.score = float('inf')
        self.affinity = 0.0

    def evaluate(self, func):
        self.score = func(self.position)
        # Para minimización: un score menor significa mayor afinidad.
        # Sumamos 1 para evitar divisiones por cero.
        self.affinity = 1.0 / (1.0 + self.score)

# 3. Función de Hipermutación
def mutate(antibody, bounds, mutation_rate):
    mutated_pos = []
    for i in range(len(bounds)):
        # Mutación gaussiana: alteramos el valor actual
        step = random.gauss(0, 1) * mutation_rate * (bounds[i][1] - bounds[i][0])
        new_val = antibody.position[i] + step
        
        # Asegurarnos de no salirnos de los límites
        new_val = max(bounds[i][0], min(new_val, bounds[i][1]))
        mutated_pos.append(new_val)
        
    return Antibody(bounds, mutated_pos)

# 4. Algoritmo de Selección Clonal (CLONALG)
def clonalg(objective_function, bounds, pop_size, max_iter):
    # Parámetros del sistema inmune
    clone_factor = 0.5   # Factor que determina la cantidad de clones
    rho = 2.5            # Factor de decaimiento para la hipermutación
    num_replace = int(pop_size * 0.15) # 15% de anticuerpos nuevos en cada ciclo (diversidad)
    
    # Inicializar población de anticuerpos
    population = [Antibody(bounds) for _ in range(pop_size)]
    
    global_best_position = []
    global_best_score = float('inf')

    for iteration in range(max_iter):
        # Evaluar la población actual
        for ab in population:
            ab.evaluate(objective_function)
            
        # Ordenar por afinidad (de mayor a menor)
        population.sort(key=lambda x: x.affinity, reverse=True)
        
        # Actualizar al mejor encontrado
        if population[0].score < global_best_score:
            global_best_score = population[0].score
            global_best_position = list(population[0].position)

        # Selección y Clonación (solo los mejores se reproducen)
        num_select = int(pop_size * 0.5)
        selected = population[:num_select]
        
        mutated_clones = []
        
        for i, ab in enumerate(selected):
            # Proporcionalidad: El mejor (rango 1) produce más clones que los demás
            num_clones = max(1, int((clone_factor * pop_size) / (i + 1)))
            
            for _ in range(num_clones):
                # Hipermutación: 
                # Alta afinidad -> Baja tasa de mutación (ajuste fino)
                # Baja afinidad -> Alta tasa de mutación (exploración)
                mutation_rate = math.exp(-rho * ab.affinity)
                
                # Crear el clon mutado
                clon_mutado = mutate(ab, bounds, mutation_rate)
                clon_mutado.evaluate(objective_function)
                mutated_clones.append(clon_mutado)

        # Unir la población original con los clones mutados y ordenarlos
        next_generation = population + mutated_clones
        next_generation.sort(key=lambda x: x.affinity, reverse=True)
        
        # Quedarnos solo con los "pop_size" mejores para la siguiente generación
        population = next_generation[:pop_size]
        
        # Reemplazo / Diversidad (Receptor Editing): 
        # Matamos a los peores anticuerpos y metemos sangre nueva aleatoria
        for i in range(pop_size - num_replace, pop_size):
            population[i] = Antibody(bounds)
            population[i].evaluate(objective_function)

        # Imprimir progreso cada 10 iteraciones
        if (iteration + 1) % 10 == 0 or iteration == 0:
            print(f"Iteración {iteration+1}: Mejor valor global = {global_best_score:.6f}")

    return global_best_position, global_best_score

# ==========================================
# Ejecución del programa
# ==========================================
if __name__ == "__main__":
    # Configuración del espacio de búsqueda: 2 dimensiones, de -10 a 10
    bounds = [(-10, 10), (-10, 10)] 
    
    # Configuración de la población
    pop_size = 40
    max_iter = 50

    print("Iniciando Sistema Inmune Artificial (CLONALG)...")
    best_pos, best_score = clonalg(objective_function, bounds, pop_size, max_iter)

    print("\n=== RESULTADO FINAL ===")
    print(f"Anticuerpo óptimo encontrado: [x: {best_pos[0]:.6f}, y: {best_pos[1]:.6f}]")
    print(f"Valor mínimo de la función (Antígeno neutralizado): {best_score:.6f}")