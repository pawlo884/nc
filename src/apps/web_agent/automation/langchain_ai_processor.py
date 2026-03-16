"""
Procesor AI oparty na LangChain – ten sam interfejs co AIProcessor.
Ustaw USE_LANGCHAIN_AI=1 (lub true/yes), aby z niego korzystać.
"""
import logging
import os
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .ai_processor import (
    ProductDescriptionStructure,
    ProductNameStructure,
    get_product_config,
    is_figi_product,
)

logger = logging.getLogger(__name__)


class AttributesOutput(BaseModel):
    """Struktura odpowiedzi LLM dla ekstrakcji atrybutów."""

    attributes: List[str] = Field(
        default_factory=list,
        description="Lista nazw atrybutów wyodrębnionych z opisu",
    )


class LangChainAIProcessor:
    """Procesor AI z użyciem LangChain (ChatOpenAI + structured output)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOVITA")
        if not api_key:
            raise ValueError(
                "API key is required. Set OPENAI_API_KEY or OPENAI_API_KEY_NOVITA."
            )
        self.api_key = api_key
        self.model = model or os.getenv("LANGCHAIN_AI_MODEL", "gpt-4o-mini")
        self._llm = None
        self._llm_name_structured = None
        self._llm_desc_structured = None
        self._llm_attributes_structured = None
        logger.info("LangChainAIProcessor zainicjalizowany (model=%s)", self.model)

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                api_key=self.api_key,
                model=self.model,
                temperature=0.7,
                max_tokens=500,
            )
        return self._llm

    def _get_llm_structured(self, pydantic_class):
        cache_key = pydantic_class.__name__
        cache = getattr(self, "_llm_structured_cache", None)
        if cache is None:
            self._llm_structured_cache = {}
            cache = self._llm_structured_cache
        if cache_key not in cache:
            cache[cache_key] = self._get_llm().with_structured_output(pydantic_class)
        return cache[cache_key]

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

        base_type = "Kostium kąpielowy"
        if product_config:
            base_type = product_config.get("base_type", base_type)
        else:
            base_type = "Figi kąpielowe" if is_figi_product(original_name) else "Kostium kąpielowy"

        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            f"Jesteś ekspertem od nazewnictwa produktów tekstylnych. "
            f"Przekształć nazwę w JSON: base_type (zawsze \"{base_type}\"), "
            f"model_name (nazwa modelu 1-30 znaków), final_name (\"{base_type} [model_name]\", max 100 znaków). "
            f"NIE dodawaj koloru, kodu (M-XXX), numerów w nawiasach, marki. Odpowiadaj tylko JSON zgodnym ze schematem."
        )
        user = f"Przekształć tę nazwę produktu w strukturę JSON:\n\n{original_name}"

        try:
            llm = self._get_llm_structured(ProductNameStructure)
            msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            if isinstance(msg, ProductNameStructure):
                return msg.to_final_name()
            return original_name
        except Exception as e:
            logger.error("LangChain enhance_product_name: %s", e)
            raise

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
            description_sections = (
                ["Dół", "Wykończenie", "Pakowanie", "Wskazówka rozmiarowa"]
                if not has_top
                else ["Góra", "Dół", "Wykończenie", "Pakowanie", "Wskazówka rozmiarowa"]
            )
        else:
            has_top = product_config.get("has_top", True)
            description_sections = product_config.get(
                "description_sections",
                ["Góra", "Dół", "Wykończenie", "Pakowanie", "Wskazówka rozmiarowa"],
            )

        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            "Jesteś ekspertem od copywritingu e-commerce (bielizna, kostiumy kąpielowe). "
            "Przekształć opis na profesjonalny, sprzedażowy. "
            "Sekcje: introduction (max 200 zn.), top_features (lista; dla fig pustą []), "
            "bottom_features (lista, min 1), finishing (50-300 zn.), packaging (30-200 zn.), size_tip (30-200 zn.). "
            "Odpowiedź wyłącznie w JSON zgodnym ze schematem."
        )
        if not has_top:
            system += " To są FIGI KĄPIELOWE – tylko dół. top_features = []."
        user = f"Przekształć opis produktu na strukturyzowany format:\n\n{original_description}"

        try:
            llm = self._get_llm_structured(ProductDescriptionStructure)
            msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            if isinstance(msg, ProductDescriptionStructure):
                return msg.to_formatted_text()
            return original_description
        except Exception as e:
            logger.error("LangChain enhance_product_description: %s", e)
            return original_description

    def create_short_description(self, description: str, max_length: int = 250) -> str:
        if not description or not description.strip():
            return ""

        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            f"Jesteś ekspertem od krótkich opisów produktów. "
            f"Twórz zwięzły, atrakcyjny opis tekstylny, max {max_length} znaków. Odpowiadaj tylko krótkim opisem."
        )
        user = f"Krótki opis na podstawie:\n\n{description}"

        try:
            llm = self._get_llm()
            out = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            text = out.content.strip() if hasattr(out, "content") else str(out)
            return (text[:max_length] if text else "") or description[:max_length]
        except Exception as e:
            logger.error("LangChain create_short_description: %s", e)
            return description[:max_length] if description else ""

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

        from langchain_core.messages import HumanMessage, SystemMessage

        system = (
            "Wyodrębnij z opisu produktu TYLKO atrybuty BEZPOŚREDNIO wspomniane. "
            "Zwróć JSON: {\"attributes\": [\"nazwa1\", \"nazwa2\", ...]}. "
            "Używaj dokładnie nazw z listy dostępnych. Nie myl przeciwnych (np. wysoki stan ≠ niski stan)."
        )
        user = (
            f"Opis: {description}\n\nDostępne atrybuty: {attrs_text}\n\n"
            "Zwróć JSON z polem attributes (lista nazw wybranych atrybutów)."
        )

        try:
            llm = self._get_llm_structured(AttributesOutput)
            msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            if not isinstance(msg, AttributesOutput):
                return []
            ids = []
            for name in msg.attributes:
                n = (name or "").strip()
                if not n:
                    continue
                aid = name_to_id.get(n.lower())
                if aid is not None and aid not in ids:
                    ids.append(aid)
            return ids[:max_attributes]
        except Exception as e:
            logger.warning("LangChain extract_attributes: %s", e)
            return []
