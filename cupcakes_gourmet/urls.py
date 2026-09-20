from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.defaults import bad_request, page_not_found, permission_denied, server_error
from django.views.generic import TemplateView

from catalogo.views import vitrine


urlpatterns = [
    path("", include("catalogo.urls")),
    path("", vitrine, name="inicio"),
    path("usuarios/", include("usuarios.urls")),
    path("carrinho/", include("carrinho.urls")),
    path("pedidos/", include("pedidos.urls")),
    path("painel/", include("painel.urls")),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    path("admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = bad_request
handler403 = permission_denied
handler404 = page_not_found
handler500 = server_error
