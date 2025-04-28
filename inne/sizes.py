import json
import os
import psycopg2
from dotenv import load_dotenv


def connect_to_postgresql():
    try:
        is_production = os.getenv("DJANGO_SETTINGS_MODULE") == 'nc.settings.prod'
        env_file = '.env.prod' if is_production else '.env.dev'
        load_dotenv(env_file)

        db_name = os.getenv("MPD_DB_NAME")
        db_user = os.getenv("MPD_DB_USER")
        db_password = os.getenv("MPD_DB_PASSWORD")
        db_host = os.getenv("MPD_DB_HOST")
        db_port = os.getenv("MPD_DB_PORT")

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

def fetch_existing_sizes(cursor):
    cursor.execute("SELECT name FROM sizes;")
    return {row[0] for row in cursor.fetchall()}

def create_sizes_list():
    return [
        "100B", "100C", "100D", "100E", "100F", "100G", "100H", "100I",
        "105B", "105C", "105D", "105E", "105F", "105G", "105H", "105I",
        "110B", "110C", "110D", "110E", "110F", "110G", "110H", "110I",
        "115B", "115C", "115D", "115E", "115F", "115G", "115H", "115I",
        "120B", "120C", "120D", "120E", "120F", "60B", "60C", "60D", "60E",
        "60F", "60G", "60H", "65AA", "65A", "65B", "65BB", "65C", "65D",
        "65E", "65F", "65G", "65H", "65I", "65J", "65K", "65L", "65M",
        "70AA", "70A", "70B", "70BB", "70C", "70D", "70DD", "70E", "70F",
        "70G", "70H", "70I", "70J", "70K", "70L", "70M", "75AA", "75A",
        "75B", "75C", "75D", "75DD", "75E", "75F", "75G", "75H", "75I",
        "75J", "75K", "75L", "75M", "80A", "80B", "80BB", "80C", "80D",
        "80E", "80F", "80G", "80H", "80I", "80J", "80K", "80L", "80M",
        "85A", "85B", "85C", "85D", "85E", "85F", "85G", "85H", "85I",
        "85J", "85K", "85L", "85M", "90A", "90B", "90C", "90D", "90E",
        "90F", "90G", "90H", "90I", "90J", "90K", "90L", "90M", "95A",
        "95B", "95C", "95D", "95E", "95F", "95G", "95H", "95I", "95J",
        "95K", "95L", "95M", "L", "M", "S", "uniwersalny", "XL", "2XL",
        "3XL", "4XL", "5XL", "XS", "36B", "36C", "38B", "38C", "38D", "38E", "40B", "40C", "40D", "40E", "42C", "42D", "42E", "44C", "44D", "46C",  
    ]

def insert_new_sizes(cursor, existing_sizes):
    sizes = create_sizes_list()
    for size in sizes:
        if size not in existing_sizes:
            cursor.execute("INSERT INTO sizes (name, category, unit, name_lower) VALUES (%s, %s, %s, %s);",
                           (size, 'underwear', 'EU', size.lower()))


def generate_sql_insert():
    sizes = create_sizes_list()
    sql_values = []

    for size in sizes:
        sql_values.append(f"('{size}', 'underwear', 'EU', '{size.lower()}')")
    
    sql_statement = "INSERT INTO sizes (name, category, unit, name_lower) VALUES " + ", ".join(sql_values) + " ON CONFLICT (name, category, unit) DO NOTHING" + ";" + "\n"
    sql_statement += "SELECT setval(pg_get_serial_sequence('sizes', 'id'), coalesce(max(id), 0) + 1, false) FROM sizes;"
    return sql_statement

def export_to_json(filename, data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Dane zapisane do {file_path}")

def save_sql_script(filename, script):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"Skrypt SQL zapisany do {file_path}")


if __name__ == "__main__":
    sizes = create_sizes_list()
    sizes_dict = {
        "sizes": [
            {"name": size, "category": "underwear", "unit": "EU", "name_lower": size.lower()}
            for size in sizes
        ]
    }
    export_to_json('sizes.json', sizes_dict)

    sql_insert_script = generate_sql_insert()
    save_sql_script('sizes.sql', sql_insert_script)
    
    conn = connect_to_postgresql()
    cursor = conn.cursor()

    try:
        existing_sizes = fetch_existing_sizes(cursor)
        insert_new_sizes(cursor, existing_sizes)
        conn.commit()
        print("Wstawianie zakończone.")
    except Exception as e:
        print(f"Błąd podczas operacji na bazie danych: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()