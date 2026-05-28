import numpy as np


def construir_X(params, COLS_BASE):
    """Convierte el dict de parámetros en el vector X de 21 features sin normalizar."""
    x = np.zeros(21, dtype=np.float32)
    x[COLS_BASE.index('N_pisos')]          = params['N_pisos']
    x[COLS_BASE.index('n_unid_lado')]      = params['n_unid_lado']
    x[COLS_BASE.index('activar_B2')]       = params['activar_B2']
    x[COLS_BASE.index('L_mod_m')]          = params['L_mod_m']
    x[COLS_BASE.index('prof_depto_m')]     = params['prof_depto_m']
    x[COLS_BASE.index('ancho_corredor_m')] = params['ancho_corredor_m']
    x[COLS_BASE.index('L_nucleo_m')]       = params['L_nucleo_m']
    x[COLS_BASE.index('B_nucleo_m')]       = params['B_nucleo_m']
    x[COLS_BASE.index('h_story_m')]        = params['h_story_m']
    x[COLS_BASE.index('fc_MPa')]           = params['fc_MPa']
    x[COLS_BASE.index('gk_kN_m2')]         = params['gk_kN_m2']
    x[COLS_BASE.index('t_muro_nucleo_m')]  = params['t_muro_nucleo_m']
    x[COLS_BASE.index('t_muro_borde_m')]   = params['t_muro_borde_m']
    x[COLS_BASE.index('t_muro_mid_m')]     = params['t_muro_mid_m']
    x[COLS_BASE.index(f"suelo_{params['suelo']}")] = 1
    x[COLS_BASE.index(f"zona_{params['zona']}")]   = 1

    mask = np.zeros(18, dtype=np.float32)
    mask[:int(params['N_pisos'])] = 1

    return x, mask
