Struktura i jej opis
Plik full.xml jest pierwszym podstawowym plikiem oferty IOF zawierającym podstawowe informacje o towarach np. opisy, zdjęcia, atrybuty, załączniki czy grupy towarów bądź składowe zestawów i kolekcji.

Szczegółowe informacje na temat domyślnego języka oferty (wymagany atrybut @language) oraz waluty oferowanych towarów (wymagany atrybut @currency zgodny z normą ISO-4217) znajdują się w węźle <products>.

W węźle <products> umieszczony jest również węzeł <product> zawierający wszystkie szczegóły pojedynczego produktu: nazwę, opis, kategorię, producenta, jednostkę miary, rozmiary, serię, gwarancję, parametry, cenę wywoławczą, cenę przekreśloną, sugerowaną cenę detaliczną, adres URL, zdjecia i ikony, jak również składowe w przypadku zestawów i kolekcji.

Każdy produkt (węzeł <product>) posiada unikalny identyfikator (wymagany atrybut @id) oraz stawkę VAT (opcjonalny atrybut @vat)

Ceny
Wszystkie zwracane w pliku ceny:

cena towaru zawarta w węźle <product><price>,
sugerowana cena towaru zawarta w węźle <product><srp>,
przekreślona cena detaliczna towaru zawarta w węźle <product><strikethrough_retail_price>,
przekreślona cena hurtowa towaru zawarta w węźle <product><strikethrough_wholesale_price>,
cena rozmiaru zawarta w węźle <product><sizes><size><price>,
sugerowana cena rozmiaru zawarta w węźle <product><sizes><size><srp>,
przekreślona cena detaliczna rozmiaru zawarta w węźle <product><sizes><size><strikethrough_retail_price>,
przekreślona cena hurtowa rozmiaru zawarta w węźle <product><sizes><size><strikethrough_wholesale_price>.
są automatycznie przeliczane na walutę klienta docelowego (atrybut @currency zgodny z normą ISO-4217 w węźle <products> ), ale bez uwzględnienia rabatów przypisanych do jego konta w serwisie dostawcy (informacje o tych cenach pomniejszonych o rabat klienta zwracane są w pliku light.xml i mają najwyższy priorytet).

Węzeł każdej ceny zawiera informacje o wartości brutto (opcjonalny atrybut @gross) oraz o wartości netto (wymagany atrybut @net).

Rozmiary
Każdy dostępny w pliku rozmiar (węzeł <size>) opisywany jest przez następujące atrybuty:

Atrybuty wymagane:

@id – identyfikator rozmiaru,
@code – unikalny kod IAI produktu np. 1454-03.
Atrybuty opcjonalne:

@panel_name - unikalna nazwa rozmiaru,
@name - nazwa rozmiaru wyświetlana w sklepie (nie musi być unikalna),
@code_producer – kod producenta,
@iaiext:code_external - kod zew. systemu (atrybut rozszerzenia IOF Extensions),
@weight – waga produktu w opakowaniu podana w gramach,
@iaiext:weight_net - waga produktu bez opakowania podana w gramach (atrybut rozszerzenia IOF Extensions).

Nazwa, opisy i zdjęcia
Nazwa towaru oraz jego opisy umieszczone są w węźle <description>. Każdy z jego elementów może być zdefiniowany w wielu językach (opcjonalny atrybut @xml:lang).

Zdjęcia oraz ikony umieszczone są w węźle <images>. Każde zdjęcie lub ikony mogą być opisane za pomocą opcjonalnych atrybutów:

daty ostatniej modyfikacji w formacie YYYY-MM-DD hh:mm:ss (atrybut @changed),
klucza md5 (atrybut @hash),
szerokości obrazu w pikselach (atrybut @width),
wysokości obrazu w pikselach (atrybut @height).

Zależności między danymi:
product.category@id jest ściśle powiązany z categories.category@id w pliku categories.xml,
product.producer@id jest ściśle powiązany z producers.producer@id w pliku producers.xml,
product.unit@id jest ściśle powiązany z units.unit@id w pliku units.xml,
product.series@id jest ściśle powiązany z series.series@id w pliku series.xml,
product.warranty@id jest ściśle powiązany z warranties.warranty@id w pliku warranties.xml,
product.sizes.size@id jest ściśle powiązany z sizes.group.size@id w pliku sizes.xml,
product.sizes.size.stock@id jest ściśle powiązany z stocks.stock@id w pliku stocks.xml,
product.parameters.parameter@id jest ściśle powiązany z parameters.parameter@id w pliku parameters.xml,
product.parameters.parameter@id z atrybutem @type = "parameter" jest ściśle powiązany z parameters.parameter@id w pliku parameters.xml,
product.parameters.parameter.@id z atrybutem @type = "section" jest ściśle powiązany z parameters.sections.section@id w pliku parameters.xml,
product.parameters.parameter.value@id jest ściśle powiązany z parameters.values.value@id w pliku parameters.xml,
products.product.group.group_by_parameter@id jest ściśle powiązany z products.product.parameters.parameter@id oraz z parameters.parameters.parameter@id w pliku parameters.xml,
products.product.group.group_by_parameter.product_value@id jest ściśle powiązany z products.product.parameters.parameter.value@id oraz z parameters.parameters.parameter@id w pliku parameters.xml.

