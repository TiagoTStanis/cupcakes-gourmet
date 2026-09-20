from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Endereco, Usuario
from usuarios.services import auth_service as servico


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("senha", ["minuscula123", "SemNumeros", "Ab1"])
def test_rejeita_senha_fora_dos_requisitos(senha):
    with pytest.raises(ValidationError):
        servico.cadastrar_usuario("Marina Souza", "marina@teste.com", senha)
    assert not Usuario.objects.exists()


def test_rejeita_email_duplicado_sem_distinguir_maiusculas(usuario_cliente):
    with pytest.raises(ValidationError, match="já está cadastrado"):
        servico.cadastrar_usuario("Outra pessoa", "CLIENTE@TESTE.COM", "Senha1234")
    assert Usuario.objects.count() == 1


def test_bloqueia_tres_erros_por_exatos_quinze_minutos(usuario_cliente):
    agora = timezone.now()
    with patch.object(servico.timezone, "now", return_value=agora):
        for tentativa in range(3):
            with pytest.raises(ValidationError, match=servico.ERRO_LOGIN):
                servico.autenticar_usuario(usuario_cliente.email, "errada")
            usuario_cliente.refresh_from_db()
            assert usuario_cliente.tentativas_login_falhas == tentativa + 1
        assert usuario_cliente.bloqueado_ate == agora + timedelta(minutes=15)
        with pytest.raises(ValidationError, match=servico.ERRO_LOGIN):
            servico.autenticar_usuario(usuario_cliente.email, "Cliente@123456")
    with patch.object(servico.timezone, "now", return_value=agora + timedelta(minutes=15)):
        usuario = servico.autenticar_usuario(usuario_cliente.email, "Cliente@123456")
    assert usuario.bloqueado_ate is None
    assert usuario.tentativas_login_falhas == 0


def test_login_correto_interrompe_sequencia_de_erros(usuario_cliente):
    with pytest.raises(ValidationError):
        servico.autenticar_usuario(usuario_cliente.email, "errada")
    servico.autenticar_usuario(usuario_cliente.email, "Cliente@123456")
    with pytest.raises(ValidationError):
        servico.autenticar_usuario(usuario_cliente.email, "errada")
    usuario_cliente.refresh_from_db()
    assert usuario_cliente.tentativas_login_falhas == 1


def test_login_sem_confirmacao_mostra_aviso_especifico(client, usuario_cliente):
    usuario_cliente.email_confirmado = False
    usuario_cliente.save()
    resposta = client.post(reverse("usuarios:login"), {"email": usuario_cliente.email, "senha": "Cliente@123456"})
    assert servico.CONTA_NAO_ATIVADA in resposta.content.decode()
    assert "_auth_user_id" not in client.session
    assert authenticate(email=usuario_cliente.email, password="Cliente@123456") is None


@pytest.mark.parametrize("email", ["cliente@teste.com", "ausente@teste.com"])
def test_erro_login_generico(client, usuario_cliente, email):
    resposta = client.post(reverse("usuarios:login"), {"email": email, "senha": "errada"})
    assert servico.ERRO_LOGIN in resposta.content.decode()
    assert "_auth_user_id" not in client.session


def test_recuperacao_responde_igual_para_email_existente_ou_ausente(client, usuario_cliente, settings, mailoutbox):
    settings.MODO_DEMO = False
    respostas = [client.post(reverse("usuarios:esqueci_senha"), {"email": email}) for email in [usuario_cliente.email, "ausente@teste.com"]]
    mensagens = [[str(mensagem) for mensagem in resposta.context["messages"]] for resposta in respostas]
    assert mensagens == [[servico.RESPOSTA_RECUPERACAO], [servico.RESPOSTA_RECUPERACAO]]
    assert respostas[0].context["link_demo"] is None
    assert respostas[1].context["link_demo"] is None
    assert len(mailoutbox) == 1
    assert "Modo demonstração" not in respostas[0].content.decode()


def test_token_expira_exatamente_em_sessenta_minutos(usuario_cliente):
    agora = timezone.now()
    with patch.object(servico.timezone, "now", return_value=agora):
        link = servico.solicitar_recuperacao(usuario_cliente.email)
    token = link.rstrip("/").split("/")[-1]
    with patch.object(servico.timezone, "now", return_value=agora + timedelta(minutes=59, seconds=59)):
        assert servico.recuperacao_valida(token)
    with patch.object(servico.timezone, "now", return_value=agora + timedelta(minutes=60)):
        assert not servico.recuperacao_valida(token)
        with pytest.raises(ValidationError):
            servico.redefinir_senha(token, "NovaSenha123")


def test_recuperacao_uso_unico_e_hash_no_banco(usuario_cliente):
    link = servico.solicitar_recuperacao(usuario_cliente.email)
    token = link.rstrip("/").split("/")[-1]
    usuario_cliente.refresh_from_db()
    assert usuario_cliente.token_recuperacao != token
    servico.redefinir_senha(token, "NovaSenha123")
    usuario_cliente.refresh_from_db()
    assert usuario_cliente.check_password("NovaSenha123")
    assert usuario_cliente.token_recuperacao is None
    assert usuario_cliente.token_recuperacao_expira is None
    with pytest.raises(ValidationError):
        servico.redefinir_senha(token, "OutraSenha123")


def test_nova_solicitacao_invalida_token_anterior(usuario_cliente):
    antigo = servico.solicitar_recuperacao(usuario_cliente.email).rstrip("/").split("/")[-1]
    novo = servico.solicitar_recuperacao(usuario_cliente.email).rstrip("/").split("/")[-1]
    assert not servico.recuperacao_valida(antigo)
    assert servico.recuperacao_valida(novo)


def test_fluxo_cadastro_ativacao_login_e_logout(client, settings, mailoutbox):
    settings.MODO_DEMO = True
    resposta = client.post(reverse("usuarios:cadastro"), {
        "nome_completo": "Marina Souza", "email": "marina@teste.com", "telefone": "",
        "senha": "Marina1234", "confirmar_senha": "Marina1234",
    })
    assert resposta.status_code == 200
    link = resposta.context["link_demo"]
    assert link and "Modo demonstração" in resposta.content.decode()
    assert len(mailoutbox) == 1
    token = link.rstrip("/").split("/")[-1]
    client.post(reverse("usuarios:ativar", args=[token]))
    with pytest.raises(ValidationError):
        servico.ativar_conta(token)
    resposta = client.post(reverse("usuarios:login"), {"email": "marina@teste.com", "senha": "Marina1234", "next": "https://externo.com/"})
    assert resposta.url == reverse("usuarios:perfil")
    assert client.get(reverse("usuarios:perfil")).status_code == 200
    assert client.get(reverse("usuarios:logout")).status_code == 405
    client.post(reverse("usuarios:logout"))
    assert "_auth_user_id" not in client.session


def test_perfil_cadastra_endereco_e_impede_remocao_por_outro_usuario(client, usuario_cliente, usuario_admin):
    client.force_login(usuario_cliente)
    resposta = client.post(reverse("usuarios:perfil"), {
        "acao": "endereco", "cep": "85884000", "logradouro": "Rua das Flores", "numero": "120",
        "bairro": "Centro", "cidade": "Medianeira", "uf": "PR", "principal": "on",
    })
    assert resposta.status_code == 302
    endereco = Endereco.objects.get(usuario=usuario_cliente)
    client.force_login(usuario_admin)
    assert client.post(reverse("usuarios:remover_endereco", args=[endereco.pk])).status_code == 404
    assert Endereco.objects.filter(pk=endereco.pk).exists()
    client.force_login(usuario_cliente)
    client.post(reverse("usuarios:remover_endereco", args=[endereco.pk]))
    assert not Endereco.objects.exists()


def test_redefinicao_pela_tela_e_link_demo(client, usuario_cliente, settings):
    settings.MODO_DEMO = True
    resposta = client.post(reverse("usuarios:esqueci_senha"), {"email": usuario_cliente.email})
    token = resposta.context["link_demo"].rstrip("/").split("/")[-1]
    rota = reverse("usuarios:redefinir", args=[token])
    assert client.get(rota).context["valido"]
    resposta = client.post(rota, {"senha": "NovaSenha123", "confirmar_senha": "NovaSenha123"})
    assert resposta.url == reverse("usuarios:login")
    assert not client.get(rota).context["valido"]


def test_login_respeita_destino_local(client, usuario_cliente):
    resposta = client.post(reverse("usuarios:login"), {"email": usuario_cliente.email, "senha": "Cliente@123456", "next": "/?origem=perfil"})
    assert resposta.url == "/?origem=perfil"
