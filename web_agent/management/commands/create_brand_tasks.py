"""
Komenda Django do tworzenia zadań automatyzacji dla każdej marki osobno
"""
from django.core.management.base import BaseCommand
from web_agent.models import WebAgentTask
from web_agent.config_builders import (
    get_all_brands,
    get_all_categories,
    create_brand_task_config
)


class Command(BaseCommand):
    help = 'Tworzy zadania automatyzacji dla każdej marki osobno'

    def add_arguments(self, parser):
        parser.add_argument(
            '--brand-id',
            type=int,
            default=None,
            help='ID konkretnej marki (jeśli podano, tworzy tylko dla tej marki)'
        )
        parser.add_argument(
            '--brand-name',
            type=str,
            default=None,
            help='Nazwa marki (jeśli podano, tworzy tylko dla tej marki)'
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
            '--category-id',
            type=int,
            default=None,
            help='ID kategorii do filtrowania (opcjonalne)'
        )
        parser.add_argument(
            '--category-name',
            type=str,
            default=None,
            help='Nazwa kategorii do filtrowania (opcjonalne)'
        )
        parser.add_argument(
            '--active',
            type=str,
            choices=['true', 'false', '1', '0', 'yes', 'no'],
            default=None,
            help='Filtrowanie po statusie aktywności: true/1/yes (tylko aktywne), false/0/no (tylko nieaktywne)'
        )
        parser.add_argument(
            '--database',
            type=str,
            default='matterhorn1',
            help='Nazwa bazy danych (domyślnie: matterhorn1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tryb testowy - tylko wyświetla co zostanie utworzone, bez zapisywania'
        )

    def handle(self, *args, **options):
        base_url = options['base_url']
        username = options.get('username')
        password = options.get('password')
        brand_id = options.get('brand_id')
        brand_name = options.get('brand_name')
        category_id = options.get('category_id')
        category_name = options.get('category_name')
        active_str = options.get('active')
        database = options.get('database', 'matterhorn1')
        dry_run = options.get('dry_run', False)

        # Przekonwertuj active na bool
        active = None
        if active_str:
            active = active_str.lower() in ['true', '1', 'yes']

        # Resolve category_id lub category_name
        if category_name and not category_id:
            categories = get_all_categories(using=database)
            category = next(
                (c for c in categories if c['name'] == category_name), None)
            if category:
                category_id = category['id']
                if not category_name:
                    category_name = category['name']
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'Nie znaleziono kategorii: {category_name}')
                )
                return

        if brand_id or brand_name:
            # Tworzenie zadania dla konkretnej marki
            self.stdout.write('Tworzenie zadania dla marki...')

            if brand_id and not brand_name:
                # Pobierz nazwę marki z bazy
                brands = get_all_brands(using=database)
                brand = next((b for b in brands if b['id'] == brand_id), None)
                if not brand:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Nie znaleziono marki z ID: {brand_id}')
                    )
                    return
                brand_name = brand['name']
            elif brand_name and not brand_id:
                # Pobierz ID marki z bazy
                brands = get_all_brands(using=database)
                brand = next(
                    (b for b in brands if b['name'] == brand_name), None)
                if not brand:
                    self.stdout.write(
                        self.style.ERROR(f'Nie znaleziono marki: {brand_name}')
                    )
                    return
                brand_id = brand['id']

            if not brand_id:
                self.stdout.write(
                    self.style.ERROR('Musisz podać brand-id lub brand-name')
                )
                return

            task_config = create_brand_task_config(
                brand_id=brand_id,
                brand_name=brand_name,
                category_id=category_id,
                category_name=category_name,
                active=active,
                base_url=base_url,
                username=username,
                password=password
            )

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    '\n[DRY RUN] Zadanie NIE zostanie utworzone:'))
                self.stdout.write(f'  Nazwa: {task_config["name"]}')
                self.stdout.write(f'  URL: {task_config["url"]}')
                self.stdout.write(f'  Brand ID: {brand_id}')
                self.stdout.write(f'  Brand Name: {brand_name}')
                return

            task = WebAgentTask.objects.create(
                name=task_config['name'],
                task_type=task_config['task_type'],
                url=task_config['url'],
                config=task_config['config'],
                status='pending'
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Zadanie utworzone dla marki "{brand_name}"!\n'
                    f'  ID zadania: {task.id}\n'
                    f'  Brand ID: {brand_id}\n'
                )
            )
        else:
            # Tworzenie zadań dla wszystkich marek
            self.stdout.write('Pobieranie listy marek z bazy danych...')

            try:
                brands = get_all_brands(using=database)
                self.stdout.write(f'Znaleziono {len(brands)} marek')

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        '\n[DRY RUN] Zostaną utworzone zadania dla:'))
                    for brand in brands[:10]:  # Pokaż pierwsze 10
                        task_config = create_brand_automation_task_config(
                            brand_id=brand['id'],
                            brand_name=brand['name'],
                            base_url=base_url,
                            username=username,
                            password=password
                        )
                        self.stdout.write(
                            f'  - {brand["name"]} (ID: {brand["id"]})')
                    if len(brands) > 10:
                        self.stdout.write(f'  ... i {len(brands) - 10} więcej')
                    return

                created_count = 0
                skipped_count = 0

                for brand in brands:
                    task_config = create_brand_automation_task_config(
                        brand_id=brand['id'],
                        brand_name=brand['name'],
                        category_id=category_id,
                        category_name=category_name,
                        active=active,
                        base_url=base_url,
                        username=username,
                        password=password
                    )

                    # Sprawdź czy zadanie już istnieje
                    existing_task = WebAgentTask.objects.filter(
                        name=task_config['name']
                    ).first()

                    if existing_task:
                        self.stdout.write(
                            f'⏭  Pominięto "{brand["name"]}" - zadanie już istnieje (ID: {existing_task.id})'
                        )
                        skipped_count += 1
                        continue

                    task = WebAgentTask.objects.create(
                        name=task_config['name'],
                        task_type=task_config['task_type'],
                        url=task_config['url'],
                        config=task_config['config'],
                        status='pending'
                    )

                    created_count += 1
                    self.stdout.write(
                        f'✓ Utworzono zadanie dla "{brand["name"]}" (ID zadania: {task.id})'
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Gotowe!\n'
                        f'  Utworzono: {created_count} zadań\n'
                        f'  Pominięto: {skipped_count} zadań (już istnieją)\n'
                        f'  Łącznie marek: {len(brands)}'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'\n✗ Błąd podczas tworzenia zadań: {str(e)}')
                )
                raise
