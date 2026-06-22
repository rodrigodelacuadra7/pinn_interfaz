from django.contrib import admin

from predictor.models import ModeloPINN


@admin.register(ModeloPINN)
class ModeloPINNAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'creado', 'actualizado')
    list_filter = ('activo',)
    readonly_fields = ('creado', 'actualizado')
    fields = ('nombre', 'archivo_modelo', 'archivo_scalers', 'activo', 'creado', 'actualizado')
    actions = ['marcar_activo']

    @admin.action(description='Marcar como modelo activo')
    def marcar_activo(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Selecciona exactamente un modelo para activar.', level='error')
            return
        modelo = queryset.first()
        modelo.activo = True
        modelo.save()
        self.message_user(request, f'"{modelo.nombre}" marcado como activo.')
