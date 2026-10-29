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
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Telefon raqamingiz (ixtiyoriy)'}),
        label="Telefon raqami"
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
    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone', 'bio', 'language']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+998 90 123 45 67'}),
            'bio': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'O\'zingiz haqingizda qisqacha...'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
        }

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
