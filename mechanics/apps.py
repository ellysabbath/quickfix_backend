# mechanics/apps.py
from django.apps import AppConfig

class MechanicsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mechanics'
    verbose_name = 'Mechanics and Service Requests'