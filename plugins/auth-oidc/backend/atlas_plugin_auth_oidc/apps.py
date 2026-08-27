from django.apps import AppConfig


class AtlasAuthOIDCConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "atlas_plugin_auth_oidc"
    label = "atlas_auth_oidc"
