#!/usr/bin/env python3
"""
Baza wiedzy dla marki Marko
Zawiera specyficzne reguły, wzorce i mapowania dla produktów tej marki
Integruje się z embeddings dla lepszej klasyfikacji
"""

try:
    from marko_embeddings_knowledge import marko_embeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class MarkoKnowledgeBase:
    """Dedykowana baza wiedzy dla marki Marko"""

    def __init__(self):
        # Nazwy modeli i ich charakterystyki
        self.model_characteristics = {
            "Ada": {
                "typical_types": ["Kostium Dwuczęściowy", "Biustonosz", "Figi"],
                "common_sizes": ["S", "M", "L", "XL"],
                "typical_colors": ["Multicolor", "Black", "White", "Fioletowy"],
                # usztywniane miseczki, dolne fiszbiny, dekolt w kształcie serca, push-up, regulowane ramiączka
                # usztywniane, fiszbiny, push-up, regulowane, zapinane z tyłu
                "usual_attributes": [30, 9, 26, 15, 24]
            },
            # Można dodać więcej modeli gdy będą znane
        }

        # Wzorce opisów dla różnych typów produktów
        self.description_patterns = {
            "kostium_usztywniony": [
                "usztywniane miseczki",
                "dolne fiszbiny",
                "dekolt w kształcie serca",
                "doskonale podtrzymuje",
                "eksponuje biust"
            ],
            "kostium_push_up": [
                "push-up",
                "unosząc biust",
                "zaokrąglając",
                "większy push-up",
                "dopasowanie biustu"
            ],
            "kostium_regulowany": [
                "regulowane ramiączki",
                "odpinane ramiączki",
                "zapinany na plecach",
                "indywidualne dopasowanie",
                "maksymalny komfort"
            ],
            "figi_niski_stan": [
                "niski stan",
                "na podszewce",
                "wiązanie po bokach",
                "podkreślają biodra",
                "subtelnie podkreślają talię"
            ],
            "kostium_luksusowy": [
                "glamour zdobienia",
                "luksusowy charakter",
                "plażowe sesje zdjęciowe",
                "wyjątkowe wakacyjne chwile",
                "zmysłowy i kobiecy"
            ],
            "kostium_pakowany": [
                "pakowany w woreczek foliowy",
                "praktyczny woreczek",
                "gotowy na podróż",
                "wskazówka: zamów rozmiar większy"
            ]
        }

        # Materiały typowe dla marki Marko
        self.typical_materials = {
            "standard_swimwear": [
                {"component": "poliamid", "percentage": 80},
                {"component": "elastan", "percentage": 20}
            ],
            "premium_swimwear": [
                {"component": "poliamid", "percentage": 85},
                {"component": "elastan", "percentage": 15}
            ]
        }

        # Mapowanie kolorów producenta
        self.producer_color_mapping = {
            "Multicolor": ["wielokolorowy", "multicolor", "multcolor"],
            "Black": ["czarny", "black"],
            "White": ["biały", "white"],
            "Fioletowy": ["fioletowy", "purple", "violet"],
            "Coral": ["koralowy", "coral", "różowy"],
            "Turkus": ["turkusowy", "morski", "niebieski"]
        }

        # Reguły dla nazw serii
        self.series_name_rules = {
            "prefix": "kostium kąpielowy",
            "suffix": "- Marko",
            "exclude_from_series": [
                "S", "M", "L", "XL",  # rozmiary
                "Biustonosz", "Figi", "Push-up",  # typy produktów
                # kolory
                "Multicolor", "Black", "White", "Fioletowy", "Coral", "Turkus"
            ]
        }

    def predict_attributes_by_model(self, model_name):
        """Przewiduje prawdopodobne atrybuty na podstawie nazwy modelu"""
        if model_name in self.model_characteristics:
            return self.model_characteristics[model_name]["usual_attributes"]
        return []

    def predict_attributes_with_embeddings(self, title, description):
        """Przewiduje atrybuty wykorzystując embeddings (hybrydowe podejście)"""
        # Najpierw sprawdź bazę wiedzy
        model_name = self._extract_model_from_title(title)
        rule_based_attrs = self.predict_attributes_by_model(model_name)

        # Jeśli embeddings są dostępne, użyj ich jako uzupełnienie
        if EMBEDDINGS_AVAILABLE:
            embedding_attrs = marko_embeddings.predict_attributes_from_description(
                description)
            # Połącz atrybuty z obu źródeł
            combined_attrs = list(set(rule_based_attrs + embedding_attrs))
            return combined_attrs

        return rule_based_attrs

    def suggest_material_composition(self, product_type, model_name):
        """Sugeruje skład materiału na podstawie typu produktu i modelu"""
        if model_name in ["Ada"]:  # modele premium
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
        # Dla Marko szukamy wzorca "Kostium kąpielowy [NazwaModelu]"
        if "Kostium kąpielowy" in title:
            model_part = title.split("Kostium kąpielowy", 1)[1].strip()
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

        if any(keyword in text for keyword in ["kostium dwuczęściowy", "biustonosz", "figi"]):
            return "kostium_dwuczesciowy"
        elif any(keyword in text for keyword in ["kostium jednoczęściowy", "one-piece", "kostium jednoczęściowy"]):
            return "kostium_jednoczesciowy"
        elif any(keyword in text for keyword in ["szorty", "spodenki"]):
            return "szorty"
        else:
            return "nieznana"

    def get_category_specific_attributes(self, category, model_name):
        """Zwraca atrybuty specyficzne dla kategorii produktu"""
        base_attributes = self.predict_attributes_by_model(model_name)

        if category == "kostium_dwuczesciowy":
            # Dodaj atrybuty specyficzne dla kostiumów dwuczęściowych
            additional_attrs = [24]  # zapinane z tyłu
            return list(set(base_attributes + additional_attrs))
        elif category == "kostium_jednoczesciowy":
            # Atrybuty specyficzne dla kostiumów jednoczęściowych
            additional_attrs = [25]  # wyższy stan
            return list(set(base_attributes + additional_attrs))
        else:
            return base_attributes

    def get_category_filter_params(self, category):
        """Zwraca parametry filtrowania dla danej kategorii"""
        if category == "kostium_dwuczesciowy":
            return {
                "category_name": "Kostium Dwuczęściowy",
                "additional_params": {"product_type": "bikini"}
            }
        elif category == "kostium_jednoczesciowy":
            return {
                "category_name": "Kostium Jednoczęściowy",
                "additional_params": {"product_type": "one-piece"}
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

    def get_model_specific_info(self, model_name):
        """Zwraca specyficzne informacje o modelu"""
        if model_name in self.model_characteristics:
            return self.model_characteristics[model_name]
        return None

    def get_brand_specific_characteristics(self):
        """Zwraca charakterystyki specyficzne dla marki Marko"""
        return {
            "brand_style": "luksusowy, kobiecy, zmysłowy",
            "target_audience": "kobiety szukające elegancji na plaży",
            "special_features": ["push-up", "usztywniane miseczki", "dekolt w kształcie serca"],
            "packaging": "praktyczny woreczek foliowy",
            "sizing_advice": "zamów rozmiar większy niż zazwyczaj"
        }

    def learn_from_product(self, product_id, title, description, category, attributes, model_name=None):
        """Uczy się z nowego produktu - dodaje do embeddings"""
        if EMBEDDINGS_AVAILABLE:
            marko_embeddings.add_product_embedding(
                product_id=product_id,
                title=title,
                description=description,
                category=category,
                attributes=attributes,
                model_name=model_name
            )
            print(f"🧠 Nauczono się z produktu {product_id}: {title}")

    def get_smart_predictions(self, title, description):
        """Zwraca inteligentne przewidywania wykorzystując embeddings"""
        predictions = {
            "category": self.get_product_category(title, description),
            "model_name": None,
            "attributes": [],
            "similar_products": [],
            "confidence": 0.0
        }

        if EMBEDDINGS_AVAILABLE:
            # Użyj embeddings do lepszych przewidywań
            predictions["category"] = marko_embeddings.predict_category_from_description(
                title, description)
            predictions["model_name"] = marko_embeddings.predict_model_name(
                title, description)
            predictions["attributes"] = self.predict_attributes_with_embeddings(
                title, description)
            predictions["similar_products"] = marko_embeddings.find_similar_products(
                f"{title} {description}", limit=3
            )

            # Oblicz pewność na podstawie liczby podobnych produktów
            if predictions["similar_products"]:
                similarities = [p.get("similarity", 0)
                                for p in predictions["similar_products"]]
                predictions["confidence"] = sum(
                    similarities) / len(similarities)
        else:
            # Fallback do reguł bazowych
            predictions["model_name"] = self._extract_model_from_title(title)
            predictions["attributes"] = self.predict_attributes_by_model(
                predictions["model_name"])

        return predictions

    def get_learning_statistics(self):
        """Zwraca statystyki uczenia się"""
        if EMBEDDINGS_AVAILABLE:
            return marko_embeddings.get_embedding_statistics()
        else:
            return {
                "embeddings_available": False,
                "total_products": 0,
                "message": "Embeddings nie są dostępne"
            }


# Globalna instancja bazy wiedzy
marko_knowledge = MarkoKnowledgeBase()
