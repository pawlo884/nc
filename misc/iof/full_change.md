Struktura i jej opis
Oprócz pliku full.xml obejmującego wszystkie oferowane towary format pozwala również na generowanie plików różnicowych full_changeYYYY-MM-DDThh-mm-ss.xml zawierających informacje o głównych węzłach towarów, które uległy ostatnio zmianie. Ilość takich plików w ofercie jest nieograniczona, a ich struktura XML jest bliźniaczą strukturą XML pliku full.xml.

YYYY-MM-DDThh-mm-ss odpowiada dacie i godzinie ostatniej zmiany w standardzie ISO 8601.

Różnicowanie odbywa się na poziomie głównego węzła towaru <product>, w którym nastąpiła dana zmiana. Przykładowo, jeśli zmianie ulegnie jeden z parametrów towaru (do towaru zostanie np. dodany nowy parametr) to w pliku full_changel.xml umieszczony zostanie cały węzeł <product> zawierający zarówno niezmienione atrybuty i inne węzły tego towaru jak i węzeł <parametrs>, w którym nowy parametr został dodany.

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
product.parameters.parameter.value@id jest ściśle powiązany z parameters.values.value@id w pliku parameters.xml.