import os
import django
import requests
from django.core.files import File
import io # Добавляем импорт io
from django.conf import settings

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cargo_14.models import Product, ProductImage

# URL изображения, которое нужно использовать для всех продуктов
DEFAULT_IMAGE_URL = "https://lens.usercontent.google.com/banana?agsi=CmdnbG9iYWw6OjAwMDA1NWNmZWM3MDAyNmQ6MDAwMDAwZWI6MTplZTIyZjQ0ZTg0MzZkNWY3OjAwMDA1NWNmZWM3MDAyNmQ6MDAwMDAzMjhlY2EwMzM2ODowMDA2NWU0MzQwNTQxNDlmEAIYASIKaW1hZ2UvanBlZw=="
DEFAULT_IMAGE_FILENAME = "default_product_image.jpg" # Имя файла, под которым будет сохранено изображение

def set_default_image_for_all_products():
    print("Начинаем устанавливать изображение по умолчанию для всех продуктов...")

    # 1. Загружаем изображение в io.BytesIO
    try:
        response = requests.get(DEFAULT_IMAGE_URL, stream=True)
        response.raise_for_status() # Проверка на HTTP ошибки
        
        # Используем io.BytesIO для хранения изображения в памяти
        image_data = io.BytesIO(response.content)
        print(f"Изображение успешно загружено с {DEFAULT_IMAGE_URL}")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке изображения с {DEFAULT_IMAGE_URL}: {e}")
        return
    except Exception as e:
        print(f"Неожиданная ошибка при загрузке изображения: {e}")
        return

    # 2. Обновляем или создаем ProductImage для всех продуктов
    products = Product.objects.all()
    for product in products:
        try:
            # Проверяем, есть ли уже ProductImage для этого продукта.
            # Если есть, обновляем его. Если нет, создаем новый.
            product_image, created = ProductImage.objects.get_or_create(product=product)
            
            # Сохраняем изображение в поле ImageField
            # File() принимает файлоподобный объект, io.BytesIO подходит
            product_image.image.save(DEFAULT_IMAGE_FILENAME, File(image_data), save=True)
            
            if created:
                print(f"  Создано новое изображение для продукта ID: {product.id} - {product.name}")
            else:
                print(f"  Обновлено изображение для продукта ID: {product.id} - {product.name}")

        except Exception as e:
            print(f"  Ошибка при установке изображения для продукта ID {product.id} - {product.name}: {e}")
    
    print("Завершено. Изображение по умолчанию установлено для всех продуктов.")

if __name__ == '__main__':
    set_default_image_for_all_products()