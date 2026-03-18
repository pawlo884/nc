import psycopg2
import os
from dotenv import load_dotenv


# Połączenie z bazą danych
def connect_to_postgresql(db_key):

    try:
        is_production = os.getenv(
            "DJANGO_SETTINGS_MODULE") == 'core.settings.prod'

        env_file = '.env.prod' if is_production else '.env.dev'

        load_dotenv(env_file)

        db_name = os.getenv("MPD_DB_NAME")
        db_user = os.getenv("MPD_DB_USER")
        db_password = os.getenv("MPD_DB_PASSWORD")
        db_host = os.getenv("MPD_DB_HOST")
        db_port = os.getenv("MPD_DB_PORT")

        if not all([db_name, db_user, db_password, db_host, db_port]):
            raise ValueError(
                f"Brak wymaganych zmiennych środowiskowych w pliku {env_file}")

        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port

        )
        print(
            f"Połączono z bazą danych {db_name} na hoście {db_host} (środowisko: {'produkcja' if is_production else 'development'})")
        return conn

    except Exception as e:
        print(f"Błąd podczas łączenia z bazą danych: {e}")
        raise

# Tworzenie tabel jeśli nie istnieją


def create_tables_if_not_exist(conn):
    cursor = conn.cursor()

    # Definicja tabel
    create_attributes_table_queries = """
        CREATE TABLE IF NOT EXISTS attributes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )
    """
    create_brands_table_queries = """
        CREATE TABLE IF NOT EXISTS brands (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255),
            logo_url TEXT,
            opis TEXT
        )
    """
    create_categories_table_queries = """
        CREATE TABLE IF NOT EXISTS categories (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            path TEXT,
            parent_id BIGINT,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """
    create_colors_table_queries = """
        CREATE TABLE IF NOT EXISTS colors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            hex_code VARCHAR(7),
            parent_id INT,
            FOREIGN KEY (parent_id) REFERENCES colors(id) ON DELETE SET NULL
        )
    """
    create_data_sources_table_queries = """
        CREATE TABLE IF NOT EXISTS data_sources (
            id SERIAL PRIMARY KEY,
            source_name VARCHAR(50) NOT NULL
        )
    """
    create_den_thickness_table_queries = """
        CREATE TABLE IF NOT EXISTS den_thickness (
            id SERIAL PRIMARY KEY,
            value INT NOT NULL UNIQUE
        )
    """
    create_product_attributes_table_queries = """
        CREATE TABLE IF NOT EXISTS product_attributes (
            id SERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            attribute_id INT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (attribute_id) REFERENCES attributes(id) ON DELETE CASCADE
        )
    """
    create_product_categories_table_queries = """
        CREATE TABLE IF NOT EXISTS product_categories (
            product_id BIGINT NOT NULL,
            category_id BIGINT NOT NULL,
            PRIMARY KEY (product_id, category_id),
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """
    create_product_den_table_queries = """
        CREATE TABLE IF NOT EXISTS product_den (
            id SERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            den_id INT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (den_id) REFERENCES den_thickness(id) ON DELETE CASCADE
        )
    """
    create_product_images_table_queries = """
        CREATE TABLE IF NOT EXISTS product_images (
            id BIGSERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            variant_id INT,
            iai_product_id INT,
            file_path VARCHAR(500) NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """
    create_product_seasons_table_queries = """
        CREATE TABLE IF NOT EXISTS product_seasons (
            id SERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            season_id INT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (season_id) REFERENCES season_categories(id) ON DELETE CASCADE
        )
    """
    create_product_set_items_table_queries = """
        CREATE TABLE IF NOT EXISTS product_set_items (
            id SERIAL PRIMARY KEY,
            set_id INT NOT NULL,
            product_id BIGINT NOT NULL,
            quantity INT DEFAULT 1,
            FOREIGN KEY (set_id) REFERENCES product_sets(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """
    create_product_sets_table_queries = """
        CREATE TABLE IF NOT EXISTS product_sets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    create_product_variants_table_queries = """
        CREATE TABLE IF NOT EXISTS product_variants (
            id SERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            variant_id INT NOT NULL,
            source_id INT NOT NULL DEFAULT 2,
            color_id INT,
            size_id BIGINT,
            ean VARCHAR(50),
            variant_uid INT,
            FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (size_id) REFERENCES sizes(id) ON DELETE CASCADE,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT,
            UNIQUE (variant_id, source_id)
        )
    """
    create_products_table_queries = """
        CREATE TABLE IF NOT EXISTS products (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            brand_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL
        )
    """
    create_season_categories_table_queries = """
        CREATE TABLE IF NOT EXISTS season_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE
        )
    """
    create_size_attributes_table_queries = """
        CREATE TABLE IF NOT EXISTS size_attributes (
            id SERIAL PRIMARY KEY,
            size_id BIGINT NOT NULL,
            attribute_name VARCHAR(50) NOT NULL,
            value DECIMAL(10,2) NOT NULL,
            unit VARCHAR(10) DEFAULT 'cm',
            FOREIGN KEY (size_id) REFERENCES sizes(id) ON DELETE CASCADE
        )
    """
    create_sizes_table_queries = """
        CREATE TABLE IF NOT EXISTS sizes (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            category VARCHAR(20) NOT NULL,
            unit VARCHAR(10) DEFAULT 'cm',
            name_lower VARCHAR(50) NOT NULL
        )
    """
    create_sources_table_queries = """
        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            location VARCHAR(500),
            type VARCHAR(20) NOT NULL
        )
    """
    create_stock_and_prices_table_queries = """
        CREATE TABLE IF NOT EXISTS stock_and_prices (
            id BIGSERIAL PRIMARY KEY,
            variant_id INT NOT NULL,
            source_id INT NOT NULL,
            stock INT DEFAULT 0,
            price DECIMAL(10,2),
            currency VARCHAR(10),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
            FOREIGN KEY (variant_id, source_id) REFERENCES product_variants_sources(variant_id, source_id) ON DELETE CASCADE
        )
    """

    create_fabric_component_table_queries = """
        CREATE TABLE IF NOT EXISTS fabric_component (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )
    """

    create_product_fabric_table_queries = """
        CREATE TABLE IF NOT EXISTS product_fabric (
            id SERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL,
            component_id INT NOT NULL,
            percentage SMALLINT NOT NULL CHECK (percentage > 0 AND percentage <= 100),
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES fabric_component(id) ON DELETE CASCADE,
            UNIQUE (product_id, component_id)
        )
    """

    # Funkcja sprawdzająca sumę procentów materiałów dla produktu
    create_check_percentage_function = """
        CREATE OR REPLACE FUNCTION check_product_fabric_percentage()
        RETURNS TRIGGER AS $$
        DECLARE
            total_percentage INTEGER;
        BEGIN
            -- Oblicz sumę procentów dla danego produktu
            SELECT COALESCE(SUM(percentage), 0) INTO total_percentage
            FROM product_fabric
            WHERE product_id = NEW.product_id;
            
            -- Sprawdź czy suma nie przekracza 100%
            IF total_percentage > 100 THEN
                RAISE EXCEPTION 'Suma procentów materiałów dla produktu % przekracza 100%% (aktualnie: %%)', 
                    NEW.product_id, total_percentage;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """

    # Trigger sprawdzający sumę procentów przed wstawieniem/aktualizacją
    create_percentage_check_trigger = """
        DROP TRIGGER IF EXISTS product_fabric_percentage_check ON product_fabric;
        CREATE TRIGGER product_fabric_percentage_check
            BEFORE INSERT OR UPDATE ON product_fabric
            FOR EACH ROW
            EXECUTE FUNCTION check_product_fabric_percentage();
    """

    # Execute the table creation queries
    cursor.execute(create_attributes_table_queries)
    cursor.execute(create_brands_table_queries)
    cursor.execute(create_categories_table_queries)
    cursor.execute(create_colors_table_queries)
    cursor.execute(create_data_sources_table_queries)
    cursor.execute(create_den_thickness_table_queries)
    cursor.execute(create_product_attributes_table_queries)
    cursor.execute(create_product_categories_table_queries)
    cursor.execute(create_product_den_table_queries)
    cursor.execute(create_product_images_table_queries)
    cursor.execute(create_product_seasons_table_queries)
    cursor.execute(create_product_set_items_table_queries)
    cursor.execute(create_product_sets_table_queries)
    cursor.execute(create_product_variants_table_queries)
    cursor.execute(create_products_table_queries)
    cursor.execute(create_season_categories_table_queries)
    cursor.execute(create_size_attributes_table_queries)
    cursor.execute(create_sizes_table_queries)
    cursor.execute(create_sources_table_queries)
    cursor.execute(create_stock_and_prices_table_queries)
    cursor.execute(create_fabric_component_table_queries)
    cursor.execute(create_product_fabric_table_queries)

    # Utwórz funkcję i trigger sprawdzający sumę procentów materiałów
    cursor.execute(create_check_percentage_function)
    cursor.execute(create_percentage_check_trigger)

    conn.commit()
    cursor.close()
