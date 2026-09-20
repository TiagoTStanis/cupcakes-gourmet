from django.urls import path

from usuarios import views


app_name = "usuarios"
urlpatterns = [
    path("cadastro/", views.cadastro, name="cadastro"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("ativar/<str:token>/", views.ativar, name="ativar"),
    path("esqueci-senha/", views.esqueci_senha, name="esqueci_senha"),
    path("redefinir/<str:token>/", views.redefinir, name="redefinir"),
    path("perfil/", views.perfil, name="perfil"),
    path("enderecos/<int:endereco_id>/remover/", views.remover_endereco, name="remover_endereco"),
]
