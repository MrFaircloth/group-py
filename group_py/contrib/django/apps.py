"""Django app configuration for GroupPy integration."""

from django.apps import AppConfig


class GroupPyDjangoConfig(AppConfig):
    """GroupPy Django app configuration."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'group_py.contrib.django'
    label = 'group_py_django'  # Avoid conflicts with other apps
    verbose_name = 'GroupMe Integration'
