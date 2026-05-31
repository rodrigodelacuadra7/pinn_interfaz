"""
Wrapper delgado sobre pinn_visualizer.py.

pinn_visualizer.py y familia_B_core.py viven en web/ (top-level del proyecto),
por lo que manage.py / gunicorn los tiene en sys.path sin configuración extra.
"""

from pinn_visualizer import generar_plotly_3d, generar_plotly_planta
from predictor.pinn.derived import enrich_params


def render_3d(params: dict, cumple: bool | None = None, T1: float | None = None) -> str:
    return generar_plotly_3d(enrich_params(params), cumple=cumple, T1=T1)


def render_planta(params: dict) -> str:
    return generar_plotly_planta(enrich_params(params))
