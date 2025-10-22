-- ============================================================================
-- Indexes dla optymalizacji synchronizacji stanów magazynowych MPD
-- ============================================================================
-- 
-- Te indexy są KRYTYCZNE dla wydajności taska update_stock_from_matterhorn1
-- Bez nich, query na updated_at będzie robić full table scan!
--
-- Wykonaj te komendy w bazie matterhorn1 (lub zzz_matterhorn1 dla dev)
-- ============================================================================

-- 1. Index na updated_at (podstawowy)
-- Używany przez główne query z time window
CREATE INDEX IF NOT EXISTS idx_productvariant_updated_at 
ON productvariant(updated_at);

-- 2. Composite index dla zmapowanych wariantów (zaawansowany)
-- Jeszcze szybsze query - filtruje is_mapped na poziomie indexu
CREATE INDEX IF NOT EXISTS idx_productvariant_mapped_updated 
ON productvariant(is_mapped, updated_at) 
WHERE is_mapped = true;

-- 3. Index na mapped_variant_uid (pomocniczy)
-- Przyspiesza lookup w MPD
CREATE INDEX IF NOT EXISTS idx_productvariant_mapped_uid 
ON productvariant(mapped_variant_uid) 
WHERE mapped_variant_uid IS NOT NULL;

-- 4. Composite index dla pełnego query (najbardziej optymalny)
-- Pokrywa wszystkie warunki z głównego query
CREATE INDEX IF NOT EXISTS idx_productvariant_sync_optimized 
ON productvariant(is_mapped, mapped_variant_uid, updated_at) 
WHERE is_mapped = true AND mapped_variant_uid IS NOT NULL;

-- ============================================================================
-- Sprawdź istniejące indexes
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'productvariant' 
AND schemaname = 'public'
ORDER BY indexname;

-- ============================================================================
-- Sprawdź rozmiar indexes
-- ============================================================================

SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_catalog.pg_stat_user_indexes
WHERE tablename = 'productvariant'
ORDER BY pg_relation_size(indexrelid) DESC;

-- ============================================================================
-- Test wydajności query (EXPLAIN ANALYZE)
-- ============================================================================

-- Test 1: Bez indexu (slow)
EXPLAIN ANALYZE
SELECT *
FROM productvariant
WHERE is_mapped = true
  AND mapped_variant_uid IS NOT NULL
  AND updated_at >= NOW() - INTERVAL '15 minutes';

-- Po utworzeniu indexów powyższe query powinno używać:
-- Index Scan using idx_productvariant_sync_optimized
-- Czas wykonania: <10ms (zamiast 100-1000ms)

-- ============================================================================
-- Vacuum i Analyze (po utworzeniu indexes)
-- ============================================================================

-- Odśwież statystyki PostgreSQL
ANALYZE productvariant;

-- Optymalizuj tabelę (opcjonalnie, jeśli masz czas)
VACUUM ANALYZE productvariant;

-- ============================================================================
-- Monitoring użycia indexes
-- ============================================================================

-- Sprawdź które indexes są używane
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'productvariant'
ORDER BY idx_scan DESC;

-- Jeśli idx_scan = 0, index nie jest używany (możesz go usunąć)
-- Jeśli idx_scan > 1000, index jest aktywnie używany (dobry znak!)

-- ============================================================================
-- Cleanup - Usuń nieużywane indexes (opcjonalnie)
-- ============================================================================

-- TYLKO jeśli masz pewność że nie są używane!
-- DROP INDEX IF EXISTS idx_productvariant_updated_at;
-- DROP INDEX IF EXISTS idx_productvariant_mapped_updated;
-- DROP INDEX IF EXISTS idx_productvariant_mapped_uid;

-- ============================================================================
-- Rekomendacje
-- ============================================================================

-- 1. Stwórz przynajmniej idx_productvariant_updated_at (minimum)
-- 2. Najlepiej stwórz idx_productvariant_sync_optimized (najbardziej optymalny)
-- 3. Po utworzeniu, uruchom ANALYZE productvariant
-- 4. Monitoruj użycie przez pg_stat_user_indexes
-- 5. Jeśli tabela jest duża (>1M rekordów), rozważ partycjonowanie po updated_at

-- ============================================================================
-- Pytania?
-- ============================================================================

-- Zobacz dokumentację: MPD_STOCK_SYNC_README.md
-- Quick start: MPD/QUICK_START_STOCK_SYNC.md
-- Changelog: MPD_STOCK_SYNC_CHANGELOG.md



