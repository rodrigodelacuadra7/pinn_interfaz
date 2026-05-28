from django.apps import AppConfig


class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'

    def ready(self):
        import logging
        logger = logging.getLogger(__name__)
        try:
            from predictor.pinn.loader import get_model_and_scalers
            get_model_and_scalers()
            logger.info('PINN model loaded successfully.')
        except Exception as exc:
            logger.warning('Could not preload PINN model at startup: %s', exc)
