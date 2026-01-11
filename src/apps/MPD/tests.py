"""
Testy dla aplikacji MPD
Testy modeli i views
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import (
    Brands, Colors, Products, ProductVariants,
    Sizes, Attributes, ProductAttribute, Sources
)


class BrandsModelTest(TestCase):
    """Testy dla modelu Brands"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brands.objects.create(
            name='Test Brand',
            logo_url='https://example.com/logo.jpg',
            opis='Test Description',
            url='https://example.com',
            iai_brand_id=123
        )

    def test_brand_creation(self):
        """Test tworzenia marki"""
        self.assertEqual(self.brand.name, 'Test Brand')
        self.assertEqual(self.brand.logo_url, 'https://example.com/logo.jpg')
        self.assertEqual(self.brand.opis, 'Test Description')
        self.assertEqual(self.brand.url, 'https://example.com')
        self.assertEqual(self.brand.iai_brand_id, 123)

    def test_brand_str(self):
        """Test metody __str__"""
        self.assertEqual(str(self.brand), 'Test Brand')

    def test_brand_str_no_name(self):
        """Test metody __str__ gdy brak nazwy"""
        brand = Brands.objects.create()
        self.assertEqual(str(brand), 'Brak nazwy')


class ColorsModelTest(TestCase):
    """Testy dla modelu Colors"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.color = Colors.objects.create(
            name='Red',
            hex_code='#FF0000',
            iai_colors_id=1
        )

    def test_color_creation(self):
        """Test tworzenia koloru"""
        self.assertEqual(self.color.name, 'Red')
        self.assertEqual(self.color.hex_code, '#FF0000')
        self.assertEqual(self.color.iai_colors_id, 1)

    def test_color_str(self):
        """Test metody __str__"""
        self.assertEqual(str(self.color), 'Red')

    def test_color_parent_relationship(self):
        """Test relacji parent"""
        parent_color = Colors.objects.create(
            name='Primary Color',
            hex_code='#000000'
        )
        child_color = Colors.objects.create(
            name='Shade of Primary',
            hex_code='#111111',
            parent_id=parent_color
        )

        self.assertEqual(child_color.parent_id, parent_color)


class ProductsModelTest(TestCase):
    """Testy dla modelu Products"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brands.objects.create(
            name='Test Brand'
        )
        self.product = Products.objects.create(
            name='Test Product',
            description='Test Description',
            short_description='Short Desc',
            brand=self.brand,
            visibility=True
        )

    def test_product_creation(self):
        """Test tworzenia produktu"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.description, 'Test Description')
        self.assertEqual(self.product.short_description, 'Short Desc')
        self.assertEqual(self.product.brand, self.brand)
        self.assertTrue(self.product.visibility)

    def test_product_str(self):
        """Test metody __str__"""
        self.assertEqual(str(self.product), 'Test Product')

    def test_product_get_brand_name(self):
        """Test metody get_brand_name"""
        self.assertEqual(self.product.get_brand_name(), 'Test Brand')

    def test_product_get_brand_name_no_brand(self):
        """Test metody get_brand_name gdy brak marki"""
        product = Products.objects.create(
            name='Product Without Brand'
        )
        self.assertEqual(product.get_brand_name(), 'Brak marki')


class ProductVariantsModelTest(TestCase):
    """Testy dla modelu ProductVariants"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brands.objects.create(
            name='Test Brand'
        )
        self.product = Products.objects.create(
            name='Test Product',
            brand=self.brand
        )
        self.color = Colors.objects.create(
            name='Red',
            hex_code='#FF0000'
        )
        self.size = Sizes.objects.create(
            name='M',
            category='Clothing'
        )

    def test_variant_creation(self):
        """Test tworzenia wariantu"""
        variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            producer_code='PROD001',
            iai_product_id=12345,
            exported_to_iai=False
        )

        self.assertEqual(variant.product, self.product)
        self.assertEqual(variant.color, self.color)
        self.assertEqual(variant.size, self.size)
        self.assertEqual(variant.producer_code, 'PROD001')
        self.assertEqual(variant.iai_product_id, 12345)
        self.assertFalse(variant.exported_to_iai)

    def test_variant_str(self):
        """Test metody __str__"""
        variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size
        )
        expected = f"{self.product.name} - {self.color.name} - {self.size.name}"
        self.assertEqual(str(variant), expected)

    def test_variant_str_no_color(self):
        """Test metody __str__ gdy brak koloru"""
        variant = ProductVariants.objects.create(
            product=self.product,
            size=self.size
        )
        self.assertIn('Brak koloru', str(variant))

    def test_variant_str_no_size(self):
        """Test metody __str__ gdy brak rozmiaru"""
        variant = ProductVariants.objects.create(
            product=self.product,
            color=self.color
        )
        self.assertIn('Brak rozmiaru', str(variant))


class SizesModelTest(TestCase):
    """Testy dla modelu Sizes"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.size = Sizes.objects.create(
            name='M',
            category='Clothing',
            unit='EU',
            name_lower='m',
            iai_size_id='SIZE001'
        )

    def test_size_creation(self):
        """Test tworzenia rozmiaru"""
        self.assertEqual(self.size.name, 'M')
        self.assertEqual(self.size.category, 'Clothing')
        self.assertEqual(self.size.unit, 'EU')
        self.assertEqual(self.size.name_lower, 'm')
        self.assertEqual(self.size.iai_size_id, 'SIZE001')

    def test_size_str(self):
        """Test metody __str__"""
        self.assertEqual(str(self.size), 'M')


class AttributesModelTest(TestCase):
    """Testy dla modelu Attributes"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.attribute = Attributes.objects.create(
            name='Material'
        )

    def test_attribute_creation(self):
        """Test tworzenia atrybutu"""
        self.assertEqual(self.attribute.name, 'Material')

    def test_attribute_str(self):
        """Test metody __str__"""
        self.assertEqual(str(self.attribute), 'Material')


class ProductAttributeModelTest(TestCase):
    """Testy dla modelu ProductAttribute"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brands.objects.create(
            name='Test Brand'
        )
        self.product = Products.objects.create(
            name='Test Product',
            brand=self.brand
        )
        self.attribute = Attributes.objects.create(
            name='Material'
        )

    def test_product_attribute_creation(self):
        """Test tworzenia atrybutu produktu"""
        product_attribute = ProductAttribute.objects.create(
            product=self.product,
            attribute=self.attribute
        )

        self.assertEqual(product_attribute.product, self.product)
        self.assertEqual(product_attribute.attribute, self.attribute)

    def test_product_attribute_str(self):
        """Test metody __str__"""
        product_attribute = ProductAttribute.objects.create(
            product=self.product,
            attribute=self.attribute
        )
        self.assertEqual(str(product_attribute), 'Material')

    def test_product_attribute_unique_together(self):
        """Test unikalności kombinacji product + attribute"""
        ProductAttribute.objects.create(
            product=self.product,
            attribute=self.attribute
        )

        # Próba utworzenia duplikatu powinna zwrócić błąd
        with self.assertRaises(Exception):
            ProductAttribute.objects.create(
                product=self.product,
                attribute=self.attribute
            )


class SourcesModelTest(TestCase):
    """Testy dla modelu Sources"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.source = Sources.objects.create(
            name='Test Source',
            location='Warsaw',
            type='Supplier',
            long_name='Test Source Long Name',
            short_name='TS',
            showcase_image='https://example.com/image.jpg',
            email='test@example.com',
            tel='123456789',
            fax='987654321',
            www='https://example.com',
            street='Test Street 1',
            zipcode='00-000',
            city='Warsaw',
            country='Poland',
            province='Mazowieckie'
        )

    def test_source_creation(self):
        """Test tworzenia źródła"""
        self.assertEqual(self.source.name, 'Test Source')
        self.assertEqual(self.source.location, 'Warsaw')
        self.assertEqual(self.source.type, 'Supplier')
        self.assertEqual(self.source.email, 'test@example.com')
        self.assertEqual(self.source.city, 'Warsaw')
        self.assertEqual(self.source.country, 'Poland')


# ==================== API TESTS ====================


class GenerateFullXMLSecureAPITest(APITestCase):
    """Testy API dla generowania pełnego XML"""
    databases = {'default', 'MPD'}  # Zezwól na zapytania do bazy MPD

    def setUp(self):
        """Przygotowanie danych testowych"""
        # Utwórz użytkownika admina
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        self.token = Token.objects.create(user=self.admin_user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_generate_full_xml_requires_admin(self):
        """Test czy generowanie XML wymaga uprawnień admina"""
        # Zwykły użytkownik
        regular_user = User.objects.create_user(
            username='regular',
            password='regularpass123'
        )
        regular_token = Token.objects.create(user=regular_user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + regular_token.key)

        url = '/mpd/generate-full-xml-secure/'
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_generate_full_xml_requires_auth(self):
        """Test czy generowanie XML wymaga autoryzacji"""
        client = APIClient()
        url = '/mpd/generate-full-xml-secure/'
        response = client.post(url)
        # DRF może zwracać 403 (Forbidden) zamiast 401
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    def test_generate_full_xml_endpoint_exists(self):
        """Test czy endpoint istnieje i zwraca odpowiedź"""
        url = '/mpd/generate-full-xml-secure/'
        response = self.client.post(url)
        # Może zwrócić 200 (sukces) lub 500 (błąd w eksporcie), ale nie 404
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])


class MPDProductModelIntegrationTest(TestCase):
    """Testy integracyjne dla modeli MPD"""

    def setUp(self):
        """Przygotowanie danych testowych"""
        self.brand = Brands.objects.create(
            name='Test Brand',
            iai_brand_id=100
        )
        self.color = Colors.objects.create(
            name='Blue',
            hex_code='#0000FF',
            iai_colors_id=1
        )
        self.size = Sizes.objects.create(
            name='L',
            category='Clothing',
            iai_size_id='SIZE_L'
        )
        self.product = Products.objects.create(
            name='Test Product',
            description='Full Description',
            short_description='Short',
            brand=self.brand,
            visibility=True
        )

    def test_product_with_variants(self):
        """Test produktu z wariantami"""
        variant1 = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            producer_code='PROD001',
            exported_to_iai=True
        )

        variant2 = ProductVariants.objects.create(
            product=self.product,
            color=self.color,
            size=None,
            producer_code='PROD002',
            exported_to_iai=False
        )

        self.assertEqual(self.product.productvariants_set.count(), 2)
        self.assertTrue(variant1.exported_to_iai)
        self.assertFalse(variant2.exported_to_iai)

    def test_product_with_attributes(self):
        """Test produktu z atrybutami"""
        attribute1 = Attributes.objects.create(name='Material')
        attribute2 = Attributes.objects.create(name='Color')

        ProductAttribute.objects.create(
            product=self.product,
            attribute=attribute1
        )
        ProductAttribute.objects.create(
            product=self.product,
            attribute=attribute2
        )

        self.assertEqual(self.product.product_attributes.count(), 2)
        attribute_names = [attr.attribute.name for attr in self.product.product_attributes.all()]
        self.assertIn('Material', attribute_names)
        self.assertIn('Color', attribute_names)
