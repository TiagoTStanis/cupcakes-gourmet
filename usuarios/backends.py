from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from usuarios.services.auth_service import autenticar_usuario


class AutenticacaoEmail(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if not email or password is None:
            return None
        try:
            return autenticar_usuario(email, password)
        except ValidationError:
            return None
