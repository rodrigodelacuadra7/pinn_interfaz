# Plan — Desplegar la web Django + PINN en Hugging Face Spaces (Docker)

## Contexto

El proyecto de tesis ya tiene una web Django funcional (`web/`) que envuelve la PINN (PyTorch CPU, torch 2.4.0) con interfaz de predicción, admin para subir modelos y sugerencias de mejora. El modelo va **horneado en la imagen** vía `web/seed/` y `seed_modelo` lo siembra como `ModeloPINN` activo al arrancar, así que no depende de disco persistente.

Objetivo: publicarlo gratis en **Hugging Face Spaces** (SDK Docker) para mostrarlo. HF da 16 GB RAM / 2 vCPU sin tarjeta de crédito — ideal para una demo PyTorch. El disco es **efímero** (las subidas por admin y la SQLite se pierden al reiniciar el Space), lo cual es aceptable porque el modelo viene en la imagen.

Restricciones de HF Docker Spaces (verificadas en docs oficiales):
- El contenedor **corre como UID 1000** → hay que crear el usuario `user` y dar permisos antes de copiar/escribir.
- La app debe escuchar en el **puerto declarado en `app_port`** del frontmatter del `README.md` (default `7860`).
- Se necesita un `README.md` con bloque YAML (`sdk: docker`, `app_port`, title, emoji…) en la **raíz del repo del Space**.
- Variables y secrets se configuran en *Settings* del Space y llegan como env vars en runtime.

**Decisiones tomadas:**
- **Space nuevo**: crear un Space Docker en HF y subir el **contenido de `web/`** como raíz del Space. El repo de GitHub queda intacto.
- **Admin habilitado en HF**: crear el superusuario automáticamente desde secrets (`DJANGO_SUPERUSER_*`) en el entrypoint, para poder demostrar la subida de modelos.

---

## Parte A — Adaptar el contenedor a HF (puerto + usuario UID 1000)

### A.1 `web/Dockerfile`
Reescribir para cumplir el patrón de permisos de HF:
- Tras instalar dependencias (que pueden seguir como root), crear el usuario: `RUN useradd -m -u 1000 user`.
- Copiar el código con `COPY --chown=user . /app/`.
- Crear y dar permiso a los directorios que se escriben en runtime **antes** de cambiar de usuario:
  `RUN mkdir -p /app/data /app/media /app/staticfiles && chown -R user:user /app/data /app/media /app/staticfiles`.
- `USER user` antes del `ENTRYPOINT`.
- `EXPOSE 7860` (informativo).
- Mantener `libgomp1` y la instalación de `torch==2.4.0` CPU-only.

> SQLite (`/app/data`), media (`/app/media`) y staticfiles (`/app/staticfiles`) deben ser escribibles por UID 1000. Los defaults de `settings.py` ya apuntan a `BASE_DIR/data` y `BASE_DIR/media`, no hace falta tocar settings para las rutas.

### A.2 `web/entrypoint.sh`
- Cambiar el bind de gunicorn de `0.0.0.0:8000` a `0.0.0.0:${PORT:-7860}` (configurable; default 7860 para HF).
- Agregar, **antes** de `gunicorn`, un bloque idempotente de superusuario automático:
  ```sh
  if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Asegurando superusuario..."
    python manage.py createsuperuser --noinput || true
  fi
  ```
  (`createsuperuser --noinput` toma `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD`; `|| true` evita fallar si ya existe.)
- Mantener `collectstatic`, `migrate` y `seed_modelo` tal como están.

---

## Parte B — Configuración del Space

### B.1 `web/README.md` (nuevo — frontmatter de HF)
Crear un README dedicado al Space con el bloque YAML al inicio:
```yaml
---
title: PINN Familia B — Respuesta Sísmica NCh433
emoji: 🏢
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
```
Debajo, una breve descripción de la demo (qué predice, cómo usarla). No interfiere con el `README.md` de la raíz del repo de GitHub (que documenta el proyecto completo).

### B.2 Variables y secrets en *Settings* del Space
- **Secrets**: `DJANGO_SECRET_KEY` (clave aleatoria), `DJANGO_SUPERUSER_PASSWORD`.
- **Variables**: `DJANGO_DEBUG=0`, `DJANGO_SUPERUSER_USERNAME=admin`, `DJANGO_SUPERUSER_EMAIL=...`, `CSRF_TRUSTED_ORIGINS=https://*.hf.space`, y opcionalmente `DJANGO_ALLOWED_HOSTS=.hf.space` (el default actual ya es `*`).

> `settings.py` ya lee `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` desde env, y Django 4.2 acepta el comodín `https://*.hf.space` en CSRF — **no se necesita cambiar código de settings**. `CSRF_TRUSTED_ORIGINS` con el dominio HF es imprescindible para que el login del admin (POST) funcione bajo HTTPS.

---

## Parte C — Crear y publicar el Space

1. Crear el Space en https://huggingface.co/new-space → SDK **Docker**, hardware **CPU basic (free)**.
2. Clonar el repo del Space (`git clone https://huggingface.co/spaces/<user>/<space>`).
3. Copiar el **contenido de `web/`** (incluido `web/seed/` con los `.pt`/`.pkl`) a la raíz del repo del Space. El `.pt` se sube por **Git LFS** (HF lo gestiona; verificar que `*.pt` y `*.pkl` queden trackeados por LFS).
4. `git add . && git commit -m "deploy inicial" && git push`.
5. HF construye la imagen automáticamente; seguir los **Build logs** y luego **Container logs** hasta ver gunicorn escuchando en `:7860`.

---

## Verificación end-to-end

1. **Build local (opcional, recomendado antes de pushear)** desde `web/`:
   `docker build -t pinn-hf . && docker run -p 7860:7860 -e PORT=7860 -e DJANGO_DEBUG=0 -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_PASSWORD=test1234 pinn-hf`
   → abrir `http://localhost:7860/`, correr una predicción; confirmar permisos (UID 1000) y que `migrate`/`seed_modelo` no fallan.
2. En el Space ya desplegado (`https://<user>-<space>.hf.space/`):
   - La interfaz carga y una predicción devuelve resultados (T₁, drifts, veredicto).
   - Un caso que **NO cumple** muestra las **sugerencias**.
   - El botón `t_muro_borde` muestra 15/18/20/22/25.
3. Admin: entrar a `/admin` con `admin` / `DJANGO_SUPERUSER_PASSWORD`, ver el `ModeloPINN` sembrado activo; subir un `.pt`/`.pkl` y comprobar que la siguiente predicción usa el nuevo (recarga por firma). Aclarar que esto **no persiste** si el Space se reinicia.

---

## Notas y trade-offs

- **Disco efímero**: tras un reinicio del Space, vuelven los archivos horneados en `web/seed/` (estado limpio). Para persistir subidas/usuarios haría falta *persistent storage* de HF (de pago) — fuera de alcance para la demo.
- **Sleep**: el Space free se duerme tras 48 h de inactividad; despierta solo con la primera visita (tarda unos segundos en recargar PyTorch).
- **Arranque**: con 2 workers gunicorn cada uno precarga la PINN (~1.4M params); con 16 GB no hay problema, pero el primer arranque tarda. Se puede bajar a `--workers 1` para acelerar/ahorrar RAM (opcional, vía edición del entrypoint).
- **GitHub intacto**: el Space es un repo aparte; aun así conviene commitear también en GitHub los cambios de A.1/A.2 (Dockerfile/entrypoint) porque mejoran la portabilidad (puerto configurable, usuario no-root).
