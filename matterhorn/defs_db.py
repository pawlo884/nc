import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv


# Połączenie z bazą danych
def connect_to_postgresql(db_key):

    try:
        is_production = os.getenv("DJANGO_SETTINGS_MODULE") == 'nc.settings.prod'

        env_file = '.env.prod' if is_production else '.env.dev'

        load_dotenv(env_file)

        db_name = os.getenv("MATTERHORN_DB_NAME")
        db_user = os.getenv("MATTERHORN_DB_USER")
        db_password = os.getenv("MATTERHORN_DB_PASSWORD")
        db_host = os.getenv("MATTERHORN_DB_HOST")
        db_port = os.getenv("MATTERHORN_DB_PORT")

        if not all([db_name, db_user, db_password, db_host, db_port]):
            raise ValueError(f"Brak wymaganych zmiennych środowiskowych w pliku {env_file}")

        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port

        )
        print(f"Połączono z bazą danych {db_name} na hoście {db_host} (środowisko: {'produkcja' if is_production else 'development'})")
        return conn
        
    except Exception as e:
        print(f"Błąd podczas łączenia z bazą danych: {e}")
        raise  
  
# Tworzenie tabel jeśli nie istnieją
def create_tables_if_not_exist(conn):
    cursor = conn.cursor()

    # Create products table if it doesn't exist
    create_products_table_query = '''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            active TEXT,
            name VARCHAR(255),
            name_without_number VARCHAR(255),
            description TEXT,
            creation_date TEXT,
            color VARCHAR(50),
            category_name VARCHAR(255),
            category_id INT,
            category_path TEXT,
            brand_id INT,
            brand VARCHAR(255),
            stock_total INT,
            url TEXT,
            new_collection TEXT,
            size_table TEXT,
            weight INT,
            size_table_txt TEXT,
            size_table_html TEXT,
            price NUMERIC(10, 2),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''

    # Create images table if it doesn't exist
    create_images_table_query = '''
        CREATE TABLE IF NOT EXISTS images (
            image_id SERIAL PRIMARY KEY,
            image_path TEXT,
            product_id INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    '''

    # Create variants table if it doesn't exist
    create_variants_table_query = '''
        CREATE TABLE IF NOT EXISTS variants (
            variant_uid SERIAL PRIMARY KEY,
            name VARCHAR(50),
            stock INT,
            max_processing_time INT,
            ean VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            product_id INT,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    '''

    # Create other colors table if it doesn't exist
    create_other_colors_table_query = '''
        CREATE TABLE IF NOT EXISTS other_colors (
            id SERIAL PRIMARY KEY,
            product_id INT NOT NULL,
            color_product_id INT NOT NULL,
            UNIQUE (product_id, color_product_id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (color_product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    '''

    # Create product in set table if it doesn't exist
    create_product_in_set_table_query = '''
        CREATE TABLE IF NOT EXISTS product_in_set (
            id SERIAL PRIMARY KEY,
            product_id INT NOT NULL,
            set_product_id INT NOT NULL,
            UNIQUE (product_id, set_product_id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (set_product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    '''

    # Create update log table if it doesn't exist
    create_update_log_table_query = '''
        CREATE TABLE IF NOT EXISTS update_log (
            id SERIAL PRIMARY KEY,
            last_update TIMESTAMP,
            description TEXT,
            data_items TEXT,
            data_inventory TEXT
        )
    '''

    # Execute the table creation queries
    cursor.execute(create_products_table_query)
    cursor.execute(create_images_table_query)
    cursor.execute(create_variants_table_query)
    cursor.execute(create_other_colors_table_query)
    cursor.execute(create_product_in_set_table_query)
    cursor.execute(create_update_log_table_query)
    conn.commit()
    cursor.close()

def import_insert_item(conn, item, images_data, variants_data, other_colors, product_sets):
    cursor = conn.cursor()

    insert_product_query = '''
        INSERT INTO products (id, active, name, name_without_number, description, creation_date, color, category_name, category_id, category_path, brand_id, brand, stock_total, url, new_collection, size_table, weight, size_table_txt, size_table_html, price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            active = EXCLUDED.active,
            name = EXCLUDED.name,
            name_without_number = EXCLUDED.name_without_number,
            description = EXCLUDED.description,
            creation_date = EXCLUDED.creation_date,
            color = EXCLUDED.color,
            category_name = EXCLUDED.category_name,
            category_id = EXCLUDED.category_id,
            category_path = EXCLUDED.category_path,
            brand_id = EXCLUDED.brand_id,
            brand = EXCLUDED.brand,
            stock_total = EXCLUDED.stock_total,
            url = EXCLUDED.url,
            new_collection = EXCLUDED.new_collection,
            size_table = EXCLUDED.size_table,
            weight = EXCLUDED.weight,
            size_table_txt = EXCLUDED.size_table_txt,
            size_table_html = EXCLUDED.size_table_html,
            price = EXCLUDED.price
    '''

    insert_image_query = '''
        INSERT INTO images (image_id, image_path, product_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (image_id) DO UPDATE SET image_path = EXCLUDED.image_path
    '''

    insert_variants_query = '''
        INSERT INTO variants (variant_uid, name, stock, max_processing_time, ean, product_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (variant_uid) DO UPDATE SET
            name = EXCLUDED.name,
            stock = EXCLUDED.stock,
            max_processing_time = EXCLUDED.max_processing_time,
            ean = EXCLUDED.ean
    '''

    insert_other_colors_query = '''
        INSERT INTO other_colors (product_id, color_product_id)
        VALUES (%s, %s)
        ON CONFLICT (product_id, color_product_id) DO NOTHING
    '''

    insert_product_sets_query = '''
        INSERT INTO product_in_set (product_id, set_product_id)
        VALUES (%s, %s)
        ON CONFLICT (product_id, set_product_id) DO NOTHING
    '''

    insert_missing_product_query = '''
        INSERT INTO products (id, name)
        VALUES (%s, %s)
        ON CONFLICT (id) DO NOTHING
    '''

    try:
        cursor.execute(insert_product_query, item)
        cursor.executemany(insert_image_query, images_data)
        cursor.executemany(insert_variants_query, variants_data)

        for product_id, color_product_id in other_colors:
            if product_id != color_product_id:
                cursor.execute("SELECT 1 FROM products WHERE id = %s", (color_product_id,))
                if not cursor.fetchone():
                    cursor.execute(insert_missing_product_query, (color_product_id, "Placeholder Name"))
                cursor.execute(insert_other_colors_query, (product_id, color_product_id))

        for product_id, set_product_id in product_sets:
            if product_id != set_product_id:
                cursor.execute("SELECT 1 FROM products WHERE id = %s", (set_product_id,))
                if not cursor.fetchone():
                    cursor.execute(insert_missing_product_query, (set_product_id, "Placeholder Name"))
                cursor.execute(insert_product_sets_query, (product_id, set_product_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("Wystąpił błąd:", e)

    finally:
        cursor.close()