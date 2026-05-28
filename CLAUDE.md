# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Jupyter Notebook interface for a Physics-Informed Neural Network (PINN) metamodel that predicts the seismic response of "Familia B" residential buildings (Chilean reinforced concrete apartment complexes) per NCh433 + DS61 standards.

Given building geometry and structural parameters, it predicts:
- Modal properties (periods T₁–T₁₈ and mode shapes Φ)
- Per-floor seismic response (displacements Ux, Uy and interstory drifts δx, δy)
- Base shear forces (Vb,x, Vb,y)
- NCh433 compliance verdict (drift limit ≤ 0.002)

## How to Run

```bash
pip install torch numpy matplotlib
jupyter lab Interfaz_PINN_FamiliaB.ipynb
```

Run cells sequentially (0–10). Edit parameters in Cell 10 and re-run from Cell 10 onward for new predictions. There are no build, test, or lint commands — this is an interactive notebook.

**Required files in project root** (already present):
- `model_fase2_seed2718.pt` — pre-trained PyTorch weights (1.377M params)
- `scalers_trial16.pkl` — serialized normalization statistics

> Cell 2 currently has hardcoded absolute paths pointing to `C:\Users\rodri\Documents\PINN\...`. If those files are absent, update `MODEL_PATH` and `SCALERS_PATH` in **Cell 0** to use relative `Path('model_fase2_seed2718.pt')` and `Path('scalers_trial16.pkl')`.

## Architecture

The notebook is organized as a 5-layer pipeline across 11 cells:

### Cell 0 — Configuration
Global constants: `MODEL_PATH`, `SCALERS_PATH`, `DRIFT_LIMIT_NCh433 = 0.002`, `MODEL_TAG`.

### Cell 1 — Neural Network Definition (`PINNModal_v4`)
Two specialized encoders share a `ResBlock` building block (Linear → LayerNorm → SiLU + residual):
- `encoder_T1` (2 ResBlocks, hidden=128) feeds `head_T1` → predicts log(T₁)
- `encoder` (4 ResBlocks, hidden=256) feeds:
  - `head_T_rest` → log-delta T₂–T₁₈
  - `head_Phi` → mode shapes (18 modes × 18 floors × 3 DOF = 972 outputs)
  - `head_resp` → per-floor Ux, Uy, δx, δy (72 outputs)
  - `head_Vb` → base shears (2 outputs)

Outputs beyond `N_pisos` are zeroed via a mask tensor. All continuous outputs are in log-space; inverse-transformed using scaler statistics from the pickle file.

### Cells 3–5 — Domain Validation & Feature Construction
`DOMAIN` dict defines valid ranges for 16 building parameters (continuous min/max or discrete enumerations). `validar_dominio()` returns warnings and a `grave` flag for extrapolation. `construir_vector_entrada()` maps 16 physical params to a 21-feature normalized input vector (14 continuous + 4 one-hot for soil type A/B/C/D and seismic zone 1/2/3 + 3 derived).

### Cells 7–8 — Inference & Post-processing
- `predict_edificio(params)` — normalizes input, runs forward pass, denormalizes outputs, returns a structured dict with keys: `params`, `modal` (T, Φ), `respuesta` (U, δ per floor), `Vb`, `geometria`.
- `reporte_normativo(resultado)` — checks max drift vs. 0.002 limit, period sanity (T₁ ∈ [0.05, 5.0] s), extrapolation risk; returns `veredicto` ("CUMPLE" / "NO CUMPLE").

### Cells 6, 9 — Visualization
- `visualizar_edificio()` — 3D wireframe of floor plates, columns, core.
- `graficar_resultados()` — 4-subplot dashboard: drift profiles with NCh433 limit, displacement profiles, first 6 modal periods, compliance banner.

### Cell 10 — User Interface
Two constructors:
- `edificio_simple(N_pisos, suelo, zona)` — 3-parameter shortcut with sensible defaults for the remaining 13 parameters.
- `edificio_experto(**kwargs)` — full 16-parameter specification.

## Key Conventions

- All variable/function names and comments are in **Spanish** (Chilean structural engineering domain).
- The model expects `batch_size=1`; no batch utilities exist.
- `np.float32` is used throughout for model I/O.
- GPU is used when available (`torch.cuda.is_available()`); CPU fallback is automatic.
- `MASS_PARTIC_MIN = 0.90` is defined in Cell 0 but never used in the compliance check.

## Remote

`https://github.com/rodrigodelacuadra7/pinn_interfaz.git` (branch: `main`)
