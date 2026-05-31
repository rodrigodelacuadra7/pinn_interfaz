def enrich_params(params: dict) -> dict:
    """
    Enriquece el dict de 16 parámetros del usuario con los campos derivados
    que build_family_B_geometry (familia_B_core.py) requiere.

    Valores fijos del tipo Familia B:
      mods_por_depto = 2
      tech_bays_each_side = 1  →  tech_mods_each_side = 2
      gap_core_to_corridor_m = 0.0
      activar_B3 = 1 (por defecto)
    """
    p = dict(params)

    MODS_POR_DEPTO    = 2
    TECH_BAYS         = 1
    TECH_MODS         = TECH_BAYS * MODS_POR_DEPTO   # = 2
    GAP_CORE_CORRIDOR = 0.0

    n_mod_res_lado = MODS_POR_DEPTO * int(p['n_unid_lado'])   # 2 × n_unid_lado
    n_mod_lado     = n_mod_res_lado + TECH_MODS               # + 2
    n_mod_total    = 2 * n_mod_lado

    Lx = round(n_mod_total * float(p['L_mod_m']) + float(p['L_nucleo_m']), 3)
    Ly = round(2.0 * float(p['prof_depto_m']) + float(p['ancho_corredor_m']), 3)
    H  = int(p['N_pisos']) * float(p['h_story_m'])

    p['Lx_m']                   = Lx
    p['Ly_m']                   = Ly
    p['H_total_m']              = round(H, 3)
    p['A_geom_m2']              = round(Lx * Ly, 3)
    p['n_mod_izq']              = n_mod_lado
    p['n_mod_der']              = n_mod_lado
    p['n_mod_total']            = n_mod_total
    p['mods_por_depto']         = MODS_POR_DEPTO
    p['tech_mods_each_side']    = TECH_MODS
    p['prof_depto_sup_m']       = float(p['prof_depto_m'])
    p['prof_depto_inf_m']       = float(p['prof_depto_m'])
    p['gap_core_to_corridor_m'] = GAP_CORE_CORRIDOR
    p.setdefault('activar_B3', 1)

    return p
