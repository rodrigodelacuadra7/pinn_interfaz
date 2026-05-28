# Modal PINN · NCH433 — Interfaz Web

Herramienta web para predecir la **respuesta sísmica de edificios residenciales Familia B** (hormigón armado chileno) utilizando una red neuronal informada por física (PINN). Evalúa automáticamente el cumplimiento de la norma **NCh433 + DS61**.

---

## ¿Qué hace esta herramienta?

Dado un edificio con sus características geométricas y de materiales, la aplicación predice en **menos de un segundo**:

- **Períodos y formas modales** — los 18 modos de vibración del edificio (T₁ a T₁₈) y las formas en que se deforma en cada uno.
- **Desplazamientos por piso** — cuánto se mueve cada piso en X e Y durante un sismo.
- **Derivas de entrepiso** — el indicador clave de daño estructural (δx y δy por piso).
- **Corte basal** — la fuerza sísmica total que actúa sobre la estructura (Vb,x y Vb,y).
- **Veredicto NCh433** — si el edificio **CUMPLE** o **NO CUMPLE** el límite de deriva ≤ 0.002.

La predicción usa un modelo de red neuronal pre-entrenado (`PINNModal_v4b`, 1.377.064 parámetros, Fase 2, semilla 2718) calibrado para edificios de **6 a 18 pisos**, suelos tipo A/B/C/D y zonas sísmicas 1/2/3.

---

## Contenido del repositorio

```
pinn_interfaz/
├── model_fase2_seed2718.pt       ← Pesos del modelo PINN (5.3 MB)
├── scalers_trial16.pkl           ← Estadísticas de normalización
├── Interfaz_PINN_FamiliaB.ipynb  ← Notebook original (referencia técnica)
├── Interfaz-handoff/             ← Diseño visual de referencia (UI)
└── web/                          ← Aplicación web Django (lo que debes ejecutar)
    ├── Dockerfile
    ├── docker-compose.yml
    └── ...
```

---

## Requisitos previos

Solo necesitas tener instalado **Docker Desktop**.

- **Windows / Mac**: descarga desde [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: instala Docker Engine siguiendo [docs.docker.com/engine/install](https://docs.docker.com/engine/install/)

Verifica que Docker está funcionando abriendo una terminal y ejecutando:

```bash
docker --version
```

Deberías ver algo como `Docker version 28.x.x`.

> **Nota:** No necesitas instalar Python, PyTorch, ni ninguna otra dependencia. Docker se encarga de todo.

---

## Cómo ejecutar la aplicación

### 1. Abre una terminal en la carpeta `web/`

En Windows puedes hacer clic derecho sobre la carpeta `web` y elegir "Abrir en Terminal", o desde PowerShell:

```powershell
cd C:\Users\rodri\OneDrive\Desktop\pinn_interfaz\web
```

### 2. Construye la imagen Docker (solo la primera vez)

```bash
docker compose build
```

Esto descarga e instala todas las dependencias dentro de un contenedor aislado. Tarda entre 3 y 8 minutos la primera vez según tu conexión. Las siguientes veces es instantáneo.

### 3. Inicia la aplicación

```bash
docker compose up
```

Cuando veas en la terminal algo como:

```
[INFO] Booting worker with pid: ...
[INFO] Arbiter booted
```

La aplicación está lista. Abre tu navegador y ve a:

```
http://localhost:8000
```

### 4. Para detener la aplicación

Presiona `Ctrl + C` en la terminal, o desde otra terminal:

```bash
docker compose down
```

---

## Cómo usar la interfaz

La pantalla está dividida en **tres columnas**:

### Columna izquierda — Parámetros del edificio

Aquí defines las características del edificio que quieres analizar. Los parámetros están agrupados en cinco secciones:

| Sección | Qué configuras |
|---|---|
| **01 Configuración sísmica** | Zona sísmica (1/2/3) y tipo de suelo (A/B/C/D) |
| **02 Geometría global** | Número de pisos (6–18), unidades por lado (2–6), bloque B2 |
| **03 Dimensiones modulares** | Módulo de longitud, profundidad de departamento, ancho de corredor, altura de entrepiso |
| **04 Núcleo y materiales** | Dimensiones del núcleo estructural, resistencia del hormigón (fc), carga de piso (gk) |
| **05 Espesores de muros** | Espesores de muros de núcleo, borde e interior (en cm) |

Una vez configurados los parámetros, presiona el botón **▶ PREDECIR**.

### Columna central — Visualización 3D

Muestra el edificio en tres dimensiones **animado con la deformada del modo sísmico seleccionado**. Puedes:

- Cambiar entre vistas **FRONTAL**, **ISO** (isométrica) y **PLANTA**.
- Reproducir o pausar la animación con los controles de la barra inferior.
- Arrastrar el cursor de tiempo para ver la deformación en cualquier instante.

Debajo del edificio 3D aparecen dos gráficos:
- **Derivas de entrepiso (δx y δy)** — con línea de límite NCh433 (0.002).
- **Espectro de respuesta NCh433** — calculado analíticamente para la zona y suelo seleccionados, con marcas en los períodos predichos.

### Columna derecha — Resultados del PINN

Muestra los outputs numéricos de la predicción:

- **KPIs**: T₁, T₂, desplazamiento máximo en techo, deriva máxima, cortes basales Vb,x y Vb,y.
- **Veredicto NCh433**: CUMPLE (verde) o NO CUMPLE (rojo), con razones del fallo si aplica.
- **Tabla de modos**: los 18 períodos predichos con sus frecuencias y frecuencias angulares. Haz clic en cualquier fila para ver ese modo animado en el 3D.
- **Formas modales**: miniaturas de las primeras 6 formas modales reales (calculadas por el PINN). Clic para seleccionar.
- **Perfil de desplazamientos Ux / Uy**: desplazamiento absoluto de cada piso.

---

## Dominio de validez del modelo

El modelo PINN fue entrenado con edificios dentro de estos rangos. Predicciones fuera de ellos pueden ser poco confiables:

| Parámetro | Rango válido |
|---|---|
| Número de pisos | 6 a 18 |
| Unidades por lado | 2 a 6 |
| Módulo de longitud | 3.20 m a 3.80 m |
| Profundidad departamento | 7.00 m a 7.90 m |
| Ancho corredor | 1.50 m a 1.90 m |
| Longitud núcleo | 5.40 m a 6.60 m |
| Ancho núcleo | 4.00 m a 5.00 m |
| Altura de entrepiso | 2.60 / 2.70 / 2.80 / 2.90 m |
| Resistencia hormigón fc | 25 / 30 / 35 / 40 MPa |
| Carga de piso gk | 6.0 / 6.5 / 7.0 / 7.5 kN/m² |
| Espesor muro núcleo | 18 / 20 / 22 / 25 / 28 / 30 cm |
| Espesor muro borde | 18 / 20 / 22 / 25 / 28 / 30 cm |
| Espesor muro interior | 15 / 18 / 20 / 22 / 25 cm |
| Tipo de suelo | A / B / C / D |
| Zona sísmica | 1 / 2 / 3 |

La aplicación advierte cuando los parámetros ingresados caen fuera del dominio.

---

## Arquitectura técnica (para desarrolladores)

### Del notebook al servidor — cómo se descompuso el `.ipynb`

El notebook original (`Interfaz_PINN_FamiliaB.ipynb`) tiene 11 celdas con código global (variables y funciones compartidas entre celdas). Para convertirlo en una aplicación web se extrajo cada bloque en un módulo Python independiente, con dependencias explícitas en vez de globales. La siguiente tabla muestra la correspondencia exacta:

| Celda del notebook | Contenido original | Archivo Django |
|---|---|---|
| **Celda 0** | Constantes de configuración: `MODEL_PATH`, `SCALERS_PATH`, `DRIFT_LIMIT_NCh433` | `pinn_web/settings.py` (rutas via env vars) y `predictor/pinn/domain.py` (constantes) |
| **Celda 1** | Clases `ResBlock` y `PINNModal_v4` (arquitectura de la red neuronal) | `predictor/pinn/model.py` — copiado sin cambios |
| **Celda 2** | Carga de pesos (`torch.load`) y scalers (`pickle.load`), variables globales `model`, `SC`, `device` | `predictor/pinn/loader.py` — convertido a singleton lazy; `predictor/apps.py` llama al loader al arrancar el servidor |
| **Celda 3** | Dict `DOMAIN` con rangos de cada parámetro y función `validar_dominio()` | `predictor/pinn/domain.py` |
| **Celda 4** | Constructores `edificio_experto()` y `edificio_simple()` con `DEFAULTS_SIMPLE` | `predictor/pinn/domain.py` (constantes de defaults) y `predictor/forms.py` (validación en Django) |
| **Celda 5** | Función `construir_X(params)` → vector de 21 features + máscara de pisos | `predictor/pinn/features.py` — adaptada para recibir `COLS_BASE` como argumento en vez de variable global |
| **Celda 6** | `visualizar_edificio()` — gráfico 3D con matplotlib | Reemplazado por `predictor/static/predictor/js/building3d.js` (Three.js interactivo con la deformada modal real del PINN) |
| **Celda 7** | `predict_edificio(params)` — función principal: normaliza, ejecuta el modelo, desnormaliza | `predictor/pinn/inference.py` — adaptada para recibir `model`, `SC` y `device` como argumentos en vez de globales |
| **Celda 8** | `reporte_normativo(res)` — verifica derivas y período contra límites NCh433 | `predictor/pinn/normativa.py` — copiada sin cambios |
| **Celda 9** | `graficar_resultados(res, rep)` — dashboard matplotlib con 4 subplots | Reemplazado por `predictor/static/predictor/js/charts.js` (SVG puro: drift vs piso, espectro NCh433, desplazamientos) |
| **Celda 10** | Ejemplo de uso: construye parámetros, llama predict, imprime y grafica | `predictor/views.py` (`api_predict`) + `predictor/static/predictor/js/app.js` (orquesta la UI) |

#### Cambios de diseño respecto al notebook

**Variables globales → inyección de dependencias**
En el notebook, `model`, `SC` y `device` son variables globales accesibles desde cualquier celda. En Django, cada función las recibe como argumento:

```python
# Notebook (global)
resultado = predict_edificio(params)  # usa `model` y `SC` globales

# Django (inyectado)
model, SC, device = get_model_and_scalers()
resultado = predict_edificio(params, model, SC, device)
```

Esto permite que el servidor cargue el modelo una sola vez (`loader.py`) y lo reutilice en todas las peticiones sin recargarlo.

**Matplotlib (server-side) → SVG + Three.js (client-side)**
Los gráficos del notebook generan imágenes PNG con matplotlib en el servidor. En la app web, todos los gráficos se dibujan en el navegador: el edificio 3D con Three.js usando las formas modales reales Φ del PINN, y los gráficos 2D con SVG puro. Ventajas: sin dependencia de matplotlib en producción, gráficos interactivos y animados.

**Celdas ejecutadas secuencialmente → petición HTTP**
El flujo del notebook (definir parámetros → ejecutar celdas en orden → ver resultado) se convierte en una sola petición `POST /api/predict` que recibe los 16 parámetros como JSON y devuelve todos los resultados en la respuesta.

---

### Stack

| Componente | Tecnología |
|---|---|
| Backend | Django 4.2 + Gunicorn |
| Modelo PINN | PyTorch 2.4 (CPU) |
| Archivos estáticos | WhiteNoise |
| Frontend 3D | Three.js r160 |
| Gráficos 2D | SVG puro (sin librerías) |
| Contenedor | Docker (Python 3.11-slim) |

### Estructura del proyecto web

```
web/
├── Dockerfile                    ← Imagen Python 3.11 + torch CPU
├── docker-compose.yml            ← Servicio en puerto 8000
├── entrypoint.sh                 ← collectstatic → gunicorn
├── requirements.txt
├── manage.py
├── pinn_web/
│   ├── settings.py               ← MODEL_PATH y SCALERS_PATH via env vars
│   ├── urls.py
│   └── wsgi.py
└── predictor/
    ├── apps.py                   ← Precarga el modelo una sola vez al arrancar
    ├── forms.py                  ← Validación de los 16 parámetros
    ├── views.py                  ← GET / y POST /api/predict
    ├── pinn/
    │   ├── model.py              ← Arquitectura PINNModal_v4 (ResBlock)
    │   ├── domain.py             ← DOMAIN dict y validar_dominio()
    │   ├── features.py           ← construir_X() → vector de 21 features
    │   ├── inference.py          ← predict_edificio()
    │   ├── normativa.py          ← reporte_normativo() NCh433
    │   ├── spectrum.py           ← Espectro NCh433 analítico
    │   └── loader.py             ← Singleton de carga del modelo
    ├── templates/predictor/
    │   └── index.html            ← Layout 3 columnas
    └── static/predictor/
        ├── css/styles.css        ← Tema dark (IBM Plex Mono/Sans)
        └── js/
            ├── app.js            ← Orquesta UI y fetch /api/predict
            ├── building3d.js     ← Edificio 3D con deformada modal real
            └── charts.js         ← Gráficos SVG (drift, espectro, desplazamientos)
```

### API

**`POST /api/predict`**

Recibe un JSON con los 16 parámetros del edificio y devuelve:

```json
{
  "modal": {
    "T": [0.712, 0.243, ...],
    "Phi_x": [[...], ...],
    "Phi_y": [[...], ...]
  },
  "respuesta": {
    "Ux_por_piso": [...],
    "Uy_por_piso": [...],
    "dx_por_piso": [...],
    "dy_por_piso": [...],
    "Vb_x": 1234567.8,
    "Vb_y": 987654.3
  },
  "normativa": {
    "veredicto": "CUMPLE",
    "deriva_x_max": 0.00134,
    "piso_dx_max": 5,
    ...
  },
  "spectrum": [[0.02, 0.18], [0.04, 0.22], ...]
}
```

### Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta Django | valor de dev (cambiar en prod) |
| `DJANGO_DEBUG` | Modo debug (`1`/`0`) | `0` en Docker |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1` |
| `MODEL_PATH` | Ruta al archivo `.pt` | `/models/model_fase2_seed2718.pt` |
| `SCALERS_PATH` | Ruta al archivo `.pkl` | `/models/scalers_trial16.pkl` |

### Ejecución en desarrollo local (sin Docker)

Requiere Python 3.10+ con `pip`:

```bash
cd web/
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
set MODEL_PATH=..\model_fase2_seed2718.pt
set SCALERS_PATH=..\scalers_trial16.pkl
python manage.py runserver
```

---

## Preguntas frecuentes

**¿Cuánto tarda cada predicción?**
Menos de 1 segundo en CPU. El modelo se carga una sola vez al iniciar el servidor (~2 segundos al arrancar), y las predicciones posteriores son instantáneas.

**¿Necesito GPU?**
No. La aplicación usa PyTorch en modo CPU, que es más que suficiente para inferencia con este modelo.

**¿Puedo cambiar el modelo por una versión más nueva?**
Sí. Reemplaza `model_fase2_seed2718.pt` y `scalers_trial16.pkl` en la raíz del repositorio. No es necesario reconstruir la imagen Docker porque los archivos se montan como volúmenes.

**¿Qué significa "FAMILIA B"?**
Familia B es una tipología de edificios residenciales chilenos de hormigón armado con núcleo central y departamentos a ambos lados de un corredor central. El PINN fue entrenado exclusivamente para esta tipología.

**¿Qué norma evalúa?**
Evalúa la **NCh433 Of.1996 Modificada 2009** (Diseño Sísmico de Edificios) junto con el **DS61** de 2011, verificando el límite de deriva de entrepiso ≤ 0.002.

---

## Créditos

Modelo PINN desarrollado como parte de un proyecto de investigación de metamodelado estructural para la familia de edificios residenciales tipo B en Chile.

- **Modelo**: `PINNModal_v4b — Fase 2, semilla 2718`
- **Parámetros**: 1.377.064
- **Framework**: PyTorch 2.x + Django 4.2
