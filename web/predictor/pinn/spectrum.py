"""
Espectro de respuesta elástica NCh433 analítico.
No depende del PINN — es una función del código sísmico.
"""

# Parámetros de suelo según NCh433
_SOIL_PARAMS = {
    'A': {'T0': 0.15, 'p': 2.0, 'S': 0.90},
    'B': {'T0': 0.30, 'p': 1.5, 'S': 1.00},
    'C': {'T0': 0.40, 'p': 1.6, 'S': 1.05},
    'D': {'T0': 0.75, 'p': 1.0, 'S': 1.20},
}

_ZONE_A0 = {1: 0.20, 2: 0.30, 3: 0.40}


def espectro_nch433(zona, suelo, T_max=4.0, n_pts=120):
    """
    Calcula el espectro de respuesta elástico Sa(T)/g según NCh433.

    Retorna lista de [T, Sa/g] para graficar.
    """
    A0 = _ZONE_A0.get(int(zona), 0.30)
    sp = _SOIL_PARAMS.get(str(suelo), _SOIL_PARAMS['C'])
    T0, p, S = sp['T0'], sp['p'], sp['S']

    points = []
    for i in range(n_pts):
        T = (i / (n_pts - 1)) * T_max + 0.02
        r = T / T0
        alpha = (1 + 4.5 * r ** p) / (1 + r ** 3)
        Sa = A0 * S * alpha
        points.append([round(T, 4), round(Sa, 5)])

    return points
