"""
Komenda Django do tworzenia zadania automatyzacji dla konkretnej marki
Użycie: python manage.py create_brand_task --brand-name "Marko" --settings=nc.settings.dev
"""
from django.core.management.base import BaseCommand
from web_agent.models import WebAgentTask
from web_agent.brand_automation import (
    get_all_brands,
    create_brand_automation_task_config
)


class Command(BaseCommand):
    help = 'Tworzy zadanie automatyzacji dla konkretnej marki'

    def add_arguments(self, parser):
        parser.add_argument(
            '--brand-id',
            type=int,
            default=None,
            help='ID marki (jeśli podano, pomija brand-name)'
        )
        parser.add_argument(
            '--brand-name',
            type=str,
            default=None,
            help='Nazwa marki (np. "Marko")'
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
            '--priority',
            type=int,
            default=0,
            help='Priorytet zadania (domyślnie: 0, wyższa wartość = wyższy priorytet)'
        )
        parser.add_argument(
            '--active',
            type=str,
            choices=['true', 'false', '1', '0'],
            default='true',
            help='Filtrowanie po statusie aktywności (domyślnie: true)'
        )
        parser.add_argument(
            '--is-mapped',
            type=str,
            choices=['true', 'false', '1', '0'],
            default='false',
            help='Filtrowanie po statusie mapowania (domyślnie: false - tylko niezmapowane)'
        )
        parser.add_argument(
            '--database',
            type=str,
            default='matterhorn1',
            help='Nazwa bazy danych (domyślnie: matterhorn1)'
        )

    def handle(self, *args, **options):
        brand_id = options.get('brand_id')
        brand_name = options.get('brand_name')
        base_url = options['base_url']
        username = options.get('username')
        password = options.get('password')
        priority = options.get('priority', 0)
        active_str = options.get('active', 'true')
        is_mapped_str = options.get('is_mapped', 'false')
        database = options.get('database', 'matterhorn1')

        # Konwertuj stringi na bool
        active = active_str.lower() in ['true', '1']
        is_mapped = is_mapped_str.lower() in ['true', '1']

        # Rozwiąż brand_id lub brand_name
        if brand_id:
            # Pobierz nazwę marki z bazy
            brands = get_all_brands(using=database)
            brand = next((b for b in brands if b['id'] == brand_id), None)
            if not brand:
                self.stdout.write(
                    self.style.ERROR(f'Nie znaleziono marki z ID: {brand_id}')
                )
                return
            brand_name = brand['name']
        elif brand_name:
            # Pobierz ID marki z bazy
            brands = get_all_brands(using=database)
            brand = next((b for b in brands if b['name'] == brand_name), None)
            if not brand:
                self.stdout.write(
                    self.style.ERROR(f'Nie znaleziono marki: {brand_name}')
                )
                return
            brand_id = brand['id']
        else:
            self.stdout.write(
                self.style.ERROR('Musisz podać --brand-id lub --brand-name')
            )
            return

        self.stdout.write(
            f'Tworzenie zadania automatyzacji dla marki: {brand_name} (ID: {brand_id})...'
        )

        # Utwórz konfigurację zadania
        task_config = create_brand_automation_task_config(
            brand_id=brand_id,
            brand_name=brand_name,
            active=active,
            is_mapped=is_mapped,
            base_url=base_url,
            username=username,
            password=password
        )

        # Sprawdź czy zadanie już istnieje dla tej marki z tymi samymi filtrami
        # Użyj właściwej bazy danych przez router
        existing_task = WebAgentTask.objects.using('zzz_web_agent').filter(
            brand_id=brand_id,
            brand_name=brand_name,
            task_type='automation',
            status__in=['pending', 'running']
        ).first()

        if existing_task:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Zadanie już istnieje dla marki "{brand_name}" (ID: {existing_task.id})'
                )
            )
            self.stdout.write(
                f'   Status: {existing_task.get_status_display()}\n'
                f'   Utworzono: {existing_task.created_at}\n'
            )
            
            response = input('Czy chcesz utworzyć nowe zadanie mimo to? (tak/nie): ')
            if response.lower() not in ['tak', 'yes', 'y', 't']:
                self.stdout.write('Anulowano tworzenie zadania.')
                return

        # Utwórz zadanie w bazie danych (użyj właściwej bazy przez router)
        task = WebAgentTask.objects.using('zzz_web_agent').create(
            name=task_config['name'],
            task_type=task_config['task_type'],
            url=task_config['url'],
            config=task_config['config'],
            brand_id=task_config['brand_id'],
            brand_name=task_config['brand_name'],
            priority=priority,
            status='pending'
        )

        success_msg = (
            f'\n✅ Zadanie utworzone pomyślnie!\n'
            f'   ID: {task.id}\n'
            f'   Nazwa: {task.name}\n'
            f'   Marka: {brand_name} (ID: {brand_id})\n'
            f'   Priorytet: {priority}\n'
            f'   Status: {task.get_status_display()}\n'
            f'   Filtry: active={active}, is_mapped={is_mapped}\n'
            f'\nAby uruchomić zadanie:\n'
            f'   POST /api/web_agent/api/tasks/{task.id}/start/\n'
            f'\nLub przez Django shell:\n'
            f'   python manage.py shell --settings=nc.settings.dev\n'
            f'   >>> from web_agent.tasks import start_web_agent_task\n'
            f'   >>> start_web_agent_task.delay({task.id})\n'
        )
        self.stdout.write(self.style.SUCCESS(success_msg))

        return None

