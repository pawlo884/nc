"""
Komenda Django do tworzenia zadania automatyzacji dla Django Admin
"""
from django.core.management.base import BaseCommand
from web_agent.models import WebAgentTask
from web_agent.django_admin_automation import create_automation_task_config


class Command(BaseCommand):
    help = 'Tworzy zadanie automatyzacji dla logowania do Django Admin i przejścia do Produktów'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['login', 'products'],
            default='products',
            help='Typ konfiguracji: login (tylko logowanie) lub products (logowanie + produkty)'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='http://localhost:8000',
            help='URL aplikacji Django'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Nazwa użytkownika (jeśli nie podano, pobiera z .env.dev)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Hasło (jeśli nie podano, pobiera z .env.dev)'
        )
        parser.add_argument(
            '--name',
            type=str,
            default=None,
            help='Nazwa zadania (domyślnie: Django Admin - Products)'
        )

    def handle(self, *args, **options):
        config_type = options['type']
        base_url = options['base_url']
        username = options.get('username')
        password = options.get('password')
        custom_name = options.get('name')

        self.stdout.write(
            f'Tworzenie zadania automatyzacji Django Admin ({config_type})...')

        # Utwórz konfigurację
        task_config = create_automation_task_config(
            config_type=config_type,
            base_url=base_url,
            username=username,
            password=password
        )

        # Użyj niestandardowej nazwy jeśli podano
        if custom_name:
            task_config['name'] = custom_name

        # Utwórz zadanie w bazie danych
        task = WebAgentTask.objects.create(
            name=task_config['name'],
            task_type=task_config['task_type'],
            url=task_config['url'],
            config=task_config['config'],
            status='pending'
        )

        success_msg = (
            f'\n✓ Zadanie utworzone pomyślnie!\n'
            f'  ID: {task.id}\n'
            f'  Nazwa: {task.name}\n'
            f'  URL: {task.url}\n'
            f'  Status: {task.status}\n'
            f'\nAby uruchomić zadanie, użyj:\n'
            f'  python manage.py shell --settings=nc.settings.dev\n'
            f'  >>> from web_agent.tasks import start_web_agent_task\n'
            f'  >>> start_web_agent_task.delay({task.id})\n'
            f'\nLub przez API:\n'
            f'  POST /api/web_agent/api/tasks/{task.id}/start/'
        )
        self.stdout.write(self.style.SUCCESS(success_msg))

        return task
