# Integración del módulo `pinn_visualizer.py` en la interfaz HTML

## Qué hace el módulo

Tres funciones públicas que devuelven **HTML embebible** (string) con figuras Plotly listas para inyectar en el frontend:

| Función | Entrada | Devuelve |
|---|---|---|
| `generar_plotly_3d(params)` | dict con los parámetros del edificio | str (HTML del 3D) |
| `generar_plotly_planta(params)` | idem | str (HTML de la planta) |
| `generar_plotly_modos(params, modal)` | params + salidas modales de la PINN | str (HTML de las formas modales) |

Las dos primeras solo necesitan los parámetros del usuario. La tercera además necesita la salida modal del modelo (períodos, formas Φ, masas).

## Dependencias

- `plotly`, `pandas`, `numpy` — instalables con pip
- `familia_B_core.py` — el módulo del usuario, debe estar accesible vía `sys.path`. Si no, antes de importar añadir:
  ```python
  import sys
  sys.path.insert(0, '/ruta/a/familia_B')
  ```

## Estructura esperada de `params`

Diccionario con las claves que `build_family_B_geometry` necesita. Mínimo:
```python
params = {
    'N_pisos': 12, 'n_unid_lado': 3, 'activar_B2': 1, 'activar_B3': 1,
    'L_mod_m': 3.5, 'prof_depto_m': 7.5, 'ancho_corredor_m': 1.7,
    'L_nucleo_m': 6.0, 'B_nucleo_m': 4.5, 'h_story_m': 2.7,
    'fc_MPa': 30, 'gk_kN_m2': 7.0,
    't_muro_nucleo_m': 0.25, 't_muro_borde_m': 0.25, 't_muro_mid_m': 0.20,
    'suelo': 'C', 'zona': 2,
    # derivados (calcular antes según las fórmulas del NB1):
    'Lx_m': ..., 'Ly_m': ..., 'H_total_m': ..., 'A_geom_m2': ...,
}
```

> Importante: si tu interfaz solo pide al usuario las variables de diseño (sin derivados), calcular `Lx_m`, `Ly_m`, `H_total_m`, `A_geom_m2` *antes* de pasarle el dict al visualizador. Las fórmulas están en el Notebook 1 / `familia_B_core.py`.

## Uso desde un endpoint (Flask, ejemplo)

```python
from flask import Flask, request, jsonify
from pinn_visualizer import generar_plotly_3d, generar_plotly_planta

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    params = request.json  # dict con los 21 parámetros completos
    # ... aquí va la inferencia de la PINN ...
    # resultados = predict_edificio(params)  # tu función existente
    
    html_3d    = generar_plotly_3d(params, cumple=resultados['cumple'], T1=resultados['T1'])
    html_plan  = generar_plotly_planta(params)
    
    return jsonify({
        'html_3d':    html_3d,
        'html_plan':  html_plan,
        'metricas':   resultados,
    })
```

## Uso desde el frontend (JavaScript)

```javascript
const res = await fetch('/predict', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(params),
});
const data = await res.json();

document.getElementById('div_3d').innerHTML    = data.html_3d;
document.getElementById('div_planta').innerHTML = data.html_plan;
// las métricas en data.metricas se renderizan como ya lo hagas hoy
```

## Notas técnicas

- `include_plotlyjs='cdn'` (default) hace que el HTML cargue Plotly desde CDN — ligero (~50 KB por figura). Usar `'inline'` solo si necesitas que funcione offline.
- `full_html=False` (default) devuelve solo el `<div>` con la figura — para insertar en una página existente. `True` devuelve un HTML completo independiente (útil para debug abriendo el string como `.html`).
- El módulo es 100% stateless: no guarda nada. Puedes llamarlo en paralelo desde múltiples requests.

## Test rápido (para verificar antes de integrar)

```python
from pinn_visualizer import generar_plotly_3d, generar_plotly_planta

params = {  # un caso conocido del dataset
    'N_pisos': 12, 'n_unid_lado': 3, 'activar_B2': 1, 'activar_B3': 1,
    'L_mod_m': 3.5, 'prof_depto_m': 7.5, 'ancho_corredor_m': 1.7,
    'L_nucleo_m': 6.0, 'B_nucleo_m': 4.5, 'h_story_m': 2.7,
    'fc_MPa': 30, 'gk_kN_m2': 7.0,
    't_muro_nucleo_m': 0.25, 't_muro_borde_m': 0.25, 't_muro_mid_m': 0.20,
    'suelo': 'C', 'zona': 2,
    'Lx_m': 49.0, 'Ly_m': 17.85, 'H_total_m': 32.4, 'A_geom_m2': 874.65,
}

html = generar_plotly_3d(params, full_html=True)
with open('test_3d.html', 'w', encoding='utf-8') as f:
    f.write(html)
# Abrir test_3d.html en el navegador y verificar que sale igual que en el notebook.
```

## Lo que YO (Claude Code) debo decidir al integrarlo

1. **Dónde calcular los derivados** (`Lx_m`, `Ly_m`, etc.). Recomendación: en una función `enrich_params(params)` que se llame ANTES de pasar a la PINN y al visualizador, para que ambos vean los mismos números.
2. **Si la PINN ya devuelve `modal` con las claves esperadas** por `generar_plotly_modos`. Verificar y, si no, mapear las salidas del modelo al formato del docstring.
3. **Manejo de errores**: si `build_family_B_geometry` falla (parámetros fuera del dominio), envolver la llamada en try/except y devolver un HTML de error legible al frontend.
