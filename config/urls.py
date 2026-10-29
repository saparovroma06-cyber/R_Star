from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Admin panel sozlamalari
admin.site.site_header = "Cargo-14 Admin Panel"
admin.site.site_title = "Cargo-14 Admin"
admin.site.index_title = "Sayt Boshqaruvi"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('cargo_14.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

