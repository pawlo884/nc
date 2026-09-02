"""
Testy `LangChainAIProcessor` (OpenRouter + .with_fallbacks() + LangSmith,
patrz automation/langchain_ai_processor.py). Zero prawdziwych wywolan
HTTP/LangSmith - `_get_chain()` jest podmieniane na `_FakeChain`, ktora
odtwarza dokladnie to, co widzialaby `_invoke()` od prawdziwego
`primary.with_fallbacks([fallback])`: kolejne proby, wywolania callbacku
(`_CallLogCallback`) per model, i albo wynik pierwszej udanej proby, albo
ostatni wyjatek gdy wszystkie zawiedly.
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


class _FakeChain:
    """Podmienia realny Runnable zwracany przez `_get_chain()`. `attempts`
    to lista (model_name, wynik_albo_wyjatek) w kolejnosci prob -
    dokladnie tak zachowuje sie `primary.with_fallbacks([fallback])`:
    probuje po kolei, zwraca pierwszy sukces, albo rzuca ostatni wyjatek
    gdy wszystkie zawiodly."""

    def __init__(self, attempts):
        self.attempts = attempts

    def invoke(self, messages, config=None):
        callbacks = (config or {}).get("callbacks") or []
        last_exc = None
        for model_name, outcome in self.attempts:
            for cb in callbacks:
                cb.on_chat_model_start(
                    {}, [messages], invocation_params={"model": model_name})
            if isinstance(outcome, Exception):
                last_exc = outcome
                for cb in callbacks:
                    cb.on_llm_error(outcome)
                continue
            for cb in callbacks:
                cb.on_llm_end(outcome)
            return outcome
        raise last_exc


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
        chain = _FakeChain([(proc.primary_model, expected)])

        with patch.object(proc, "_get_chain", return_value=chain):
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
        chain = _FakeChain([
            (proc.primary_model, RuntimeError("primary model niedostępny")),
            (proc.fallback_model, expected),
        ])

        with patch.object(proc, "_get_chain", return_value=chain):
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
        chain = _FakeChain([
            (proc.primary_model, RuntimeError("primary padł")),
            (proc.fallback_model, RuntimeError("fallback też padł")),
        ])

        with patch.object(proc, "_get_chain", return_value=chain):
            with self.assertRaises(RuntimeError):
                proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertFalse(log[0]["success"])
        self.assertFalse(log[1]["success"])

    def test_malformed_llm_output_rejected_by_pydantic_falls_back(self):
        """Gdy primary zwraca cos co nie przejdzie walidacji schematu (to co
        realnie robi .with_structured_output() gdy LLM zwroci zly JSON -
        rzuca ValidationError), fallback ma szanse przejąć, tak samo jak przy
        kazdym innym wyjatku primary."""
        proc = _make_processor()
        try:
            ProductNameStructure(base_type="", model_name="", final_name="")
        except ValidationError as exc:
            malformed_error = exc
        expected = ProductNameStructure(
            base_type="Kostium kąpielowy", model_name="Ada",
            final_name="Kostium kąpielowy Ada")
        chain = _FakeChain([
            (proc.primary_model, malformed_error),
            (proc.fallback_model, expected),
        ])

        with patch.object(proc, "_get_chain", return_value=chain):
            result = proc.enhance_product_name("Kostium kąpielowy Model Ada M-803 - Marko")

        self.assertEqual(result, "Kostium kąpielowy Ada")
        log = proc.pop_call_log()
        self.assertFalse(log[0]["success"])
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
        chain = _FakeChain([(proc.primary_model, expected)])

        with patch.object(proc, "_get_chain", return_value=chain):
            result = proc.enhance_product_description("Kostium kąpielowy, fiszbiny, regulowane boki")

        self.assertIn("Regulowane boki", result)
        self.assertTrue(proc.pop_call_log()[0]["success"])

    def test_both_models_fail_returns_original_text(self):
        proc = _make_processor()
        chain = _FakeChain([
            (proc.primary_model, RuntimeError("primary padł")),
            (proc.fallback_model, RuntimeError("fallback też padł")),
        ])
        original = "Oryginalny, niezmieniony opis produktu."

        with patch.object(proc, "_get_chain", return_value=chain):
            result = proc.enhance_product_description(original)

        self.assertEqual(result, original)
        log = proc.pop_call_log()
        self.assertEqual(len(log), 2)
        self.assertFalse(log[0]["success"])
        self.assertFalse(log[1]["success"])

    def test_empty_description_returns_empty_without_calling_model(self):
        proc = _make_processor()
        with patch.object(proc, "_get_chain") as get_chain:
            result = proc.enhance_product_description("")
        self.assertEqual(result, "")
        get_chain.assert_not_called()


class LangChainAIProcessorShortDescriptionAndAttributesTest(TestCase):
    def test_create_short_description_truncates(self):
        proc = _make_processor()
        chain = _FakeChain([
            (proc.primary_model, _FakeMessage("x" * 300)),
        ])
        with patch.object(proc, "_get_chain", return_value=chain):
            result = proc.create_short_description("opis bazowy", max_length=250)
        self.assertEqual(len(result), 250)

    def test_create_short_description_both_fail_truncates_original(self):
        proc = _make_processor()
        chain = _FakeChain([
            (proc.primary_model, RuntimeError("padł")),
            (proc.fallback_model, RuntimeError("padł")),
        ])
        original = "y" * 300
        with patch.object(proc, "_get_chain", return_value=chain):
            result = proc.create_short_description(original, max_length=250)
        self.assertEqual(result, original[:250])

    def test_extract_attributes_maps_names_to_ids(self):
        proc = _make_processor()
        available = [
            {"id": 1, "name": "Wysoki stan"},
            {"id": 2, "name": "Niski stan"},
            {"id": 3, "name": "Push-up"},
        ]
        chain = _FakeChain([
            (proc.primary_model, AttributesOutput(attributes=["Wysoki stan", "Push-Up", "Nieznany"])),
        ])
        with patch.object(proc, "_get_chain", return_value=chain):
            ids = proc.extract_attributes_from_description("opis", available)
        self.assertEqual(ids, [1, 3])

    def test_extract_attributes_both_fail_returns_empty_list(self):
        proc = _make_processor()
        available = [{"id": 1, "name": "Wysoki stan"}]
        chain = _FakeChain([
            (proc.primary_model, RuntimeError("padł")),
            (proc.fallback_model, RuntimeError("padł")),
        ])
        with patch.object(proc, "_get_chain", return_value=chain):
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
