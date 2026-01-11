-- Skrypt do utworzenia tabeli iai_product_counter w istniejącej bazie danych MPD
-- Uruchom ten skrypt w bazie danych MPD, aby dodać tabelę licznika

-- Utwórz tabelę iai_product_counter
CREATE TABLE IF NOT EXISTS iai_product_counter (
    id INTEGER PRIMARY KEY DEFAULT 1,
    counter_value BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Inicjalizuj tabelę z wartością początkową
INSERT INTO iai_product_counter (id, counter_value) 
VALUES (1, 0) 
ON CONFLICT (id) DO NOTHING;

-- Ustaw aktualną wartość licznika na maksymalną wartość iai_product_id + 1
-- (jeśli tabela product_variants już istnieje i ma dane)
UPDATE iai_product_counter 
SET counter_value = COALESCE((SELECT MAX(iai_product_id) FROM product_variants), 0) + 1
WHERE id = 1;

-- Sprawdź aktualną wartość licznika
SELECT * FROM iai_product_counter;
