"""
Sugerencias físicas de mejora para edificios que NO cumplen NCh433.
Portado desde la Celda 11 del notebook Interfaz_PINN_FamiliaB_update.ipynb.

Devuelve una lista de dicts con:
    parametro  : nombre del parámetro a modificar
    accion     : 'aumentar' o 'disminuir'
    razon      : justificación física
    prioridad  : 'alta', 'media' o 'baja'
"""

from predictor.pinn.domain import DRIFT_LIMIT_NCh433


def sugerir_modificaciones(res: dict, rep: dict, edificio: dict) -> list[dict]:
    """
    Genera sugerencias cualitativas razonadas para mejorar el cumplimiento NCh433.
    Retorna lista vacía si el edificio cumple.

    Parámetros
    ----------
    res      : resultado de predict_edificio()
    rep      : resultado de reporte_normativo()
    edificio : dict de parámetros del edificio (los mismos 16 del usuario)
    """
    if rep['veredicto'] == 'CUMPLE':
        return []

    N         = int(edificio['N_pisos'])
    pisos_tot = N
    sugs: list[dict] = []

    # ── Deriva en Y (controlada por núcleo B1 y muros transversales B3) ──────────
    if not rep['cumple_dy']:
        piso_dy   = rep['piso_dy_max']
        exc_dy    = (rep['deriva_y_max'] / DRIFT_LIMIT_NCh433 - 1) * 100
        en_altura = piso_dy > pisos_tot * 0.6
        en_base   = piso_dy <= pisos_tot * 0.3
        critico   = exc_dy > 30

        razon = (
            f"La deriva máxima en Y ({rep['deriva_y_max']:.5f}) excede el límite "
            f"NCh433 en un {exc_dy:+.0f}% en el piso {piso_dy}. "
        )
        if en_altura:
            razon += (
                "Al concentrarse en la mitad superior del edificio, el problema "
                "apunta a falta de rigidez global transversal — el núcleo B1 es "
                "el principal aportante en altura por su gran inercia."
            )
        elif en_base:
            razon += (
                "Al concentrarse en los pisos bajos, el problema sugiere "
                "concentración de esfuerzo cortante en la base del núcleo y los "
                "muros transversales."
            )
        else:
            razon += (
                "La distribución sugiere insuficiencia de rigidez transversal en general."
            )

        sugs.append({
            'parametro': 't_muro_nucleo_m',
            'accion':    'aumentar',
            'razon':     razon + " Aumentar el espesor del núcleo (B1) es lo más "
                                  "eficiente para reducir la deriva en Y.",
            'prioridad': 'alta' if critico else 'media',
        })
        sugs.append({
            'parametro': 't_muro_borde_m',
            'accion':    'aumentar',
            'razon':     "Los muros laterales extremos (B2) y los transversales que "
                         "comparten su espesor contribuyen a la rigidez Y, "
                         "especialmente si el aumento del núcleo no es suficiente.",
            'prioridad': 'media',
        })

    # ── Deriva en X (controlada por muros longitudinales B4) ─────────────────────
    if not rep['cumple_dx']:
        piso_dx   = rep['piso_dx_max']
        exc_dx    = (rep['deriva_x_max'] / DRIFT_LIMIT_NCh433 - 1) * 100
        en_altura = piso_dx > pisos_tot * 0.6
        critico   = exc_dx > 30

        razon = (
            f"La deriva máxima en X ({rep['deriva_x_max']:.5f}) excede el límite "
            f"NCh433 en un {exc_dx:+.0f}% en el piso {piso_dx}. "
            "La rigidez longitudinal depende principalmente de los muros B4 y, "
            "en menor medida, del núcleo."
        )
        sugs.append({
            'parametro': 't_muro_mid_m',
            'accion':    'aumentar',
            'razon':     razon + " Aumentar el espesor de los muros intermedios "
                                  "longitudinales (B4) es la vía directa para "
                                  "reducir la deriva en X.",
            'prioridad': 'alta' if critico else 'media',
        })
        if en_altura:
            sugs.append({
                'parametro': 'L_nucleo_m',
                'accion':    'aumentar',
                'razon':     "Al concentrarse la deriva X en la mitad superior, "
                             "ampliar la dimensión longitudinal del núcleo (B1) "
                             "ayuda más que añadir espesor a los muros del borde.",
                'prioridad': 'media',
            })

    # ── Ambas direcciones fallan: sugerir reducir altura o mejorar hormigón ───────
    if not rep['cumple_dx'] and not rep['cumple_dy']:
        sugs.append({
            'parametro': 'N_pisos',
            'accion':    'disminuir',
            'razon':     "Si ambas direcciones exceden el límite y los espesores ya "
                         "están en el rango alto del dominio, considerar un edificio "
                         "con menor N_pisos. La rigidez requerida crece más rápido "
                         "que linealmente con la altura.",
            'prioridad': 'baja',
        })
        sugs.append({
            'parametro': 'fc_MPa',
            'accion':    'aumentar',
            'razon':     "Aumentar la resistencia del hormigón eleva el módulo "
                         "elástico E = 4700·√fc, mejorando la rigidez global en "
                         "ambas direcciones. Es una palanca eficiente cuando los "
                         "espesores ya son altos.",
            'prioridad': 'baja',
        })

    return sugs
