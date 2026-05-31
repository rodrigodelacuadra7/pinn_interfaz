# ============================================================
# familia_B_core.py
# Archivo generado automáticamente desde Notebook 1
# ============================================================

import numpy as np
from pprint import pprint

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    _MPL = True
except ImportError:
    _MPL = False



def rect_dict(x, y, w, h, label="", group="", role="", direction=""):
    """Empaqueta un rectángulo en diccionario uniforme para ploteo."""
    return {
        "x": float(x), "y": float(y),
        "w": float(w), "h": float(h),
        "label": label, "group": group,
        "role": role,   "direction": direction
    }


def sample_from_spec(spec, rng):
    """Muestrea un valor según la especificación de la variable."""
    if spec["type"] == "int":
        return int(rng.integers(spec["min"], spec["max"] + 1))
    elif spec["type"] == "float":
        return float(rng.uniform(spec["min"], spec["max"]))
    elif spec["type"] == "choice":
        val = rng.choice(spec["values"])
        return val.item() if hasattr(val, "item") else val
    else:
        raise ValueError(f"Tipo no soportado: {spec['type']}")


def build_params_B(cfg, randomize=False, seed=42, overrides=None):
    """
    Construye el diccionario de parámetros completo de un edificio Familia B.

    Cambios incorporados:
    - Se reserva una bahía técnica del tamaño de un departamento a cada lado del núcleo
      en la franja superior.
    - El frente del núcleo, en la franja inferior, se declara como hall.
    - El resto de la planta se contabiliza como departamentos.
    """
    rng = np.random.default_rng(seed)
    p   = dict(cfg["defaults"])

    if randomize:
        for k, spec in cfg["variable_ranges"].items():
            p[k] = sample_from_spec(spec, rng)

    if overrides is not None:
        p.update(overrides)

    # ── Identidad fija ────────────────────────────────────────────────────
    p["mods_por_depto"]    = cfg["fixed"]["mods_por_depto"]
    p["tech_bays_each_side"] = cfg["fixed"].get("tech_bays_each_side", 1)
    p["tech_mods_each_side"] = p["tech_bays_each_side"] * p["mods_por_depto"]

    p["prof_depto_sup_m"]  = p["prof_depto_m"]
    p["prof_depto_inf_m"]  = p["prof_depto_m"]

    # ── Simetría: misma cantidad de módulos a ambos lados ─────────────────
    # n_unid_lado representa departamentos habitacionales por lado en la fila superior,
    # sin contar la bahía técnica contigua al núcleo.
    p["n_mod_res_lado"] = p["mods_por_depto"] * p["n_unid_lado"]
    p["n_mod_lado"]    = p["n_mod_res_lado"] + p["tech_mods_each_side"]

    p["n_mod_izq"]   = p["n_mod_lado"]
    p["n_mod_der"]   = p["n_mod_lado"]
    p["n_mod_total"] = p["n_mod_izq"] + p["n_mod_der"]

    # ── Conteos de unidades y departamentos ───────────────────────────────
    # Fila superior: se excluye la bahía técnica a cada lado del núcleo.
    p["n_unid_fila_sup"] = 2 * p["n_unid_lado"]

    # Fila inferior: todo lo que queda a ambos lados del hall central es departamento.
    p["n_unid_lado_inf"] = p["n_unid_lado"] + p["tech_bays_each_side"]
    p["n_unid_fila_inf"] = 2 * p["n_unid_lado_inf"]

    p["n_zonas_tecnicas_piso"] = 2 * p["tech_bays_each_side"]
    p["n_hall_piso"] = 1
    p["n_deptos_piso"] = p["n_unid_fila_sup"] + p["n_unid_fila_inf"]

    # ── Dimensiones globales ──────────────────────────────────────────────
    p["Lx_m"]      = p["n_mod_total"] * p["L_mod_m"] + p["L_nucleo_m"]
    p["Ly_m"]      = p["prof_depto_inf_m"] + p["ancho_corredor_m"] + p["prof_depto_sup_m"]
    p["H_total_m"] = p["N_pisos"] * p["h_story_m"]
    p["A_geom_m2"] = p["Lx_m"] * p["Ly_m"]
    p["aspect_ratio_Lx_Ly"] = p["Lx_m"] / p["Ly_m"]
    p["aspect_ratio_ok"]    = p["aspect_ratio_Lx_Ly"] >= cfg["fixed"]["aspect_ratio_min"]

    # ── Programa habitacional ─────────────────────────────────────────────
    p["A_unid_sup_geom_m2"] = p["mods_por_depto"] * p["L_mod_m"] * p["prof_depto_sup_m"]
    p["A_unid_inf_geom_m2"] = p["mods_por_depto"] * p["L_mod_m"] * p["prof_depto_inf_m"]

    p["A_util_sup_m2"] = p["n_unid_fila_sup"] * p["A_unid_sup_geom_m2"]
    p["A_util_inf_m2"] = p["n_unid_fila_inf"] * p["A_unid_inf_geom_m2"]
    p["A_util_m2"]     = p["A_util_sup_m2"] + p["A_util_inf_m2"]

    p["A_tecnica_m2"] = p["n_zonas_tecnicas_piso"] * p["mods_por_depto"] * p["L_mod_m"] * p["prof_depto_sup_m"]
    p["A_hall_m2"]    = p["L_nucleo_m"] * p["prof_depto_inf_m"]

    p["A_bruta_m2"] = p["A_util_m2"] / p["eficiencia_planta"]
    p["eff_real"]   = p["A_util_m2"] / p["A_geom_m2"]

    p["area_unid_sup_ok"] = (cfg["fixed"]["area_unidad_min_m2"]
                             <= p["A_unid_sup_geom_m2"]
                             <= cfg["fixed"]["area_unidad_max_m2"])
    p["area_unid_inf_ok"] = (cfg["fixed"]["area_unidad_min_m2"]
                             <= p["A_unid_inf_geom_m2"]
                             <= cfg["fixed"]["area_unidad_max_m2"])

    # ── Verificación del núcleo ───────────────────────────────────────────
    p["B_nucleo_frac_Ly"]  = p["B_nucleo_m"] / p["Ly_m"]
    p["B_nucleo_frac_ok"]  = p["B_nucleo_frac_Ly"] <= cfg["fixed"]["B_nucleo_frac_Ly_max"]
    p["margen_nucleo_m"]   = p["prof_depto_sup_m"] - (p["B_nucleo_m"]
                              + p["gap_core_to_corridor_m"])

    # ── Material: E de ACI 318 ────────────────────────────────────────────
    p["E_MPa"] = 4700.0 * np.sqrt(p["fc_MPa"])

    return p


def build_family_B_geometry(p):
    Lx, Ly     = p["Lx_m"], p["Ly_m"]
    nL, nR     = p["n_mod_izq"], p["n_mod_der"]
    mods_depto = p["mods_por_depto"]
    Lm         = p["L_mod_m"]
    Ln, Bn     = p["L_nucleo_m"], p["B_nucleo_m"]
    prof_sup   = p["prof_depto_sup_m"]
    prof_inf   = p["prof_depto_inf_m"]
    wc         = p["ancho_corredor_m"]
    gap        = p["gap_core_to_corridor_m"]

    tech_mods = p.get("tech_mods_each_side", mods_depto)
    tech_w    = tech_mods * Lm

    t_core = p["t_muro_nucleo_m"]
    t_ext  = p["t_muro_borde_m"]
    t_mid  = p["t_muro_mid_m"]

    y_cor_0 = prof_inf
    y_cor_1 = prof_inf + wc

    x_nuc_0 = nL * Lm
    x_nuc_1 = x_nuc_0 + Ln
    y_nuc_0 = y_cor_1 + gap
    y_nuc_1 = y_nuc_0 + Bn

    x_left_inner  = t_ext
    x_right_inner = Lx - t_ext

    geom = {
        "outline":      rect_dict(0, 0, Lx, Ly, label="CONTORNO"),
        "corridor":     rect_dict(0, y_cor_0, Lx, wc, label="CORREDOR"),
        "core_box":     rect_dict(x_nuc_0, y_nuc_0, Ln, Bn, label="NUCLEO"),
        "hall_zone":    rect_dict(x_nuc_0, 0.0, Ln, y_cor_0, label="HALL"),
        "tech_zones":   [],
        "core_cells":   [],
        "walls":        [],
        "module_lines": [],
        "unit_lines":   [],
        "unit_labels":  [],
    }

    # ── B1: Muros del núcleo ──────────────────────────────────────────────
    third = Ln / 3.0
    xA0 = x_nuc_0
    xB0 = x_nuc_0 + third
    xC0 = x_nuc_0 + 2 * third

    geom["walls"] += [
        rect_dict(xA0,               y_nuc_0, t_core, Bn,    "B1-1", "B1", "núcleo", "Y"),
        rect_dict(xB0 - t_core,      y_nuc_0, t_core, Bn,    "B1-2", "B1", "núcleo", "Y"),
        rect_dict(xC0 - t_core,      y_nuc_0, t_core, Bn,    "B1-3", "B1", "núcleo", "Y"),
        rect_dict(x_nuc_1 - t_core,  y_nuc_0, t_core, Bn,    "B1-4", "B1", "núcleo", "Y"),
        rect_dict(xA0, y_nuc_1 - t_core, third, t_core,      "B1-5", "B1", "núcleo", "X"),
        rect_dict(xB0, y_nuc_1 - t_core, third, t_core,      "B1-6", "B1", "núcleo", "X"),
        rect_dict(xC0, y_nuc_1 - t_core, third, t_core,      "B1-7", "B1", "núcleo", "X"),
    ]

    pad = 0.18
    geom["core_cells"] += [
        rect_dict(xA0 + t_core + pad, y_nuc_0 + pad,
                  third - t_core - 2*pad, Bn - t_core - 2*pad, "ASC 1"),
        rect_dict(xB0 + pad,          y_nuc_0 + pad,
                  third - 2*pad,          Bn - t_core - 2*pad, "ESC"),
        rect_dict(xC0 + pad,          y_nuc_0 + pad,
                  third - t_core - 2*pad, Bn - t_core - 2*pad, "ASC 2"),
    ]

    # ── Zonas técnicas ────────────────────────────────────────────────────
    geom["tech_zones"] += [
        rect_dict(x_nuc_0 - tech_w, y_cor_1, tech_w, prof_sup, "TEC L"),
        rect_dict(x_nuc_1,          y_cor_1, tech_w, prof_sup, "TEC R"),
    ]

    # ── B2: Muros extremos ────────────────────────────────────────────────
    if p["activar_B2"] == 1:
        geom["walls"] += [
            rect_dict(0.0,      0.0, t_ext, Ly, "B2-L", "B2", "extremo completo", "Y"),
            rect_dict(Lx-t_ext, 0.0, t_ext, Ly, "B2-R", "B2", "extremo completo", "Y"),
        ]

    # ── B4: Muros longitudinales del pasillo ──────────────────────────────
    # B4-SUP y B4-INF: espesor = t_mid en ambos casos
    # B4-SUP arranca en y_cor_1, B4-INF arranca en y_cor_0 - t_mid
    # El gap entre B4-SUP y el núcleo es visual — no afecta OpenSees
    # Los vanos de puertas NO se descuentan — limitación documentada

    L_SUP_L = max(x_nuc_0 - x_left_inner,  0.10)
    L_SUP_R = max(x_right_inner - x_nuc_1,  0.10)
    L_INF_L = max(x_nuc_0 - x_left_inner,  0.10)
    L_INF_R = max(x_right_inner - x_nuc_1,  0.10)

    geom["walls"] += [
        rect_dict(x_left_inner, y_cor_1,         L_SUP_L, t_mid, "B4-SUP-L", "B4", "pasillo superior izq", "X"),
        rect_dict(x_nuc_1,      y_cor_1,         L_SUP_R, t_mid, "B4-SUP-R", "B4", "pasillo superior der", "X"),
        rect_dict(x_left_inner, y_cor_0 - t_mid, L_INF_L, t_mid, "B4-INF-L", "B4", "pasillo inferior izq", "X"),
        rect_dict(x_nuc_1,      y_cor_0 - t_mid, L_INF_R, t_mid, "B4-INF-R", "B4", "pasillo inferior der", "X"),
    ]

    # ── Líneas de módulo ──────────────────────────────────────────────────
    for i in range(1, nL):
        x = i * Lm
        geom["module_lines"] += [((x, 0.0), (x, y_cor_0)), ((x, y_cor_1), (x, Ly))]
    for j in range(1, nR):
        x = x_nuc_1 + j * Lm
        geom["module_lines"] += [((x, 0.0), (x, y_cor_0)), ((x, y_cor_1), (x, Ly))]
    geom["module_lines"] += [((0.0, y_cor_0), (Lx, y_cor_0)),
                             ((0.0, y_cor_1), (Lx, y_cor_1))]

    # ── Líneas de unidad ──────────────────────────────────────────────────
    for i in range(mods_depto, nL - tech_mods + 1, mods_depto):
        geom["unit_lines"].append(((i * Lm, y_cor_1), (i * Lm, Ly)))
    geom["unit_lines"].append(((x_nuc_0 - tech_w, y_cor_1), (x_nuc_0 - tech_w, Ly)))
    geom["unit_lines"].append(((x_nuc_1 + tech_w, y_cor_1), (x_nuc_1 + tech_w, Ly)))
    for j in range(tech_mods + mods_depto, nR + 1, mods_depto):
        geom["unit_lines"].append(((x_nuc_1 + j * Lm, y_cor_1), (x_nuc_1 + j * Lm, Ly)))
    for i in range(mods_depto, nL + 1, mods_depto):
        geom["unit_lines"].append(((i * Lm, 0.0), (i * Lm, y_cor_0)))
    for j in range(mods_depto, nR + 1, mods_depto):
        geom["unit_lines"].append(((x_nuc_1 + j * Lm, 0.0), (x_nuc_1 + j * Lm, y_cor_0)))

    # ── B3: Medianeros — lógica original restaurada ───────────────────────
    # Generados desde el extremo izquierdo en pasos de ancho_depto.
    # El último medianero siempre queda a ~ancho_depto del extremo derecho.
    # Lógica idéntica al PKL anterior (dataset_familyB_cases_20260505_0005.pkl)
    if p["activar_B3"] == 1:
        ancho_depto = mods_depto * Lm

        def clean_x(xs):
            """Elimina duplicados y posiciones que solapan con muros extremos B2."""
            out = []
            for x in sorted(xs):
                if x - t_mid/2 <= t_ext + 1e-6:
                    continue
                if x + t_mid/2 >= Lx - t_ext - 1e-6:
                    continue
                if not out or abs(x - out[-1]) > 1e-6:
                    out.append(x)
            return out

        # ── B3 Superior ───────────────────────────────────────────────────
        x_top = []
        x_top += [i * Lm for i in range(mods_depto, nL - tech_mods + 1, mods_depto)]
        x_top += [x_nuc_0 - tech_w]
        x_top += [x_nuc_1 + tech_w]
        x_top += [x_nuc_1 + j * Lm for j in range(tech_mods + mods_depto, nR, mods_depto)]

        # ── B3 Inferior ───────────────────────────────────────────────────
        x_bot = []
        x_bot += [i * Lm for i in range(mods_depto, nL + 1, mods_depto)]
        x_bot += [x_nuc_0, x_nuc_1]
        x_bot += [x_nuc_1 + j * Lm for j in range(mods_depto, nR, mods_depto)]

        for k, x in enumerate(clean_x(x_top)):
            geom["walls"].append(
                rect_dict(x - t_mid/2, y_cor_1, t_mid, Ly - y_cor_1,
                          f"B3-T-{k+1}", "B3", "medianero superior", "Y")
            )
        for k, x in enumerate(clean_x(x_bot)):
            geom["walls"].append(
                rect_dict(x - t_mid/2, 0.0, t_mid, y_cor_0,
                          f"B3-B-{k+1}", "B3", "medianero inferior", "Y")
            )

    # ── Etiquetas de departamentos ────────────────────────────────────────
    uid = 1
    for g in range(0, nL - tech_mods, mods_depto):
        x0 = g * Lm; x1 = x0 + mods_depto * Lm
        geom["unit_labels"].append((f"D{uid}", 0.5*(x0+x1), 0.5*(y_cor_1+Ly)))
        uid += 1
    for g in range(tech_mods, nR, mods_depto):
        x0 = x_nuc_1 + g * Lm; x1 = x0 + mods_depto * Lm
        geom["unit_labels"].append((f"D{uid}", 0.5*(x0+x1), 0.5*(y_cor_1+Ly)))
        uid += 1
    for g in range(0, nL, mods_depto):
        x0 = g * Lm; x1 = x0 + mods_depto * Lm
        geom["unit_labels"].append((f"D{uid}", 0.5*(x0+x1), 0.5*(0.0+y_cor_0)))
        uid += 1
    for g in range(0, nR, mods_depto):
        x0 = x_nuc_1 + g * Lm; x1 = x0 + mods_depto * Lm
        geom["unit_labels"].append((f"D{uid}", 0.5*(x0+x1), 0.5*(0.0+y_cor_0)))
        uid += 1

    return geom


def wall_group_table_B(cfg):
    rows = []
    for g, data in cfg["wall_groups"].items():
        rows.append({
            "grupo":              g,
            "nombre":             data["name"],
            "estado":             data["state"],
            "aporte_principal":   data["main_direction"],
            "rol":                data["main_role"],
            "se_activa_en_pares": data["paired"],
        })
    return pd.DataFrame(rows)


def variable_table_B(cfg, p):
    rows = []

    for k, v in cfg["fixed"].items():
        rows.append({"variable": k, "categoria": "fija",
                     "valor_actual": v, "rango_o_catalogo": "fijo",
                     "comentario": "Identidad / restricción base"})

    for k, spec in cfg["variable_ranges"].items():
        rango = (f"{spec['min']} a {spec['max']}"
                 if spec["type"] in ["int", "float"] else str(spec["values"]))
        rows.append({"variable": k, "categoria": "variable",
                     "valor_actual": p.get(k), "rango_o_catalogo": rango,
                     "comentario": "Editable"})

    derived_keys = [
        "n_mod_lado", "n_mod_izq", "n_mod_der", "n_mod_total",
        "n_unid_fila_sup", "n_unid_fila_inf", "n_unid_lado_inf", "n_deptos_piso",
        "n_zonas_tecnicas_piso", "n_hall_piso",
        "Lx_m", "Ly_m", "H_total_m", "A_geom_m2",
        "A_unid_sup_geom_m2", "A_unid_inf_geom_m2",
        "A_util_m2", "A_tecnica_m2", "A_hall_m2", "A_bruta_m2", "eff_real",
        "aspect_ratio_Lx_Ly", "aspect_ratio_ok",
        "area_unid_sup_ok", "area_unid_inf_ok",
        "B_nucleo_frac_Ly", "B_nucleo_frac_ok", "margen_nucleo_m",
        "E_MPa"
    ]
    for k in derived_keys:
        rows.append({"variable": k, "categoria": "derivada",
                     "valor_actual": p.get(k), "rango_o_catalogo": "derivada",
                     "comentario": "Calculada automáticamente"})

    return pd.DataFrame(rows)


def plot_family_B_plan(geom, p, ax=None, show_labels=True, cfg=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(16, 8))

    family_name = "Familia B"
    if cfg is not None:
        family_name = cfg.get("meta", {}).get("family_name", "Familia B")

    outline = geom["outline"]
    ax.add_patch(Rectangle((outline["x"], outline["y"]), outline["w"], outline["h"],
                            fill=False, edgecolor="black", linewidth=2))

    cor = geom["corridor"]
    ax.add_patch(Rectangle((cor["x"], cor["y"]), cor["w"], cor["h"],
                            facecolor="lightgreen", edgecolor="green", alpha=0.25))
    ax.text(cor["x"] + cor["w"]/2, cor["y"] + cor["h"]/2,
            "CORREDOR CENTRAL", ha="center", va="center",
            fontsize=10, color="green", weight="bold")

    core = geom["core_box"]
    ax.add_patch(Rectangle((core["x"], core["y"]), core["w"], core["h"],
                            fill=False, edgecolor="purple", linewidth=1.2, linestyle=":"))
    ax.text(core["x"] + core["w"]/2, core["y"] + core["h"] + 0.18,
            "NÚCLEO CENTRAL", ha="center", va="bottom",
            fontsize=10, color="purple", weight="bold")

    for cell in geom["core_cells"]:
        ax.add_patch(Rectangle((cell["x"], cell["y"]), cell["w"], cell["h"],
                               facecolor="lavender", edgecolor="purple", alpha=0.35))
        ax.text(cell["x"] + cell["w"]/2, cell["y"] + cell["h"]/2,
                cell["label"], ha="center", va="center",
                fontsize=8, color="purple", weight="bold")

    for tech in geom.get("tech_zones", []):
        ax.add_patch(Rectangle((tech["x"], tech["y"]), tech["w"], tech["h"],
                               facecolor="mistyrose", edgecolor="crimson", alpha=0.35, hatch="//"))
        ax.text(tech["x"] + tech["w"]/2, tech["y"] + tech["h"]/2,
                tech["label"], ha="center", va="center",
                fontsize=8, color="crimson", weight="bold")

    hall = geom.get("hall_zone", None)
    if hall is not None:
        ax.add_patch(Rectangle((hall["x"], hall["y"]), hall["w"], hall["h"],
                               facecolor="lightyellow", edgecolor="goldenrod", alpha=0.35, hatch=".."))
        ax.text(hall["x"] + hall["w"]/2, hall["y"] + hall["h"]/2,
                "HALL", ha="center", va="center",
                fontsize=9, color="goldenrod", weight="bold")

    for p1, p2 in geom["module_lines"]:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], linestyle=":", color="0.55", lw=0.8)

    for p1, p2 in geom["unit_lines"]:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], linestyle="--", color="orange", lw=1.2)

    color_map = {
        "B1": "steelblue",
        "B2": "firebrick",
        "B3": "darkorange",
        "B4": "seagreen",
    }

    for w in geom["walls"]:
        c = color_map.get(w["group"], "gray")
        ax.add_patch(Rectangle((w["x"], w["y"]), w["w"], w["h"],
                               facecolor=c, edgecolor=c, alpha=0.80))
        if show_labels:
            ax.text(w["x"] + w["w"]/2, w["y"] + w["h"]/2, w["label"],
                    ha="center", va="center", fontsize=6, color="white", weight="bold")

    if show_labels:
        for txt, x, y in geom["unit_labels"]:
            ax.text(x, y, txt, ha="center", va="center", fontsize=8)

    ax.set_title(
        f"{family_name} | "
        f"N={p['N_pisos']} pisos | Deptos/piso={p['n_deptos_piso']} | "
        f"A_unid={p['A_unid_sup_geom_m2']:.1f} m² | "
        f"Lx/Ly={p['aspect_ratio_Lx_Ly']:.2f} | "
        f"B_nuc/Ly={p['B_nucleo_frac_Ly']:.2f}"
    )

    ax.set_xlim(-0.5, p["Lx_m"] + 0.5)
    ax.set_ylim(-0.5, p["Ly_m"] + 0.8)
    ax.set_aspect("equal")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.grid(alpha=0.25)

    return ax


def plot_family_B_3D(geom, p, ax=None):
    if ax is None:
        fig = plt.figure(figsize=(12, 10))
        ax  = fig.add_subplot(111, projection="3d")

    color_map = {"B1": "steelblue", "B2": "firebrick", "B3": "darkorange", "B4": "seagreen"}

    for k in range(p["N_pisos"] + 1):
        z    = k * p["h_story_m"]
        slab = [[0, 0, z], [p["Lx_m"], 0, z],
                [p["Lx_m"], p["Ly_m"], z], [0, p["Ly_m"], z]]
        poly = Poly3DCollection([slab], alpha=0.04, facecolor="gray", edgecolor="gray")
        ax.add_collection3d(poly)

    for w in geom["walls"]:
        c     = color_map.get(w["group"], "gray")
        faces = prism_faces(w["x"], w["y"], 0.0, w["w"], w["h"], p["H_total_m"])
        poly  = Poly3DCollection(faces, alpha=0.65, facecolor=c,
                                 edgecolor="k", linewidth=0.25)
        ax.add_collection3d(poly)

    ax.set_title(f"Vista 3D esquemática — {FAMILIA_B_CFG['meta']['family_name']}"
                 f" | {p['N_pisos']} pisos")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_xlim(0, p["Lx_m"])
    ax.set_ylim(0, p["Ly_m"])
    ax.set_zlim(0, p["H_total_m"])
    ax.view_init(elev=24, azim=-58)
