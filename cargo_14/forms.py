from django import forms
from django.contrib.auth.models import User
from allauth.account.forms import LoginForm, SignupForm
from .models import Product, ProductImage, Category, UserProfile, Comment, SupportTicket
from cargo_14.telegram_utils import send_telegram_notification

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text', 'rating']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Fikringizni yozing...'}),
            'rating': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 5, 'placeholder': 'Baho (1-5)'}),
        }

class UserRegisterForm(SignupForm): # Наследуемся от SignupForm
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ismingiz'}),
        label="Ism"
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Familiyangiz'}),
        label="Familiya"
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67'}),
        label="Telefon raqami *"
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Yashash manziliniz'}),
        label="Yashash manzili"
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'O\'zingiz haqingizda qisqacha...'}),
        required=False,
        label="O'zi haqida"
    )
    avatar = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-input-file'
    }), label="Profil rasmi (Avatar)")

    def signup(self, request, user):
        # Сохраняем first_name и last_name в модели User
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.save()

        # Сохраняем phone_number и bio в UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data.get('phone_number')
        profile.address = self.cleaned_data.get('address')
        profile.bio = self.cleaned_data.get('bio')
        if self.cleaned_data.get('avatar'):
            profile.avatar = self.cleaned_data['avatar']
        profile.save()

        # Отправка уведомления в Telegram
        message_text = (
            f"<b>Yangi foydalanuvchi ro'yxatdan o'tdi!</b>\n\n"
            f"<b>Foydalanuvchi nomi:</b> {user.username}\n"
            f"<b>Ism:</b> {user.first_name or 'Kiritilmagan'}\n"
            f"<b>Familiya:</b> {user.last_name or 'Kiritilmagan'}\n"
            f"<b>Email:</b> {user.email or 'Kiritilmagan'}\n"
            f"<b>Telefon raqami:</b> {profile.phone or 'Kiritilmagan'}\n"
            f"<b>O'zi haqida:</b>\n{profile.bio or 'Kiritilmagan'}\n"
            f"<b>Ro'yxatdan o'tgan sana:</b> {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        send_telegram_notification(message_text)

        return user

class UserLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-input', 'placeholder': 'Foydalanuvchi nomi yoki login'
    }), label="Login")
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input', 'placeholder': 'Parolingiz'
    }), label="Parol")

class ProductCreateForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-input-file'
    }), label="Asosiy rasm")

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'price', 'sale', 'count',
            'is_recommended_pack', 'about'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Masalan: Moshina, Skeyt, Gel Blaster...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Narxi (UZS)'}),
            'sale': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Chegirma % (masalan 10)'}),
            'count': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Ombordagi soni'}),

            'is_recommended_pack': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'about': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Mahsulot haqida batafsil ma\'lumot...'}),
        }

class UserProfileEditForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67'}),
        label="Telefon raqami *",
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Toshkent, Chilonzor tumani, 9-kvartal...'}),
        label="Yashash manzili",
    )

    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone', 'address', 'latitude', 'longitude', 'bio', 'language']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'O\'zingiz haqingizda qisqacha...'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }


class CheckoutForm(forms.Form):
    """Xarid paytida so'raladigan majburiy ma'lumotlar: ism, telefon, manzil va xarita nuqtasi."""
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ism va familiya'}),
        label="Ism familiya *",
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67'}),
        label="Telefon raqami *",
    )
    address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Viloyat, tuman, ko\'cha, uy'}),
        label="Yetkazib berish manzili *",
    )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    PAYMENT_CHOICES = [
        ('cash', '💵 Naqd pul'),
        ('card', '💳 Karta orqali'),
        ('transfer', '🏦 Bank o\'tkazmasi'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        label="To'lov usuli *",
    )
    card_number = forms.CharField(
        max_length=19, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '8600 1234 5678 9012', 'inputmode': 'numeric'}),
        label="Karta raqami",
    )
    card_holder = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'SARADOR KARIMOV'}),
        label="Karta egasi",
    )
    card_expiry = forms.CharField(
        max_length=5, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'MM/YY', 'inputmode': 'numeric'}),
        label="Muddati",
    )
    card_cvv = forms.CharField(
        max_length=3, required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'CVV', 'inputmode': 'numeric'}),
        label="CVV",
    )
    transfer_bank = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Masalan: Kapitalbank'}),
        label="Bank nomi",
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = [c for c in phone if c.isdigit()]
        if len(digits) < 9:
            raise forms.ValidationError("Telefon raqamini to'liq kiriting (kamida 9 ta raqam).")
        return phone

    @staticmethod
    def _luhn_ok(number):
        digits = [int(d) for d in number if d.isdigit()]
        if len(digits) < 12:
            return False
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('payment_method')

        if method == 'card':
            number = (cleaned.get('card_number') or '').replace(' ', '')
            if not number:
                self.add_error('card_number', "Karta raqamini kiriting.")
            elif not self._luhn_ok(number):
                self.add_error('card_number', "Karta raqami noto'g'ri. Raqamni tekshiring.")
            if not (cleaned.get('card_holder') or '').strip():
                self.add_error('card_holder', "Karta egasining ism-familiyasini kiriting.")
            expiry = (cleaned.get('card_expiry') or '').strip()
            if not expiry:
                self.add_error('card_expiry', "Kartaning muddatini kiriting (MM/YY).")
            if not (cleaned.get('card_cvv') or '').strip():
                self.add_error('card_cvv', "CVV kodni kiriting.")

        elif method == 'transfer':
            if not (cleaned.get('transfer_bank') or '').strip():
                self.add_error('transfer_bank', "Bank nomini kiriting.")

        return cleaned

from allauth.socialaccount.forms import SignupForm as SocialSignupFormBase

class SocialSignupForm(SocialSignupFormBase):
    # Добавьте сюда поля, которые вы хотите запросить у пользователя при регистрации через соцсети
    # Например, если вы хотите запросить номер телефона или био
    # phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={
    #     'class': 'form-input', 'placeholder': 'Telefon raqamingiz (ixtiyoriy)'
    # }))
    # bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'O\'zingiz haqingizda qisqacha...'}), required=False)

    def save(self, request):
        # Реализуйте логику сохранения дополнительных полей, если они есть
        user = super(SocialSignupForm, self).save(request)
        # if self.cleaned_data.get('phone'):
        #     user.profile.phone = self.cleaned_data['phone']
        # if self.cleaned_data.get('bio'):
        #     user.profile.bio = self.cleaned_data['bio']
        # user.profile.save()
        return user

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['account_name', 'phone_number', 'complaint']
        widgets = {
            'account_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Akkaunt nomi'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Telefon raqamingiz'}),
            'complaint': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5, 'placeholder': 'Shikoyatingizni yozing...'}),
        }

class ProductImageUpdateForm(forms.ModelForm):
    image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-input-file'}),
        label="Asosiy rasm"
    )

    class Meta:
        model = ProductImage
        fields = ['image']
