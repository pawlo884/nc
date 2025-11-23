"""
Workflow dla logowania do Django Admin i nawigacji
"""
import os
from typing import Optional
from dotenv import load_dotenv
from ..core import Workflow, Action, ActionType

logger = __import__('logging').getLogger(__name__)


class DjangoAdminWorkflow:
    """
    Tworzy workflow do logowania do Django Admin i nawigacji do produktów.
    """
    
    @staticmethod
    def create_login_workflow(
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        env_file: str = '.env.dev'
    ) -> Workflow:
        """
        Tworzy workflow do logowania do Django Admin
        
        Args:
            base_url: URL aplikacji Django
            username: Nazwa użytkownika (jeśli None, pobiera z .env)
            password: Hasło (jeśli None, pobiera z .env)
            env_file: Ścieżka do pliku .env
            
        Returns:
            Workflow do logowania
        """
        # Pobierz dane logowania
        if username is None or password is None:
            # Znajdź ścieżkę do .env.dev (może być w katalogu głównym projektu)
            env_path = env_file
            if not os.path.isabs(env_file):
                # Spróbuj znaleźć plik .env.dev w katalogu głównym projektu
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                env_path = os.path.join(project_root, env_file)
            
            logger.info(f'Ładuję zmienne z: {env_path}')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                logger.info('✓ Plik .env.dev załadowany')
            else:
                logger.warning(f'⚠️ Plik .env.dev nie istnieje: {env_path}')
                
            username = username or os.getenv('DJANGO_ADMIN_USERNAME', '')
            password = password or os.getenv('DJANGO_ADMIN_PASSWORD', '')
            
        logger.info(f'Logowanie - username: {username}, password: {"*" * len(password) if password else "BRAK"}')
        
        if not username or not password:
            logger.warning('Brak danych logowania! Sprawdź .env.dev lub podaj username/password')
            logger.warning(f'  DJANGO_ADMIN_USERNAME: {"USTAWIONE" if username else "BRAK"}')
            logger.warning(f'  DJANGO_ADMIN_PASSWORD: {"USTAWIONE" if password else "BRAK"}')
            
        workflow = Workflow(name='Django Admin Login')
        
        # 1. Nawigacja do strony głównej
        workflow.add_step(
            name='Nawigacja do strony głównej',
            action=Action(
                ActionType.NAVIGATE,
                url=base_url,
                wait_until='load',
                timeout=30000
            )
        )
        
        # 2. Sprawdź czy link do admina istnieje
        workflow.add_step(
            name='Sprawdź czy link do admina istnieje',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const adminLink = document.querySelector('a[href="/admin/"]');
                    if (adminLink) {
                        return {
                            link_found: true,
                            link_text: adminLink.textContent.trim(),
                            link_href: adminLink.href
                        };
                    }
                    // Sprawdź alternatywne selektory
                    const altLinks = document.querySelectorAll('a');
                    const adminLinks = Array.from(altLinks).filter(a => 
                        a.href.includes('/admin/') || 
                        a.textContent.toLowerCase().includes('admin') ||
                        a.textContent.toLowerCase().includes('administracja')
                    );
                    return {
                        link_found: false,
                        alternative_links: adminLinks.map(a => ({
                            text: a.textContent.trim(),
                            href: a.href
                        })),
                        message: 'Link do admina nie znaleziony'
                    };
                })()'''
            )
        )
        
        # 3. Kliknięcie linku do admina
        workflow.add_step(
            name='Kliknięcie linku do admina',
            action=Action(
                ActionType.CLICK,
                selector='a[href="/admin/"]',
                timeout=10000,
                optional=True  # Opcjonalne - może być że już jesteśmy na stronie logowania
            )
        )
        
        # 4. Oczekiwanie na formularz logowania
        workflow.add_step(
            name='Oczekiwanie na formularz logowania',
            action=Action(
                ActionType.WAIT_FOR,
                selector='input[name="username"], #id_username',
                timeout=15000
            )
        )
        
        # 5. Wypełnienie username
        workflow.add_step(
            name='Wypełnienie username',
            action=Action(
                ActionType.FILL,
                selector='input[name="username"], #id_username',
                value=username,
                timeout=10000
            )
        )
        
        # 6. Wypełnienie password
        workflow.add_step(
            name='Wypełnienie password',
            action=Action(
                ActionType.FILL,
                selector='input[name="password"], #id_password, input[type="password"]',
                value=password,
                timeout=10000
            )
        )
        
        # 7. Kliknięcie submit
        workflow.add_step(
            name='Kliknięcie submit',
            action=Action(
                ActionType.CLICK,
                selector='input[type="submit"], button[type="submit"], button[type="submit"].submit-row',
                timeout=10000
            )
        )
        
        # 8. Oczekiwanie na zalogowanie
        workflow.add_step(
            name='Oczekiwanie na zalogowanie',
            action=Action(
                ActionType.WAIT_FOR,
                selector='.user-tools, a[href*="/admin/matterhorn1"], #user-tools, .dashboard',
                timeout=20000
            )
        )
        
        # 9. Sprawdź czy logowanie się powiodło
        workflow.add_step(
            name='Sprawdź status logowania',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const userTools = document.querySelector('.user-tools, #user-tools');
                    const dashboard = document.querySelector('.dashboard');
                    const isLoggedIn = !!(userTools || dashboard);
                    const currentUrl = window.location.href;
                    const isOnLoginPage = currentUrl.includes('/admin/login/');
                    
                    return {
                        logged_in: isLoggedIn && !isOnLoginPage,
                        is_on_login_page: isOnLoginPage,
                        current_url: currentUrl,
                        user_tools_found: !!userTools,
                        dashboard_found: !!dashboard
                    };
                })()'''
            )
        )
        
        return workflow
    
    @staticmethod
    def create_navigate_to_products_workflow(
        products_url: str
    ) -> Workflow:
        """
        Tworzy workflow do nawigacji do listy produktów
        
        Args:
            products_url: URL do listy produktów (z filtrami)
            
        Returns:
            Workflow do nawigacji
        """
        workflow = Workflow(name='Navigate to Products')
        
        # 1. Nawigacja do produktów
        workflow.add_step(
            name='Nawigacja do listy produktów',
            action=Action(
                ActionType.NAVIGATE,
                url=products_url,
                wait_until='load',
                timeout=30000
            )
        )
        
        # 2. Oczekiwanie na tabelę produktów
        workflow.add_step(
            name='Oczekiwanie na tabelę produktów',
            action=Action(
                ActionType.WAIT_FOR,
                selector='table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                timeout=15000
            )
        )
        
        # 3. Czekaj 10 sekund
        workflow.add_step(
            name='Czekanie 10 sekund',
            action=Action(
                ActionType.WAIT,
                params={'seconds': 10}
            )
        )
        
        return workflow
    
    @staticmethod
    def create_apply_filters_workflow(
        active: bool = True,
        is_mapped: bool = False
    ) -> Workflow:
        """
        Tworzy workflow do zastosowania filtrów w liście produktów
        
        Args:
            active: Filtr active (True/False)
            is_mapped: Filtr is_mapped (True/False)
            
        Returns:
            Workflow do zastosowania filtrów
        """
        workflow = Workflow(name='Apply Filters')
        
        # 1. Oczekiwanie na sidebar z filtrami
        workflow.add_step(
            name='Oczekiwanie na sidebar z filtrami',
            action=Action(
                ActionType.WAIT_FOR,
                selector='#changelist-filter, .changelist-filters',
                timeout=10000
            )
        )
        
        # 2. Zastosuj filtr active
        workflow.add_step(
            name=f'Zastosuj filtr active={active}',
            action=Action(
                ActionType.EVALUATE,
                expression=f'''(() => {{
                    const filterSection = document.querySelector('#changelist-filter');
                    if (!filterSection) {{
                        return {{ filter_section_found: false, error: 'Nie znaleziono sekcji filtrów' }};
                    }}
                    
                    // Znajdź sekcję "active"
                    const activeSection = Array.from(filterSection.querySelectorAll('h3, .filter-title')).find(el => {{
                        const text = el.textContent.toLowerCase();
                        return text.includes('active') || text.includes('aktywne');
                    }});
                    
                    if (!activeSection) {{
                        return {{ active_section_found: false, error: 'Nie znaleziono sekcji active' }};
                    }}
                    
                    // Znajdź link do wartości active
                    const activeValue = {repr(str(active).lower())};
                    const activeLinks = activeSection.parentElement?.querySelectorAll('a') || [];
                    let activeLink = null;
                    
                    for (const link of activeLinks) {{
                        const linkText = link.textContent.toLowerCase().trim();
                        if (activeValue === 'true' && (linkText.includes('true') || linkText.includes('tak') || linkText.includes('yes'))) {{
                            activeLink = link.href;
                            break;
                        }} else if (activeValue === 'false' && (linkText.includes('false') || linkText.includes('nie') || linkText.includes('no'))) {{
                            activeLink = link.href;
                            break;
                        }}
                    }}
                    
                    if (activeLink) {{
                        return {{
                            navigate_to_url: activeLink,
                            active_filter_found: true,
                            active_value: activeValue
                        }};
                    }}
                    
                    return {{
                        active_filter_found: false,
                        error: 'Nie znaleziono linku do wartości active=' + activeValue
                    }};
                }})()'''
            )
        )
        
        # 3. Oczekiwanie na załadowanie przefiltrowanej listy
        workflow.add_step(
            name='Oczekiwanie na przefiltrowaną listę (active)',
            action=Action(
                ActionType.WAIT_FOR,
                selector='table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                timeout=15000
            )
        )
        
        # 4. Zastosuj filtr is_mapped
        workflow.add_step(
            name=f'Zastosuj filtr is_mapped={is_mapped}',
            action=Action(
                ActionType.EVALUATE,
                expression=f'''(() => {{
                    const filterSection = document.querySelector('#changelist-filter');
                    if (!filterSection) {{
                        return {{ filter_section_found: false, error: 'Nie znaleziono sekcji filtrów' }};
                    }}
                    
                    // Znajdź sekcję "is_mapped"
                    const mappedSection = Array.from(filterSection.querySelectorAll('h3, .filter-title')).find(el => {{
                        const text = el.textContent.toLowerCase();
                        return text.includes('mapped') || text.includes('zmapowane');
                    }});
                    
                    if (!mappedSection) {{
                        return {{ mapped_section_found: false, error: 'Nie znaleziono sekcji is_mapped' }};
                    }}
                    
                    // Znajdź link do wartości is_mapped
                    const mappedValue = {repr(str(is_mapped).lower())};
                    const mappedLinks = mappedSection.parentElement?.querySelectorAll('a') || [];
                    let mappedLink = null;
                    
                    for (const link of mappedLinks) {{
                        const linkText = link.textContent.toLowerCase().trim();
                        if (mappedValue === 'false' && (linkText.includes('false') || linkText.includes('nie') || linkText.includes('no') || linkText.includes('0'))) {{
                            mappedLink = link.href;
                            break;
                        }} else if (mappedValue === 'true' && (linkText.includes('true') || linkText.includes('tak') || linkText.includes('yes') || linkText.includes('1'))) {{
                            mappedLink = link.href;
                            break;
                        }}
                    }}
                    
                    if (mappedLink) {{
                        return {{
                            navigate_to_url: mappedLink,
                            mapped_filter_found: true,
                            mapped_value: mappedValue
                        }};
                    }}
                    
                    return {{
                        mapped_filter_found: false,
                        error: 'Nie znaleziono linku do wartości is_mapped=' + mappedValue
                    }};
                }})()'''
            )
        )
        
        # 5. Oczekiwanie na załadowanie przefiltrowanej listy
        workflow.add_step(
            name='Oczekiwanie na przefiltrowaną listę (is_mapped)',
            action=Action(
                ActionType.WAIT_FOR,
                selector='table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                timeout=15000
            )
        )
        
        # 6. Sprawdź czy filtry zostały zastosowane
        workflow.add_step(
            name='Sprawdź czy filtry zostały zastosowane',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const url = new URL(window.location.href);
                    const activeParam = url.searchParams.get('active__exact');
                    const mappedParam = url.searchParams.get('is_mapped__exact');
                    
                    return {
                        active_filter_applied: !!activeParam,
                        active_value: activeParam,
                        mapped_filter_applied: !!mappedParam,
                        mapped_value: mappedParam,
                        current_url: window.location.href,
                        message: 'Filtry: active=' + (activeParam || 'brak') + ', is_mapped=' + (mappedParam || 'brak')
                    };
                })()'''
            )
        )
        
        return workflow
    
    @staticmethod
    def create_select_brand_workflow(
        brand_name: str = 'Marko'
    ) -> Workflow:
        """
        Tworzy workflow do wyboru marki w filtrach Django Admin
        
        Args:
            brand_name: Nazwa marki do wyboru (domyślnie: Marko)
            
        Returns:
            Workflow do wyboru marki
        """
        workflow = Workflow(name='Select Brand')
        
        # 1. Przejdź do listy produktów (jeśli jeszcze nie jesteśmy)
        workflow.add_step(
            name='Nawigacja do listy produktów',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const isOnProductsPage = window.location.pathname.includes('/admin/matterhorn1/product/');
                    if (!isOnProductsPage) {
                        return {
                            navigate_to_url: '/admin/matterhorn1/product/'
                        };
                    }
                    return { already_on_page: true };
                })()'''
            )
        )
        
        # 2. Oczekiwanie na sidebar z filtrami
        workflow.add_step(
            name='Oczekiwanie na sidebar z filtrami',
            action=Action(
                ActionType.WAIT_FOR,
                selector='#changelist-filter, .changelist-filters',
                timeout=10000
            )
        )
        
        # 3. Znajdź i kliknij filtr marki
        workflow.add_step(
            name='Znajdź i kliknij filtr marki',
            action=Action(
                ActionType.EVALUATE,
                expression=f'''(() => {{
                    // Znajdź link do marki w filtrach
                    const filterLinks = document.querySelectorAll('#changelist-filter a, .changelist-filters a');
                    let brandLink = null;
                    const brandName = {repr(brand_name)};
                    
                    for (const link of filterLinks) {{
                        const linkText = link.textContent.trim();
                        // Szukaj linku który zawiera nazwę marki
                        if (linkText.includes(brandName)) {{
                            brandLink = link.href;
                            console.log('Znaleziono link do marki:', brandLink);
                            break;
                        }}
                    }}
                    
                    if (brandLink) {{
                        return {{
                            navigate_to_url: brandLink,
                            brand_found: true
                        }};
                    }}
                    
                    return {{
                        brand_found: false,
                        message: 'Nie znaleziono marki ' + brandName + ' w filtrach'
                    }};
                }})()'''
            )
        )
        
        # 4. Oczekiwanie na załadowanie przefiltrowanej listy
        workflow.add_step(
            name='Oczekiwanie na przefiltrowaną listę',
            action=Action(
                ActionType.WAIT_FOR,
                selector='table.changelist tbody tr, table#result_list tbody tr, table tbody tr',
                timeout=15000
            )
        )
        
        # 5. Sprawdź czy filtr został zastosowany
        workflow.add_step(
            name='Sprawdź czy filtr marki został zastosowany',
            action=Action(
                ActionType.EVALUATE,
                expression='''(() => {
                    const url = new URL(window.location.href);
                    const brandParam = url.searchParams.get('brand__id__exact');
                    const activeFilter = document.querySelector('#changelist-filter .selected, .changelist-filters .selected');
                    
                    return {{
                        brand_filter_applied: !!brandParam,
                        brand_id: brandParam,
                        active_filter_visible: !!activeFilter,
                        current_url: window.location.href,
                        message: brandParam ? 'Filtr marki został zastosowany' : 'Filtr marki nie został zastosowany'
                    }};
                })()'''
            )
        )
        
        return workflow
