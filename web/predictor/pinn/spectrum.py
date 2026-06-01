"""
Espectro de diseño NCh433 Mod.Of2012 + DS61  (Art. 6.3.5).
Devuelve curvas elástica y de diseño, límites Sa_min/Sa_max y factor R*.
"""

# ── Constantes globales ───────────────────────────────────────────────────────
_I      = 1.00   # factor de importancia (categoría II)
_Ro     = 11.0   # sistema de muros de hormigón armado
_G      = 9.81   # m/s²

# ── Parámetros de suelo — Tabla 6.3 NCh433 + DS61 ─────────────────────────────
_SOIL_PARAMS = {
    'A': {'S': 0.90, 'T0': 0.15, 'Tp': 0.20, 'n': 1.00, 'p': 2.00},
    'B': {'S': 1.00, 'T0': 0.30, 'Tp': 0.35, 'n': 1.33, 'p': 1.50},
    'C': {'S': 1.05, 'T0': 0.40, 'Tp': 0.45, 'n': 1.40, 'p': 1.60},
    'D': {'S': 1.20, 'T0': 0.75, 'Tp': 0.85, 'n': 1.80, 'p': 1.00},
}

# ── Aceleración efectiva A0 — Tabla 6.2 NCh433 ───────────────────────────────
_ZONE_A0 = {1: 0.20, 2: 0.30, 3: 0.40}


def _Rstar(T_star, T0, Ro=_Ro):
    """Factor de reducción R* — NCh433 Art. 6.3.5.3."""
    T_star = max(T_star, 1e-6)
    den = 0.10 * T0 + T_star / (Ro - 1.0)
    return 1.0 + T_star / den


def _alpha(T, Tp, n):
    """Factor de amplificación α — NCh433 Ec. 6-9."""
    x = max(T, 0.0) / Tp
    return (1.0 + 4.5 * x ** n) / (1.0 + x ** 3)


def espectro_nch433(zona, suelo, T_star=None, T_max=4.0, n_pts=200):
    """
    Calcula espectro de diseño NCh433 Art. 6.3.5.

    Parámetros
    ----------
    zona    : int   zona sísmica (1, 2 o 3)
    suelo   : str   tipo de suelo (A, B, C o D)
    T_star  : float período fundamental del edificio (para calcular R*)
    T_max   : float período máximo de la grilla (s)
    n_pts   : int   número de puntos

    Retorna
    -------
    dict con claves:
        T            : lista de períodos
        Sa_elastic_g : Sa elástico / g  (sin reducción)
        Sa_design_g  : Sa diseño / g    (con R* y límites)
        Sa_min_g     : límite inferior Sa/g
        Sa_max_g     : límite superior Sa/g
        Rstar        : factor de reducción calculado con T_star
        A0_g         : aceleración efectiva en g
        S, T0, Tp    : parámetros del suelo
    """
    A0 = _ZONE_A0.get(int(zona), 0.30)
    sp = _SOIL_PARAMS.get(str(suelo).upper(), _SOIL_PARAMS['C'])
    S, T0, Tp, n = sp['S'], sp['T0'], sp['Tp'], sp['n']

    Tstar = T_star if (T_star and T_star > 0) else 0.5
    Rstar = _Rstar(Tstar, T0)

    Sa_min = S * A0 * _I / 6.0
    Sa_max = 0.35 * S * A0

    Ts, Sa_e_list, Sa_d_list = [], [], []
    for i in range(n_pts):
        T = 0.02 + (i / (n_pts - 1)) * (T_max - 0.02)
        alpha = _alpha(T, Tp, n)
        Sa_e  = S * A0 * alpha * _I
        Sa_d  = max(Sa_min, min(Sa_max, Sa_e / Rstar))
        Ts.append(round(T, 4))
        Sa_e_list.append(round(Sa_e, 5))
        Sa_d_list.append(round(Sa_d, 5))

    return {
        'T':            Ts,
        'Sa_elastic_g': Sa_e_list,
        'Sa_design_g':  Sa_d_list,
        'Sa_min_g':     round(Sa_min, 5),
        'Sa_max_g':     round(Sa_max, 5),
        'Rstar':        round(Rstar, 4),
        'A0_g':         A0,
        'S':            S,
        'T0':           T0,
        'Tp':           Tp,
    }
