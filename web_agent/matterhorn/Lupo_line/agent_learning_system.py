#!/usr/bin/env python3
"""
System uczenia agenta dla marki Lupo Line
Pozwala na zbieranie danych, analizę wzorców i ciągłe doskonalenie
"""

import json
import os
from datetime import datetime
from collections import defaultdict, Counter


class AgentLearningSystem:
    """System uczenia i doskonalenia agenta"""

    def __init__(self, knowledge_base_path="lupo_line_learned_data.json"):
        self.knowledge_base_path = knowledge_base_path
        self.learned_data = self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Wczytuje zapisaną bazę wiedzy"""
        if os.path.exists(self.knowledge_base_path):
            try:
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Błąd wczytywania bazy wiedzy: {e}")

        return {
            "products_processed": [],
            "pattern_success_rate": {},
            "attribute_correlations": {},
            "model_characteristics": {},
            "description_patterns": {},
            "material_patterns": {},
            "title_optimization_patterns": {},
            "error_patterns": [],
            "learning_statistics": {
                "total_products": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "last_updated": None
            }
        }

    def save_knowledge_base(self):
        """Zapisuje bazę wiedzy do pliku"""
        self.learned_data["learning_statistics"]["last_updated"] = datetime.now(
        ).isoformat()

        try:
            with open(self.knowledge_base_path, 'w', encoding='utf-8') as f:
                json.dump(self.learned_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Baza wiedzy zapisana: {self.knowledge_base_path}")
        except Exception as e:
            print(f"❌ Błąd zapisu bazy wiedzy: {e}")

    def log_product_processing(self, product_data):
        """Loguje przetwarzanie produktu"""
        timestamp = datetime.now().isoformat()

        product_entry = {
            "timestamp": timestamp,
            "title": product_data.get("title", ""),
            "model": product_data.get("model", ""),
            "description": product_data.get("description", ""),
            "detected_attributes": product_data.get("attributes", []),
            "producer_color": product_data.get("producer_color", ""),
            "main_color": product_data.get("main_color", ""),
            "series_name": product_data.get("series_name", ""),
            "material_composition": product_data.get("materials", []),
            "success": product_data.get("success", False),
            "errors": product_data.get("errors", [])
        }

        self.learned_data["products_processed"].append(product_entry)
        self.learned_data["learning_statistics"]["total_products"] += 1

        if product_data.get("success", False):
            self.learned_data["learning_statistics"]["successful_extractions"] += 1
        else:
            self.learned_data["learning_statistics"]["failed_extractions"] += 1

        # Analizuj wzorce modelu
        self._analyze_model_patterns(product_entry)

        # Analizuj wzorce atrybutów
        self._analyze_attribute_patterns(product_entry)

        # Analizuj wzorce materiałów
        self._analyze_material_patterns(product_entry)

        print(
            f"📊 Zalogowano produkt: {product_data.get('title', 'Bez tytułu')}")

    def _analyze_model_patterns(self, product):
        """Analizuje wzorce dla modeli"""
        model = product.get("model", "")
        if not model:
            return

        if model not in self.learned_data["model_characteristics"]:
            self.learned_data["model_characteristics"][model] = {
                "count": 0,
                "typical_attributes": Counter(),
                "typical_colors": Counter(),
                "typical_materials": Counter(),
                "success_rate": {"successful": 0, "total": 0}
            }

        model_data = self.learned_data["model_characteristics"][model]
        model_data["count"] += 1
        model_data["success_rate"]["total"] += 1

        if product.get("success", False):
            model_data["success_rate"]["successful"] += 1

        # Zbieraj statystyki atrybutów
        for attr in product.get("detected_attributes", []):
            model_data["typical_attributes"][str(attr)] += 1

        # Zbieraj statystyki kolorów
        producer_color = product.get("producer_color", "")
        if producer_color:
            model_data["typical_colors"][producer_color] += 1

        # Zbieraj statystyki materiałów
        for material in product.get("material_composition", []):
            component = material.get("component", "")
            if component:
                model_data["typical_materials"][component] += 1

    def _analyze_attribute_patterns(self, product):
        """Analizuje wzorce atrybutów"""
        description = product.get("description", "").lower()
        attributes = product.get("detected_attributes", [])

        # Analizuj co powoduje wykrycie konkretnych atrybutów
        for attr in attributes:
            attr_key = f"attr_{attr}"
            if attr_key not in self.learned_data["attribute_correlations"]:
                self.learned_data["attribute_correlations"][attr_key] = {
                    "successful_phrases": Counter(),
                    "context_words": Counter()
                }

            # Szukaj fraz w opisie (heurystyka)
            words = description.split()
            for i, word in enumerate(words):
                # Zapisuj 3-gramy zawierające interesujące słowa
                if len(word) > 3:  # Pomijaj krótkie słowa
                    start = max(0, i-1)
                    end = min(len(words), i+2)
                    phrase = " ".join(words[start:end])
                    self.learned_data["attribute_correlations"][attr_key]["successful_phrases"][phrase] += 1

    def _analyze_material_patterns(self, product):
        """Analizuje wzorce materiałów"""
        materials = product.get("material_composition", [])
        model = product.get("model", "")

        if materials and model:
            material_signature = "_".join(
                [f"{m['component']}_{m['percentage']}" for m in materials])

            if "material_by_model" not in self.learned_data["material_patterns"]:
                self.learned_data["material_patterns"]["material_by_model"] = {}

            if model not in self.learned_data["material_patterns"]["material_by_model"]:
                self.learned_data["material_patterns"]["material_by_model"][model] = Counter(
                )

            self.learned_data["material_patterns"]["material_by_model"][model][material_signature] += 1

    def get_model_insights(self, model_name):
        """Zwraca insights dla konkretnego modelu"""
        if model_name not in self.learned_data["model_characteristics"]:
            return None

        model_data = self.learned_data["model_characteristics"][model_name]

        # Najczęstsze atrybuty (>50% przypadków)
        total_count = model_data["count"]
        frequent_attributes = [
            int(attr) for attr, count in model_data["typical_attributes"].items()
            if count / total_count > 0.5
        ]

        # Najczęstsze kolory
        frequent_colors = [
            color for color, count in model_data["typical_colors"].most_common(3)
        ]

        # Success rate
        success_rate = 0
        if model_data["success_rate"]["total"] > 0:
            success_rate = model_data["success_rate"]["successful"] / \
                model_data["success_rate"]["total"]

        return {
            "model": model_name,
            "sample_size": total_count,
            "success_rate": round(success_rate, 2),
            "frequent_attributes": frequent_attributes,
            "frequent_colors": frequent_colors,
            "recommendation": self._generate_model_recommendation(model_data)
        }

    def _generate_model_recommendation(self, model_data):
        """Generuje rekomendacje dla modelu"""
        recommendations = []

        success_rate = 0
        if model_data["success_rate"]["total"] > 0:
            success_rate = model_data["success_rate"]["successful"] / \
                model_data["success_rate"]["total"]

        if success_rate < 0.8:
            recommendations.append(
                "Model wymaga poprawy - niska skuteczność wykrywania")

        if len(model_data["typical_attributes"]) < 2:
            recommendations.append(
                "Zbyt mało atrybutów - sprawdź czy opis jest kompletny")

        return recommendations

    def generate_learning_report(self):
        """Generuje raport uczenia"""
        stats = self.learned_data["learning_statistics"]

        report = {
            "summary": {
                "total_products": stats["total_products"],
                "success_rate": round(stats["successful_extractions"] / max(1, stats["total_products"]), 2),
                "last_updated": stats["last_updated"]
            },
            "top_models": [],
            "problem_areas": [],
            "recommendations": []
        }

        # Top modele
        for model, data in self.learned_data["model_characteristics"].items():
            if data["count"] >= 3:  # Minimum 3 próbki
                insights = self.get_model_insights(model)
                if insights:
                    report["top_models"].append(insights)

        # Sortuj modele według sample size
        report["top_models"] = sorted(
            report["top_models"], key=lambda x: x["sample_size"], reverse=True)

        return report


# Globalna instancja systemu uczenia
learning_system = AgentLearningSystem()
