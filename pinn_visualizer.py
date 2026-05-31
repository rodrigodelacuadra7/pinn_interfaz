"""
pinn_visualizer.py
==================
Módulo de visualización Plotly para edificios Familia B.

Entrega tres funciones que devuelven HTML embebible (string) con las figuras
Plotly listas para inyectar en un frontend via `innerHTML`:

    - generar_plotly_3d(params)           -> str (HTML)
    - generar_plotly_planta(params)       -> str (HTML)
    - generar_plotly_modos(params, modal) -> str (HTML)   [opcional]

Las dos primeras solo necesitan los 21 parámetros del edificio. La tercera
además necesita la salida modal de la PINN (períodos, formas y masas).

Dependencias:
    - plotly
    - pandas, numpy
    - familia_B_core.py  (tu módulo de geometría; debe estar en sys.path o
      en la misma carpeta)

Uso típico desde un endpoint Flask/FastAPI:

    from pinn_visualizer import generar_plotly_3d, generar_plotly_planta
    html_3d    = generar_plotly_3d(params)
    html_plan  = generar_plotly_planta(params)
    # Devolver al frontend (p.ej. en un JSON) y allá:
    #   document.getElementById('div_3d').innerHTML = html_3d;
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# IMPORT del core de la Familia B. Debe estar disponible en sys.path.
# Si tu instalación lo tiene en otra ruta, añadir antes de importar este módulo:
#   import sys; sys.path.insert(0, '/ruta/a/familia_B')
from familia_B_core import build_family_B_geometry


# ─── PALETA DE COLORES (idéntica a la celda visualizadora del notebook) ────
COLOR_3D = {
    'B1': 'rgba( 52, 152, 219, 0.80)',   # azul        — núcleo central
    'B2': 'rgba(139,   0,   0, 0.85)',   # rojo oscuro — muros laterales extremos
    'B3': 'rgba(255, 165,   0, 0.80)',   # naranja     — muros transversales
    'B4': 'rgba( 34, 139,  34, 0.80)',   # verde       — muros longitudinales
}
COLOR_FILL = {
    'B1': 'rgba( 52, 152, 219, 0.85)',
    'B2': 'rgba(139,   0,   0, 0.90)',
    'B3': 'rgba(255, 165,   0, 0.85)',
    'B4': 'rgba( 34, 139,  34, 0.85)',
}
COLOR_LINE = {
    'B1': 'steelblue',
    'B2': 'darkred',
    'B3': 'darkorange',
    'B4': 'darkgreen',
}
COLOR_LOSA = 'rgba(189, 195, 199, 0.20)'
COLOR_CM   = 'rgba( 39, 174,  96, 1.00)'


# ─── HELPER INTERNO ─────────────────────────────────────────────────────────
def _geometry_to_wall_df(geom: dict, params: dict) -> pd.DataFrame:
    """
    Convierte geom['walls'] (lista de dicts) al DataFrame con columnas
    estandarizadas (cx, cy, area_plan_m2). Réplica exacta de la función
    `geometry_to_wall_df` del Notebook 3.
    """
    rows = []
    for w in geom['walls']:
        x, y, ww, hh = float(w['x']), float(w['y']), float(w['w']), float(w['h'])
        rows.append({
            'label':       w.get('label', ''),
            'group':       w.get('group', ''),
            'role':        w.get('role', ''),
            'orientation': w.get('orientation', ''),
            'x': x, 'y': y, 'w': ww, 'h': hh,
            'cx': x + ww / 2,
            'cy': y + hh / 2,
            'area_plan_m2': ww * hh,
        })
    return pd.DataFrame(rows)


def _construir_geometria(params: dict) -> tuple[dict, pd.DataFrame]:
    """
    A partir de los params del usuario, construye `geom` (dict con
    corredor y muros) y `wall_df` (DataFrame estandarizado). Esta es la
    función que reemplaza al `case['wall_df']` que se leía del PKL.
    """
    geom    = build_family_B_geometry(params)
    wall_df = _geometry_to_wall_df(geom, params)
    return geom, wall_df


# ════════════════════════════════════════════════════════════════════════════
# 1. VISTA 3D
# ════════════════════════════════════════════════════════════════════════════
def generar_plotly_3d(params: dict,
                      cumple: bool | None = None,
                      T1: float | None = None,
                      include_plotlyjs: str = 'cdn',
                      full_html: bool = False) -> str:
    """
    Genera la vista 3D del edificio Familia B y devuelve el HTML embebible.

    Parámetros
    ----------
    params : dict
        Los 16 parámetros del edificio: N_pisos, n_unid_lado, activar_B2,
        L_mod_m, prof_depto_m, ancho_corredor_m, L_nucleo_m, B_nucleo_m,
        h_story_m, fc_MPa, gk_kN_m2, t_muro_nucleo_m, t_muro_borde_m,
        t_muro_mid_m, suelo, zona, y los derivados Lx_m, Ly_m, H_total_m,
        A_geom_m2, activar_B3 (todos los que `build_family_B_geometry`
        necesite).
    cumple : bool, opcional
        Si se provee, se muestra en el título.
    T1 : float, opcional
        Si se provee, se muestra en el título.
    include_plotlyjs : str
        'cdn' (recomendado, ligero) o 'inline' (autocontenido pero pesado).
    full_html : bool
        False devuelve solo el <div> con la figura (para inyectar en otra
        página); True devuelve un HTML completo independiente.

    Devuelve
    --------
    str — HTML listo para insertar con innerHTML.
    """
    geom, wall_df = _construir_geometria(params)

    N  = int(params['N_pisos'])
    Lx = float(params['Lx_m'])
    Ly = float(params['Ly_m'])
    h  = float(params['h_story_m'])
    H  = N * h
    xCM, yCM = Lx / 2, Ly / 2

    n_por_grupo = {g: int((wall_df['group'] == g).sum()) for g in ['B1', 'B2', 'B3', 'B4']}

    traces = []

    # ── Muros (Mesh3d) ─────────────────────────────────────────────────────
    for _, wall in wall_df.iterrows():
        cx = float(wall['cx']); cy = float(wall['cy'])
        w  = float(wall['w']);  hw = float(wall['h'])
        grp = str(wall.get('group', 'B3'))

        if w >= hw:
            orient = 'X'; L = w;  t = hw
            x0, x1 = cx - L / 2, cx + L / 2
            y0, y1 = cy - t / 2, cy + t / 2
        else:
            orient = 'Y'; L = hw; t = w
            x0, x1 = cx - t / 2, cx + t / 2
            y0, y1 = cy - L / 2, cy + L / 2

        color_3d = COLOR_3D.get(grp, 'rgba(200,200,200,0.75)')

        traces.append(go.Mesh3d(
            x=[x0, x1, x1, x0, x0, x1, x1, x0],
            y=[y0, y0, y1, y1, y0, y0, y1, y1],
            z=[0, 0, 0, 0, H, H, H, H],
            i=[0, 0, 1, 1, 0, 0, 4, 4, 0, 3, 1, 2],
            j=[1, 2, 2, 5, 4, 5, 5, 7, 3, 7, 5, 6],
            k=[2, 3, 5, 6, 5, 1, 7, 3, 7, 4, 2, 7],
            color=color_3d,
            opacity=0.75,
            flatshading=True,
            lighting=dict(ambient=0.7, diffuse=0.5),
            showscale=False,
            name=f'Muro {grp}',
            hovertemplate=f"Grupo={grp}<br>orient={orient}<br>L={L:.2f}m t={t:.2f}m<extra></extra>",
        ))

    # ── Losas ──────────────────────────────────────────────────────────────
    for piso in range(1, N + 1):
        z = piso * h
        traces.append(go.Mesh3d(
            x=[0, Lx, Lx, 0, 0, Lx, Lx, 0],
            y=[0, 0, Ly, Ly, 0, 0, Ly, Ly],
            z=[z, z, z, z, z + 0.01, z + 0.01, z + 0.01, z + 0.01],
            i=[0, 0, 4, 4], j=[1, 2, 5, 6], k=[2, 3, 6, 7],
            color=COLOR_LOSA, opacity=0.15,
            flatshading=True, showscale=False,
            name=f'Losa {piso}', hoverinfo='skip',
        ))

    # ── Centro de masa ─────────────────────────────────────────────────────
    traces.append(go.Scatter3d(
        x=[xCM] * (N + 1), y=[yCM] * (N + 1),
        z=[p * h for p in range(N + 1)],
        mode='markers+lines',
        marker=dict(size=4, color=COLOR_CM),
        line=dict(color=COLOR_CM, width=3),
        name='CM',
    ))

    # ── Perímetro (líneas grises) ──────────────────────────────────────────
    corners = [(0, 0), (Lx, 0), (Lx, Ly), (0, Ly), (0, 0)]
    for i in range(4):
        x0c, y0c = corners[i]; x1c, y1c = corners[i + 1]
        for z_e in [0, H]:
            traces.append(go.Scatter3d(
                x=[x0c, x1c], y=[y0c, y1c], z=[z_e, z_e],
                mode='lines', line=dict(color='gray', width=1),
                showlegend=False, hoverinfo='skip',
            ))
        traces.append(go.Scatter3d(
            x=[x0c, x0c], y=[y0c, y0c], z=[0, H],
            mode='lines', line=dict(color='gray', width=1),
            showlegend=False, hoverinfo='skip',
        ))

    # ── Layout ─────────────────────────────────────────────────────────────
    max_dim = max(Lx, Ly, H)
    titulo_extra = ''
    if T1 is not None:
        titulo_extra += f" | T1={T1:.3f}s"
    if cumple is not None:
        titulo_extra += f" | {'CUMPLE ✅' if cumple else 'NO CUMPLE ❌'}"

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(
            text=(f"Vista 3D — {N} pisos | "
                  f"Lx={Lx:.1f}m × Ly={Ly:.1f}m{titulo_extra}"),
            font=dict(size=11),
        ),
        scene=dict(
            xaxis=dict(title='X [m]', range=[0, Lx]),
            yaxis=dict(title='Y [m]', range=[0, Ly]),
            zaxis=dict(title='Z [m]', range=[0, H]),
            aspectmode='manual',
            aspectratio=dict(x=Lx / max_dim, y=Ly / max_dim, z=H / max_dim),
            camera=dict(eye=dict(x=1.8, y=-1.8, z=1.0)),
        ),
        legend=dict(font=dict(size=9), x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=50, b=0),
        height=600,
        paper_bgcolor='white',
    )
    fig.add_annotation(
        xref='paper', yref='paper', x=0.99, y=0.01,
        text=(f"B1 Núcleo (azul):       {n_por_grupo['B1']}<br>"
              f"B2 Laterales (rojo):    {n_por_grupo['B2']}<br>"
              f"B3 Transvers. (naranja):{n_por_grupo['B3']}<br>"
              f"B4 Longitud. (verde):   {n_por_grupo['B4']}<br>"
              f"H total: {H:.1f} m<br>"
              f"Lx/Ly: {Lx / Ly:.2f}"),
        showarrow=False, align='right', font=dict(size=9),
        bgcolor='rgba(255,255,255,0.8)', bordercolor='gray', borderwidth=1,
    )

    return fig.to_html(include_plotlyjs=include_plotlyjs, full_html=full_html)


# ════════════════════════════════════════════════════════════════════════════
# 2. PLANTA
# ════════════════════════════════════════════════════════════════════════════
def generar_plotly_planta(params: dict,
                          include_plotlyjs: str = 'cdn',
                          full_html: bool = False) -> str:
    """
    Genera la planta del edificio Familia B y devuelve el HTML embebible.

    Muestra: perímetro, corredor (verde claro), muros con color por grupo
    (B1 azul, B2 rojo, B3 naranja, B4 verde) y el centro de masa (✕ verde).
    """
    geom, wall_df = _construir_geometria(params)

    N  = int(params['N_pisos'])
    Lx = float(params['Lx_m'])
    Ly = float(params['Ly_m'])
    xCM, yCM = Lx / 2, Ly / 2

    traces = []

    # ── Perímetro ──────────────────────────────────────────────────────────
    traces.append(go.Scatter(
        x=[0, Lx, Lx, 0, 0], y=[0, 0, Ly, Ly, 0],
        mode='lines', line=dict(color='black', width=2),
        showlegend=False,
    ))

    # ── Corredor ───────────────────────────────────────────────────────────
    cor = geom['corridor']
    traces.append(go.Scatter(
        x=[cor['x'], cor['x'] + cor['w'], cor['x'] + cor['w'],
           cor['x'], cor['x']],
        y=[cor['y'], cor['y'], cor['y'] + cor['h'],
           cor['y'] + cor['h'], cor['y']],
        mode='lines', fill='toself',
        fillcolor='rgba(144,238,144,0.25)',
        line=dict(color='green', width=1),
        name='Corredor',
    ))

    # ── Muros ──────────────────────────────────────────────────────────────
    for _, wall in wall_df.iterrows():
        cx = float(wall['cx']); cy = float(wall['cy'])
        w  = float(wall['w']);  hw = float(wall['h'])
        grp = str(wall.get('group', 'B3'))
        x0, x1 = cx - w / 2,  cx + w / 2
        y0, y1 = cy - hw / 2, cy + hw / 2

        traces.append(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            mode='lines', fill='toself',
            fillcolor=COLOR_FILL.get(grp, 'rgba(200,200,200,0.8)'),
            line=dict(color=COLOR_LINE.get(grp, 'gray'), width=1),
            showlegend=False,
            hovertemplate=f"Grupo={grp}<br>w={w:.2f}m h={hw:.2f}m<extra></extra>",
        ))

    # ── Centro de masa ─────────────────────────────────────────────────────
    traces.append(go.Scatter(
        x=[xCM], y=[yCM],
        mode='markers',
        marker=dict(size=12, color='green', symbol='x'),
        name='CM',
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(
            text=(f"Planta — {N} pisos | fc={params['fc_MPa']:.0f} MPa | "
                  f"Azul=B1  Rojo=B2  Naranja=B3  Verde=B4  ✕=CM"),
            font=dict(size=11),
        ),
        xaxis=dict(title='X [m]', scaleanchor='y', scaleratio=1),
        yaxis=dict(title='Y [m]'),
        height=450,
        paper_bgcolor='white',
        plot_bgcolor='rgba(248,248,248,1)',
        font=dict(size=9),
    )
    return fig.to_html(include_plotlyjs=include_plotlyjs, full_html=full_html)


# ════════════════════════════════════════════════════════════════════════════
# 3. FORMAS MODALES (opcional, requiere salidas modales de la PINN)
# ════════════════════════════════════════════════════════════════════════════
def generar_plotly_modos(params: dict,
                         modal: dict,
                         include_plotlyjs: str = 'cdn',
                         full_html: bool = False) -> str:
    """
    Genera la grilla de formas modales. Necesita las salidas modales de
    la PINN (o de OpenSees).

    Parámetros
    ----------
    modal : dict con claves:
        'T_r'           : array shape (18,)  — períodos por modo
        'Phi_x'         : array shape (N, 18) — formas modales en X
        'Phi_y'         : array shape (N, 18) — formas modales en Y
        'Phi_theta'     : array shape (N, 18) — formas modales torsionales
        'mass_acc_x'    : array shape (18,)  — masa acumulada X (fracción 0–1)
        'mass_acc_y'    : array shape (18,)  — masa acumulada Y
        'mass_part_x'   : array shape (18,)  — masa participante X
        'mass_part_y'   : array shape (18,)  — masa participante Y
    """
    N = int(params['N_pisos'])

    T_r         = np.asarray(modal['T_r'])
    Phi_x       = np.asarray(modal['Phi_x'])
    Phi_y       = np.asarray(modal['Phi_y'])
    Phi_theta   = np.asarray(modal['Phi_theta'])
    mass_acc_x  = np.asarray(modal['mass_acc_x'])
    mass_acc_y  = np.asarray(modal['mass_acc_y'])
    mass_part_x = np.asarray(modal['mass_part_x'])
    mass_part_y = np.asarray(modal['mass_part_y'])

    # Modos necesarios para alcanzar 90% en ambas direcciones
    UMBRAL = 0.90
    n_modos_90 = 18
    for r in range(18):
        if mass_acc_x[r] >= UMBRAL and mass_acc_y[r] >= UMBRAL:
            n_modos_90 = r + 1
            break

    pisos = list(range(1, N + 1))
    modos_plot = []
    for r in range(n_modos_90):
        ciclo = r % 3
        if ciclo == 0:
            phi = Phi_y[:N, r];     dir_label = 'Y';  color = 'steelblue'
        elif ciclo == 1:
            phi = Phi_theta[:N, r]; dir_label = 'Rz'; color = 'mediumpurple'
        else:
            phi = Phi_x[:N, r];     dir_label = 'X';  color = 'tomato'

        es_vacio = np.abs(phi).max() < 1e-10
        phi_norm = phi / (np.abs(phi).max() + 1e-12) if not es_vacio else np.zeros(N)
        titulo = (f"M{r+1} ({dir_label}) T={T_r[r]:.3f}s<br>"
                  f"γx={mass_part_x[r]*100:.0f}% γy={mass_part_y[r]*100:.0f}%  "
                  f"Σx={mass_acc_x[r]*100:.0f}% Σy={mass_acc_y[r]*100:.0f}%")
        modos_plot.append(dict(titulo=titulo, phi_norm=phi_norm,
                               color=color, vacio=es_vacio))

    N_COLS = 4
    N_ROWS = (n_modos_90 + N_COLS - 1) // N_COLS
    fig = make_subplots(
        rows=N_ROWS, cols=N_COLS,
        subplot_titles=[m['titulo'] for m in modos_plot],
        shared_yaxes=False,
        vertical_spacing=0.12,
        horizontal_spacing=0.06,
    )
    for idx, modo in enumerate(modos_plot):
        row = idx // N_COLS + 1
        col = idx % N_COLS + 1
        if modo['vacio']:
            fig.add_trace(go.Scatter(
                x=[0], y=[N // 2 + 1], mode='text',
                text=['VACÍO'], textfont=dict(color='gray', size=9),
                showlegend=False,
            ), row=row, col=col)
        else:
            fig.add_trace(go.Bar(
                x=modo['phi_norm'], y=pisos, orientation='h',
                marker_color=modo['color'], opacity=0.25,
                showlegend=False, hoverinfo='skip',
            ), row=row, col=col)
            fig.add_trace(go.Scatter(
                x=modo['phi_norm'], y=pisos, mode='lines+markers',
                line=dict(color=modo['color'], width=1.5),
                marker=dict(size=4, color=modo['color']),
                showlegend=False,
                hovertemplate='P%{y}: Φ=%{x:.3f}<extra></extra>',
            ), row=row, col=col)
        fig.add_vline(x=0, line_dash='dash', line_color='black',
                      line_width=0.8, row=row, col=col)
        fig.update_yaxes(
            tickvals=pisos, ticktext=[f'P{p}' for p in pisos],
            tickfont=dict(size=7), row=row, col=col,
        )
        fig.update_xaxes(
            range=[-1.1, 1.1], tickfont=dict(size=7),
            title_text='Φ', title_font=dict(size=8),
            row=row, col=col,
        )

    altura = max(350, N_ROWS * 280)
    fig.update_layout(
        title=dict(
            text=(f"Formas modales — {N} pisos | "
                  f"{n_modos_90} modos para ≥90% masa  |  "
                  f"Azul=Y  Morado=Torsión  Rojo=X"),
            font=dict(size=11),
        ),
        height=altura,
        paper_bgcolor='white',
        plot_bgcolor='white',
        barmode='overlay',
        showlegend=False,
        font=dict(size=8),
    )
    for ann in fig.layout.annotations:
        ann.font.size = 8

    return fig.to_html(include_plotlyjs=include_plotlyjs, full_html=full_html)
