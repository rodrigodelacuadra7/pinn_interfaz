from django.core.validators import FileExtensionValidator
from django.db import models


class ModeloPINN(models.Model):
    """Registro de un par modelo/scalers subido por el administrador."""

    nombre = models.CharField(
        max_length=200,
        help_text='Nombre descriptivo, ej. "model_fase2_definitivo seed2718"',
    )
    archivo_modelo = models.FileField(
        upload_to='modelos/',
        validators=[FileExtensionValidator(allowed_extensions=['pt'])],
        help_text='Archivo de pesos PyTorch (.pt)',
    )
    archivo_scalers = models.FileField(
        upload_to='modelos/',
        validators=[FileExtensionValidator(allowed_extensions=['pkl'])],
        help_text='Archivo de scalers pickle (.pkl)',
    )
    activo = models.BooleanField(
        default=False,
        help_text='Solo un registro puede estar activo a la vez.',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Modelo PINN'
        verbose_name_plural = 'Modelos PINN'
        ordering = ['-creado']

    def __str__(self):
        estado = '✓ activo' if self.activo else 'inactivo'
        return f'{self.nombre} [{estado}]'

    def save(self, *args, **kwargs):
        # Solo un registro activo: desactiva los demás antes de guardar.
        if self.activo:
            ModeloPINN.objects.exclude(pk=self.pk).filter(activo=True).update(activo=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_activo(cls):
        """Devuelve el registro activo o None."""
        return cls.objects.filter(activo=True).first()
