from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

class BaseCreatedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Category(BaseCreatedModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategoriya nomi")
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

def default_weapon_info():
    """Спецификации по умолчанию для страйкбольного/гидробольного привода"""
    return {
        "caliber": "6mm BB / 7-8mm Gel",
        "power_source": "Elektr (AEG)",
        "material": "ABS Plastic / Metall",
    }

class Product(BaseCreatedModel):
    class FireMode(models.TextChoices):
        SINGLE = '1_shot', '1 ta o\'q (Yakka / Одиночный)'
        BURST_2 = '2_burst', '2 ta o\'q (Ikkitalik / Двойка)'
        BURST_3 = '3_burst', '3 ta o\'q (Burst / Очередь по 3)'
        BURST_5 = '5_burst', '5 ta o\'q (Burst / Очередь по 5)'
        AUTO = 'auto', 'Avtomat (Uzluksiz / Автомат)'
        SHOTGUN = 'multi_scatter', '5-10 ta (Sochma / Дробовик)'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="E'lon muallifi"
    )
    name = models.CharField(max_length=255, verbose_name="Mahsulot nomi")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Kategoriya")
    rating = models.IntegerField(default=5, validators=[MinValueValidator(0), MaxValueValidator(5)])
    about = models.TextField(verbose_name="Tavsif")
    price = models.IntegerField(verbose_name="Narxi")
    sale = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Chegirma %")
    shipping_cost = models.IntegerField(default=0, verbose_name="Yetkazib berish narxi")
    count = models.IntegerField(default=1, verbose_name="Ombordagi / mavjud soni")    
    # min_count = models.IntegerField(default=1)
    
    # Характеристики для страйкбола / гидробола
    safety_age = models.IntegerField(default=14, validators=[MinValueValidator(14)], verbose_name="Minimal yosh")
    
    # Вместимость магазина и количество пуль при одном нажатии на спуск
    magazine_capacity = models.IntegerField(
        default=250,
        verbose_name="1 ta magazindagi o'qlar/orblar soni (Вместимость)",
        blank=True, null=True
    )
    shots_per_trigger = models.CharField(
        max_length=50,
        choices=FireMode.choices,
        default=FireMode.SINGLE,
        verbose_name="1 ta bosishda chiqadigan o'qlar soni (Спуск)",
        blank=True, null=True
    )

    is_recommended_pack = models.BooleanField(default=False, verbose_name="Tayyor komplekt (Pak)")
    info = models.JSONField(default=default_weapon_info, blank=True, verbose_name="Xarakteristikalar (JSON)")
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    def __str__(self):
        return self.name

    @property
    def sale_price(self):
        return self.price - (self.price * self.sale / 100)

    @property
    def is_new(self):
        return timezone.now() - self.created_at <= timedelta(days=5)

    @property
    def average_rating(self):
        comments = self.comments.all()
        if comments.exists():
            return round(sum(c.rating for c in comments) / comments.count(), 1)
        return self.rating

    @property
    def comments_count(self):
        return self.comments.count()

    class Meta:
        ordering = ['-created_at']

class ProductImage(BaseCreatedModel):
    image = models.ImageField(upload_to='products/', verbose_name="Mahsulot rasmi")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')

    def __str__(self):
        return f"Rasm: {self.product.name}"

class UserProfile(BaseCreatedModel):
    LANG_UZ = 'uz'
    LANG_RU = 'ru'
    LANG_EN = 'en'
    LANG_CHOICES = [
        (LANG_UZ, "O'zbek"),
        (LANG_RU, 'Русский'),
        (LANG_EN, 'English'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Profil rasmi (Avatar)")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    bio = models.TextField(blank=True, verbose_name="O'zi haqida")
    is_verified_14 = models.BooleanField(default=True, verbose_name="14 yosh tasdiqlangan")
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default=LANG_UZ, verbose_name="Til / Язык")
    has_saved_payment_method = models.BooleanField(default=False, verbose_name="Saqlangan to'lov usuli mavjud")
    first_login_completed = models.BooleanField(default=False, verbose_name="Birinchi kirish tugallandi")

    def __str__(self):
        return f"Profil: {self.user.username}"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()

# Интеграция с Telegram
class TelegramUserProfile(BaseCreatedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tg_profile')
    tg_user_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Telegram ID")
    is_verified_14 = models.BooleanField(default=False, verbose_name="14 yosh tasdiqi")

    def __str__(self):
        return f"TG: {self.user.username}"

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(verbose_name="Fikr / Sharh")
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Baho (1-5)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.product.name} ({self.rating}★)'

    class Meta:
        ordering = ['-created_at']

# Модель Избранное (Favorites / Wishlist)
class Favorite(BaseCreatedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_favorite_product'),
        ]

    def __str__(self):
        return f"{self.user.username} ❤️ {self.product.name}"

class Cart(BaseCreatedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')

    def __str__(self):
        return f'{self.user} savati'

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(BaseCreatedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product'),
        ]

    @property
    def total_price(self):
        return self.product.sale_price * self.quantity

class Promocode(BaseCreatedModel):
    name = models.CharField(max_length=50, unique=True, verbose_name="Promokod")
    live_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    sale = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    def __str__(self):
        return f'{self.name} (-{self.sale}%)'

    @property
    def is_valid(self):
        return self.is_active and self.live_time > timezone.now()

class Order(BaseCreatedModel):
    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        PROCESSING = 'processing', 'Jarayonda'
        COMPLETED = 'completed', 'Yetkazildi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    promocode = models.ForeignKey(Promocode, on_delete=models.SET_NULL, null=True, blank=True)
    promocode_sale = models.IntegerField(default=0)
    shipping_cost = models.IntegerField(default=0)
    via_telegram = models.BooleanField(default=False, verbose_name="Bot orqali buyurtma")

    class DeliveryMethod(models.TextChoices):
        PICKUP = 'pickup', 'O\'zim olib ketaman'
        DELIVERY = 'delivery', 'Kuryer orqali yetkazib berish'

    delivery_method = models.CharField(max_length=20, choices=DeliveryMethod.choices, default=DeliveryMethod.PICKUP, verbose_name="Yetkazib berish usuli")

    @property
    def items_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def discount(self):
        return self.items_price * self.promocode_sale / 100

    @property
    def total_price(self):
        return self.items_price - self.discount + self.shipping_cost

class OrderItem(BaseCreatedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.price * self.quantity


class News(BaseCreatedModel):
    """Yangiliklar va e'lonlar - Новости и объявления"""
    URGENCY_NORMAL = 'normal'
    URGENCY_HOT = 'hot'
    URGENCY_CHOICES = [
        (URGENCY_NORMAL, 'Oddiy'),
        (URGENCY_HOT, 'Shoshilinch / Горячая'),
    ]

    title_uz = models.CharField(max_length=255, verbose_name="Sarlavha (UZ)")
    title_ru = models.CharField(max_length=255, verbose_name="Заголовок (RU)")
    title_en = models.CharField(max_length=255, verbose_name="Title (EN)")
    body_uz = models.TextField(verbose_name="Matn (UZ)")
    body_ru = models.TextField(verbose_name="Текст (RU)")
    body_en = models.TextField(verbose_name="Text (EN)")
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default=URGENCY_NORMAL)
    promocode = models.ForeignKey(
        Promocode, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Bog'langan promokod"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    def __str__(self):
        return self.title_ru

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Yangilik"
        verbose_name_plural = "Yangiliklar"

class SupportTicket(BaseCreatedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Foydalanuvchi"
    )
    account_name = models.CharField(max_length=255, verbose_name="Akkaunt nomi")
    phone_number = models.CharField(max_length=20, verbose_name="Telefon raqami")
    complaint = models.TextField(verbose_name="Shikoyat/Murojaat")
    is_resolved = models.BooleanField(default=False, verbose_name="Hal etilgan")

    def __str__(self):
        return f"Murojaat #{self.id} - {self.account_name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Murojaat"
        verbose_name_plural = "Murojaatlar"
