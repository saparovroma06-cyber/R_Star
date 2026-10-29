from django.apps import AppConfig


class Cargo14Config(AppConfig):
    name = 'cargo_14'

    def ready(self):
        import cargo_14.signals # Импортируем сигналы
