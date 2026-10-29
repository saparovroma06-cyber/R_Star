from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

class CustomAdminSite(admin.AdminSite):
    site_header = "Cargo-14 Admin Panel"
    site_title = "Cargo-14 Admin"
    index_title = "Sayt Boshqaruvi"
    
    # Добавляем пользовательский CSS
    extra_css = ['admin/css/custom_admin.css'] # Путь относительно STATIC_URL

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        
        # Добавляем ссылку на страницу презентации
        presentation_url = reverse('cargo_14:presentation') # Используем 'cargo_14:presentation'
        extra_context['custom_links'] = [
            {'url': presentation_url, 'name': 'Sayt Funksiyalari Prezentatsiyasi'},
        ]
        return super().index(request, extra_context)

# Создаем экземпляр нашего кастомного админ-сайта
custom_admin_site = CustomAdminSite(name='custom_admin')