#!/usr/bin/env python3
"""
Baza wiedzy z embeddings dla marki Marko
Wykorzystuje embeddings do semantycznego wyszukiwania i klasyfikacji produktów
"""

import json
import os
import numpy as np
from typing import List, Dict, Optional
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn nie jest zainstalowany. Uruchom: pip install scikit-learn numpy")

# Próba importu OpenAI dla embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class MarkoEmbeddingsKnowledge:
    """Baza wiedzy wykorzystująca embeddings dla marki Marko"""

    def __init__(self, embeddings_file="marko_embeddings.json", model_file="marko_model.pkl"):
        self.embeddings_file = embeddings_file
        self.model_file = model_file
        self.embeddings_data = {}
        self.vectorizer = None
        self.cluster_model = None
        self.openai_client = None

        if OPENAI_AVAILABLE:
            self.openai_client = OpenAI()

        self._load_embeddings()
        self._initialize_models()

    def _load_embeddings(self):
        """Ładuje zapisane embeddings z pliku"""
        if os.path.exists(self.embeddings_file):
            try:
                with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                    self.embeddings_data = json.load(f)
                print(f"✅ Załadowano embeddings z {self.embeddings_file}")
            except Exception as e:
                print(f"⚠️ Błąd ładowania embeddings: {e}")
                self.embeddings_data = {}
        else:
            print(
                f"📝 Tworzenie nowego pliku embeddings: {self.embeddings_file}")
            self.embeddings_data = {
                "products": [],
                "patterns": [],
                "categories": [],
                "last_updated": None
            }

    def _initialize_models(self):
        """Inicjalizuje modele ML"""
        if not SKLEARN_AVAILABLE:
            self.vectorizer = None
            self.cluster_model = None
            return

        # TF-IDF vectorizer dla lokalnych embeddings
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # Polskie słowa nie są w standardowych stop words
            ngram_range=(1, 2)
        )

        # K-means dla klasteryzacji
        self.cluster_model = KMeans(n_clusters=5, random_state=42)

    def generate_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Generuje embedding za pomocą OpenAI API"""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ Błąd generowania OpenAI embedding: {e}")
            return None

    def generate_local_embedding(self, text: str) -> np.ndarray:
        """Generuje lokalny embedding za pomocą TF-IDF"""
        if not SKLEARN_AVAILABLE or not self.vectorizer:
            # Fallback - zwróć pusty array
            return np.array([])

        if not hasattr(self, '_fitted_vectorizer'):
            # Pierwszy raz - fit na wszystkich tekstach
            all_texts = []
            for product in self.embeddings_data.get("products", []):
                all_texts.append(
                    f"{product.get('title', '')} {product.get('description', '')}")

            if all_texts:
                self.vectorizer.fit(all_texts)
                self._fitted_vectorizer = True
            else:
                # Fallback - fit na przykładowych tekstach
                sample_texts = [
                    "kostium kąpielowy usztywniane miseczki",
                    "biustonosz push-up regulowane ramiączka",
                    "figi niski stan wiązanie po bokach"
                ]
                self.vectorizer.fit(sample_texts)
                self._fitted_vectorizer = True

        return self.vectorizer.transform([text]).toarray()[0]

    def add_product_embedding(self, product_id: int, title: str, description: str,
                              category: str, attributes: List[int], model_name: str = None):
        """Dodaje embedding produktu do bazy wiedzy"""
        text = f"{title} {description}".lower()

        # Generuj embeddings
        openai_embedding = self.generate_openai_embedding(text)
        local_embedding = self.generate_local_embedding(text).tolist()

        product_data = {
            "id": product_id,
            "title": title,
            "description": description,
            "category": category,
            "attributes": attributes,
            "model_name": model_name,
            "openai_embedding": openai_embedding,
            "local_embedding": local_embedding,
            "text": text
        }

        # Sprawdź czy produkt już istnieje
        existing_idx = None
        for i, existing in enumerate(self.embeddings_data.get("products", [])):
            if existing.get("id") == product_id:
                existing_idx = i
                break

        if existing_idx is not None:
            self.embeddings_data["products"][existing_idx] = product_data
        else:
            self.embeddings_data["products"].append(product_data)

        self._save_embeddings()

    def find_similar_products(self, query_text: str, limit: int = 5) -> List[Dict]:
        """Znajduje podobne produkty na podstawie zapytania"""
        query_embedding = self.generate_local_embedding(query_text.lower())
        products = self.embeddings_data.get("products", [])

        if not products:
            return []

        similarities = []
        for product in products:
            if product.get("local_embedding"):
                product_embedding = np.array(product["local_embedding"])
                similarity = cosine_similarity(
                    [query_embedding], [product_embedding])[0][0]
                similarities.append((similarity, product))

        # Sortuj według podobieństwa
        similarities.sort(key=lambda x: x[0], reverse=True)

        return [product for similarity, product in similarities[:limit]]

    def predict_attributes_from_description(self, description: str) -> List[int]:
        """Przewiduje atrybuty na podstawie opisu produktu"""
        # Znajdź podobne produkty
        similar_products = self.find_similar_products(description, limit=10)

        if not similar_products:
            return []

        # Zbierz wszystkie atrybuty z podobnych produktów
        all_attributes = []
        for product in similar_products:
            all_attributes.extend(product.get("attributes", []))

        # Policz częstotliwość atrybutów
        from collections import Counter
        attribute_counts = Counter(all_attributes)

        # Zwróć najczęściej występujące atrybuty (powyżej progu)
        threshold = max(1, len(similar_products) // 3)
        predicted_attributes = [
            attr for attr, count in attribute_counts.items()
            if count >= threshold
        ]

        return predicted_attributes

    def predict_category_from_description(self, title: str, description: str) -> str:
        """Przewiduje kategorię na podstawie opisu"""
        text = f"{title} {description}".lower()
        similar_products = self.find_similar_products(text, limit=5)

        if not similar_products:
            return "nieznana"

        # Policz kategorie
        from collections import Counter
        categories = [p.get("category", "nieznana") for p in similar_products]
        category_counts = Counter(categories)

        # Zwróć najczęstszą kategorię
        return category_counts.most_common(1)[0][0]

    def predict_model_name(self, title: str, description: str) -> Optional[str]:
        """Przewiduje nazwę modelu na podstawie opisu"""
        text = f"{title} {description}".lower()
        similar_products = self.find_similar_products(text, limit=5)

        if not similar_products:
            return None

        # Znajdź najczęściej występujący model
        from collections import Counter
        models = [p.get("model_name")
                  for p in similar_products if p.get("model_name")]

        if not models:
            return None

        model_counts = Counter(models)
        return model_counts.most_common(1)[0][0]

    def get_embedding_statistics(self) -> Dict:
        """Zwraca statystyki embeddings"""
        products = self.embeddings_data.get("products", [])

        if not products:
            return {"total_products": 0}

        categories = [p.get("category", "nieznana") for p in products]
        models = [p.get("model_name") for p in products if p.get("model_name")]

        from collections import Counter

        return {
            "total_products": len(products),
            "categories": dict(Counter(categories)),
            "models": dict(Counter(models)),
            "has_openai_embeddings": any(p.get("openai_embedding") for p in products),
            "last_updated": self.embeddings_data.get("last_updated")
        }

    def cluster_products(self, n_clusters: int = 5) -> Dict:
        """Klasteryzuje produkty na podstawie embeddings"""
        products = self.embeddings_data.get("products", [])

        if len(products) < n_clusters:
            return {"error": "Za mało produktów do klasteryzacji"}

        # Przygotuj embeddings
        embeddings = []
        product_ids = []

        for product in products:
            if product.get("local_embedding"):
                embeddings.append(product["local_embedding"])
                product_ids.append(product["id"])

        if not embeddings:
            return {"error": "Brak embeddings do klasteryzacji"}

        # Klasteryzacja
        embeddings_array = np.array(embeddings)
        clusters = self.cluster_model.fit_predict(embeddings_array)

        # Grupuj produkty według klastrów
        cluster_groups = {}
        for product_id, cluster in zip(product_ids, clusters):
            if cluster not in cluster_groups:
                cluster_groups[cluster] = []
            cluster_groups[cluster].append(product_id)

        return {
            "n_clusters": n_clusters,
            "clusters": cluster_groups,
            "total_products": len(product_ids)
        }

    def _save_embeddings(self):
        """Zapisuje embeddings do pliku"""
        import datetime
        self.embeddings_data["last_updated"] = datetime.datetime.now(
        ).isoformat()

        try:
            with open(self.embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_data, f,
                          ensure_ascii=False, indent=2)
            print(f"💾 Zapisano embeddings do {self.embeddings_file}")
        except Exception as e:
            print(f"❌ Błąd zapisywania embeddings: {e}")

    def export_embeddings_for_analysis(self, output_file: str = "marko_embeddings_analysis.json"):
        """Eksportuje embeddings do analizy"""
        analysis_data = {
            "statistics": self.get_embedding_statistics(),
            "clusters": self.cluster_products(),
            # Pierwsze 10 produktów
            "sample_products": self.embeddings_data.get("products", [])[:10]
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            print(f"📊 Eksportowano analizę do {output_file}")
        except Exception as e:
            print(f"❌ Błąd eksportu: {e}")


# Globalna instancja embeddings knowledge
marko_embeddings = MarkoEmbeddingsKnowledge()
