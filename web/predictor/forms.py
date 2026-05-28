from django import forms
from predictor.pinn.domain import DOMAIN, validar_dominio


class EdificioForm(forms.Form):
    N_pisos = forms.IntegerField(
        min_value=6, max_value=18,
        initial=8,
        label='N° Pisos',
    )
    n_unid_lado = forms.IntegerField(
        min_value=2, max_value=6,
        initial=3,
        label='Unidades por lado',
    )
    activar_B2 = forms.TypedChoiceField(
        choices=[(0, 'No'), (1, 'Sí')],
        coerce=int,
        initial=1,
        label='Activar bloque B2',
    )
    L_mod_m = forms.FloatField(
        min_value=3.20, max_value=3.80,
        initial=3.50,
        label='L módulo [m]',
    )
    prof_depto_m = forms.FloatField(
        min_value=7.00, max_value=7.90,
        initial=7.50,
        label='Prof. depto [m]',
    )
    ancho_corredor_m = forms.FloatField(
        min_value=1.50, max_value=1.90,
        initial=1.70,
        label='Ancho corredor [m]',
    )
    L_nucleo_m = forms.FloatField(
        min_value=5.40, max_value=6.60,
        initial=6.00,
        label='L núcleo [m]',
    )
    B_nucleo_m = forms.FloatField(
        min_value=4.00, max_value=5.00,
        initial=4.50,
        label='B núcleo [m]',
    )
    h_story_m = forms.TypedChoiceField(
        choices=[(v, f'{v} m') for v in [2.60, 2.70, 2.80, 2.90]],
        coerce=float,
        initial=2.70,
        label='H entrepiso [m]',
    )
    fc_MPa = forms.TypedChoiceField(
        choices=[(v, f'{v} MPa') for v in [25, 30, 35, 40]],
        coerce=int,
        initial=30,
        label='fc [MPa]',
    )
    gk_kN_m2 = forms.TypedChoiceField(
        choices=[(v, f'{v} kN/m²') for v in [6.0, 6.5, 7.0, 7.5]],
        coerce=float,
        initial=7.0,
        label='Carga gk [kN/m²]',
    )
    t_muro_nucleo_m = forms.TypedChoiceField(
        choices=[(v, f'{int(v*100)} cm') for v in [0.18, 0.20, 0.22, 0.25, 0.28, 0.30]],
        coerce=float,
        initial=0.25,
        label='t muro núcleo',
    )
    t_muro_borde_m = forms.TypedChoiceField(
        choices=[(v, f'{int(v*100)} cm') for v in [0.18, 0.20, 0.22, 0.25, 0.28, 0.30]],
        coerce=float,
        initial=0.25,
        label='t muro borde',
    )
    t_muro_mid_m = forms.TypedChoiceField(
        choices=[(v, f'{int(v*100)} cm') for v in [0.15, 0.18, 0.20, 0.22, 0.25]],
        coerce=float,
        initial=0.20,
        label='t muro interior',
    )
    suelo = forms.ChoiceField(
        choices=[('A', 'A — Roca'), ('B', 'B — Denso'), ('C', 'C — Firme'), ('D', 'D — Medio')],
        initial='C',
        label='Tipo de suelo',
    )
    zona = forms.TypedChoiceField(
        choices=[(1, 'Zona 1'), (2, 'Zona 2'), (3, 'Zona 3')],
        coerce=int,
        initial=2,
        label='Zona sísmica',
    )

    def clean(self):
        cleaned = super().clean()
        if not self.errors:
            avisos, grave = validar_dominio(cleaned)
            if grave:
                raise forms.ValidationError(
                    'Parámetros fuera del dominio de entrenamiento: ' + '; '.join(avisos)
                )
            cleaned['_avisos'] = avisos
        return cleaned
