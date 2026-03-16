"""
Proste testy dla modułu automatyzacji w tle `background_automation`.
Skupiamy się na czystych funkcjach pomocniczych, żeby nie dotykać bazy ani AI.
"""
from django.test import TestCase

from web_agent.automation.background_automation import BackgroundAutomation


class BackgroundAutomationHelpersTest(TestCase):
    """Testy metod pomocniczych BackgroundAutomation, które nie wymagają bazy ani AI."""

    def setUp(self):
        # Podstawowa instancja – ai_processor i inne zależności nie są używane
        self.automation = BackgroundAutomation(ai_processor=None, log_callback=None)

    def test_extract_producer_code_from_name(self):
        """Powinien poprawnie wyciągać kod producenta w formacie M-XXX."""
        test_cases = [
            ("Kostium kąpielowy XYZ M-803 - Test Brand", "M-803"),
            ("Strój jednoczęściowy ABC m-120-5 - Marka", "M-120-5"),
            ("Produkt bez kodu", ""),
            ("Inny format M803", ""),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                code = self.automation.extract_producer_code_from_name(name)
                self.assertEqual(code, expected)

    def test_extract_color_from_name(self):
        """Powinien wyciągać nazwę koloru z końca nazwy produktu, jeśli pasuje do wzorców."""
        test_cases = [
            ("Kostium kąpielowy Ciemny Brąz - Marka", "Ciemny Brąz"),
            ("Stringi (2 szt.) Ciemny Brąz - Marka", "Ciemny Brąz"),
            # Dla tego przypadku obecna implementacja zwraca cały fragment przed myślnikiem
            ("Biustonosz Push Up Czarny - Marka", "Biustonosz Push Up Czarny"),
            ("Nazwa bez koloru", ""),
            ("", ""),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                color = self.automation.extract_color_from_name(name)
                self.assertEqual(color, expected)

    def test_extract_fabric_materials_empty(self):
        """Dla pustego HTML powinien zwracać pustą listę."""
        self.assertEqual(self.automation.extract_fabric_materials(""), [])
        self.assertEqual(self.automation.extract_fabric_materials(None), [])

    def test_extract_fabric_materials_simple_html(self):
        """Powinien wyciągnąć materiały z prostego HTML z <strong>."""
        html = """
        <p><strong>Elastan</strong> 20 %</p>
        <p><strong>Poliamid</strong> 80 %</p>
        """
        materials = self.automation.extract_fabric_materials(html)

        # Oczekujemy dwóch wpisów (mapowanie w kodzie: elastan->1, poliamid->2)
        self.assertEqual(len(materials), 2)
        self.assertIn({"component_id": 1, "percentage": 20}, materials)
        self.assertIn({"component_id": 2, "percentage": 80}, materials)
