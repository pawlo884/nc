import os
import time
import urllib.parse
from datetime import datetime
import json
from dotenv import load_dotenv
import requests
from .defs_db import connect_to_postgresql, create_tables_if_not_exist, import_insert_item
import psycopg2
import logging
import pytz

logger = logging.getLogger(__name__)

# Ustawienie strefy czasowej
warsaw_tz = pytz.timezone('Europe/Warsaw')

# Dodanie filtru do loggera, który doda strefę czasową
class TimezoneFilter(logging.Filter):
    def filter(self, record):
        record.timezone = datetime.now(warsaw_tz).strftime('%z')
        return True

# Usunięcie wszystkich istniejących handlerów
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Dodanie filtru strefy czasowej
logger.addFilter(TimezoneFilter())

# Ładowanie zmiennych środowiskowych
load_dotenv('.env.dev')
api_key = os.getenv('api_key')
headersMatterhorn = {
    "Content-Type": "application/json",
    "Authorization": api_key
}

# OK
def get_last_id():
    connection = connect_to_postgresql('matterhorn')
    create_tables_if_not_exist(connection)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT MAX(id) AS last_id FROM products WHERE name != 'Placeholder Name' AND name != '0 Nowy artykul - 0'")
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result[0] if result and result[0] is not None else 0

# OK
def import_all_by_one():
    load_dotenv('.env.dev')
    logger.info("Rozpoczynam import produktów...")
        
    last_id = get_last_id()
    logger.info(f"Ostatni ID w bazie: {last_id}")
    null_count = 0
    # Pobieramy nagłówki z .env
    api_key = os.getenv('api_key')
    headersMatterhorn = {
        "Content-Type": "application/json",
        "Authorization": api_key
    }
    logger.info(f"Używane nagłówki: {headersMatterhorn}")

    base_url = "https://matterhorn.pl/B2BAPI/ITEMS/"
    logger.info(f"Używany URL: {base_url}")

    for i in range(last_id + 1, last_id + 250000):
        url = f"{base_url}{i}"
        logger.info(f"Pobieranie danych z: {url}")

        attempt = 1
        max_attempts = 100
        json_decode_attempts = 0
        max_json_decode_attempts = 100
        db_connection_attempts = 0
        max_db_connection_attempts = 100

        while attempt <= max_attempts:
            try:
                response = requests.get(url, headers=headersMatterhorn)

                time.sleep(0.6)

                if response.status_code == 200:
                    try:
                        # Sprawdzamy czy odpowiedź nie jest pusta
                        if not response.text.strip():
                            logger.warning(f"Pusta odpowiedź dla URL: {url}")
                            break

                        item = response.json()
                        logger.debug(
                            f"Przetworzono JSON: {json.dumps(item, indent=2)[:500]}")
                        json_decode_attempts = 0

                        if item.get("creation_date") is None:
                            null_count += 1
                            logger.warning(
                                f"Pominięto import dla URL: {url} ponieważ creation_date jest NULL. {null_count}")
                            if null_count >= 200:
                                logger.warning(
                                    f"Pole 'creation_date' jest puste dla {null_count} kolejnych importów. Koniec importu")
                                return
                            break
                        else:
                            null_count = 0

                        logger.info(
                            f"Pobrano produkt ID: {item['id']}, Nazwa: {item['name']}")
                        yield item

                        if 'url' in item and isinstance(item['url'], str):
                            item['url'] = item['url'].replace(
                                'http://matterhorn-wholesale.com', 'http://matterhorn.pl')

                        price = item["prices"].get("PLN", None)
                        item_data = (
                            item["id"],
                            item["active"],
                            item["name"].lstrip(),
                            item["name_without_number"].lstrip(),
                            item["description"],
                            item["creation_date"],
                            item["color"],
                            item["category_name"],
                            item["category_id"],
                            item["category_path"],
                            item["brand_id"],
                            item["brand"],
                            item["stock_total"],
                            item["url"],
                            item["new_collection"],
                            item["size_table"],
                            item["weight"],
                            item["size_table_txt"],
                            item["size_table_html"],
                            price
                        )

                        if item.get("images"):
                            images_data = [
                                (image.split('_')[-1].split('.jpg')[0], image, item["id"]) for image in item["images"]
                            ]
                        else:
                            images_data = []

                        variants_data = []
                        if isinstance(item.get("variants"), list):
                            variants_data = [
                                (
                                    int(variant["variant_uid"]),
                                    variant["name"],
                                    int(variant["stock"]),
                                    int(variant["max_processing_time"]),
                                    variant["ean"],
                                    item["id"]
                                )
                                for variant in item["variants"]
                            ]

                        other_colors = []
                        if isinstance(item.get("other_colors"), list):
                            for color_id in item.get("other_colors", []):
                                product_id = item["id"]
                                color_product_id = int(color_id)

                                if product_id != color_product_id:
                                    other_colors.append(
                                        (product_id, color_product_id))

                        product_sets = []
                        if isinstance(item.get("products_in_set"), list):
                            for product_in_set_id in item.get("products_in_set", []):
                                product_id = item["id"]
                                related_product_id = int(product_in_set_id)

                                if product_id != related_product_id:
                                    product_sets.append(
                                        (product_id, related_product_id))

                        # Próba połączenia z bazą danych z ponownymi próbami
                        while db_connection_attempts < max_db_connection_attempts:
                            try:
                                connection = connect_to_postgresql('matterhorn')
                                create_tables_if_not_exist(connection)
                                import_insert_item(
                                    connection, item_data, images_data, variants_data, other_colors, product_sets)
                                connection.close()
                                logger.info(
                                    f"Zapisano produkt ID: {item['id']} do bazy danych")
                                db_connection_attempts = 0
                                break
                            except Exception as e:
                                db_connection_attempts += 1
                                logger.error(
                                    f"Błąd połączenia z bazą danych (próba {db_connection_attempts}/{max_db_connection_attempts}): {str(e)}")
                                if db_connection_attempts < max_db_connection_attempts:
                                    time.sleep(5)
                                else:
                                    logger.error(
                                        "Osiągnięto maksymalną liczbę prób połączenia z bazą danych. Przechodzę do następnego produktu.")
                                    break

                        break
                    except json.JSONDecodeError as e:
                        json_decode_attempts += 1
                        if json_decode_attempts < max_json_decode_attempts:
                            logger.error(
                                f"Błąd dekodowania JSON dla URL: {url}. Próba {json_decode_attempts} z {max_json_decode_attempts}. Błąd: {str(e)}")
                            logger.debug(
                                f"Treść odpowiedzi: {response.text[:500]}")
                            logger.info("Ponawiam próbę po 5 sekundach...")
                            time.sleep(5)
                            continue
                        else:
                            logger.error(
                                f"Błąd dekodowania JSON dla URL: {url} po {max_json_decode_attempts} próbach. Błąd: {str(e)}")
                            logger.debug(
                                f"Treść odpowiedzi: {response.text[:500]}")
                            break
                    except Exception as e:
                        logger.error(
                            f"Błąd podczas przetwarzania odpowiedzi dla URL: {url}. Błąd: {str(e)}")
                        logger.debug(f"Treść odpowiedzi: {response.text[:500]}")
                        break
                elif 500 <= response.status_code <= 600:
                    logger.warning(
                        f"Otrzymano kod odpowiedzi {response.status_code} dla URL: {url}. Próba {attempt} z {max_attempts}")
                    if attempt < max_attempts:
                        logger.info("Odczekaj 10 sekund przed kolejną próbą...")
                        time.sleep(10)
                        attempt += 1
                        continue
                    else:
                        logger.error(
                            f"Nie udało się nawiązać połączenia dla URL: {url} po {max_attempts} próbach.")
                        break
                else:
                    logger.warning(
                        f"Nieoczekiwany kod odpowiedzi {response.status_code} dla URL: {url}")
                    logger.debug(f"Treść odpowiedzi: {response.text[:500]}")
                    break
            except requests.exceptions.RequestException as e:
                logger.error(f"Błąd połączenia dla URL: {url}. Błąd: {str(e)}")
                if attempt < max_attempts:
                    logger.info("Odczekaj 10 sekund przed kolejną próbą...")
                    time.sleep(10)
                    attempt += 1
                    continue
                else:
                    break

    logger.info("Import produktów zakończony.")

# OK
def get_latest_timestamp():
    """
    Pobiera najnowszy timestamp z tabeli `variants` i zwraca go jako ciąg znaków.
    """
    try:
        connection = connect_to_postgresql(
            'matterhorn')  # Zmienione na PostgreSQL
        cursor = connection.cursor()

        # Pobieranie najnowszego timestamp
        query = "SELECT MAX(timestamp) FROM variants"
        cursor.execute(query)
        latest_timestamp = cursor.fetchone()[0]

        if not latest_timestamp:
            # Jeśli tabela jest pusta, domyślnie zwróć minimalny czas jako string
            latest_timestamp = "1970-01-01 00:00:00"
        else:
            # Konwertuj obiekt datetime na string
            latest_timestamp = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        print(f"[INFO] Najnowszy timestamp: {latest_timestamp}")
        return latest_timestamp
    except Exception as e:
        print(f"[ERROR] Nie udało się pobrać najnowszego timestamp: {e}")
        return "2025-04-08 00:00:00"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and not connection.closed:
            connection.close()

# OK
def get_last_update_time():
    try:
        connection = connect_to_postgresql('matterhorn')
        cursor = connection.cursor()
        cursor.execute(
            "SELECT last_update AT TIME ZONE 'Europe/Warsaw' FROM update_log ORDER BY last_update DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result and result[0]:
            return result[0].strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Domyślny czas, jeśli brak wpisów
            return datetime.now(pytz.timezone('Europe/Warsaw')).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"[ERROR] Nie udało się pobrać czasu ostatniej aktualizacji: {e}")
        return "2024-04-08 00:00:00"


def round_down_to_10_minutes(dt):
    """
    Zaokrągla czas w dół do najbliższych 10 minut
    """
    minute = dt.minute
    # Zaokrąglenie w dół do najbliższych 10 minut
    rounded_minute = (minute // 10) * 10
    return dt.replace(minute=rounded_minute, second=0, microsecond=0)


def log_update_error(last_update_time_rounded, description, error_message, start_time):
    try:
        connection = connect_to_postgresql(
            'matterhorn')  # Zmienione na PostgreSQL
        cursor = connection.cursor()
        full_description = f"{description} (Czas aktualizacji: {start_time})"
        cursor.execute(
            "INSERT INTO update_log (last_update, description, data_items, data_inventory) VALUES (%s, %s, %s, %s)",
            (last_update_time_rounded, full_description,
             json.dumps([]), json.dumps([]))
        )
        connection.commit()
        cursor.close()
        connection.close()
        print(f"[INFO] Zapisano błąd aktualizacji: {error_message}")
    except Exception as e:
        print(f"[ERROR] Nie udało się zapisać błędu aktualizacji: {e}")


def update_inventory_v3():
    logger.info("Rozpoczynam aktualizację stanów magazynowych.")
    # Zapisz czas rozpoczęcia aktualizacji
    start_time = round_down_to_10_minutes(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    base_url_items = "https://matterhorn.pl/B2BAPI/ITEMS/"
    base_url_inventory = "https://matterhorn.pl/B2BAPI/ITEMS/INVENTORY/"
    last_update_time = get_last_update_time()
    logger.info(f"Ostatnia aktualizacja: {last_update_time}")
    last_update_time_rounded = last_update_time[:-2] + "00"
    encoded_time = urllib.parse.quote(last_update_time_rounded.split(" ")[1])
    update_date = last_update_time_rounded.split(" ")[0]
    page = 1
    total_data_length = 0
    total_data_length_inventory = 0
    total_data_items = []
    total_data_inventory = []

    while True:
        # Budowanie URL do pobrania danych z API
        b_url = f"{base_url_items}?page={page}&last_update={update_date}%20{encoded_time}&limit=1000"
        i_url = f"{base_url_inventory}?page={page}&last_update={update_date}%20{encoded_time}&limit=1000"

        logger.info(f"PAGE={page} URL API ITEMS: {b_url}, URL API INVENTORY: {i_url}")
        attempt = 1
        max_attempts = 3
        connection = None

        while attempt <= max_attempts:
            try:
                logger.info(f"Próba {attempt}/{max_attempts} pobrania danych z API.")
                response_items = requests.get(b_url, headers=headersMatterhorn, timeout=120)
                time.sleep(2)
                response_inventory = requests.get(i_url, headers=headersMatterhorn, timeout=120)
                logger.info(f"Status odpowiedzi API: {response_items.status_code} i {response_inventory.status_code}")
                
                # Dodajemy logi dla treści odpowiedzi
                logger.debug(f"Treść odpowiedzi ITEMS: {response_items.text[:500]}")
                logger.debug(f"Treść odpowiedzi INVENTORY: {response_inventory.text[:500]}")

                if response_items.status_code == 200 and response_inventory.status_code == 200:
                    logger.info("Pomyślnie pobrano dane z API.")
                    if response_items.text and response_inventory.text:
                        try:
                            data_items = response_items.json()          # /ITEMS
                            data_inventory = response_inventory.json()  # /INVENTORY
                            logger.info(f"Liczba rekordów w odpowiedzi: ITEMS-{len(data_items)}, INVENTORY-{len(data_inventory)}")
                        except ValueError as e:
                            logger.error(f"Błąd konwersji danych z API: {e}")
                            if attempt < max_attempts:
                                logger.info(f"Ponawiam próbę {attempt + 1}/{max_attempts} po 15 sekundach...")
                                time.sleep(15)
                                attempt += 1
                                continue
                            else:
                                logger.error("Osiągnięto maksymalną liczbę prób. Zapisuję błąd i kończę działanie.")
                                log_update_error(last_update_time_rounded, "Błąd konwersji danych z API", str(e), start_time)
                                return False
                    else:
                        logger.error("Odpowiedź API jest pusta.")
                        log_update_error(last_update_time_rounded, "Pusta odpowiedź API", "Odpowiedź API jest pusta.", start_time)
                        return False

                    # Liczenie pobranych rekordów
                    data_length = len(data_items)
                    data_length_inventory = len(data_inventory)
                    total_data_length += data_length
                    total_data_length_inventory += data_length_inventory
                    total_data_items.extend(data_items)
                    total_data_inventory.extend(data_inventory)

                    logger.info(f"Liczba rekordów w odpowiedzi: ITEMS-{data_length} INVENTORY-{data_length_inventory}")
                    time.sleep(1)

                    # Warunek zakończenia pętli, gdy brak nowych danych
                    if data_length == 0 and data_length_inventory == 0:
                        logger.info("Brak nowych danych do przetworzenia.")
                        break

                    # Połączenie z bazą danych
                    connection = connect_to_postgresql('matterhorn')
                    logger.info("Połączono z bazą danych.")
                    time.sleep(1)
                    cursor = connection.cursor()

                    # Iteracja po danych z API ITEMS
                    logger.info(f"Rozpoczynam przetwarzanie {len(data_items)} produktów z API ITEMS")
                    for item in data_items:
                        if not item:
                            logger.warning("Pusty element w danych ITEMS. Pomijanie.")
                            continue

                        # Pobieranie informacji o produkcie
                        id = item.get("id")  # ID produktu
                        active = item.get("active")  # false/true
                        new_collection = item.get("new_collection")  # Y/N
                        color = item.get("color")  # Kolor
                        stock_total = item.get("stock_total")  # Stock total
                        product_in_set = item.get("products_in_set", [])
                        if product_in_set is None:
                            product_in_set = []
                        other_colors = item.get("other_colors", [])
                        if other_colors is None:
                            other_colors = []
                        price = item["prices"].get("PLN", None)

                        logger.info(f"Przetwarzam produkt ID={id}")
                        logger.info(f"Szczegóły produktu: active={active}, new_collection={new_collection}, color={color}, stock_total={stock_total}, price={price}")

                        # Aktualizacja tabeli products
                        update_products_query = """
                        UPDATE products 
                        SET active = %s,
                            new_collection = %s,
                            price = %s,
                            color = %s,
                            stock_total = %s
                        WHERE id = %s
                        """
                        try:
                            cursor.execute(update_products_query, (active, new_collection, price, color, stock_total, id))
                            logger.info(f"Zaktualizowano produkt ID={id} w tabeli products")
                        except Exception as e:
                            logger.error(f"Błąd podczas aktualizacji produktu ID={id}: {e}")
                            continue

                        # Dodawanie powiązań zestawów
                        update_product_in_set_query = """
                        INSERT INTO product_in_set (product_id, set_product_id)
                        VALUES (%s, %s)
                        ON CONFLICT (product_id, set_product_id) DO NOTHING
                        """

                        for set_pid in product_in_set:
                            # pomijaj, gdy to ten sam produkt
                            if set_pid == id:
                                continue

                            logger.info(f"Przetwarzam powiązanie zestawu: product_id={id}, set_product_id={set_pid}")

                            # Sprawdzenie istnienia `id` w tabeli `products`
                            cursor.execute("SELECT 1 FROM products WHERE id = %s", (id,))

                            if not cursor.fetchone():
                                # Jeśli `product_id` nie istnieje, dodaj placeholder
                                cursor.execute("INSERT INTO products (id, name) VALUES (%s, %s)", (id, "Placeholder Name"))
                                logger.info(f"Dodano placeholder dla produktu o ID={id}")

                            # Sprawdzenie istnienia `set_pid` w tabeli `products`
                            cursor.execute("SELECT 1 FROM products WHERE id = %s", (set_pid,))
                            if not cursor.fetchone():
                                # Jeśli `set_product_id` nie istnieje, dodaj placeholder
                                cursor.execute("INSERT INTO products (id, name) VALUES (%s, %s)", (set_pid, "Placeholder Name"))
                                logger.info(f"Dodano placeholder dla produktu o ID={set_pid}")
                            
                            try:
                                # Wstawienie do tabeli `product_in_set` tylko w jednym kierunku
                                cursor.execute(update_product_in_set_query, (id, set_pid))
                                logger.info(f"Dodano powiązanie zestawu: product_id={id}, set_product_id={set_pid}")
                            except Exception as e:
                                logger.error(f"Błąd podczas dodawania powiązania zestawu: {e}")
                                continue

                        # Dodawanie powiązań kolorów
                        update_other_colors_query = """
                        INSERT INTO other_colors (product_id, color_product_id)
                        VALUES (%s, %s)
                        ON CONFLICT (product_id, color_product_id) DO NOTHING
                        """

                        for color_pid in other_colors:
                            # pomijaj, gdy to ten sam produkt
                            if color_pid == id:
                                continue

                            logger.info(f"Przetwarzam powiązanie koloru: product_id={id}, color_product_id={color_pid}")

                            # sprawdzanie istnienia "id" w tabeli "products"
                            cursor.execute("SELECT 1 FROM products WHERE id = %s", (id,))

                            if not cursor.fetchone():
                                # Jeśli "product_id" nie istnieje, dodaj rekord z "id" i nazwą "Placeholder Name"
                                cursor.execute("INSERT INTO products (id, name) VALUES (%s, %s)", (id, "Placeholder Name"))
                                logger.info(f"Dodano placeholder dla produktu o ID={id}")

                            # sprawdzanie istnienia color_pid w tabeli products
                            cursor.execute("SELECT 1 FROM products WHERE id = %s", (color_pid,))
                            if not cursor.fetchone():
                                # jeśli 'color_product_id" nie istnieje dodaj placeholder
                                cursor.execute("INSERT INTO products (id, name) VALUES (%s, %s)", (color_pid, "Placeholder Name"))
                                logger.info(f"Dodano placeholder dla produktu o ID={color_pid}")

                            try:
                                cursor.execute(update_other_colors_query, (id, color_pid))
                                logger.info(f"Dodano powiązanie koloru: product_id={id}, color_product_id={color_pid}")
                            except Exception as e:
                                logger.error(f"Błąd podczas dodawania powiązania koloru: {e}")
                                continue

                        # Commit po każdym produkcie
                        try:
                            connection.commit()
                            logger.info(f"Zatwierdzono zmiany dla produktu ID={id}")
                        except Exception as e:
                            logger.error(f"Błąd podczas zatwierdzania zmian dla produktu ID={id}: {e}")
                            connection.rollback()
                            continue

                    logger.info("Zakończono przetwarzanie produktów z API ITEMS")

                    # Iteracja po danych z API INVENTORY
                    for item in data_inventory:
                        inventory = item.get("inventory", [])
                        # Jeśli 'inventory' nie jest listą pobierz dane z bazy
                        if not isinstance(inventory, list):
                            logger.warning(f"Nieprawidłowa wartość inventory dla ID={item.get('id', 'Brak')}. Ustawianie stock=0 dla wszystkich variant_uid.")
                            inventory = []

                            # Pobieranie wariantów z bazy danych
                            cursor.execute("SELECT variant_uid FROM variants WHERE product_id = %s", (item['id'],))
                            result = cursor.fetchall()

                            # Pominięcie rekordu, jeśli nie znaleziono wariantów
                            if not result:
                                logger.warning(f"Brak wariantów dla produktu ID={item['id']}. Pomijam.")
                                continue

                            # dodanie wariantów z zerowym stanem magazynowym
                            for variant_uid in result:
                                inventory.append({"variant_uid": variant_uid[0], "stock": 0})

                        for variant in inventory:
                            # Sprawdzenie, czy 'variant_uid' istnieje w danych i czy jego wartość jest prawidłowa
                            if 'variant_uid' not in variant or not isinstance(variant['variant_uid'], (int, str)):
                                logger.warning(f"Pomijam rekord bez prawidłowego 'variant_uid' w inventory dla produktu ID={item['id']}")
                                continue  # Pominięcie rekordu

                            # Próba konwersji na int, jeśli się nie powiedzie, pominięcie rekordu
                            try:
                                variant_uid = int(variant["variant_uid"])
                            except ValueError:
                                logger.error(f"Nieprawidłowy format 'variant_uid' dla produktu ID={item['id']}. Pomijam.")
                                continue

                            stock = int(variant["stock"], 0)
                            name = str(variant["variant_name"]).replace(" ", "")
                            max_processing_time = int(variant.get("max_processing_time", 0))
                            ean = str(variant.get("ean", ""))
                            product_id = int(item["id"])

                            logger.info(f"Przetwarzanie wariantu UID={variant_uid}, Stock={stock}, Name={name}, Ean={ean}")
                            
                            # upewnienie się, że rekord istnieje w tabeli products
                            cursor.execute("SELECT 1 FROM products WHERE id = %s", (product_id,))

                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO products (id, name) VALUES (%s, %s)", (product_id, "Placeholder Name"))
                                logger.info(f"Dodano placeholder dla produktu o ID={product_id}")
                            
                            # Sprawdzanie czy rekord istnieje
                            cursor.execute("SELECT stock FROM variants WHERE variant_uid = %s", (variant_uid,))
                            record = cursor.fetchone()

                            if record:
                                # Aktualizacja istniejącego rekordu w tabeli variants
                                update_query = """
                                UPDATE variants
                                SET stock = %s,
                                    name = COALESCE(name, %s),
                                    ean = %s,
                                    max_processing_time = %s,
                                    product_id = %s
                                WHERE variant_uid = %s    
                                """
                                cursor.execute(update_query, (stock, name, ean, max_processing_time, product_id, variant_uid))
                            else:
                                # Dodanie nowego rekordu
                                insert_query = """
                                INSERT INTO variants (variant_uid, stock, max_processing_time, name, ean, product_id)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """
                                cursor.execute(insert_query, (variant_uid, stock, max_processing_time, name, ean, product_id))

                            # Commit po każdej iteracji, aby uniknąć utraty danych w przypadku awarii
                            connection.commit()

                    # Zatwierdzanie zmian w bazie
                    if connection:
                        try:
                            connection.commit()
                            logger.info("Wszystkie zmiany zostały zatwierdzone.")
                        except Exception as e:
                            logger.error(f"Błąd podczas zatwierdzania zmian: {e}")
                        finally:
                            cursor.close()
                            connection.close()
                    else:
                        logger.error("Brak połączenia z bazą danych.")

                    # Po zakończeniu iteracji zwiększ page
                    page += 1
                    time.sleep(1)  # Zachowano opóźnienie po każdej iteracji
                    break

            except ValueError as e:
                logger.error(f"Wystąpił błąd konwersji danych: {e}")
                logger.error(f"Nie udało się pobrać danych z API. Status: {response_items.status_code} i {response_inventory.status_code}")
                log_update_error(last_update_time_rounded, "Błąd konwersji danych", str(e), start_time)
            except Exception as e:
                logger.error(f"Wystąpił błąd: {e}")
                log_update_error(last_update_time_rounded, "Błąd podczas aktualizacji", str(e), start_time)

        # Jeśli brak danych, przerwij pętlę
        if data_length == 0 and data_length_inventory == 0:
            break

    # Ostateczne zapisanie informacji o aktualizacji
    update_last_update_time(start_time, total_data_length, total_data_length_inventory, total_data_items, total_data_inventory)
    logger.info("Aktualizacja zakończona.")
    return


def update_last_update_time(start_time, total_data_length, total_data_length_inventory, total_data_items, total_data_inventory):
    try:
        connection = connect_to_postgresql('matterhorn')
        cursor = connection.cursor()
        description = f"Zaktualizowano rekordów: {total_data_length}, {total_data_length_inventory}"
        # Serializacja danych JSON
        data_item_json = json.dumps(total_data_items)
        data_inventory_json = json.dumps(total_data_inventory)
        cursor.execute("INSERT INTO update_log (last_update, description, data_items, data_inventory) VALUES (%s, %s, %s, %s)", (start_time, description, data_item_json, data_inventory_json))
        connection.commit()
        cursor.close()
        connection.close()
        print("[INFO] Zapisano czas ostatniej aktualizacji.")
    except Exception as e:
        print(f"[ERROR] Nie udało się zapisać czasu ostatniej aktualizacji: {e}")


def clean_update_log():
    try:
        # Zmień na funkcję połączenia z PostgreSQL
        connection = connect_to_postgresql('matterhorn')
        cursor = connection.cursor()

        # usuwanie rekordów starszych niż 10 dni
        delete_query = """
        DELETE FROM update_log
        WHERE last_update < NOW() - INTERVAL '10 days'
        """
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount

        connection.commit()
        print(f"[INFO] Usunięto {deleted_count} rekordów starszych niż 10 dni.")

        cursor.close()
        connection.close()

        return f"Usunięto {deleted_count} rekordów starszych niż 10 dni."
    except Exception as e:
        print(f"Nie udało się usunąć rekordów starszych niż 10 dni: {e}")
        return f"Nie udało się usunąć rekordów starszych niż 10 dni: {e}"


def add_new_product_to_matterhorn(destination_cursor, source_cursor, product, request):
    destination_cursor.execute("SELECT id FROM brands WHERE brand_lower = %s", (product.brand.lower(),))
    brand_result = destination_cursor.fetchone()
    if not brand_result:
        messages.error(request, f"Brak marki {product.brand} dla {product.name}")
        return None
    brand_id = brand_result[0]

    with transaction.atomic(using='MasterProductDatabase'):
        destination_cursor.execute("INSERT INTO products (name, description, brand_id) VALUES (%s, %s, %s) RETURNING id",
            (product.name, product.description, brand_id))
        new_product_id = destination_cursor.fetchone()[0]
        source_cursor.execute("UPDATE products SET mapped_product_id = %s WHERE id = %s", (new_product_id, product.id))
        connections['matterhorn'].commit()
        messages.success(request, f"Dodano {product.name} jako nowy produkt z ID {new_product_id}.")

    source_cursor.execute(
        "SELECT color, price FROM products WHERE id = %s", (product.id,))
    product_color, product_price = source_cursor.fetchone() or (None, 0)

    if not product_color:
        messages.error(request, f"Brak koloru dla {product.name}. Pomijam.")
        return None

    # Kolory
    destination_cursor.execute(
        "SELECT id FROM colors WHERE name = %s", (product_color,))
    color_result = destination_cursor.fetchone()
    color_id = color_result[0] if color_result else None
    if not color_id:
        messages.error(request, f"Kolor '{product_color}' nie istnieje.")
        return None

    # Warianty
    source_cursor.execute(
        "SELECT name, stock, ean, variant_uid FROM variants WHERE product_id = %s", (product.id,))
    variants = source_cursor.fetchall()
    for size_name, stock, ean, variant_uid in variants:
        destination_cursor.execute(
            "SELECT id FROM sizes WHERE name = %s", (size_name,))
        size_result = destination_cursor.fetchone()
        size_id = size_result[0] if size_result else None
        if not size_id:
            messages.error(request, f"Brak rozmiaru '{size_name}' w bazie.")
            continue

        with transaction.atomic(using='MasterProductDatabase'):
            destination_cursor.execute(
                "SELECT variant_id FROM product_variants WHERE variant_uid = %s AND source_id = %s",
                (variant_uid, 2))
            variant_result = destination_cursor.fetchone()
            if variant_result:
                variant_id = variant_result[0]
            else:
                destination_cursor.execute(
                    "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                variant_id = destination_cursor.fetchone()[0]
                destination_cursor.execute("""
                    INSERT INTO product_variants (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                           (variant_id, new_product_id, color_id, size_id, ean, variant_uid, 2))

            destination_cursor.execute("""
                INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency)
                VALUES (%s, %s, %s, %s, 'PLN')
                ON CONFLICT (variant_id, source_id) DO UPDATE SET
                stock = EXCLUDED.stock,
                price = EXCLUDED.price
            """, (variant_id, 2, stock, product_price))

            source_cursor.execute("""
                UPDATE variants
                SET mapped_variant_id = %s
                WHERE variant_uid = %s
                """, (variant_id, variant_uid))

            source_cursor.execute(
                "UPDATE variants SET mapped_variant_id = %s WHERE variant_uid = %s", (variant_id, variant_uid))
            connections['matterhorn'].commit()

        messages.success(
            request, f"Wariant '{size_name}/{product_color}' zaktualizowany/dodany.")


def export_to_products(modeladmin, request, queryset):
    """
    Eksportuje zaznaczone produkty do products, dodając warianty (rozmiar x kolor x stock x cena).
    """
    print("Function export_to_products called")

    if 'manual_confirm' in request.GET:
        product_id = request.GET.get('product_id')
        confirmed_product_id = request.GET.get('confirmed_product_id')
        referrer = request.GET.get(
            'referrer', request.META.get('HTTP_REFERER', '/admin/'))
        print(
            f"Product ID: {product_id}, Confirmed Product ID: {confirmed_product_id}")

        if confirmed_product_id and product_id:
            try:
                with connections['matterhorn'].cursor() as source_cursor:
                    source_cursor.execute(
                        "UPDATE products SET mapped_product_id = %s WHERE id = %s",
                        (confirmed_product_id, product_id)
                    )
                    connections['matterhorn'].commit()
                    print(
                        f"Updated product {product_id} with mapped_product_id {confirmed_product_id}")
                    messages.success(
                        request, f"Produkt {product_id} przypisany do ID {confirmed_product_id}.")
            except Exception as e:
                print(f"Error updating mapped_product_id: {e}")
                messages.error(request, f"Błąd podczas aktualizacji: {e}")

            # Dodaj logikę eksportu wariantów poniżej:
            with connections['MasterProductDatabase'].cursor() as destination_cursor, \
                    connections['matterhorn'].cursor() as source_cursor:

                source_cursor.execute(
                    "SELECT color, price FROM products WHERE id = %s", (product_id,))
                color_result = source_cursor.fetchone()
                product_color, product_price = color_result if color_result else (
                    None, 0)

                if not product_color:
                    messages.error(
                        request, f"Brak koloru dla produktu {product.name}. Pomijam.")

                else:
                    destination_cursor.execute(
                        "SELECT id FROM colors WHERE name = %s", (product_color,))
                    color_id = destination_cursor.fetchone()[0]

                    source_cursor.execute(
                        "SELECT name, stock, ean, variant_uid FROM variants WHERE product_id = %s", (product_id,))
                    variants = source_cursor.fetchall()

                    for size_name, stock, ean, variant_uid in variants:
                        destination_cursor.execute(
                            "SELECT id FROM sizes WHERE name = %s", (size_name,))
                        size_id = destination_cursor.fetchone()[0]

                        with transaction.atomic(using='MasterProductDatabase'):
                            destination_cursor.execute(
                                "SELECT variant_id FROM product_variants WHERE variant_uid = %s AND source_id = %s",
                                (variant_uid, 2)
                            )
                            variant_result = destination_cursor.fetchone()

                            if variant_result:
                                variant_id = variant_result[0]
                            else:
                                destination_cursor.execute(
                                    "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                                variant_id = destination_cursor.fetchone()[0]

                                destination_cursor.execute("""
                                    INSERT INTO product_variants (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                                           (variant_id, confirmed_product_id, color_id, size_id, ean, variant_uid, 2))

                            destination_cursor.execute("""
                                INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency)
                                VALUES (%s, %s, %s, %s, 'PLN')
                                ON DUPLICATE KEY UPDATE stock=VALUES(stock), price=VALUES(price)
                            """, (variant_id, 2, stock, product_price))

                            source_cursor.execute(
                                "UPDATE variants SET mapped_variant_id = %s WHERE variant_uid = %s",
                                (variant_id, variant_uid)
                            )
                            connections['matterhorn'].commit()

                        messages.success(
                            request, f"Wariant '{size_name}/{product_color}' zaktualizowany/dodany.")

        return redirect(referrer)

    try:
        with connections['MasterProductDatabase'].cursor() as destination_cursor, connections['matterhorn'].cursor() as source_cursor:

            for product in queryset:
                new_product_id = product.mapped_product_id

                # 🔄 Sprawdzanie powiązanych produktów z kolorem
                if not new_product_id:
                    for other_color in product.other_colors.all():
                        if other_color.color_product.mapped_product_id and other_color.color_product.id != product.id:
                            new_product_id = other_color.color_product.mapped_product_id
                            source_cursor.execute(
                                "UPDATE products SET mapped_product_id = %s WHERE id = %s", (new_product_id, product.id))
                            connections['matterhorn'].commit()
                            messages.info(
                                request, f"{product.name} używa ID {new_product_id} z {other_color.color_product.name}.")

                            source_cursor.execute(
                                "SELECT color, price FROM products WHERE id = %s", (product.id,))
                            product_color, product_price = source_cursor.fetchone() or (None, 0)

                            if not product_color:
                                messages.error(
                                    request, f"Brak koloru dla {product.name}. Pomijam.")
                                return None

                            # Kolory
                            destination_cursor.execute(
                                "SELECT id FROM colors WHERE name = %s", (product_color,))
                            color_result = destination_cursor.fetchone()
                            color_id = color_result[0] if color_result else None
                            if not color_id:
                                messages.error(
                                    request, f"Kolor '{product_color}' nie istnieje.")
                                continue

                            # Warianty
                            source_cursor.execute(
                                "SELECT name, stock, ean, variant_uid FROM variants WHERE product_id = %s", (product.id,))
                            variants = source_cursor.fetchall()
                            for size_name, stock, ean, variant_uid in variants:
                                destination_cursor.execute(
                                    "SELECT id FROM sizes WHERE name = %s", (size_name,))
                                size_result = destination_cursor.fetchone()
                                size_id = size_result[0] if size_result else None
                                if not size_id:
                                    messages.error(
                                        request, f"Brak rozmiaru '{size_name}' w bazie.")
                                    continue

                                with transaction.atomic(using='MasterProductDatabase'):
                                    destination_cursor.execute(
                                        "SELECT variant_id FROM product_variants WHERE variant_uid = %s AND source_id = %s",
                                        (variant_uid, 2))
                                    variant_result = destination_cursor.fetchone()
                                    if variant_result:
                                        variant_id = variant_result[0]
                                    else:
                                        destination_cursor.execute(
                                            "SELECT COALESCE(MAX(variant_id), 0) + 1 FROM product_variants")
                                        variant_id = destination_cursor.fetchone()[
                                            0]
                                        destination_cursor.execute("""
                                            INSERT INTO product_variants (variant_id, product_id, color_id, size_id, ean, variant_uid, source_id)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                                                   (variant_id, new_product_id, color_id, size_id, ean, variant_uid, 2))

                                    destination_cursor.execute("""
                                        INSERT INTO stock_and_prices (variant_id, source_id, stock, price, currency)
                                        VALUES (%s, %s, %s, %s, 'PLN')
                                        ON CONFLICT (variant_id, source_id) DO UPDATE SET
                                        stock = EXCLUDED.stock, price = EXCLUDED.price
                                    """, (variant_id, 2, stock, product_price))

                                    source_cursor.execute("""
                                        UPDATE variants
                                        SET mapped_variant_id = %s
                                        WHERE variant_uid = %s
                                        """, (variant_id, variant_uid))

                                    source_cursor.execute(
                                        "UPDATE variants SET mapped_variant_id = %s WHERE variant_uid = %s", (variant_id, variant_uid))
                                    connections['matterhorn'].commit()

                                messages.success(
                                    request, f"Wariant '{size_name}/{product_color}' zaktualizowany/dodany.")
                            break
                # 🔍 Fuzzy dopasowanie
                if not new_product_id:
                    destination_cursor.execute("""
                        SELECT id, name FROM products 
                        WHERE brand_id = (SELECT id FROM brands WHERE brand_lower = %s)
                    """, (product.brand.lower(),))

                    existing_products = {row[1]: row[0]
                                         for row in destination_cursor.fetchall()}

                    # Sprawdzenie, czy nazwa produktu docelowego zawiera się w nazwie nowego produktu (podciąg)
                    substring_match = next(
                        ((existing_name, existing_id) for existing_name, existing_id in existing_products.items(
                        ) if existing_name.lower() in product.name.lower()),
                        None
                    )

                    if substring_match:
                        existing_name, existing_id = substring_match
                        new_product_id = existing_id
                        source_cursor.execute(
                            "UPDATE products SET mapped_product_id = %s WHERE id = %s",
                            (new_product_id, product.id)
                        )
                        connections['matterhorn'].commit()
                        messages.info(
                            request, f"{product.name} automatycznie dopasowano (zgodność podciągu) do {existing_name}.")
                    else:
                        # Jeżeli nie było podciągu, kontynuuj fuzzy matching
                        best_matches = process.extract(
                            product.name, existing_products.keys(), scorer=fuzz.ratio, limit=5)

                        if best_matches:
                            best_match, best_score, _ = best_matches[0]
                            if best_score > 99:
                                new_product_id = existing_products[best_match]
                                source_cursor.execute(
                                    "UPDATE products SET mapped_product_id = %s WHERE id = %s",
                                    (new_product_id, product.id)
                                )
                                connections['matterhorn'].commit()
                                messages.info(
                                    request, f"{product.name} dopasowano do {best_match} (score: {best_score}).")

                            elif best_score > 50:
                                return render(request, 'admin/confirm_product.html', {
                                    'product': product,
                                    'matches': best_matches,
                                    'existing_products': existing_products,
                                    'referrer': request.get_full_path()
                                })

                # 🆕 Utworzenie produktu, jeśli nadal brak ID
                if not new_product_id:
                    new_product_id = add_new_product_to_matterhorn(
                        destination_cursor, source_cursor, product, request)
                    if not new_product_id:
                        continue
        messages.success(
            request, f"Eksport zakończony dla {queryset.count()} produktów")
    except Exception as e:
        messages.error(request, f"Błąd eksportu: {e}")

