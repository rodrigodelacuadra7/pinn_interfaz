# Plan — Desplegar la web Django + PINN en Oracle Cloud (Always Free)

## Contexto

El proyecto de tesis tiene una web Django funcional (`web/`) que envuelve la PINN (PyTorch CPU, torch 2.4.0) con interfaz de predicción, admin para subir modelos y sugerencias de mejora. Ya viene con `web/docker-compose.yml` (servicio `pinn-web`, volúmenes nombrados `pinn-db`/`pinn-media`, healthcheck y `restart: unless-stopped`), y el modelo va horneado en `web/seed/` + sembrado por `seed_modelo`.

Objetivo: publicarlo gratis y **siempre encendido** en **Oracle Cloud Infrastructure (OCI) Always Free** para mostrarlo, como alternativa a Hugging Face. A diferencia de HF, OCI da una **VM dedicada con disco persistente**, por lo que las subidas por el admin y la base SQLite **sí sobreviven** a reinicios, y **no hay sleep** por inactividad.

### Por qué Oracle vs. Hugging Face (comparación rápida)
| | Hugging Face Spaces | Oracle Cloud Always Free |
|---|---|---|
| Recursos | 16 GB RAM / 2 vCPU | **24 GB RAM / 4 vCPU** (Ampere A1 ARM) |
| Persistencia | Disco efímero (se pierde al reiniciar) | **Disco persistente** (200 GB) |
| Sleep | Duerme tras 48 h | **Siempre encendido** |
| Setup | Push a git, build automático | **Manual** (crear VM, instalar Docker, firewall) |
| Tarjeta de crédito | No requiere | **Requiere** (verificación, no cobra en Always Free) |
| HTTPS/dominio | `*.hf.space` gratis | Hay que montarlo (IP pública + reverse proxy) |
| Arquitectura | x86 | **ARM (aarch64)** → ojo con la rueda de torch |

Trade-off: OCI es más potente y persistente pero el setup es manual y usa ARM. Para esta app `docker-compose` ya existente, el grueso del trabajo es aprovisionar la VM y abrir puertos.

---

## Parte A — Aprovisionar la VM

1. Crear cuenta en https://www.oracle.com/cloud/free/ (pide tarjeta para verificación; el shape Always Free no cobra). Elegir una **Home Region** con capacidad de Ampere A1.
2. Crear instancia de cómputo:
   - **Shape**: `VM.Standard.A1.Flex` (Ampere ARM) con **4 OCPUs / 24 GB RAM** — el límite Always Free completo. (Evitar los micro AMD `E2.1.Micro`: solo 1 GB RAM, insuficiente para PyTorch.)
   - **Imagen**: Ubuntu 22.04 LTS (o Oracle Linux 9). Este plan asume **Ubuntu**.
   - **SSH**: subir tu clave pública (genera una con `ssh-keygen` si no tenés).
   - **Networking**: dejar que cree una VCN con subred pública e IP pública.
3. Anotar la **IP pública** asignada.

> Si Ampere A1 aparece "out of capacity", reintentar (es común) o cambiar de Availability Domain / región.

---

## Parte B — Abrir puertos (dos capas de firewall)

OCI bloquea todo por defecto en **dos** niveles; hay que abrir ambos:

1. **Security List / NSG de la VCN** (consola web): agregar Ingress Rules para
   - TCP **80** (HTTP) y TCP **443** (HTTPS) desde `0.0.0.0/0`.
   - (Opcional, solo para pruebas directas: TCP **8000**.)
2. **Firewall del host** (la imagen de Ubuntu en OCI trae iptables restrictivo):
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```

---

## Parte C — Preparar el servidor

Conectar por SSH (`ssh ubuntu@<IP>`) e instalar Docker:
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu      # re-loguear para que tome el grupo
```
Docker Compose v2 ya viene como plugin (`docker compose`).

Traer el código (una de las dos):
- `git clone https://github.com/rodrigodelacuadra7/pinn_interfaz.git` (rama actual), o
- `scp -r` de la carpeta del proyecto.

> El `.pt`/`.pkl` viajan: si clonás de GitHub, asegurate de que `web/seed/*.pt` y `*.pkl` estén versionados (Git LFS) o subilos por `scp` al `web/seed/`.

---

## Parte D — Ajuste por arquitectura ARM (aarch64) — CRÍTICO

El `web/Dockerfile` instala torch desde `--index-url https://download.pytorch.org/whl/cpu`, que está pensado para **x86 CPU-only**. En **ARM/aarch64** la rueda CPU de PyTorch es la **default de PyPI** (no hay variante CUDA para ARM).

Acción: hacer que la instalación de torch funcione en ARM. Opciones:
- **A (recomendada)**: editar `web/Dockerfile` para instalar torch desde PyPI por defecto en ARM, p.ej. dejar `RUN pip install torch==2.4.0` (sin el index-url CPU) — en aarch64 PyPI ya entrega la rueda CPU. Verificar que exista `torch==2.4.0` para `cp311`/`aarch64`; si no, ajustar a la versión disponible más cercana.
- **B**: usar un `Dockerfile` con lógica condicional por `TARGETARCH` (buildx), instalando del index CPU en `amd64` y de PyPI en `arm64`.

> Esta es la principal diferencia de esfuerzo respecto a HF. Conviene **buildear en la propia VM** (que ya es ARM) para evitar cross-build.

---

## Parte E — Configurar y levantar

1. Crear `web/.env` (a partir de `web/.env.example`) con valores de producción:
   ```env
   HOST_PORT=8000
   DJANGO_SECRET_KEY=<clave-aleatoria-larga>
   DJANGO_DEBUG=0
   DJANGO_ALLOWED_HOSTS=<IP-o-dominio>
   CSRF_TRUSTED_ORIGINS=https://<dominio>     # o http://<IP>:8000 para pruebas
   ```
   El `docker-compose.yml` ya consume `HOST_PORT`, `DJANGO_SECRET_KEY`, etc.
2. Build + up desde `web/`:
   ```bash
   cd web && docker compose build && docker compose up -d
   docker compose logs -f      # ver migrate / seed_modelo / "PINN model ready"
   ```
3. Crear el superusuario (acá sí persiste, no hace falta automatizarlo como en HF):
   ```bash
   docker compose exec pinn-web python manage.py createsuperuser
   ```

> Persistencia: `pinn-db` y `pinn-media` son volúmenes Docker en el disco de la VM → la DB y los modelos subidos por el admin **sobreviven** a `docker compose down/up` y a reinicios de la VM.

---

## Parte F — HTTPS y dominio (recomendado para una demo presentable)

La app por defecto sirve gunicorn en el 8000 sin TLS. Para una URL limpia y HTTPS, anteponer un reverse proxy. Opción simple con **Caddy** (TLS automático de Let's Encrypt):

1. Apuntar un dominio a la IP pública. Si no tenés dominio: usar `sslip.io` / `nip.io` (p.ej. `<IP>.sslip.io`) o DuckDNS.
2. Agregar un servicio `caddy` al compose (o `docker run`) con un `Caddyfile`:
   ```
   tu-dominio.sslip.io {
       reverse_proxy pinn-web:8000
   }
   ```
   Poner `pinn-web` y `caddy` en la misma red de compose; Caddy expone 80/443 y obtiene el certificado solo.
3. Actualizar en `web/.env`: `DJANGO_ALLOWED_HOSTS=tu-dominio.sslip.io` y `CSRF_TRUSTED_ORIGINS=https://tu-dominio.sslip.io` (necesario para el login del admin por POST bajo HTTPS).

> Alternativa mínima sin TLS: dejar el 8000 abierto en ambos firewalls y acceder por `http://<IP>:8000` (sirve para mostrar, pero el admin sin HTTPS es menos recomendable).

---

## Verificación end-to-end

1. `docker compose ps` → contenedor `Up (healthy)`.
2. Abrir `http://<IP>:8000/` (o `https://<dominio>/`): la interfaz carga y una predicción devuelve T₁, drifts y veredicto.
3. Caso que **NO cumple** → muestra las **sugerencias**.
4. Botón `t_muro_borde` muestra 15/18/20/22/25.
5. `/admin`: entrar con el superusuario, ver el `ModeloPINN` sembrado activo; subir un `.pt`/`.pkl`, marcarlo activo y confirmar (sin reiniciar) que la siguiente predicción usa el nuevo (recarga por firma).
6. **Persistencia**: `docker compose restart` (o reiniciar la VM) y comprobar que el modelo subido y el superusuario **siguen** ahí.

---

## Notas y trade-offs

- **ARM es el único punto delicado**: validar la rueda de `torch==2.4.0` para aarch64 (Parte D). Si diera problemas, bajar/subir de versión de torch a una con rueda ARM disponible.
- **Always Free real**: mientras se use el shape A1 dentro de los límites (4 OCPU / 24 GB / 200 GB block storage), no hay cobro. Cuentas inactivas pueden reclamar recursos A1 — mantener la VM en uso.
- **Mantenimiento manual**: a diferencia de HF, acá vos administrás SO, parches y Docker. `restart: unless-stopped` + reinicio automático de la VM cubren la mayoría de caídas.
- **Reutiliza el compose existente**: el grueso del despliegue es infra (VM + firewall + ARM); el código de la app casi no cambia salvo el ajuste de torch para ARM.
- Comparar este plan con `DEPLOY_HUGGINGFACE.md` antes de decidir.
