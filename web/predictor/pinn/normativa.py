from predictor.pinn.domain import DRIFT_LIMIT_NCh433


def reporte_normativo(res):
    """Evalúa cumplimiento NCh433 y devuelve veredicto con razones."""
    dx = res['respuesta']['dx_por_piso']
    dy = res['respuesta']['dy_por_piso']
    razones_fallo = []

    dx_max, dx_pos = float(dx.max()), int(dx.argmax()) + 1
    dy_max, dy_pos = float(dy.max()), int(dy.argmax()) + 1
    cumple_dx = dx_max <= DRIFT_LIMIT_NCh433
    cumple_dy = dy_max <= DRIFT_LIMIT_NCh433

    if not cumple_dx:
        exc = (dx_max / DRIFT_LIMIT_NCh433 - 1) * 100
        razones_fallo.append(
            f"Deriva en X excede el límite NCh433 ({DRIFT_LIMIT_NCh433}): "
            f"dx_max = {dx_max:.5f} en piso {dx_pos} ({exc:+.1f}% sobre el límite)")
    if not cumple_dy:
        exc = (dy_max / DRIFT_LIMIT_NCh433 - 1) * 100
        razones_fallo.append(
            f"Deriva en Y excede el límite NCh433 ({DRIFT_LIMIT_NCh433}): "
            f"dy_max = {dy_max:.5f} en piso {dy_pos} ({exc:+.1f}% sobre el límite)")

    T1 = float(res['modal']['T'][0])
    H  = res['geometria']['H']
    T1_aprox = 0.05 * H ** 0.75
    if T1 < 0.05 or T1 > 5.0:
        razones_fallo.append(
            f"Período fundamental fuera de rango físico razonable: T1 = {T1:.3f}s")

    veredicto = 'CUMPLE' if (cumple_dx and cumple_dy and not razones_fallo) else 'NO CUMPLE'
    return dict(
        veredicto     = veredicto,
        cumple_dx     = cumple_dx,
        cumple_dy     = cumple_dy,
        deriva_x_max  = dx_max,
        piso_dx_max   = dx_pos,
        deriva_y_max  = dy_max,
        piso_dy_max   = dy_pos,
        T1            = T1,
        T1_referencia = T1_aprox,
        razones_fallo = razones_fallo,
        extrapolando  = res['extrapolando'],
    )
