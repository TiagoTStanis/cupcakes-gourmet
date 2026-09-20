from django.urls import path

from catalogo import views

app_name = "catalogo"

urlpatterns = [
    path("", views.vitrine, name="vitrine"),
    path("inicio/", views.vitrine, name="inicio"),
    path("busca/", views.busca, name="busca"),
    path("busca/api/", views.busca_api, name="busca_api"),
    path("produto/<slug:slug>/", views.produto_detalhe, name="produto_detalhe"),
]
