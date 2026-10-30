"""Algoritmo de Colonia de Hormigas (ACO) para el problema del viajante.

Ejecutar: python ant_colony.py
No requiere instalar bibliotecas externas.
"""

import math
import random


# Coordenadas de las ciudades (ejemplo reproducible).
CIUDADES = {
    "A": (0, 0),
    "B": (2, 6),
    "C": (5, 3),
    "D": (7, 8),
    "E": (9, 1),
    "F": (12, 5),
    "G": (4, 10),
    "H": (11, 11),
}

NUM_HORMIGAS = 20
ITERACIONES = 100
ALFA = 1.0              # Influencia de la feromona.
BETA = 3.0              # Influencia de la distancia (visibilidad).
EVAPORACION = 0.5      # Proporcion de feromona que se evapora.
DEPOSITO = 100.0       # Feromona aportada en funcion de la ruta.
SEMILLA = 42           # Hace reproducible el ejemplo.


def matriz_distancias(coordenadas):
    """Calcula las distancias euclidianas entre todas las ciudades."""
    return [
        [math.dist(a, b) for b in coordenadas]
        for a in coordenadas
    ]


def longitud_ruta(ruta, distancias):
    """Suma el recorrido, incluido el regreso a la ciudad inicial."""
    return sum(
        distancias[ruta[i]][ruta[(i + 1) % len(ruta)]]
        for i in range(len(ruta))
    )


def construir_ruta(distancias, feromonas, generador):
    """Una hormiga escoge su siguiente ciudad por feromona y cercania."""
    n = len(distancias)
    ruta = [generador.randrange(n)]
    pendientes = set(range(n)) - set(ruta)

    while pendientes:
        actual = ruta[-1]
        opciones = sorted(pendientes)
        pesos = [
            (feromonas[actual][j] ** ALFA)
            * ((1.0 / distancias[actual][j]) ** BETA)
            for j in opciones
        ]
        siguiente = generador.choices(opciones, weights=pesos, k=1)[0]
        ruta.append(siguiente)
        pendientes.remove(siguiente)

    return ruta


def ejecutar_aco():
    """Realiza iteraciones de exploracion, evaporacion y deposito."""
    nombres = list(CIUDADES)
    distancias = matriz_distancias(list(CIUDADES.values()))
    n = len(nombres)
    feromonas = [[1.0 for _ in range(n)] for _ in range(n)]
    generador = random.Random(SEMILLA)
    mejor_ruta = []
    mejor_distancia = float("inf")

    print("ALGORITMO ANT COLONY OPTIMIZATION (ACO)")
    print("Problema: visitar todas las ciudades y regresar al origen")
    print(f"Ciudades: {', '.join(nombres)}")
    print(f"Hormigas: {NUM_HORMIGAS} | Iteraciones: {ITERACIONES}\n")

    for iteracion in range(1, ITERACIONES + 1):
        recorridos = []
        for _ in range(NUM_HORMIGAS):
            ruta = construir_ruta(distancias, feromonas, generador)
            distancia = longitud_ruta(ruta, distancias)
            recorridos.append((ruta, distancia))
            if distancia < mejor_distancia:
                mejor_ruta, mejor_distancia = ruta[:], distancia

        # Evaporacion: reduce la influencia de rutas antiguas.
        for i in range(n):
            for j in range(n):
                if i != j:
                    feromonas[i][j] *= 1.0 - EVAPORACION
                    feromonas[i][j] = max(feromonas[i][j], 1e-12)

        # Deposito: las rutas cortas refuerzan mas sus conexiones.
        for ruta, distancia in recorridos:
            aporte = DEPOSITO / distancia
            for i in range(n):
                a, b = ruta[i], ruta[(i + 1) % n]
                feromonas[a][b] += aporte
                feromonas[b][a] += aporte

        if iteracion == 1 or iteracion % 10 == 0:
            print(f"Iteracion {iteracion:>3}: mejor distancia = {mejor_distancia:.2f}")

    camino = mejor_ruta + [mejor_ruta[0]]
    print("\nRESULTADO FINAL")
    print("Mejor ruta encontrada:", " -> ".join(nombres[i] for i in camino))
    print(f"Distancia total: {mejor_distancia:.2f} unidades")
    print("Nota: ACO es una metaheuristica; no garantiza el optimo absoluto.")


if __name__ == "__main__":
    ejecutar_aco()
