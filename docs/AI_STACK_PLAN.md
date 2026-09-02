# Plan: stack AI dla web_agent (LangChain + OpenRouter + LangSmith)

Dotyczy warstwy AI w `apps/web_agent` — wzbogacanie danych produktu
(nazwa / opis / krótki opis / atrybuty) przed wypełnieniem formularza MPD.

## Stan obecny (2026-09)

| Element | Stan |
| --- | --- |
| `AIProcessor` (`ai_processor.py`, ~2500 LOC) | **Aktywny domyślnie.** Bezpośredni OpenAI SDK, `api_type` = openai / huggingface, klucze OpenAI / Novita / HF. Rozgałęziony, trudny w utrzymaniu |
| `LangChainAIProcessor` (`langchain_ai_processor.py`) | **WIP, opt-in** przez `USE_LANGCHAIN_AI=1`. LangChain `ChatOpenAI` → OpenRouter, primary `moonshotai/kimi-k2-thinking` + fallback `openai/gpt-4o-mini` przez `.with_fallbacks()` |
| OpenRouter | Klucz w `.env.dev` (`OPENROUTER_API_KEY`). Używany tylko przez `LangChainAIProcessor`. Routing = primary→fallback dla **wszystkich** operacji tym samym modelem |
| LangSmith | Klucze w `.env.dev` (`LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=nc`). Ambient tracing każdego `ChatOpenAI.invoke()`, tagi `["web_agent","product-enrichment", <op>]` |
| Lokalny log wywołań | `_CallLogCallback` → `pop_call_log()` → `ProductProcessingLog.processing_data["_ai_pipeline"]` (który model, sukces/błąd, czas) |
| Prompty | Model `AIPrompt` w bazie, edytowalne w Django Admin, `is_active` + `render()` |
| `openai-agents` | W `requirements.txt`, **nieużywany** nigdzie w kodzie |

## Cel

1. **LangChain** jako jedyna warstwa AI (koniec z `AIProcessor` i ręcznym rozgałęzianiem po dostawcy).
2. **OpenRouter** = świadomy wybór i routing modelu **per zadanie** (nie jeden model do wszystkiego), z kontrolą kosztu / latencji / providera.
3. **LangSmith + observability** = śledzenie całego przebiegu automatyzacji (nie pojedynczego calla), koszt i jakość widoczne bez wchodzenia w kod.

---

## Fazy

### Faza 0 — domknięcie WIP

- [ ] scommitować `langchain_ai_processor.py` + `tasks.py` + `tests_langchain_ai_processor.py` + `requirements*`
- [ ] `USE_LANGCHAIN_AI` do `docs/env.sample.md` i `docs/env.test.sample.md` (+ opis)
- [ ] `LANGSMITH_*` i `OPENROUTER_API_KEY` do szablonów env (bez wartości)
- [ ] potwierdzić, że przy `USE_LANGCHAIN_AI=1` do klienta OpenRouter nie trafia `OPENAI_API_KEY` (jest już w diffie `tasks.py`)

### Faza 1 — LangChain domyślny

- [ ] testy parytetu: `LangChainAIProcessor` vs `AIProcessor` na tym samym wejściu dla name / description / short_description / attributes
- [ ] `USE_LANGCHAIN_AI=1` domyślnie w dev, potem prod (k3s env)
- [ ] okres przejściowy: legacy `AIProcessor` zostaje jako fallback za flagą
- [ ] po okresie przejściowym: usunąć `AIProcessor` + ścieżki huggingface / Novita + `OPENAI_API_KEY_NOVITA` / `HF_TOKEN` z env

### Faza 2 — OpenRouter: routing modeli per zadanie

- [ ] mapa `operacja → profil modelu`, np.:
  - `name` → tani, szybki (np. `openai/gpt-4o-mini` / `google/gemini-flash`)
  - `description` → mocny reasoning (np. `kimi-k2-thinking` / `anthropic/claude-*`)
  - `attributes` → tani + structured output
  - `short_description` → tani
- [ ] źródło konfiguracji: rozszerzyć `AIPrompt` o `model` / `model_profile` (edycja w adminie) **albo** `settings.AI_MODEL_ROUTING`
- [ ] per-model: `temperature`, `max_tokens`, `reasoning.effort` (hack dla kimi już jest — uogólnić)
- [ ] OpenRouter provider preferences (`extra_body={"provider": {...}}`) — kontrola kosztu / latencji / `data_collection`
- [ ] fallback per profil (nie jeden globalny) — `.with_fallbacks()` z listą z konfiguracji
- [ ] koszt per operacja z `usage` OpenRouter → `ProductProcessingLog`

### Faza 3 — Observability / śledzenie agentów

- [ ] LangSmith: `run_name` + metadata z `AutomationRun.id`, `brand_id`, `product_id` — jeden trace = jeden przebieg automatyzacji, nie pojedynczy call
- [ ] LangSmith dashboard (projekt `nc`): koszt, latencja, % fallbacku, błędy — per operacja i per model
- [ ] Django Admin: agregacja `_ai_pipeline` na poziomie `AutomationRun` (liczba calli, koszt, rozkład modeli, fallback rate)
- [ ] alert / sygnał gdy fallback rate > próg (primary pada) — kandydat do zmiany primary
- [ ] (rozważyć) LangSmith datasets + evaluators — regresja jakości przy edycji `AIPrompt` w adminie (dziś edycja promptu = zmiana bez pomiaru)

### Faza 4 — (opcjonalnie) prawdziwy agent tool-use

- [ ] decyzja: albo usunąć nieużywane `openai-agents` z `requirements.txt`, albo świadomie zaplanować migrację automatyzacji formularza na agenta z narzędziami (osobny epic)

---

## Ryzyka / uwagi

- **Edycja promptów w adminie bez pomiaru jakości** — największe ryzyko regresji. Faza 3 (datasets/evaluators) to adresuje.
- **`kimi-k2-thinking` jako primary** — model rozumujący, pożera `max_tokens` na niewidoczne reasoning_tokens; wymaga `reasoning.effort=low` (już obejście w kodzie). Przy routingu per-zadanie rozważyć czy w ogóle powinien być primary dla krótkich operacji.
- **Klucze** — `OPENROUTER_API_KEY`, `LANGSMITH_API_KEY` tylko w `.env.dev` / sekretach k3s, nigdy w repo.
- **Koszt** — OpenRouter zwraca `usage` z realnym kosztem $ per call; wpiąć w `ProductProcessingLog` żeby koszt automatyzacji był mierzalny.
