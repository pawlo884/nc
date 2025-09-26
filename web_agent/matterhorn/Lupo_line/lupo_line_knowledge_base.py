#!/usr/bin/env python3
"""
Baza wiedzy dla marki Lupo Line
Zawiera specyficzne reguły, wzorce i mapowania dla produktów tej marki
"""


class LupoLineKnowledgeBase:
    """Dedykowana baza wiedzy dla marki Lupo Line"""

    def __init__(self):
        # Nazwy modeli i ich charakterystyki
        self.model_characteristics = {
            "Sofia": {
                "typical_types": ["Figi", "Biustonosz", "Strój Jednoczęściowy"],
                "common_sizes": ["Big", "Small"],
                "typical_colors": ["Black", "Multicolor", "White"],
                # regulowane, regulowane ramiączka
                "usual_attributes": [26, 15]
            },
            "Ember": {
                "typical_types": ["Biustonosz", "Bralet", "Strój Jednoczęściowy"],
                "common_sizes": ["Big"],
                "typical_colors": ["Multicolor", "Black"],
                # na fiszbinach, usztywniane miseczki
                "usual_attributes": [9, 30]
            },
            "Aqua": {
                "typical_types": ["Biustonosz", "Kopa", "Strój Jednoczęściowy"],
                "common_sizes": ["Big", "Small"],
                "typical_colors": ["Turkus", "Blue"],
                # usztywniane miseczki, wiązane na szyi, zapinane z tyłu
                "usual_attributes": [30, 29, 24]
            },
            "Wave": {
                "typical_types": ["Biustonosz", "Strój Jednoczęściowy"],
                "common_sizes": ["Big"],
                "typical_colors": ["Multicolor", "Black"],
                # miękkie miseczki, na fiszbinach, regulowane ramiączka, nieodpinane, duży biust
                "usual_attributes": [27, 9, 15, 23, 5]
            },
            "Mirage": {
                "typical_types": ["Figi", "Strój Jednoczęściowy"],
                "common_sizes": ["Big"],
                "typical_colors": ["Multicolor", "Black"],
                "usual_attributes": [25, 26]  # wyższy stan, regulowane
            },
            "Coral": {
                "typical_types": ["Biustonosz", "Figi", "Strój Jednoczęściowy"],
                "common_sizes": ["Big", "Small"],
                # Coral to nazwa modelu, nie kolor!
                "typical_colors": ["Coral"],
                "usual_attributes": [26, 15]
            },
            "Gabriella": {
                "typical_types": ["Szorty Kąpielowe", "Strój Jednoczęściowy"],
                "common_sizes": ["Big", "Small"],
                "typical_colors": ["Multicolor", "Black"],
                # regulowane, wyższy stan (prawdopodobnie)
                "usual_attributes": [26, 25]
            }
        }

        # Wzorce opisów dla różnych typów produktów
        self.description_patterns = {
            "figi_regulowane": [
                "wiązane na troczki",
                "umożliwiają regulację",
                "ściągane sznureczki",
                "regulowane po bokach"
            ],
            "biustonosz_usztywniony": [
                "usztywniony fiszbinami",
                "usztywniane miseczki",
                "doskonale podtrzymuje",
                "modeluje biust"
            ],
            "biustonosz_miekki": [
                "miękkie miseczki",
                "soft cup",
                "bez fiszbina",
                "naturalny kształt"
            ],
            "wiazany_na_szyi": [
                "wiązany na szyi",
                "wiązane na szyi",
                "halter",
                "wiązanie na karku"
            ],
            "stroj_jednoczesciowy": [
                "strój jednoczęściowy",
                "one-piece",
                "kostium jednoczęściowy",
                "cały strój"
            ],
            "stroj_jednoczesciowy_z_biustonoszem": [
                "z wbudowanym biustonoszem",
                "biustonosz w stroju",
                "usztywniany biustonosz",
                "podtrzymujący biust"
            ],
            "stroj_jednoczesciowy_regulowany": [
                "regulowane ramiączka",
                "możliwość regulacji",
                "dostosowywany",
                "elastyczny"
            ]
        }

        # Materiały typowe dla marki
        self.typical_materials = {
            "standard_swimwear": [
                {"component": "poliamid", "percentage": 85},
                {"component": "elastan", "percentage": 15}
            ],
            "premium_swimwear": [
                {"component": "poliamid", "percentage": 80},
                {"component": "elastan", "percentage": 20}
            ]
        }

        # Mapowanie kolorów producenta
        self.producer_color_mapping = {
            "Multicolor": ["wielokolorowy", "multicolor", "multcolor"],
            "Black": ["czarny", "black"],
            "White": ["biały", "white"],
            "Turkus": ["turkusowy", "morski", "niebieski"],
            "Coral": ["koralowy", "coral", "różowy"]
        }

        # Reguły dla nazw serii
        self.series_name_rules = {
            "prefix": "strój kąpielowy",
            "suffix": "- Lupo Line",
            "exclude_from_series": [
                "Big", "Small",  # rozmiary
                "Bralet", "Kopa", "Push-up",  # typy produktów
                # kolory (z wyjątkiem Coral jako model)
                "Multicolor", "Black", "White", "Turkus", "Coral"
            ]
        }

    def predict_attributes_by_model(self, model_name):
        """Przewiduje prawdopodobne atrybuty na podstawie nazwy modelu"""
        if model_name in self.model_characteristics:
            return self.model_characteristics[model_name]["usual_attributes"]
        return []

    def suggest_material_composition(self, product_type, model_name):
        """Sugeruje skład materiału na podstawie typu produktu i modelu"""
        if model_name in ["Wave", "Aqua"]:  # modele premium
            return self.typical_materials["premium_swimwear"]
        else:
            return self.typical_materials["standard_swimwear"]

    def validate_product_consistency(self, title, description, attributes):
        """Sprawdza spójność produktu z bazą wiedzy marki"""
        issues = []

        # Wyciągnij nazwę modelu z tytułu
        model_name = self._extract_model_from_title(title)

        if model_name and model_name in self.model_characteristics:
            expected_attrs = self.model_characteristics[model_name]["usual_attributes"]

            # Sprawdź czy brakuje typowych atrybutów
            missing_attrs = set(expected_attrs) - set(attributes)
            if missing_attrs:
                issues.append({
                    "type": "missing_typical_attributes",
                    "model": model_name,
                    "missing": list(missing_attrs),
                    "suggestion": f"Model {model_name} zwykle ma te atrybuty"
                })

        return issues

    def enhance_description_analysis(self, description):
        """Wzbogaca analizę opisu o wiedzę specyficzną dla marki"""
        enhanced_patterns = []

        for pattern_type, keywords in self.description_patterns.items():
            for keyword in keywords:
                if keyword.lower() in description.lower():
                    enhanced_patterns.append({
                        "pattern": pattern_type,
                        "keyword": keyword,
                        "confidence": self._calculate_confidence(keyword, description)
                    })

        return enhanced_patterns

    def get_smart_color_suggestions(self, title):
        """Inteligentne sugestie kolorów na podstawie tytułu"""
        suggestions = []

        for producer_color, variants in self.producer_color_mapping.items():
            for variant in variants:
                if variant.lower() in title.lower():
                    suggestions.append({
                        "producer_color": producer_color,
                        "detected_variant": variant,
                        "confidence": 0.9 if variant == producer_color else 0.7
                    })

        return suggestions

    def _extract_model_from_title(self, title):
        """Wyciąga nazwę modelu z tytułu"""
        if "Model " in title:
            model_part = title.split("Model ", 1)[1]
            model_name = model_part.split()[0] if model_part.split() else ""
            return model_name
        return None

    def _calculate_confidence(self, keyword, description):
        """Oblicza pewność dopasowania wzorca"""
        # Prosta heurystyka - można rozbudować
        if keyword in description:
            return 0.9
        elif keyword.lower() in description.lower():
            return 0.8
        else:
            return 0.5

    def get_product_category(self, title, description=""):
        """Określa kategorię produktu na podstawie tytułu i opisu"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ["strój jednoczęściowy", "one-piece", "kostium jednoczęściowy"]):
            return "stroj_jednoczesciowy"
        elif any(keyword in text for keyword in ["biustonosz", "bralet", "figi", "kopa"]):
            return "biustonosz"
        elif any(keyword in text for keyword in ["szorty", "spodenki"]):
            return "szorty"
        else:
            return "nieznana"

    def get_category_specific_attributes(self, category, model_name):
        """Zwraca atrybuty specyficzne dla kategorii produktu"""
        base_attributes = self.predict_attributes_by_model(model_name)
        
        if category == "stroj_jednoczesciowy":
            # Dodaj atrybuty specyficzne dla strojów jednoczęściowych
            additional_attrs = [25]  # wyższy stan
            return list(set(base_attributes + additional_attrs))
        elif category == "biustonosz":
            # Atrybuty specyficzne dla biustonoszy
            return base_attributes
        else:
            return base_attributes

    def get_category_filter_params(self, category):
        """Zwraca parametry filtrowania dla danej kategorii"""
        if category == "stroj_jednoczesciowy":
            return {
                "category_name": "Strój Jednoczęściowy",
                "additional_params": {"product_type": "one-piece"}
            }
        elif category == "biustonosz":
            return {
                "category_name": "Biustonosz",
                "additional_params": {"product_type": "bra"}
            }
        else:
            return {
                "category_name": None,
                "additional_params": {}
            }

    def validate_category_consistency(self, title, description, category):
        """Sprawdza spójność kategorii z treścią produktu"""
        detected_category = self.get_product_category(title, description)
        
        if detected_category != category:
            return {
                "type": "category_mismatch",
                "expected": category,
                "detected": detected_category,
                "suggestion": f"Produkt wydaje się być {detected_category}, nie {category}"
            }
        return None


# Globalna instancja bazy wiedzy
lupo_knowledge = LupoLineKnowledgeBase()
