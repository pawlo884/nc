import mysql.connector
import psycopg2

# Ustawienia dla połączenia z bazą MySQL
mysql_config = {
    'user': 'm1380_pawlo884',
    'password': 'Relisys17',
    'host': 'mysql68.mydevil.net',
    'database': 'm1380_matterhorn'
}

# Ustawienia dla połączenia z bazą PostgreSQL
postgresql_config = {
    'dbname': 'zzz_matterhorn',
    'user': 'doadmin',
    'password': 'AVNS_7h22feiJEsbaRFL7B3i',
    'host': 'db-postgresql-fra1-18304-do-user-18661095-0.l.db.ondigitalocean.com',
    'port': '25060'
}

# Połączenie z bazą MySQL
mysql_conn = mysql.connector.connect(**mysql_config)
mysql_cursor = mysql_conn.cursor(dictionary=True)

# Połączenie z bazą PostgreSQL
postgresql_conn = psycopg2.connect(**postgresql_config)
postgresql_cursor = postgresql_conn.cursor()

try:
    # Sprawdzenie ostatniego ID w PostgreSQL, gdzie active IS NULL
    postgresql_cursor.execute("SELECT MIN(id) FROM products WHERE active IS NULL")
    last_id = postgresql_cursor.fetchone()[0] or 0

    # Pobranie nowych danych z MySQL, gdzie id > last_id i active IS NULL
    mysql_cursor.execute(
        "SELECT * FROM products WHERE id > %s",
        (last_id,)
    )
    products = mysql_cursor.fetchall()

    # Wstawianie danych do PostgreSQL
    insert_query = """
    INSERT INTO products (id, active, name, name_without_number, description, creation_date,
        color, category_name, category_id, category_path, brand_id, brand,
        stock_total, url, new_collection, size_table, weight, size_table_txt,
        size_table_html, price, timestamp, mapped_product_id, is_mapped, last_updated
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    for product in products:
        postgresql_cursor.execute(insert_query, (
            product.get('id'), 
            product.get('active'), 
            product.get('name'), 
            product.get('name_without_number'),
            product.get('description'), 
            product.get('creation_date'), 
            product.get('color'), 
            product.get('category_name'),
            product.get('category_id'), 
            product.get('category_path'), 
            product.get('brand_id'), 
            product.get('brand'),
            product.get('stock_total'), 
            product.get('url'), 
            product.get('new_collection'), 
            product.get('size_table'),
            product.get('weight'), 
            product.get('size_table_txt'), 
            product.get('size_table_html'), 
            product.get('price'),
            product.get('timestamp'), 
            product.get('mapped_product_id'), 
            bool(product.get('is_mapped')),
            product.get('last_updated')
        ))
        print(f"Inserted product ID: {product['id']}")

        # Zatwierdzenie zmian
        postgresql_conn.commit()

finally:
    # Zamknięcie połączeń
    mysql_cursor.close()
    mysql_conn.close()
    postgresql_cursor.close()
    postgresql_conn.close()