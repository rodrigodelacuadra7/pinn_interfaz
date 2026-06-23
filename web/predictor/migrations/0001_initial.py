import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ModeloPINN',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(
                    help_text='Nombre descriptivo, ej. "model_fase2_definitivo seed2718"',
                    max_length=200,
                )),
                ('archivo_modelo', models.FileField(
                    help_text='Archivo de pesos PyTorch (.pt)',
                    upload_to='modelos/',
                    validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pt'])],
                )),
                ('archivo_scalers', models.FileField(
                    help_text='Archivo de scalers pickle (.pkl)',
                    upload_to='modelos/',
                    validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pkl'])],
                )),
                ('activo', models.BooleanField(
                    default=False,
                    help_text='Solo un registro puede estar activo a la vez.',
                )),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Modelo PINN',
                'verbose_name_plural': 'Modelos PINN',
                'ordering': ['-creado'],
            },
        ),
    ]
