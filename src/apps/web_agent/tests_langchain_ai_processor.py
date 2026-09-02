"""
Testy `LangChainAIProcessor` (OpenRouter + reczny fallback primary->fallback
+ LangSmith, patrz automation/langchain_ai_processor.py). Zero prawdziwych
wywolan HTTP/LangSmith - `_get_model_chain()` jest podmieniane, zeby kazdy
model (primary/fallback) mial wlasny, niezalezny fake `.invoke()`: albo
zwraca wynik, albo rzuca wyjatek - dokladnie tak jak _invoke() to konsumuje
(try/except wokol calego chain.invoke() per model, sukces/blad z
PRAWDZIWEGO wyniku tej proby, nie z LLM-owych callbackow - patrz docstring
modulu o tym, dlaczego to wazne dla walidacji Pydantic).
"""
from unittest.mock import patch

from django.test import TestCase
from pydantic import ValidationError

from web_agent.automation.ai_processor import (
    ProductDescriptionStructure,
    ProductNameStructure,
)
from web_agent.automation.langchain_ai_processor import (
    AttributesOutput,
    LangChainAIProcessor,
)


class _FakeSingleChain:
    """Odpowiednik chaina zwracanego przez _get_model_chain() dla JEDNEGO
    modelu - jeden fake `.invoke()`, albo zwraca `outcome`, albo (gdy
    `outcome` jest wyjatkiem - w tym pydantic.ValidationError, dokladnie to
    co realnie rzuca .with_structured_output() gdy LLM zwroci zly JSON) go
    rzuca."""

    def __init__(self, outcome):
        self.outcome = outcome

    def invoke(self, messages, config=None):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _patch_model_chains(proc, outcomes):
    """outcomes: dict model_name -> wynik_albo_wyjatek. Model bez wpisu w
    outcomes, jesli zostanie faktycznie wywolany, rzuci KeyError - to
    celowe, ujawnia gdyby kod probowal model, ktorego test nie oczekiwal."""

    def fake_get_model_chain(model, cache_key, pydantic_class=None):
        return _FakeSingleChain(outcomes[model])

    return patch.object(proc, "_get_model_chain", side_effect=fake_get_model_chain)


class _FakeMessage:
    """Odpowiednik AIMessage zwracanego przez ChatOpenAI bez structured output
    (create_short_description) - liczy się tylko `.content`."""

    def __init__(self, content):
        self.content = content


def _make_processor():
    return LangChainAIProcessor(api_key="test-openrouter-key")


class LangChainAIProcessorNameTest(TestCase):
    def test_primary_success_fallback_unused(self):
        proc = _make_processor()
        expected = ProductNameStructure(
            base_type="Kostium kąpielowy", model_name="Ada",
            final_name="Kostium kąpielowy Ada")

        with _patch_model_chains(proc, {proc.primary_model: expected}):
            result = proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        self.assertEqual(result, "Kostium kąpielowy Ada")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["model"], proc.primary_model)
        self.assertTrue(log[0]["success"])

    def test_primary_fails_fallback_takes_over(self):
        proc = _make_processor()
        expected = ProductNameStructure(
            base_type="Figi kąpielowe", model_name="Lupo",
            final_name="Figi kąpielowe Lupo")
        outcomes = {
            proc.primary_model: RuntimeError("primary model niedostępny"),
            proc.fallback_model: expected,
        }

        with _patch_model_chains(proc, outcomes):
            result = proc.enhance_product_name("Figi kąpielowe Lupo M-120 - Marko")

        self.assertEqual(result, "Figi kąpielowe Lupo")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["model"], proc.primary_model)
        self.assertFalse(log[0]["success"])
        self.assertEqual(log[1]["model"], proc.fallback_model)
        self.assertTrue(log[1]["success"])

    def test_both_models_fail_raises(self):
        proc = _make_processor()
        outcomes = {
            proc.primary_model: RuntimeError("primary padł"),
            proc.fallback_model: RuntimeError("fallback też padł"),
        }

        with _patch_model_chains(proc, outcomes):
            with self.assertRaises(RuntimeError):
                proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertFalse(log[0]["success"])
        self.assertFalse(log[1]["success"])

    def test_primary_validation_error_falls_back_and_is_logged_as_failure(self):
        """Kluczowy przypadek: primary "odpowiada" (LLM sie wywoluje), ale
        JSON nie przechodzi walidacji Pydantic (@field_validator w
        ProductNameStructure) - .with_structured_output() rzuca
        ValidationError z kroku parsera. Musi to zostac policzone jako
        PORAZKA primary (nie sukces), a fallback ma przejac."""
        proc = _make_processor()
        try:
            ProductNameStructure(base_type="", model_name="", final_name="")
        except ValidationError as exc:
            malformed_error = exc
        expected = ProductNameStructure(
            base_type="Kostium kąpielowy", model_name="Ada",
            final_name="Kostium kąpielowy Ada")
        outcomes = {
            proc.primary_model: malformed_error,
            proc.fallback_model: expected,
        }

        with _patch_model_chains(proc, outcomes):
            result = proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        self.assertEqual(result, "Kostium kąpielowy Ada")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["model"], proc.primary_model)
        self.assertFalse(log[0]["success"], "primary z odrzuconym przez Pydantic JSON-em NIE jest sukcesem")
        self.assertEqual(log[1]["model"], proc.fallback_model)
        self.assertTrue(log[1]["success"])

    def test_empty_name_raises_before_any_call(self):
        proc = _make_processor()
        with self.assertRaises(ValueError):
            proc.enhance_product_name("   ")


class LangChainAIProcessorDescriptionTest(TestCase):
    def test_primary_success(self):
        proc = _make_processor()
        expected = ProductDescriptionStructure(
            introduction="Elegancki kostium kąpielowy o klasycznym kroju i wysokiej jakości wykonaniu.",
            top_features=["Miękkie fiszbiny – wygodne dopasowanie"],
            bottom_features=["Regulowane boki – idealne dopasowanie"],
            finishing="Wykończenie lamówką w tym samym kolorze, staranne szwy, elastyczny materiał.",
            packaging="Produkt pakowany w ekologiczną torebkę z logo marki.",
            size_tip="Zalecamy wybór rozmiaru zgodnego z tabelą rozmiarów producenta.",
        )

        with _patch_model_chains(proc, {proc.primary_model: expected}):
            result = proc.enhance_product_description("Kostium kąpielowy, fiszbiny, regulowane boki")

        self.assertIn("Regulowane boki", result)
        self.assertTrue(proc.pop_call_log()[0]["success"])

    def test_both_models_fail_returns_original_text(self):
        proc = _make_processor()
        outcomes = {
            proc.primary_model: RuntimeError("primary padł"),
            proc.fallback_model: RuntimeError("fallback też padł"),
        }
        original = "Oryginalny, niezmieniony opis produktu."

        with _patch_model_chains(proc, outcomes):
            result = proc.enhance_product_description(original)

        self.assertEqual(result, original)
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertFalse(log[0]["success"])
        self.assertFalse(log[1]["success"])

    def test_empty_description_returns_empty_without_calling_model(self):
        proc = _make_processor()
        with patch.object(proc, "_get_model_chain") as get_chain:
            result = proc.enhance_product_description("")
        self.assertEqual(result, "")
        get_chain.assert_not_called()


class LangChainAIProcessorShortDescriptionAndAttributesTest(TestCase):
    def test_create_short_description_truncates(self):
        proc = _make_processor()
        with _patch_model_chains(proc, {proc.primary_model: _FakeMessage("x" * 300)}):
            result = proc.create_short_description("opis bazowy", max_length=250)
        self.assertEqual(len(result), 250)

    def test_create_short_description_both_fail_truncates_original(self):
        proc = _make_processor()
        outcomes = {
            proc.primary_model: RuntimeError("padł"),
            proc.fallback_model: RuntimeError("padł"),
        }
        original = "y" * 300
        with _patch_model_chains(proc, outcomes):
            result = proc.create_short_description(original, max_length=250)
        self.assertEqual(result, original[:250])

    def test_extract_attributes_maps_names_to_ids(self):
        proc = _make_processor()
        available = [
            {"id": 1, "name": "Wysoki stan"},
            {"id": 2, "name": "Niski stan"},
            {"id": 3, "name": "Push-up"},
        ]
        outcome = AttributesOutput(attributes=["Wysoki stan", "Push-Up", "Nieznany"])
        with _patch_model_chains(proc, {proc.primary_model: outcome}):
            ids = proc.extract_attributes_from_description("opis", available)
        self.assertEqual(ids, [1, 3])

    def test_extract_attributes_both_fail_returns_empty_list(self):
        proc = _make_processor()
        available = [{"id": 1, "name": "Wysoki stan"}]
        outcomes = {
            proc.primary_model: RuntimeError("padł"),
            proc.fallback_model: RuntimeError("padł"),
        }
        with _patch_model_chains(proc, outcomes):
            ids = proc.extract_attributes_from_description("opis", available)
        self.assertEqual(ids, [])


class LangChainAIProcessorInitTest(TestCase):
    def test_requires_api_key(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("OPENROUTER_API_KEY", None)
            with self.assertRaises(ValueError):
                LangChainAIProcessor()

    def test_default_models(self):
        proc = LangChainAIProcessor(api_key="test-key")
        self.assertTrue(proc.primary_model)
        self.assertTrue(proc.fallback_model)
        self.assertNotEqual(proc.primary_model, proc.fallback_model)

    def test_pop_call_log_clears_state(self):
        proc = _make_processor()
        proc._call_log.append({"model": "x", "success": True})
        first = proc.pop_call_log()
        second = proc.pop_call_log()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
