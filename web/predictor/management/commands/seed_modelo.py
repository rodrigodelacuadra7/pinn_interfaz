"""
Management command: seed_modelo
Crea el registro PINN activo inicial a partir de los archivos en web/seed/,
si no existe ningún registro en la base de datos. Idempotente.
"""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


SEED_DIR = Path(__file__).resolve().parents[3] / 'seed'
SEED_MODEL   = SEED_DIR / 'model_fase2_definitivo.pt'
SEED_SCALERS = SEED_DIR / 'scalers_trial16_DEFINITIVO.pkl'


class Command(BaseCommand):
    help = 'Siembra el modelo PINN inicial en la base de datos (idempotente).'

    def handle(self, *args, **options):
        from predictor.models import ModeloPINN

        if ModeloPINN.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                'seed_modelo: ya existe al menos un registro PINN — sin cambios.'
            ))
            return

        if not SEED_MODEL.exists() or not SEED_SCALERS.exists():
            self.stderr.write(self.style.WARNING(
                f'seed_modelo: no se encontraron archivos semilla en {SEED_DIR}. '
                'Sube el modelo manualmente desde el admin.'
            ))
            return

        # Copiar archivos al directorio media
        media_modelos = Path(settings.MEDIA_ROOT) / 'modelos'
        media_modelos.mkdir(parents=True, exist_ok=True)

        dst_model   = media_modelos / SEED_MODEL.name
        dst_scalers = media_modelos / SEED_SCALERS.name
        shutil.copy2(SEED_MODEL, dst_model)
        shutil.copy2(SEED_SCALERS, dst_scalers)

        # Crear registro con rutas relativas a MEDIA_ROOT
        ModeloPINN.objects.create(
            nombre='model_fase2_definitivo (semilla inicial)',
            archivo_modelo=f'modelos/{SEED_MODEL.name}',
            archivo_scalers=f'modelos/{SEED_SCALERS.name}',
            activo=True,
        )
        self.stdout.write(self.style.SUCCESS(
            'seed_modelo: registro PINN inicial creado y marcado como activo.'
        ))
