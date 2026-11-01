"""
Procesor AI: OpenRouter przez LangChain, tracing przez LangSmith. Ten sam
publiczny interfejs co AIProcessor (ai_processor.py) - wołany z tych samych
miejsc (product_processor.py, background_automation.py,
browser_automation.py, run_automation.py) bez zadnych zmian tam. Ustaw
USE_LANGCHAIN_AI=1 (get_ai_processor w ai_processor.py), zeby z niego
korzystac.

Routing = dwie rzeczy naraz:
1. Miedzy modelami (niezawodnosc) - primary->fallback per proba, patrz
   _invoke() nizej.
2. Miedzy OPERACJAMI (koszt/jakosc) - DEFAULT_MODEL_ROUTING przypisuje inna
   pare modeli kazdej operacji (name/description/attributes/
   short_description), nie jeden globalny primary/fallback dla wszystkiego.
   `description` dostaje mocny model rozumujacy jako primary (uzasadnione -
   copywriting), pozostale trzy dostaja tani/szybki model jako primary z
   tym samym mocnym modelem w odwodzie jako fallback (niezawodnosc nie
   spada - trudniejszy model zawsze jest dostepny, tylko rzadziej
   potrzebny). Nadpisywalne per operacja przez AI_MODEL_<OP>_<ROLE> env
   vary bez redeployu kodu - patrz _resolve_model().

Fallback (miedzy modelami) to JAWNA petla primary->fallback w _invoke() (nie
LangChainowe .with_fallbacks()) - kazda proba to osobny .invoke(), wiec
kazda i tak jest osobnym spanem w LangSmith (dodatkowo otagowanym nazwa
modelu), ale sukces/blad kazdej proby liczymy z PRAWDZIWEGO wyniku TEGO
wywolania (try/except), a nie z LLM-owych callbackow. To celowe:
.with_structured_output() to w rzeczywistosci DWA kroki (LLM, potem parser
Pydantic) - .with_fallbacks() + callback na poziomie LLM widzi tylko
pierwszy krok i potrafi zaraportowac model jako "sukces", mimo ze jego JSON
zostal odrzucony przez walidacje Pydantic (@field_validator w
ProductNameStructure/ProductDescriptionStructure) i wyrzucony na rzecz
fallbacku - reczna petla z try/except wokol calego chain.invoke() (LLM +
parser) tego nie ma, bo widzi realny wynik, nie tylko polowe.

Kontrola = dwa niezalezne mechanizmy, nie jeden zamiast drugiego:
1. LangSmith (ambient) - samo LANGSMITH_TRACING=true + LANGSMITH_API_KEY w
   .env.dev instrumentuje KAZDE wywolanie ChatOpenAI.invoke() bez zmian w
   kodzie. Tu tylko doklejamy tags/metadata (config= w .invoke()), zeby
   trace'y byly opisane, nie golym UUID.
2. Lokalny, programistyczny zapis per-attempt w _invoke() (ktory model
   probowal, sukces/blad, czas) NIEZALEZNY od LangSmith - zeby
   processing_data w Django admin (ProductProcessingLog) mial te informacje
   nawet bez otwierania LangSmith UI. pop_call_log() to eksponuje.
"""
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .ai_processor import (
    ProductDescriptionStructure,
    ProductNameStructure,
    is_figi_product,
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# operacja (ten sam cache_key co w _invoke()) -> (primary, fallback). Oba
# modele juz zweryfikowane na zywym OpenRouter w tej sesji (structured i
# nie-structured output) - swiadomie zero nowych, niesprawdzonych
# model-slugow tutaj; dywersyfikacja o trzeci model to osobny krok, do
# zweryfikowania na zywo przed uzyciem jako domyslny.
DEFAULT_MODEL_ROUTING: Dict[str, Tuple[str, str]] = {
    "name": ("openai/gpt-4o-mini", "moonshotai/kimi-k2-thinking"),
    "description": ("moonshotai/kimi-k2-thinking", "openai/gpt-4o-mini"),
    "attributes": ("openai/gpt-4o-mini", "moonshotai/kimi-k2-thinking"),
    "short_description": ("openai/gpt-4o-mini", "moonshotai/kimi-k2-thinking"),
}

# reasoning.effort to wlasciwosc MODELU (kimi jest modelem rozumujacym), nie
# operacji/pozycji - kimi moze byc primary (description) albo fallback
# (pozostale trzy operacje), w obu przypadkach potrzebuje tego samego
# obejscia (patrz komentarz w _get_llm o reasoning_tokens zjadajacych
# max_tokens).
REASONING_EFFORT_BY_MODEL: Dict[str, str] = {
    "moonshotai/kimi-k2-thinking": "low",
}

# Wsteczna zgodnosc: te zmienne istnialy PRZED routingiem per operacja i
# ustawialy globalny primary/fallback dla wszystkiego. Dzis maja sens tylko
# dla description (jedynej operacji, dla ktorej kimi-k2-thinking byl i jest
# domyslnym primary) - .env.dev juz ma OPENAI_MODEL_PRODUCT_ENRICHMENT
# ustawione, nie chcemy zeby przestalo dzialac.
_LEGACY_ENV_OVERRIDE: Dict[Tuple[str, str], str] = {
    ("description", "primary"): "OPENAI_MODEL_PRODUCT_ENRICHMENT",
    ("description", "fallback"): "LANGCHAIN_FALLBACK_MODEL",
}


def _resolve_model(operation: str, role: str) -> str:
    """Wybiera model dla (operacja, rola). Kolejnosc: AI_MODEL_<OP>_<ROLE>
    (nowy, per-operacyjny override) > legacy env (tylko description,
    wstecznie kompatybilne z OPENAI_MODEL_PRODUCT_ENRICHMENT/
    LANGCHAIN_FALLBACK_MODEL) > DEFAULT_MODEL_ROUTING. Pozwala zmienic model
    per operacja bez redeployu kodu."""
    env_key = f"AI_MODEL_{operation.upper()}_{role.upper()}"
    value = os.getenv(env_key)
    if value:
        return value
    legacy_key = _LEGACY_ENV_OVERRIDE.get((operation, role))
    if legacy_key:
        value = os.getenv(legacy_key)
        if value:
            return value
    idx = 0 if role == "primary" else 1
    return DEFAULT_MODEL_ROUTING[operation][idx]


class AttributesOutput(BaseModel):
    """Struktura odpowiedzi LLM dla ekstrakcji atrybutów."""

    attributes: List[str] = Field(
        default_factory=list,
        description="Lista nazw atrybutów wyodrębnionych z opisu",
    )


def _get_prompt(name: str, **kwargs) -> Optional[str]:
    """Pobiera aktywny prompt z bazy (AIPrompt, edytowalny w Django Admin) i
    wypełnia zmienne. Ten sam wzorzec i te same nazwy promptów co
    AIProcessor._get_prompt (ai_processor.py:333) - jedno źródło prawdy dla
    obu procesorów, edycja w adminie działa niezależnie od tego, który jest
    aktywny (USE_LANGCHAIN_AI)."""
    try:
        from web_agent.models import AIPrompt
        prompt = AIPrompt.objects.filter(name=name, is_active=True).first()
        if prompt:
            return prompt.render(**kwargs)
        logger.warning("Nie znaleziono aktywnego promptu: %s", name)
        return None
    except Exception as e:
        logger.error("Błąd podczas pobierania promptu %s: %s", name, e)
        return None


class LangChainAIProcessor:
    """Procesor AI: OpenRouter, model routowany PER OPERACJA (patrz
    DEFAULT_MODEL_ROUTING), reczny fallback (petla try/except w _invoke() -
    patrz docstring modulu), tracing przez LangSmith."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key is required. Ustaw OPENROUTER_API_KEY w .env.dev."
            )
        # `model` (jesli podany) nadpisuje primary WSZYSTKICH operacji - uzyte
        # dzis tylko w testach/debugowaniu, produkcyjnie routing jest per
        # operacja (self._routing) i konfigurowany env-varami, nie tym argumentem.
        self._routing: Dict[str, Tuple[str, str]] = {
            op: (model or _resolve_model(op, "primary"), _resolve_model(op, "fallback"))
            for op in DEFAULT_MODEL_ROUTING
        }
        self._chains: Dict[tuple, object] = {}
        self._call_log: List[Dict] = []
        logger.info(
            "LangChainAIProcessor zainicjalizowany (OpenRouter, routing=%s)",
            self._routing,
        )

    def pop_call_log(self) -> List[Dict]:
        """Zwraca i czyści dotychczas zebrane wpisy (który model, sukces/błąd,
        czas trwania) - wołane przez tasks.py po process_product_data(), żeby
        dopisać do ProductProcessingLog.processing_data."""
        log = self._call_log
        self._call_log = []
        return log

    def _get_llm(self, model: str):
        from langchain_openai import ChatOpenAI
        kwargs = dict(
            base_url=OPENROUTER_BASE_URL,
            api_key=self.api_key,
            model=model,
            temperature=0.7,
            max_tokens=1500,
        )
        reasoning_effort = REASONING_EFFORT_BY_MODEL.get(model)
        if reasoning_effort:
            # modele rozumujace (dzis: kimi-k2-thinking) bez tego zjadaja co
            # najmniej polowe max_tokens na niewidoczne reasoning_tokens,
            # zanim zdaza dokonczyc strukturyzowany JSON (zweryfikowane na
            # prawdziwym wywolaniu OpenRouter: max_tokens=1500 -> 989
            # reasoning, max_tokens=4000 -> 2467 reasoning, oba razy "length
            # limit was reached", opis nigdy sie nie konczyl). OpenRouter-owy
            # `reasoning.effort` przycina budzet rozumowania niezaleznie od
            # max_tokens odpowiedzi. Modele nie-rozumujace (gpt-4o-mini) nie
            # dostaja tego kwarga wcale - nie tylko jest im zbedny, ale nie
            # ma pewnosci ze kazdy model na OpenRouter go ignoruje bez zmian
            # zachowania.
            kwargs["extra_body"] = {"reasoning": {"effort": reasoning_effort}}
        return ChatOpenAI(**kwargs)

    def _get_model_chain(self, model: str, cache_key: str, pydantic_class=None):
        """Chain dla POJEDYNCZEGO modelu (opcjonalnie ze strukturyzowanym
        wyjściem), cache'owany per (model, operacja), żeby nie tworzyć
        nowego klienta HTTP przy każdym wywołaniu. Fallback między modelami
        to pętla w _invoke() (nie .with_fallbacks()) - patrz docstring
        modułu, dlaczego."""
        key = (model, cache_key)
        if key not in self._chains:
            llm = self._get_llm(model)
            if pydantic_class is not None:
                llm = llm.with_structured_output(pydantic_class)
            self._chains[key] = llm
        return self._chains[key]

    def _invoke(self, cache_key: str, system: str, user: str, *, tags: List[str],
                pydantic_class=None):
        """Próbuje primary, potem fallback - osobny chain.invoke() na próbę
        (osobny span w LangSmith, otagowany nazwą modelu), sukces/błąd
        każdej próby liczony z jej PRAWDZIWEGO wyniku (try/except wokół
        całego invoke - LLM + parser Pydantic), nie z LLM-owych callbacków
        (patrz docstring modułu). Zwraca wynik pierwszej udanej próby albo
        None gdy obie zawiodły (obie zalogowane w _call_log)."""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        attempts: List[Dict] = []
        result = None
        for model in self._routing[cache_key]:
            started = time.monotonic()
            try:
                chain = self._get_model_chain(model, cache_key, pydantic_class)
                result = chain.invoke(
                    messages,
                    config={"tags": ["web_agent", "product-enrichment", *tags, model]},
                )
                attempts.append({
                    "model": model, "success": True,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "operation": cache_key,
                })
                break
            except Exception as e:
                logger.error("LangChain invoke (%s) %s nieudane: %s", cache_key, model, e)
                attempts.append({
                    "model": model, "success": False, "error": str(e),
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "operation": cache_key,
                })
        self._call_log.extend(attempts)
        return result

    def enhance_product_name(
        self,
        original_name: str,
        product_config: Optional[Dict] = None,
        use_structured: bool = True,
    ) -> str:
        if not original_name or not original_name.strip():
            raise ValueError("Oryginalna nazwa produktu jest pusta")
        if not use_structured:
            return original_name

        if product_config:
            base_type = product_config.get("base_type", "Kostium kąpielowy")
        else:
            base_type = "Figi kąpielowe" if is_figi_product(original_name) else "Kostium kąpielowy"
        example_format = f"{base_type} [model_name]"
        example_input = f"{base_type} Model Ada M-803 (1) Lilia - Marko"
        example_output = f'{{"base_type": "{base_type}", "model_name": "Ada", "final_name": "{base_type} Ada"}}'

        system = _get_prompt(
            "product_name_system", base_type=base_type,
            example_format=example_format, example_input=example_input,
            example_output=example_output,
        ) or (
            f'Jesteś ekspertem od nazewnictwa produktów tekstylnych. Przekształć nazwę '
            f'w JSON: base_type (zawsze "{base_type}"), model_name (nazwa modelu 1-30 '
            f'znaków), final_name ("{example_format}", max 100 znaków). NIE dodawaj '
            f'koloru, kodu (M-XXX), numerów w nawiasach, marki. Tylko JSON.'
        )
        user = _get_prompt("product_name_user", original_name=original_name) or (
            f"Przekształć tę nazwę produktu w strukturę JSON:\n\n{original_name}"
        )

        result = self._invoke(
            "name", system, user, tags=["name"], pydantic_class=ProductNameStructure)
        if isinstance(result, ProductNameStructure):
            return result.to_final_name()
        primary, fallback = self._routing["name"]
        raise RuntimeError(
            f"Nie udało się ulepszyć nazwy produktu ani przez {primary}, "
            f"ani przez {fallback}"
        )

    def enhance_product_description(
        self,
        original_description: str,
        product_name: Optional[str] = None,
        product_config: Optional[Dict] = None,
        use_structured: bool = True,
    ) -> str:
        if not original_description or not original_description.strip():
            return ""
        if not use_structured:
            return original_description

        if not product_config:
            has_top = not (product_name and is_figi_product(product_name))
        else:
            has_top = product_config.get("has_top", True)
        suffix = "" if has_top else "_figi"

        if not has_top:
            product_type_instruction = (
                "To są FIGI KĄPIELOWE - produkt składa się TYLKO z dołu, NIE MA góry. "
                "NIE generuj sekcji 'Góra'."
            )
            top_features_instruction = "top_features: NIE UŻYWAJ, ustaw jako pustą listę []."
        else:
            product_type_instruction = "To jest KOSTIUM KĄPIELOWY - góra (biustonosz) i dół (figi)."
            top_features_instruction = (
                "top_features: cechy góry, WYMAGANE MINIMUM 1, format "
                '"cecha – opis korzyści", max 10, każda max 300 znaków.'
            )
        description_sections = (
            ["Dół", "Wykończenie", "Pakowanie", "Wskazówka rozmiarowa"] if not has_top
            else ["Góra", "Dół", "Wykończenie", "Pakowanie", "Wskazówka rozmiarowa"]
        )
        bottom_features_warning = (
            "bottom_features MUSI zawierać przynajmniej 1 element."
            if not has_top else
            "top_features i bottom_features MUSZĄ zawierać przynajmniej 1 element."
        )

        system = _get_prompt(
            f"product_description_system{suffix}",
            has_top=has_top,
            product_type_instruction=product_type_instruction,
            top_features_instruction=top_features_instruction,
            description_sections=", ".join(f'"{s}"' for s in description_sections),
            bottom_features_warning=bottom_features_warning,
        ) or (
            "Jesteś ekspertem od copywritingu e-commerce (bielizna, kostiumy kąpielowe). "
            f"{product_type_instruction} Przekształć opis na profesjonalny, sprzedażowy. "
            f"Sekcje: introduction (max 200 zn.), {top_features_instruction} "
            "bottom_features (lista, min 1), finishing (50-300 zn.), packaging (30-200 zn.), "
            f"size_tip (30-200 zn.). {bottom_features_warning} Tylko JSON."
        )
        user = _get_prompt(
            f"product_description_user{suffix}",
            original_description=original_description, has_top=has_top,
        ) or f"Przekształć opis produktu na strukturyzowany format:\n\n{original_description}"

        result = self._invoke(
            "description", system, user, tags=["description"],
            pydantic_class=ProductDescriptionStructure,
        )
        if isinstance(result, ProductDescriptionStructure):
            return result.to_formatted_text()
        primary, fallback = self._routing["description"]
        logger.error(
            "Nie udało się ulepszyć opisu ani przez %s, ani przez %s - zwracam oryginał",
            primary, fallback,
        )
        return original_description

    def create_short_description(self, description: str, max_length: int = 250) -> str:
        if not description or not description.strip():
            return ""

        system = (
            f"Jesteś ekspertem od krótkich opisów produktów. Twórz zwięzły, "
            f"atrakcyjny opis tekstylny, max {max_length} znaków. Odpowiadaj tylko krótkim opisem."
        )
        user = f"Krótki opis na podstawie:\n\n{description}"

        result = self._invoke("short_description", system, user, tags=["short-description"])
        if result is not None:
            text = result.content.strip() if hasattr(result, "content") else str(result).strip()
            if text:
                return text[:max_length]
        return description[:max_length]

    def extract_attributes_from_description(
        self,
        description: str,
        available_attributes: List[Dict],
        similarity_threshold: float = 0.05,
        min_attributes: int = 3,
        max_attributes: int = 15,
    ) -> List[int]:
        if not description or not description.strip() or not available_attributes:
            return []

        attrs_text = ", ".join(a["name"] for a in available_attributes)
        name_to_id = {a["name"].lower(): a["id"] for a in available_attributes}

        system = _get_prompt("attributes_extraction_system") or (
            "Wyodrębnij z opisu produktu TYLKO atrybuty BEZPOŚREDNIO wspomniane. "
            'Zwróć JSON: {"attributes": ["nazwa1", "nazwa2", ...]}. '
            "Używaj dokładnie nazw z listy dostępnych. Nie myl przeciwnych "
            "(np. wysoki stan ≠ niski stan)."
        )
        user = _get_prompt(
            "attributes_extraction_user", description=description,
            available_attrs_text=attrs_text,
        ) or (
            f"Opis: {description}\n\nDostępne atrybuty: {attrs_text}\n\n"
            "Zwróć JSON z polem attributes (lista nazw wybranych atrybutów)."
        )

        result = self._invoke(
            "attributes", system, user, tags=["attributes"],
            pydantic_class=AttributesOutput,
        )
        if not isinstance(result, AttributesOutput):
            return []

        ids = []
        for name in result.attributes:
            n = (name or "").strip()
            if not n:
                continue
            aid = name_to_id.get(n.lower())
            if aid is not None and aid not in ids:
                ids.append(aid)
        return ids[:max_attributes]

    def process_product_data(self, product_data: Dict) -> Dict:
        """Przetwarza name/description/short_description produktu przez AI -
        ten sam interfejs co AIProcessor.process_product_data
        (ai_processor.py:2492)."""
        logger.info(
            "Przetwarzanie danych produktu przez AI (LangChain/OpenRouter): %s",
            product_data.get("name", "Unknown"),
        )
        processed = product_data.copy()

        if processed.get("name"):
            processed["name"] = self.enhance_product_name(processed["name"])

        if processed.get("description"):
            processed["description"] = self.enhance_product_description(
                processed["description"], product_name=processed.get("name"))

        if not processed.get("short_description") and processed.get("description"):
            processed["short_description"] = self.create_short_description(
                processed["description"])

        return processed
