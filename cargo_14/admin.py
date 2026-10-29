from django.contrib import admin
from django.contrib.auth.models import Permission
from .models import (
    Category, Product, ProductImage, Comment,
    Cart, CartItem, Order, OrderItem, Promocode,
    TelegramUserProfile, UserProfile, Favorite, News,
    SupportTicket # Добавляем SupportTicket
)


admin.site.site_header = "Cargo-14 Admin Panel"
admin.site.site_title = "Cargo-14 Admin"
admin.site.index_title = "Sayt Boshqaruvi"

_default_admin_index = admin.site.index

def custom_admin_index(request, extra_context=None):
    if extra_context is None:
        extra_context = {}
    try:
        from django.contrib.auth.models import User
        extra_context['dashboard_stats'] = {
            'products_count': Product.objects.count(),
            'orders_count': Order.objects.count(),
            'users_count': User.objects.count(),
            'tickets_count': SupportTicket.objects.count(),
            'new_orders_count': Order.objects.filter(status='new').count(),
            'open_tickets_count': SupportTicket.objects.filter(is_resolved=False).count(),
        }
    except Exception:
        extra_context['dashboard_stats'] = {}
    return _default_admin_index(request, extra_context)

admin.site.index = custom_admin_index


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_type', 'codename']
    search_fields = ['name', 'codename']
    list_filter = ['content_type__app_label']



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']
    fields = ['product', 'name', 'price', 'quantity', 'total_price']


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'user', 'price', 'sale', 'count', 'magazine_capacity', 'shots_per_trigger', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'shots_per_trigger', 'is_recommended_pack']
    search_fields = ['name', 'about']
    list_editable = ['is_active', 'price', 'sale']
    inlines = [ProductImageInline]
    fieldsets = (
        ('Asosiy ma\'lumot', {'fields': ('user', 'name', 'category', 'about', 'is_active', 'is_recommended_pack')}),
        ('Narx va miqdor', {'fields': ('price', 'sale', 'count', 'shipping_cost')}),
        ('Qurol xarakteristikalari', {'fields': ('magazine_capacity', 'shots_per_trigger', 'safety_age', 'info')}),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['user__username', 'product__name', 'text']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'sale', 'is_active', 'live_time', 'is_valid']
    list_editable = ['is_active']
    search_fields = ['name']

    @admin.display(boolean=True, description='Amal qilyapti?')
    def is_valid(self, obj):
        return obj.is_valid


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'items_count', 'formatted_total_price', 'created_at']
    inlines = [CartItemInline]

    @admin.display(description="Jami summa")
    def formatted_total_price(self, obj):
        from django.contrib.humanize.templatetags.humanize import intcomma
        return f"{intcomma(obj.total_price)} UZS"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'status', 'formatted_total_price', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'full_name', 'phone']
    inlines = [OrderItemInline]

    @admin.display(description="Jami summa")
    def formatted_total_price(self, obj):
        from django.contrib.humanize.templatetags.humanize import intcomma
        return f"{intcomma(obj.total_price)} UZS"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'language', 'is_verified_14', 'has_saved_payment_method']
    list_filter = ['language', 'is_verified_14', 'has_saved_payment_method']
    search_fields = ['user__username', 'phone']


@admin.register(TelegramUserProfile)
class TelegramUserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'tg_user_id', 'is_verified_14']


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title_ru', 'urgency', 'promocode', 'is_active', 'created_at']
    list_filter = ['urgency', 'is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('O\'zbek tili', {'fields': ('title_uz', 'body_uz')}),
        ('Русский язык', {'fields': ('title_ru', 'body_ru')}),
        ('English', {'fields': ('title_en', 'body_en')}),
        ('Parametrlar', {'fields': ('urgency', 'promocode', 'is_active')}),
    )

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'phone_number', 'is_resolved', 'created_at']
    list_filter = ['is_resolved']
    search_fields = ['account_name', 'phone_number', 'complaint']
    list_editable = ['is_resolved']
    readonly_fields = ['user', 'account_name', 'phone_number', 'complaint', 'created_at'] # Эти поля редактируются только при создании