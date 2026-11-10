import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.views.generic import RedirectView
from .telegram_utils import send_telegram_notification
from .models import Category, Product, ProductImage, Cart, CartItem, UserProfile, Comment, Favorite, News, Order, OrderItem, Promocode

from .forms import UserRegisterForm, UserLoginForm, ProductCreateForm, UserProfileEditForm, CommentForm, SupportTicketForm, ProductImageUpdateForm

# ---------- helpers ----------
LANG_KEY = 'ui_lang'

def get_lang(request):
    """Текущий язык интерфейса: session > profile > 'uz'"""
    lang = request.session.get(LANG_KEY) if hasattr(request, 'session') else None
    if not lang and hasattr(request, 'user') and request.user.is_authenticated:
        try:
            lang = request.user.profile.language
        except Exception:
            pass
    return lang or 'uz'


def set_language_view(request):
    """POST /set-language/?lang=ru"""
    lang = request.GET.get('lang', 'uz')
    if lang not in ('uz', 'ru', 'en'):
        lang = 'uz'
    request.session[LANG_KEY] = lang
    if request.user.is_authenticated:
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.language = lang
            profile.save(update_fields=['language'])
        except Exception:
            pass
    return redirect(request.META.get('HTTP_REFERER', '/'))



# ---------- views ----------
def home(request):
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    lang = get_lang(request)

    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category', 'user').prefetch_related('images', 'comments')

    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    if search_query:
        products = products.filter(name__icontains=search_query)

    cart = None
    user_favorites_ids = set()
    favorites_count = 0
    user_products_count = 0
    open_tutorial = False # Default value

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        user_favorites_ids = set(request.user.favorites.values_list('product_id', flat=True))
        favorites_count = len(user_favorites_ids)
        user_products_count = request.user.products.count()
        if not request.user.profile.first_login_completed:
            open_tutorial = True
    else:
        # Ro'yxatdan o'tmagan foydalanuvchilar uchun
        if not request.session.get('tutorial_shown', False):
            open_tutorial = True
            request.session['tutorial_shown'] = True # Tutorial ko'rsatilganini belgilash

    # Pagination: 4 products per page
    paginator = Paginator(products, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
        'cart': cart,
        'user_favorites_ids': user_favorites_ids,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'lang': lang,
        'open_tutorial': open_tutorial,
    }
    return render(request, 'cargo_14/index.html', context)


def news_view(request):
    """Yangiliklar va e'lonlar sahifasi"""
    lang = get_lang(request)
    news_items = News.objects.filter(is_active=True).select_related('promocode')

    cart = None
    favorites_count = 0
    user_products_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        favorites_count = request.user.favorites.count()
        user_products_count = request.user.products.count()

    context = {
        'news_items': news_items,
        'lang': lang,
        'cart': cart,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
    }
    return render(request, 'cargo_14/news.html', context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category', 'user__profile').prefetch_related('images', 'comments__user__profile'),
        pk=pk,
        is_active=True
    )
    lang = get_lang(request)
    
    cart = None
    is_favorite = False
    favorites_count = 0
    user_products_count = 0

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        favorites_count = request.user.favorites.count()
        user_products_count = request.user.products.count()

    similar_products = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]

    comment_form = CommentForm()
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, "Sharh qoldirish uchun avval tizimga kiring!")
            return redirect('account_login')
        
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.product = product
            comment.save()
            messages.success(request, "Fikringiz muvaffaqiyatli saqlandi!")
            return redirect('cargo_14:product_detail', pk=pk)



    context = {
        'product': product,
        'cart': cart,
        'is_favorite': is_favorite,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'similar_products': similar_products,
        'comment_form': comment_form,
        'comments': product.comments.all(),
        'lang': lang,
    }
    return render(request, 'cargo_14/detail.html', context)


def support_view(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save()
            
            # Отправка сообщения в Telegram
            message_text = (
                f"<b>Yangi murojaat!</b>\n\n"
                f"<b>Akkaunt nomi:</b> {ticket.account_name}\n"
                f"<b>Telefon raqami:</b> {ticket.phone_number}\n"
                f"<b>Murojaat:</b>\n{ticket.complaint}\n\n"
                f"ID: {ticket.id}"
            )
            send_telegram_notification(message_text)

            messages.success(request, "Sizning murojaatingiz qabul qilindi! Tez orada siz bilan bog'lanamiz.")
            return redirect('cargo_14:home')
    else:
        form = SupportTicketForm()

    return render(request, 'cargo_14/support.html', {'form': form})


@login_required(login_url='account_login')
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if not created:
        fav.delete()
        favorited = False
        message = f"'{product.name}' saralanganlardan olib tashlandi"
    else:
        favorited = True
        message = f"'{product.name}' saralanganlarga qo'shildi"

    total_favs = request.user.favorites.count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'success': True,
            'favorited': favorited,
            'favorites_count': total_favs,
            'message': message,
        })
    
    messages.info(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'cargo_14:home'))


@login_required(login_url='account_login')
def favorites_list(request):
    lang = get_lang(request)
    favorites = Favorite.objects.filter(user=request.user).select_related('product__category').prefetch_related('product__images')
    cart = Cart.objects.filter(user=request.user).first()
    favorites_count = favorites.count()
    user_products_count = request.user.products.count()
    return render(request, 'cargo_14/favorites.html', {
        'favorites': favorites,
        'cart': cart,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'lang': lang,
    })





def register_view(request):
    if request.user.is_authenticated:
        return redirect('cargo_14:home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            if form.cleaned_data.get('avatar'):
                profile.avatar = form.cleaned_data['avatar']
                profile.save()

            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.username}! Ro'yxatdan muvaffaqiyatli o'tdingiz.")
            return redirect('cargo_14:home')
    else:
        form = UserRegisterForm()

    return render(request, 'cargo_14/register.html', {'form': form})


class AllauthLoginRedirectView(RedirectView):
    permanent = False
    url = reverse_lazy('account_login')

login_view = AllauthLoginRedirectView.as_view()


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan chiqdingiz.")
    return redirect('cargo_14:home')


@login_required(login_url='account_login')
def profile_view(request):
    lang = get_lang(request)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    my_products = Product.objects.filter(user=request.user).prefetch_related('images')
    favorites_count = request.user.favorites.count()
    user_products_count = my_products.count()
    
    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Sync language to session
            request.session[LANG_KEY] = profile.language
            messages.success(request, "Profilingiz muvaffaqiyatli yangilandi!")
            return redirect('cargo_14:profile')
    else:
        form = UserProfileEditForm(instance=profile)

    return render(request, 'cargo_14/profile.html', {
        'profile': profile,
        'form': form,
        'my_products': my_products,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'lang': lang,
    })


@login_required(login_url='account_login')
def my_products_view(request):
    """Mening e'lonlarim sahifasi"""
    lang = get_lang(request)
    my_products = Product.objects.filter(user=request.user).select_related('category').prefetch_related('images')
    cart = Cart.objects.filter(user=request.user).first()
    favorites_count = request.user.favorites.count()
    return render(request, 'cargo_14/my_products.html', {
        'my_products': my_products,
        'cart': cart,
        'favorites_count': favorites_count,
        'user_products_count': my_products.count(),
        'lang': lang,
    })


@login_required(login_url='account_login')
def delete_product_view(request, pk):
    """Mahsulotni o'chirish"""
    product = get_object_or_404(Product, pk=pk, user=request.user)
    product_name = product.name
    product.delete()
    messages.success(request, f"'{product_name}' e'loni muvaffaqiyatli o'chirildi!")
    return redirect('cargo_14:my_products')


@login_required(login_url='account_login')
def add_product_view(request):
    lang = get_lang(request)
    if request.method == 'POST':
        form = ProductCreateForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()

            image_file = form.cleaned_data.get('image')
            if image_file:
                ProductImage.objects.create(product=product, image=image_file)

            # Отправка уведомления в Telegram о новом товаре
            message_text = (
                f"<b>Yangi mahsulot qo'shildi!</b>\n\n"
                f"<b>Nomi:</b> {product.name}\n"
                f"<b>Kategoriya:</b> {product.category.name}\n"
                f"<b>Narxi:</b> {product.price} UZS\n"
                f"<b>Chegirma:</b> {product.sale}%\n"
                f"<b>Sotuvchi:</b> {product.user.username}\n"
                f"<b>Havola:</b> http://127.0.0.1:8000/product/{product.id}/\n"
            )
            send_telegram_notification(message_text)

            messages.success(request, f"'{product.name}' mahsuloti muvaffaqiyatli qo'shildi!")
            return redirect('cargo_14:my_products')
    else:
        form = ProductCreateForm()

    favorites_count = request.user.favorites.count()
    user_products_count = request.user.products.count()
    return render(request, 'cargo_14/add_product.html', {
        'form': form,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'lang': lang,
    })

@login_required(login_url='account_login')
def edit_product_main_image_view(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    lang = get_lang(request)
    
    # Получаем текущее главное изображение (если есть)
    main_image = product.images.first()

    if request.method == 'POST':
        form = ProductImageUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            # Удаляем старое главное изображение, если оно есть
            if main_image:
                main_image.image.delete(save=False) # Удаляем файл, но не объект из БД пока
                main_image.delete() # Удаляем объект из БД

            # Создаем новое изображение
            ProductImage.objects.create(product=product, image=form.cleaned_data['image'])
            messages.success(request, f"'{product.name}' mahsulotining asosiy rasmi yangilandi!")
            return redirect('cargo_14:product_detail', pk=pk)
    else:
        form = ProductImageUpdateForm()

    context = {
        'lang': lang,
        'product': product,
        'form': form,
        'main_image': main_image,
    }
    return render(request, 'cargo_14/edit_product_main_image.html', context)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.GET.get('format') == 'json'
    )
    
    if not request.user.is_authenticated:
        session_cart = request.session.get('session_cart', {})
        str_id = str(product_id)
        session_cart[str_id] = session_cart.get(str_id, 0) + 1
        request.session['session_cart'] = session_cart
        total_items = sum(session_cart.values())
        request.session['cart_count'] = total_items
        if is_ajax:
            return JsonResponse({
                'success': True,
                'guest': True,
                'items_count': total_items,
                'message': f"{product.name} savatga qo'shildi"
            })
        return redirect('cargo_14:cart_view')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    total_items = cart.items_count

    if is_ajax:
        return JsonResponse({
            'success': True,
            'guest': False,
            'items_count': total_items,
            'total_price': float(cart.total_price),
            'message': f"{product.name} savatga qo'shildi"
        })
    
    return redirect('cargo_14:cart_view')


def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    else:
        session_cart = request.session.get('session_cart', {})
        str_id = str(product_id)
        if str_id in session_cart:
            del session_cart[str_id]
            request.session['session_cart'] = session_cart
            request.session['cart_count'] = sum(session_cart.values())
    messages.info(request, "Mahsulot savatdan olib tashlandi.")
    return redirect('cargo_14:cart_view')


def clear_cart(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart.items.all().delete()
    else:
        request.session.pop('session_cart', None)
        request.session['cart_count'] = 0
    messages.info(request, "Savat tozalandi.")
    return redirect('cargo_14:cart_view')


def cart_view(request):
    lang = get_lang(request)
    favorites_count = 0
    user_products_count = 0
    cart_items_data = []
    total_price = 0
    items_count = 0

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # Migrate guest session cart if any
        session_cart = request.session.get('session_cart', {})
        if session_cart:
            for pid_str, qty in session_cart.items():
                p = Product.objects.filter(id=int(pid_str), is_active=True).first()
                if p:
                    ci, created = CartItem.objects.get_or_create(cart=cart, product=p)
                    if not created:
                        ci.quantity += qty
                    else:
                        ci.quantity = qty
                    ci.save()
            request.session.pop('session_cart', None)
            request.session.pop('cart_count', None)

        favorites_count = request.user.favorites.count()
        user_products_count = request.user.products.count()
        for item in cart.items.select_related('product'):
            cart_items_data.append({
                'product': item.product,
                'quantity': item.quantity,
                'total_price': item.total_price,
            })
        total_price = cart.total_price
        items_count = cart.items_count
    else:
        session_cart = request.session.get('session_cart', {})
        if session_cart:
            pids = [int(k) for k in session_cart.keys()]
            products = Product.objects.filter(id__in=pids, is_active=True)
            prod_map = {p.id: p for p in products}
            for pid_str, qty in session_cart.items():
                pid = int(pid_str)
                if pid in prod_map:
                    p = prod_map[pid]
                    subtotal = p.sale_price * qty
                    total_price += subtotal
                    items_count += qty
                    cart_items_data.append({
                        'product': p,
                        'quantity': qty,
                        'total_price': subtotal,
                    })

    return render(request, 'cargo_14/cart.html', {
        'cart_items': cart_items_data,
        'total_price': total_price,
        'items_count': items_count,
        'favorites_count': favorites_count,
        'user_products_count': user_products_count,
        'lang': lang,
    })

def apply_promocode_view(request):
    """AJAX endpoint: promokodni tekshirish va qo'llash (GET va POST ni qo'llab-quvvatlaydi)"""
    code = (request.POST.get('promocode') or request.GET.get('code') or request.GET.get('promocode') or '').strip()
    if not code:
        return JsonResponse({'success': False, 'message': 'Promokod kiritilmagan.'})

    try:
        promo = Promocode.objects.get(name__iexact=code, is_active=True)
    except Promocode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Promokod topilmadi.'})

    if not promo.is_valid:
        return JsonResponse({'success': False, 'message': 'Promokod muddati tugagan.'})

    return JsonResponse({
        'success': True,
        'discount': promo.sale,
        'discount_percentage': promo.sale,
        'promocode_name': promo.name,
        'message': f"Promokod '{promo.name}' qo'llanildi! Chegirma: {promo.sale}%",
    })


@login_required(login_url='account_login') # Используем 'account_login'
def checkout_view(request):
    lang = get_lang(request)
    if request.method == 'POST':
        delivery_method = request.POST.get('delivery_method')
        total_amount = float(request.POST.get('total_amount'))
        promocode_name = request.POST.get('promocode_name')
        promocode_discount = float(request.POST.get('promocode_discount', 0))

        if not delivery_method:
            messages.error(request, "Iltimos, yetkazib berish usulini tanlang!")
            return redirect('cargo_14:cart_view')

        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()

        if not cart_items:
            messages.error(request, "Savat bo'sh, buyurtma berish mumkin emas.")
            return redirect('cargo_14:home')

        promocode_obj = None
        if promocode_name: # <-- Промокод необязателен, эта проверка удалена
            try:
                promocode_obj = Promocode.objects.get(name__iexact=promocode_name, is_active=True)
                if not promocode_obj.is_valid:
                    promocode_obj = None # Промокод недействителен
            except Promocode.DoesNotExist:
                promocode_obj = None

        # --- Имитация платежной логики ---
        user_profile = request.user.profile
        payment_status_message = ""

        if user_profile.has_saved_payment_method:
            # Если есть сохраненная карта, запрашиваем подтверждение (имитация)
            # В реальном приложении здесь была бы интеграция с платежным шлюзом
            payment_status_message = "To'lov usuli tasdiqlandi (saqlangan karta orqali)."
            # Здесь можно было бы добавить логику для отправки запроса на подтверждение в платежный шлюз
        else:
            # Если нет сохраненной карты, просим "add_payment_method" (имитация)
            # В реальном приложении здесь был бы редирект на страницу платежного шлюза для ввода данных
            user_profile.has_saved_payment_method = True # Имитируем сохранение карты
            user_profile.save()
            payment_status_message = "Yangi to'lov usuli qo'shildi (imitatsiya)."
            messages.info(request, "To'lov usuli muvaffaqiyatli 'qo'shildi'. Keyingi saf undan foydalanishingiz mumkin.")
        # --- Конец имитации платежной логики ---

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    full_name=request.user.first_name + " " + request.user.last_name if request.user.first_name and request.user.last_name else request.user.username,
                    phone=user_profile.phone if user_profile.phone else 'Kiritilmagan',
                    address="Manzil kiritilmagan", # В реальном приложении здесь была бы форма для адреса
                    delivery_method=delivery_method,
                    shipping_cost=15000 if delivery_method == 'delivery' else 0,
                    promocode=promocode_obj,
                    promocode_sale=promocode_discount,
                )

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        name=item.product.name,
                        price=item.product.sale_price,
                        quantity=item.quantity,
                    )
                
                cart.items.all().delete()

            # Отправка уведомления о покупке в Telegram
            order_items_details = "\n".join([f"- {item.name} ({item.quantity} dona) - {item.total_price} UZS" for item in order.items.all()])
            telegram_message = (
                f"<b>Yangi buyurtma!</b>\n\n"
                f"<b>Buyurtma ID:</b> {order.id}\n"
                f"<b>Foydalanuvchi:</b> {order.user.username} ({order.full_name})\n"
                f"<b>Telefon:</b> {order.phone}\n"
                f"<b>Umumiy narx:</b> {order.total_price} UZS\n"
                f"<b>Yetkazib berish:</b> {order.get_delivery_method_display()}\n"
                f"<b>Promokod:</b> {order.promocode.name if order.promocode else 'Yo\'q'}{f' ({order.promocode_sale}%)' if order.promocode_sale else ''}\n"
                f"<b>To'lov holati:</b> {payment_status_message}\n\n"
                f"<b>Mahsulotlar:</b>\n{order_items_details}\n\n"
                f"<b>Admin panel:</b> http://127.0.0.1:8000/admin/cargo_14/order/{order.id}/change/"
            )
            send_telegram_notification(telegram_message)

            messages.success(request, f"Buyurtmangiz #{order.id} muvaffaqiyatli qabul qilindi! Tez orada siz bilan bog'lanamiz.")
            return redirect(f"{reverse('cargo_14:thank_you')}?delivery_method={delivery_method}")
        except Exception as e:
            messages.error(request, f"Buyurtma berishda xatolik yuz berdi: {e}")
            return redirect('cargo_14:cart_view')
    
    return redirect('cargo_14:cart_view')

def thank_you_view(request):
    lang = get_lang(request)
    # Здесь можно получить последнюю созданную заявку для пользователя, если нужно
    # Например: last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    delivery_method = request.GET.get('delivery_method', '') # Получаем способ доставки из параметров URL

    context = {
        'lang': lang,
        'delivery_method': delivery_method,
        # 'last_order': last_order, # Раскомментируйте, если нужно передать данные о заказе
    }
    return render(request, 'cargo_14/thank_you.html', context)

@login_required(login_url='account_login') # Используем 'account_login'
def manage_payment_methods_view(request):
    lang = get_lang(request)
    user_profile = request.user.profile

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_payment_method':
            user_profile.has_saved_payment_method = True
            user_profile.save()
            messages.success(request, "To'lov usuli muvaffaqiyatli 'qo'shildi'.")
        elif action == 'remove_payment_method':
            user_profile.has_saved_payment_method = False
            user_profile.save()
            messages.info(request, "To'lov usuli muvaffaqiyatli 'o'chirildi'.")
        return redirect('cargo_14:manage_payment_methods')

    context = {
        'lang': lang,
        'user_profile': user_profile,
        'has_saved_payment_method': user_profile.has_saved_payment_method,
    }
    return render(request, 'cargo_14/manage_payment_methods.html', context)

def presentation_view(request):
    lang = get_lang(request)
    context = {
        'lang': lang,
    }
    return render(request, 'cargo_14/presentation.html', context)

def mark_tutorial_completed(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        profile.first_login_completed = True
        profile.save()
    else:
        request.session['tutorial_shown'] = True
    return JsonResponse({'success': True})


@csrf_exempt
def ai_assistant_view(request):
    """
    Cargo-14 Tactical AI Assistant Endpoint
    Foydalanuvchi savollariga javob beradi: mahsulotlar, chegirmalar, yetkazib berish, promokodlar va o'quv qo'llanma
    """
    if request.method not in ('POST', 'GET'):
        return JsonResponse({'success': False, 'message': 'Faqat GET yoki POST qabul qilinadi.'}, status=405)

    user_text = ""
    req_lang = None
    if request.method == 'POST':
        if request.content_type and 'application/json' in request.content_type:
            try:
                body = json.loads(request.body.decode('utf-8'))
                user_text = body.get('message', '').strip()
                req_lang = body.get('lang')
            except Exception:
                user_text = ""
        if not user_text:
            user_text = request.POST.get('message', '').strip()
            req_lang = req_lang or request.POST.get('lang')
    else:
        user_text = request.GET.get('message', '').strip()
        req_lang = request.GET.get('lang')

    session_lang = get_lang(request)
    lang = req_lang or session_lang or 'uz'

    # Agar xabarda kirill harflari bo'lsa, avtomatik rus tilida javob beramiz
    if bool(re.search(r'[а-яА-ЯёЁ]', user_text)):
        lang = 'ru'
    elif any(en_w in user_text.lower() for en_w in ['hello', 'price', 'delivery', 'discount', 'weapon', 'gun', 'blaster', 'toy']):
        if not req_lang or req_lang == 'en':
            lang = 'en'

    lower_text = user_text.lower()
    reply = ""
    products_data = []
    open_tutorial = False

    # 1. O'quv qo'llanma (Tutorial / Onboarding)
    if any(k in lower_text for k in ['обучен', 'инструкц', 'туториал', 'гид', 'qo\'llanma', 'qollanma', 'yordamchi tur', 'sayt qanday', 'как пользоват', 'как работ', 'start tour', 'tutorial', 'ekskursiya']):
        open_tutorial = True
        if lang == 'ru':
            reply = "🚀 <b>Интерактивное обучение Cargo-14 запущено!</b><br>Я подсвечу ключевые элементы сайта (режимы, поиск, карточки оружия, корзину и личный кабинет). Вы можете выйти в любой момент через кнопку «✕»."
        elif lang == 'en':
            reply = "🚀 <b>Cargo-14 Interactive Tour launched!</b><br>I will guide you through the key features. You can exit at any time using the «✕» button."
        else:
            reply = "🚀 <b>Cargo-14 interaktiv o'quv qo'llanmasi ishga tushirildi!</b><br>Hozir sizga saytning barcha asosiy bo'limlarini (rejimlar, qidiruv, qurollar, savat va profil) ko'rsatib beraman. Istalgan vaqtda «✕» orqali chiqishingiz mumkin."

    # 2. Promokodlar va chegirmalar
    elif any(k in lower_text for k in ['promokod', 'промокод', 'promo', 'kupon', 'купон', 'skidka', 'chegirma', 'скидк']):
        now = timezone.now()
        active_promos = list(Promocode.objects.filter(is_active=True, live_time__gt=now)[:3])
        if active_promos:
            if lang == 'ru':
                promo_list = "<br>".join([f"🏷️ <b>{p.name}</b> — <b>{p.sale}%</b> скидка" for p in active_promos])
                reply = f"🔥 <b>Актуальные промокоды Cargo-14:</b><br>{promo_list}<br><br>💡 <i>Введите любой из них в корзине при оформлении заказа для мгновенной скидки!</i>"
            elif lang == 'en':
                promo_list = "<br>".join([f"🏷️ <b>{p.name}</b> — <b>{p.sale}%</b> off" for p in active_promos])
                reply = f"🔥 <b>Active Cargo-14 Promocodes:</b><br>{promo_list}<br><br>💡 <i>Apply them in your cart for an instant discount!</i>"
            else:
                promo_list = "<br>".join([f"🏷️ <b>{p.name}</b> — <b>{p.sale}%</b> chegirma" for p in active_promos])
                reply = f"🔥 <b>Hozirda amal qilayotgan promokodlar:</b><br>{promo_list}<br><br>💡 <i>Savat sahifasida ushbu promokodlardan birini kiritib chegirmaga ega bo'ling!</i>"
        else:
            if lang == 'ru':
                reply = "Ayni paytda maxsus promokod yo'q, ammo katalogda -25% gacha chegirmali tayyor to'plamlar mavjud!"
                reply = "В данный момент специальных промокодов нет, но в каталоге множество товаров с горячими скидками до -30%! Ищите карточки с ярлыком «-SALE»."
            elif lang == 'en':
                reply = "No promo codes active right now, but check out bundle deals with up to 30% off in our catalog!"
            else:
                reply = "Hozircha maxsus promokodlar yo'q, biroq katalogdagi ko'plab mahsulotlarga qizil yorliqli katta chegirmalar e'lon qilingan!"

    # 3. Yetkazib berish va to'lov
    elif any(k in lower_text for k in ['dostavk', 'yetkaz', 'доставк', 'samovivoz', 'olib ketish', 'kuryer', 'курьер', 'yetkazib berish', 'shipping', 'to\'lov', 'оплат', 'to\'lash']):
        if lang == 'ru':
            reply = (
                "📦 <b>Условия доставки и оплаты:</b><br><br>"
                "• <b>Самовывоз:</b> Бесплатно из нашего тактического пункта в Ташкенте.<br>"
                "• <b>Курьерская доставка:</b> <b>15 000 UZS</b> до двери по всему городу.<br>"
                "• <b>Срок:</b> Доставка в течение 24 часов.<br>"
                "💳 Оплата: наличными или картой при получении, либо онлайн в корзине."
            )
        elif lang == 'en':
            reply = (
                "📦 <b>Delivery and Payment Terms:</b><br><br>"
                "• <b>Self-pickup:</b> Free from our central pickup point in Tashkent.<br>"
                "• <b>Courier delivery:</b> <b>15,000 UZS</b> directly to your door.<br>"
                "• <b>Timing:</b> Within 24 hours.<br>"
                "💳 Payment: Cash or card upon arrival, or via online checkout."
            )
        else:
            reply = (
                "📦 <b>Yetkazib berish va to'lov shartlari:</b><br><br>"
                "• <b>O'zingiz olib ketish (Samovivoz):</b> Toshkent markazidagi punktimizdan MUTLAQO BEPUL.<br>"
                "• <b>Kuryer orqali yetkazish:</b> Toshkent bo'ylab eshikkacha <b>15 000 UZS</b>.<br>"
                "• <b>Muddati:</b> Buyurtma tasdiqlangandan so'ng 24 soat ichida.<br>"
                "💳 To'lov: Naqd, karta yoki sayt orqali to'g'ridan-to'g'ri."
            )

    # 4. Yosh va xavfsizlik (14+ yosh)
    elif any(k in lower_text for k in ['14 yosh', 'возраст', 'yosh', 'bolalar', 'дети', 'xavfsiz', 'безопасн', 'age', 'safe']):
        if lang == 'ru':
            reply = (
                "🛡️ <b>Возрастной регламент и безопасность:</b><br><br>"
                "• Все тактические приводы и гель-бластеры предназначены для игроков от <b>14 лет</b>.<br>"
                "• Гелевые шарики (орбизы) на 95% состоят из воды, не оставляют синяков и пятен на одежде.<br>"
                "• ⚠️ Всегда надевайте защитные тактические очки во время стрельбы!"
            )
        elif lang == 'en':
            reply = (
                "🛡️ <b>Safety & Age Guidelines:</b><br><br>"
                "• All tactical airsoft and gel blasters are intended for players aged <b>14 and up</b>.<br>"
                "• Gel orbs are 95% water, eco-friendly and break upon impact without staining clothes.<br>"
                "• ⚠️ Always wear safety glasses during combat matches!"
            )
        else:
            reply = (
                "🛡️ <b>Yosh va xavfsizlik qoidalari:</b><br><br>"
                "• Saytdagi barcha taktik privodlar va gel blasterlar <b>14 yoshdan katta</b> bo'lganlar uchun.<br>"
                "• Orbiz sharlari 95% suvdan iborat bo'lib, ekologik toza va nishonga tekkanida kiyimda dog' qoldirmaydi.<br>"
                "• ⚠️ O'yin davomida doimo taktik himoya ko'zoynagini taqib oling!"
            )

    # 5. Mahsulot qidirish va tavsiya berish
    else:
        qs = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')

        # Narx bo'yicha qidiruv (masalan: "100 ming", "150000", "200 000 gacha")
        max_price = None
        price_num_match = re.search(r'(\d+[\d\s]*)\s*(ming|k|uzs|сум|so\'m|som)?', lower_text)
        if price_num_match:
            try:
                raw_n = price_num_match.group(1).replace(' ', '')
                num_v = int(raw_n)
                if 'ming' in lower_text or 'k' in lower_text:
                    if num_v < 1000:
                        num_v *= 1000
                if num_v >= 5000:
                    max_price = num_v
            except ValueError:
                pass

        # Toifa bo'yicha aniqlash
        cat_matched = False
        for cat in Category.objects.all():
            if cat.name.lower() in lower_text or (cat.slug and cat.slug.lower() in lower_text):
                qs = qs.filter(category=cat)
                cat_matched = True
                break

        if not cat_matched:
            if any(w in lower_text for w in ['gel', 'blaster', 'gidro', 'орбиз', 'гелевый']):
                qs = qs.filter(Q(name__icontains='gel') | Q(category__name__icontains='Gidrobol') | Q(about__icontains='gel'))
            elif any(w in lower_text for w in ['pistolet', 'пистолет', 'glock', 'beretta', 'colt']):
                qs = qs.filter(Q(name__icontains='pistolet') | Q(category__name__icontains='Pistolet'))
            elif any(w in lower_text for w in ['avtomat', 'автомат', 'ak-47', 'ak47', 'm4', 'm4a1', 'rifle']):
                qs = qs.filter(Q(name__icontains='avtomat') | Q(category__name__icontains='Avtomat'))
            elif any(w in lower_text for w in ['snayper', 'снайпер', 'miltiq', 'awp', 'kar98']):
                qs = qs.filter(Q(category__name__icontains='Snayper') | Q(name__icontains='snayper'))
            elif any(w in lower_text for w in ['shlem', 'niqob', 'maska', 'ochki', 'ko\'zoynak', 'шлем', 'маск', 'очк']):
                qs = qs.filter(Q(category__name__icontains='Shlem') | Q(name__icontains='niqob') | Q(name__icontains='ochki'))
            elif any(w in lower_text for w in ['mashina', 'машин', 'skeyt', 'скейт', 'transport']):
                qs = qs.filter(Q(category__name__icontains='Moshina') | Q(category__name__icontains='Skeyt') | Q(name__icontains='mashina') | Q(name__icontains='skeyt'))
            elif any(w in lower_text for w in ['arzon', 'chegirma', 'sale', 'скидк', 'cheap']):
                qs = qs.filter(sale__gt=0).order_by('-sale')
            elif any(w in lower_text for w in ['salom', 'privet', 'hello', 'hi', 'start', 'привет', 'здравствуй', 'assalom']):
                qs = qs.order_by('-sale', '-created_at')
                if lang == 'ru':
                    reply = "👋 <b>Приветствую, боец!</b> Я тактический ИИ-помощник Cargo-14.<br>Помогу выбрать идеальный гидробольный бластер, расскажу про характеристики, скидки и доставку. Что ищете?"
                elif lang == 'en':
                    reply = "👋 <b>Hello warrior!</b> I am your Cargo-14 Tactical AI Assistant.<br>I can recommend top gel blasters, check deals, and assist with checkout. What are you looking for?"
                else:
                    reply = "👋 <b>Assalomu alaykum, jangchi!</b> Men Cargo-14 taktik AI yordamchisiman.<br>Sizga eng yaxshi gel blaster, avtomat va aksessuarlar tanlashda, chegirmalar va yetkazib berishda ko'maklashaman. Nima qidiryapsiz?"
            else:
                words = [w for w in re.findall(r'\w+', lower_text) if len(w) > 2]
                if words:
                    q_obj = Q()
                    for w in words:
                        q_obj |= Q(name__icontains=w) | Q(about__icontains=w) | Q(category__name__icontains=w)
                    qs = qs.filter(q_obj)

        if max_price:
            qs = qs.filter(price__lte=max_price)

        matched_products = list(qs[:4])
        for p in matched_products:
            first_img = p.images.first()
            img_url = first_img.image.url if first_img else None
            products_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category.name,
                'price': p.price,
                'sale_price': int(p.sale_price),
                'sale': p.sale,
                'image_url': img_url,
                'url': f"/product/{p.id}/",
                'shots': p.get_shots_per_trigger_display() if hasattr(p, 'get_shots_per_trigger_display') else '',
                'capacity': p.magazine_capacity or 250,
            })

        if not reply:
            if products_data:
                if lang == 'ru':
                    reply = f"🎯 <b>Найдено {len(products_data)} тактических товаров по вашему запросу:</b><br>Кликните по товару, чтобы открыть его характеристики и оформить заказ."
                elif lang == 'en':
                    reply = f"🎯 <b>Found {len(products_data)} tactical items matching your request:</b><br>Click any card below to view details."
                else:
                    reply = f"🎯 <b>So'rovingizga mos {len(products_data)} ta mahsulot topildi:</b><br>Batafsil ko'rish uchun mahsulot kartasini bosing."
            else:
                if lang == 'ru':
                    reply = "🔍 Точных совпадений не найдено. Попробуйте нажать одну из быстрых подсказок ниже или спросите, например: <i>«Покажи гель-бластеры»</i> или <i>«Есть ли скидки?»</i>."
                elif lang == 'en':
                    reply = "🔍 No exact matches found. Try clicking one of the quick suggestions below or ask for <i>«Gel blasters»</i> or <i>«Discount deals»</i>."
                else:
                    reply = "🔍 Aniq mahsulot topilmadi. Quyidagi tezkor tugmalardan birini bosing yoki masalan: <i>«Gel blasterlar»</i>, <i>«Chegirmalar bormi?»</i> deb so'rang."

    quick_actions = [
        {"title": "🔫 Gel Blasterlar" if lang != 'ru' else "🔫 Гель-бластеры", "query": "Gel blaster"},
        {"title": "🔥 Chegirmalar" if lang != 'ru' else "🔥 Скидки", "query": "Katta chegirmalar"},
        {"title": "📦 Yetkazib berish" if lang != 'ru' else "📦 Доставка", "query": "Yetkazib berish shartlari qanday?"},
        {"title": "🏷️ Promokodlar" if lang != 'ru' else "🏷️ Промокоды", "query": "Qanday promokodlar bor?"},
        {"title": "🎓 Sayt bo'yicha qo'llanma" if lang != 'ru' else "🎓 Обучение по сайту", "query": "Sayt bo'yicha o'quv qo'llanmani boshlash"},
    ]

    return JsonResponse({
        'success': True,
        'reply': reply,
        'products': products_data,
        'quick_actions': quick_actions,
        'open_tutorial': open_tutorial,
        'lang': lang,
    })