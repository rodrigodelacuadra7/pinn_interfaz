---
title: PINN Familia B — Respuesta Sísmica NCh433
emoji: 🏢
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# PINN Familia B — Predicción de Respuesta Sísmica

Demo de un metamodelo PINN (Physics-Informed Neural Network) para predecir la
respuesta sísmica de edificios "Familia B" (departamentos chilenos de hormigón armado)
según la normativa **NCh433 + DS61**.

## ¿Qué predice?

A partir de la geometría y parámetros estructurales del edificio, el modelo entrega:

- **Propiedades modales**: períodos T₁–T₁₈ y formas modales Φ
- **Respuesta sísmica por piso**: desplazamientos Ux, Uy y derivas de entrepiso δx, δy
- **Cortantes basales**: Vb,x, Vb,y
- **Verificación normativa**: cumplimiento del límite de deriva ≤ 0.002 (NCh433)

## Cómo usar la demo

1. Completa los parámetros del edificio en el formulario (o usa los valores por defecto).
2. Presiona **Predecir** para obtener los resultados.
3. Revisa el veredicto normativo y las gráficas de derivas y desplazamientos.

> **Nota:** Esta es una demo académica. El disco es efímero: los modelos subidos por
> el admin no persisten entre reinicios del Space.
