Struktura i jej opis
Plik gateway.xml jest głównym plikiem struktury formatu IOF stanowiącym zbiór szczegółowych informacji o dostawcy oraz adresów URL do podstawowych, różnicowych oraz referencyjnych plików oferty.

Szczegółowe dane dostawcy, czyli pod węzły

<long_name> - długa nazwa dostawcy,
<short_name> - skrócona nazwa dostawcy (nie może zawierać biały spacji, dopuszcza znak dolnego podkreślenia oraz symbole "0-9", "a-z", "A-Z"),
<showcase_image> - adres URL do logotypu dostawcy,
<email> - adres poczty elektronicznej dostawcy,
<tel> - numer telefonu dostawcy,
<fax> - faks dostawcy,
<www> - adres URL strony dostawcy,
<street> - ulica adresu dostawcy,
<zipcode> - kod pocztowy adresu dostawcy,
<city> - miasto adresu dostawcy,
<country> - kraj adresu dostawcy,
<province>- województwo adresu dostawcy.
umieszczone są w wymaganym węźle <meta>, w którym zwracana jest również:

informacja o dacie wygenerowania oferty, czyli pod węzeł <meta><time><offer> z atrybutem @created,
informację o dacie wygaśnięcia oferty, czyli pod węzeł <meta><time><offer> z atrybutem @expires.
Dalsze węzły wskazują na adresy URL do poszczególnych plików formatu:

Węzły wymagane
<full> – adres URL do pierwszego podstawowego pliku oferty full.xml - zawierającego podstawowe informacje o towarach np. opisy, zdjęcia, atrybuty, załączniki czy grupy towarów bądź składowe zestawów i kolekcji itp.,
<light> – adres URL do drugiego podstawowego pliku oferty light.xml - zawierającego informacje m.in. o rozmiarach, ich lokalizacji na magazynie i stanach dyspozycyjnych, kodach producenta, wagach oraz cenach uwzględniających rabaty i walutę indywidualnego odbiorcy,
<categories> – adres URL do referencyjnego pliku oferty categories.xml - stanowiącego zbiór wszystkich kategorii towarów dostawcy,
<sizes> – adres URL do referencyjnego pliku oferty sizes.xml - stanowiącego zbiór wszystkich rozmiarów towarów dostawcy,
<producers> – adres URL do referencyjnego pliki oferty producers.xml - stanowiącego zbiór wszystkich producentów towarów dostawcy.
Węzły opcjonalne
<change> - adresy URL do opcjonalnych plików oferty full_changeYYYY-MM-DDThh-mm-ss.xml - stanowiących pliki różnicowe dla podstawowego pliku oferty full.xml i zawierających informacje o głównych węzłach towarów, które uległy ostatnio zmianie,
<series> – adres URL do referencyjnego pliku oferty series.xml - stanowiącego zbiór wszystkich serii towarów dostawcy,
<warranties> – adres URL do referencyjnego pliku oferty warranties.xml - stanowiącego zbiór wszystkich gwarancji towarów dostawcy.,
<parameters> – adres URL do referencyjnego pliku oferty parameters.xml - stanowiącego zbiór wszystkich parametrów towarów dostawcy,
<units> – adres URL do referencyjnego pliku oferty units.xml - stanowiącego zbiór wszystkich jednostek miary towarów dostawcy,
<stocks> - adres URL do referencyjnego pliku oferty stocks.xml - stanowiącego zbiór wszystkich magazynów towarów dostawcy,
<preset> - adres URL do ostatniego opcjonalnego pliku oferty preset.xml - przechowującego informacje na temat konfiguracji oferty na potrzeby programu służącego do jej synchronizacji (np. Downloader).


Uwaga dotycząca znaczników opcjonalnych
W przypadku braku jednostki miary, serii, gwarancji czy parametrów dla danego towaru w pliku full.xml, puste tagi dodatkowe np. <unit/>, czy <series/> nie będą akceptowane, w takim przypadku nie należy takich tagów określać w pliku w ogóle.

