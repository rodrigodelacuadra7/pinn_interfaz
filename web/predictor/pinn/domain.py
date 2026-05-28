DOMAIN = {
    'N_pisos':          {'min': 6,    'max': 18,  'tipo': 'int'},
    'n_unid_lado':      {'min': 2,    'max': 6,   'tipo': 'int'},
    'activar_B2':       {'set': [0, 1]},
    'L_mod_m':          {'min': 3.20, 'max': 3.80, 'tipo': 'float'},
    'prof_depto_m':     {'min': 7.00, 'max': 7.90, 'tipo': 'float'},
    'ancho_corredor_m': {'min': 1.50, 'max': 1.90, 'tipo': 'float'},
    'L_nucleo_m':       {'min': 5.40, 'max': 6.60, 'tipo': 'float'},
    'B_nucleo_m':       {'min': 4.00, 'max': 5.00, 'tipo': 'float'},
    'h_story_m':        {'set': [2.60, 2.70, 2.80, 2.90]},
    'fc_MPa':           {'set': [25, 30, 35, 40]},
    'gk_kN_m2':         {'set': [6.0, 6.5, 7.0, 7.5]},
    't_muro_nucleo_m':  {'set': [0.18, 0.20, 0.22, 0.25, 0.28, 0.30]},
    't_muro_borde_m':   {'set': [0.18, 0.20, 0.22, 0.25, 0.28, 0.30]},
    't_muro_mid_m':     {'set': [0.15, 0.18, 0.20, 0.22, 0.25]},
    'suelo':            {'set': ['A', 'B', 'C', 'D']},
    'zona':             {'set': [1, 2, 3]},
}

DEFAULTS_SIMPLE = dict(
    activar_B2=1, L_mod_m=3.50, prof_depto_m=7.50, ancho_corredor_m=1.70,
    L_nucleo_m=6.00, B_nucleo_m=4.50, h_story_m=2.70, gk_kN_m2=7.0,
    t_muro_nucleo_m=0.25, t_muro_borde_m=0.25, t_muro_mid_m=0.20,
)

DRIFT_LIMIT_NCh433 = 0.002


def validar_dominio(params):
    """Devuelve (lista de avisos, bandera de fuera de dominio grave)."""
    avisos = []
    grave = False
    for k, dom in DOMAIN.items():
        if k not in params:
            continue
        v = params[k]
        if 'set' in dom and v not in dom['set']:
            avisos.append(f"'{k}={v}' fuera del catálogo {dom['set']}")
            grave = True
        elif 'min' in dom:
            if v < dom['min'] or v > dom['max']:
                avisos.append(f"'{k}={v}' fuera del rango [{dom['min']}, {dom['max']}]")
                if k == 'N_pisos':
                    grave = True
    return avisos, grave
