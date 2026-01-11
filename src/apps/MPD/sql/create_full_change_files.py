# Skrypt SQL do utworzenia tabeli full_change_files
# Tabela przechowuje informacje o wygenerowanych plikach full_change.xml

sql_content = """
-- Skrypt do utworzenia tabeli full_change_files
-- Tabela przechowuje informacje o wygenerowanych plikach full_change.xml

CREATE TABLE IF NOT EXISTS full_change_files (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    timestamp VARCHAR(50) NOT NULL, -- YYYY-MM-DDTHH-MM-SS
    created_at TIMESTAMP NOT NULL,
    bucket_url TEXT,
    local_path VARCHAR(500),
    file_size BIGINT DEFAULT 0,
    created_at_record TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indeksy dla lepszej wydajności
CREATE INDEX IF NOT EXISTS idx_full_change_files_created_at ON full_change_files(created_at);
CREATE INDEX IF NOT EXISTS idx_full_change_files_timestamp ON full_change_files(timestamp);
CREATE INDEX IF NOT EXISTS idx_full_change_files_filename ON full_change_files(filename);

-- Komentarze do tabeli i kolumn
COMMENT ON TABLE full_change_files IS 'Tabela przechowuje informacje o wygenerowanych plikach full_change.xml z datą w nazwie';
COMMENT ON COLUMN full_change_files.id IS 'Unikalny identyfikator rekordu';
COMMENT ON COLUMN full_change_files.filename IS 'Nazwa pliku (np. full_change2025-08-25T10-30-45.xml)';
COMMENT ON COLUMN full_change_files.timestamp IS 'Timestamp z nazwy pliku (YYYY-MM-DDTHH-MM-SS)';
COMMENT ON COLUMN full_change_files.created_at IS 'Data i czas utworzenia pliku';
COMMENT ON COLUMN full_change_files.bucket_url IS 'URL do pliku w buckecie S3/DO Spaces';
COMMENT ON COLUMN full_change_files.local_path IS 'Ścieżka do lokalnego pliku';
COMMENT ON COLUMN full_change_files.file_size IS 'Rozmiar pliku w bajtach';
COMMENT ON COLUMN full_change_files.created_at_record IS 'Data i czas utworzenia rekordu w bazie danych';
"""

