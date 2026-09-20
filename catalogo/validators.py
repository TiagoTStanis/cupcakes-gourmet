import os
from django.core.exceptions import ValidationError
from PIL import Image

LIMITE_TAMANHO_IMAGEM_BYTES = 5 * 1024 * 1024
EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png"}


def validar_imagem(arquivo):
    if not arquivo:
        return

    nome = getattr(arquivo, "name", "")
    extensao = os.path.splitext(nome)[1].lower()
    if extensao not in EXTENSOES_VALIDAS:
        raise ValidationError("Extensão inválida. Envie uma imagem JPG ou PNG.")

    tamanho = getattr(arquivo, "size", None)
    if tamanho is not None and tamanho > LIMITE_TAMANHO_IMAGEM_BYTES:
        raise ValidationError("A imagem deve ter no máximo 5MB.")

    posicao_original = None
    if hasattr(arquivo, "tell") and hasattr(arquivo, "seek"):
        try:
            posicao_original = arquivo.tell()
        except (AttributeError, OSError):
            posicao_original = None

    try:
        if hasattr(arquivo, "seek"):
            arquivo.seek(0)
        with Image.open(arquivo) as img:
            img.verify()
            formato = (img.format or "").upper()
            if formato not in {"JPEG", "PNG"}:
                raise ValidationError("O formato interno da imagem deve ser JPG ou PNG.")
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("O arquivo enviado não é uma imagem válida.")
    finally:
        if hasattr(arquivo, "seek") and posicao_original is not None:
            try:
                arquivo.seek(posicao_original)
            except OSError:
                pass
