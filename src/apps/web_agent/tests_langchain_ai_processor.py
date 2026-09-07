"""
Testy `LangChainAIProcessor` (OpenRouter, model routowany PER OPERACJA -
DEFAULT_MODEL_ROUTING - + reczny fallback primary->fallback + LangSmith,
patrz automation/langchain_ai_processor.py). Zero prawdziwych wywolan
HTTP/LangSmith - `_get_model_chain()` jest podmieniane, zeby kazdy model
(primary/fallback DANEJ operacji) mial wlasny, niezalezny fake `.invoke()`:
albo zwraca wynik, albo rzuca wyjatek - dokladnie tak jak _invoke() to
konsumuje (try/except wokol calego chain.invoke() per model, sukces/blad z
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
    DEFAULT_MODEL_ROUTING,
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


class LangChainAIProcessorRoutingTest(TestCase):
    """Router per operacja - rdzen tej zmiany (Faza 2, #195)."""

    def test_different_operations_get_different_default_primary(self):
        proc = _make_processor()
        # description dostaje mocny model rozumujacy, pozostale tanio/szybko -
        # nie ten sam primary dla wszystkiego, jak przed routingiem per operacja.
        self.assertNotEqual(proc._routing["name"][0], proc._routing["description"][0])
        self.assertEqual(proc._routing["name"][0], proc._routing["attributes"][0])
        self.assertEqual(proc._routing["name"][0], proc._routing["short_description"][0])

    def test_fallback_is_the_other_model_for_every_operation(self):
        proc = _make_processor()
        for op, (primary, fallback) in proc._routing.items():
            with self.subTest(operation=op):
                self.assertNotEqual(primary, fallback)

    def test_matches_default_model_routing_table(self):
        proc = _make_processor()
        for op, expected in DEFAULT_MODEL_ROUTING.items():
            with self.subTest(operation=op):
                self.assertEqual(proc._routing[op], expected)

    def test_env_override_changes_only_that_operation(self):
        with patch.dict("os.environ", {"AI_MODEL_NAME_PRIMARY": "some/override-model"}):
            proc = LangChainAIProcessor(api_key="test-key")
        self.assertEqual(proc._routing["name"][0], "some/override-model")
        # inne operacje nie zostaly dotkniete przez override "name"
        self.assertEqual(
            proc._routing["description"], DEFAULT_MODEL_ROUTING["description"])

    def test_legacy_env_vars_still_override_description(self):
        """OPENAI_MODEL_PRODUCT_ENRICHMENT/LANGCHAIN_FALLBACK_MODEL istnialy
        przed routingiem per operacja i sa juz ustawione w .env.dev - musza
        dalej dzialac (tylko dla description)."""
        with patch.dict("os.environ", {
            "OPENAI_MODEL_PRODUCT_ENRICHMENT": "legacy/primary-model",
            "LANGCHAIN_FALLBACK_MODEL": "legacy/fallback-model",
        }):
            proc = LangChainAIProcessor(api_key="test-key")
        self.assertEqual(
            proc._routing["description"], ("legacy/primary-model", "legacy/fallback-model"))
        # legacy zmienne nie maja wplywu na inne operacje
        self.assertEqual(proc._routing["name"], DEFAULT_MODEL_ROUTING["name"])

    def test_per_operation_env_var_wins_over_legacy(self):
        with patch.dict("os.environ", {
            "AI_MODEL_DESCRIPTION_PRIMARY": "new/primary-model",
            "OPENAI_MODEL_PRODUCT_ENRICHMENT": "legacy/primary-model",
        }):
            proc = LangChainAIProcessor(api_key="test-key")
        self.assertEqual(proc._routing["description"][0], "new/primary-model")


class LangChainAIProcessorNameTest(TestCase):
    def test_primary_success_fallback_unused(self):
        proc = _make_processor()
        primary_model = proc._routing["name"][0]
        expected = ProductNameStructure(
            base_type="Kostium kąpielowy", model_name="Ada",
            final_name="Kostium kąpielowy Ada")

        with _patch_model_chains(proc, {primary_model: expected}):
            result = proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        self.assertEqual(result, "Kostium kąpielowy Ada")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["model"], primary_model)
        self.assertTrue(log[0]["success"])

    def test_primary_fails_fallback_takes_over(self):
        proc = _make_processor()
        primary_model, fallback_model = proc._routing["name"]
        expected = ProductNameStructure(
            base_type="Figi kąpielowe", model_name="Lupo",
            final_name="Figi kąpielowe Lupo")
        outcomes = {
            primary_model: RuntimeError("primary model niedostępny"),
            fallback_model: expected,
        }

        with _patch_model_chains(proc, outcomes):
            result = proc.enhance_product_name("Figi kąpielowe Lupo M-120 - Marko")

        self.assertEqual(result, "Figi kąpielowe Lupo")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["model"], primary_model)
        self.assertFalse(log[0]["success"])
        self.assertEqual(log[1]["model"], fallback_model)
        self.assertTrue(log[1]["success"])

    def test_both_models_fail_raises(self):
        proc = _make_processor()
        primary_model, fallback_model = proc._routing["name"]
        outcomes = {
            primary_model: RuntimeError("primary padł"),
            fallback_model: RuntimeError("fallback też padł"),
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
        primary_model, fallback_model = proc._routing["name"]
        try:
            ProductNameStructure(base_type="", model_name="", final_name="")
        except ValidationError as exc:
            malformed_error = exc
        expected = ProductNameStructure(
            base_type="Kostium kąpielowy", model_name="Ada",
            final_name="Kostium kąpielowy Ada")
        outcomes = {
            primary_model: malformed_error,
            fallback_model: expected,
        }

        with _patch_model_chains(proc, outcomes):
            result = proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        self.assertEqual(result, "Kostium kąpielowy Ada")
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["model"], primary_model)
        self.assertFalse(log[0]["success"], "primary z odrzuconym przez Pydantic JSON-em NIE jest sukcesem")
        self.assertEqual(log[1]["model"], fallback_model)
        self.assertTrue(log[1]["success"])

    def test_empty_name_raises_before_any_call(self):
        proc = _make_processor()
        with self.assertRaises(ValueError):
            proc.enhance_product_name("   ")


class LangChainAIProcessorDescriptionTest(TestCase):
    def test_primary_success(self):
        proc = _make_processor()
        primary_model = proc._routing["description"][0]
        expected = ProductDescriptionStructure(
            introduction="Elegancki kostium kąpielowy o klasycznym kroju i wysokiej jakości wykonaniu.",
            top_features=["Miękkie fiszbiny – wygodne dopasowanie"],
            bottom_features=["Regulowane boki – idealne dopasowanie"],
            finishing="Wykończenie lamówką w tym samym kolorze, staranne szwy, elastyczny materiał.",
            packaging="Produkt pakowany w ekologiczną torebkę z logo marki.",
            size_tip="Zalecamy wybór rozmiaru zgodnego z tabelą rozmiarów producenta.",
        )

        with _patch_model_chains(proc, {primary_model: expected}):
            result = proc.enhance_product_description("Kostium kąpielowy, fiszbiny, regulowane boki")

        self.assertIn("Regulowane boki", result)
        self.assertTrue(proc.pop_call_log()[0]["success"])

    def test_both_models_fail_returns_original_text(self):
        proc = _make_processor()
        primary_model, fallback_model = proc._routing["description"]
        outcomes = {
            primary_model: RuntimeError("primary padł"),
            fallback_model: RuntimeError("fallback też padł"),
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
        primary_model = proc._routing["short_description"][0]
        with _patch_model_chains(proc, {primary_model: _FakeMessage("x" * 300)}):
            result = proc.create_short_description("opis bazowy", max_length=250)
        self.assertEqual(len(result), 250)

    def test_create_short_description_both_fail_truncates_original(self):
        proc = _make_processor()
        primary_model, fallback_model = proc._routing["short_description"]
        outcomes = {
            primary_model: RuntimeError("padł"),
            fallback_model: RuntimeError("padł"),
        }
        original = "y" * 300
        with _patch_model_chains(proc, outcomes):
            result = proc.create_short_description(original, max_length=250)
        self.assertEqual(result, original[:250])

    def test_extract_attributes_maps_names_to_ids(self):
        proc = _make_processor()
        primary_model = proc._routing["attributes"][0]
        available = [
            {"id": 1, "name": "Wysoki stan"},
            {"id": 2, "name": "Niski stan"},
            {"id": 3, "name": "Push-up"},
        ]
        outcome = AttributesOutput(attributes=["Wysoki stan", "Push-Up", "Nieznany"])
        with _patch_model_chains(proc, {primary_model: outcome}):
            ids = proc.extract_attributes_from_description("opis", available)
        self.assertEqual(ids, [1, 3])

    def test_extract_attributes_both_fail_returns_empty_list(self):
        proc = _make_processor()
        primary_model, fallback_model = proc._routing["attributes"]
        available = [{"id": 1, "name": "Wysoki stan"}]
        outcomes = {
            primary_model: RuntimeError("padł"),
            fallback_model: RuntimeError("padł"),
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

    def test_pop_call_log_clears_state(self):
        proc = _make_processor()
        proc._call_log.append({"model": "x", "success": True})
        first = proc.pop_call_log()
        second = proc.pop_call_log()
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
