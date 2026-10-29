from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from .telegram_utils import send_telegram_notification

@receiver(post_save, sender=Order)
def order_status_changed_notification(sender, instance, created, **kwargs):
    if created:
        message_text = (
            f"<b>Yangi buyurtma yaratildi!</b>\n\n"
            f"<b>Buyurtma ID:</b> {instance.id}\n"
            f"<b>Foydalanuvchi:</b> {instance.user.username}\n"
            f"<b>Umumiy narx:</b> {instance.total_price} UZS\n"
            f"<b>Yetkazib berish usuli:</b> {instance.get_delivery_method_display()}\n"
            f"<b>Status:</b> {instance.get_status_display()}\n"
            f"<b>Havola:</b> http://127.0.0.1:8000/admin/cargo_14/order/{instance.id}/change/"
        )
        send_telegram_notification(message_text)
    else:
        # Проверяем, изменился ли статус
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                message_text = (
                    f"<b>Buyurtma statusi o'zgardi!</b>\n\n"
                    f"<b>Buyurtma ID:</b> {instance.id}\n"
                    f"<b>Foydalanuvchi:</b> {instance.user.username}\n"
                    f"<b>Eski status:</b> {old_instance.get_status_display()}\n"
                    f"<b>Yangi status:</b> {instance.get_status_display()}\n"
                    f"<b>Havola:</b> http://127.0.0.1:8000/admin/cargo_14/order/{instance.id}/change/"
                )
                send_telegram_notification(message_text)
        except sender.DoesNotExist:
            pass # Объект был только что создан, это будет обработано в 'created' ветке