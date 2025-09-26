#!/usr/bin/env python3
"""
Test generowania gateway.xml bez bazy danych
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import hashlib


def create_test_gateway_xml():
    """Tworzy testowy plik gateway.xml z wszystkimi wymaganymi elementami"""

    # Utwórz główny element
    root = ET.Element("provider_description")
    root.set("file_format", "IOF")
    root.set("version", "3.0")
    root.set("generated_by", "nc")
    root.set("generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Meta element
    meta = ET.SubElement(root, "meta")

    long_name = ET.SubElement(meta, "long_name")
    long_name.text = "Matterhorn"

    short_name = ET.SubElement(meta, "short_name")
    short_name.text = "Matterhorn"

    showcase_image = ET.SubElement(meta, "showcase_image")
    showcase_image.set(
        "url", "https://matterhorn.pl/rwd_layout/assets/images/logo-hurt-pl.png")

    email = ET.SubElement(meta, "email")
    email.text = "info@matterhorn.pl"

    tel = ET.SubElement(meta, "tel")
    tel.text = "+48 503 503 875"

    fax = ET.SubElement(meta, "fax")
    fax.text = "+48 503 503 876"

    www = ET.SubElement(meta, "www")
    www.text = "https://matterhorn.pl"

    address = ET.SubElement(meta, "address")
    street = ET.SubElement(address, "street")
    street.text = "Katowicka 51"
    zipcode = ET.SubElement(address, "zipcode")
    zipcode.text = "41-400"
    city = ET.SubElement(address, "city")
    city.text = "Mysłowice"
    country = ET.SubElement(address, "country")
    country.text = "Poland"

    time_elem = ET.SubElement(meta, "time")
    offer_created = ET.SubElement(time_elem, "offer")
    offer_created.set("created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    offer_expires = ET.SubElement(time_elem, "offer")
    offer_expires.set("expires", "2025-09-05 10:03:05")

    # Wymagane elementy
    base_url = "http://212.127.93.27:8000"

    # Full element
    full = ET.SubElement(root, "full")
    full.set("url", f"{base_url}/mpd/generate-full-xml/")
    full.set("hash", "37ab9459cde95b92d817358062087f6b")
    full.set("changed", "2025-08-29 08:55:58")

    changes = ET.SubElement(full, "changes")
    change = ET.SubElement(changes, "change")
    change.set("url", f"{base_url}/mpd/full_change2025-08-28T13-38-24.xml")
    change.set("hash", "079b1ae73620827594b89713ba487efa")
    change.set("changed", "2025-08-28 13:38:24")

    # Light element
    light = ET.SubElement(root, "light")
    light.set("url", f"{base_url}/mpd/generate-light-xml/")
    light.set("hash", "50dbf9fd43f67fe9216a3b0ebdd033b2")
    light.set("changed", "2025-08-29 09:56:39")

    # Categories element
    categories = ET.SubElement(root, "categories")
    categories.set("url", f"{base_url}/mpd/generate-categories-xml/")
    categories.set("hash", "de79e4be79ab05f0e4a868390cbd9fca")
    categories.set("changed", "2025-08-29 08:56:04")

    # Sizes element
    sizes = ET.SubElement(root, "sizes")
    sizes.set("url", f"{base_url}/mpd/generate-sizes-xml/")
    sizes.set("hash", "79fdf0582ed98fa3a97872dcf051c460")
    sizes.set("changed", "2025-08-29 09:03:52")

    # Producers element (opcjonalny)
    producers = ET.SubElement(root, "producers")
    producers.set("url", f"{base_url}/mpd/generate-producers-xml/")
    producers.set("hash", "2b57687afb892c18eb515463dfce793d")
    producers.set("changed", "2025-08-29 10:02:55")

    # Opcjonalne elementy zgodnie ze schematem XSD
    # Units element
    units = ET.SubElement(root, "units")
    units.set("url", f"{base_url}/mpd/generate-units-xml/")
    units.set("hash", "")
    units.set("changed", "")

    # Parameters element
    parameters = ET.SubElement(root, "parameters")
    parameters.set("url", f"{base_url}/mpd/generate-parameters-xml/")
    parameters.set("hash", "")
    parameters.set("changed", "")

    # Stocks element
    stocks = ET.SubElement(root, "stocks")
    stocks.set("url", f"{base_url}/mpd/generate-stocks-xml/")
    stocks.set("hash", "")
    stocks.set("changed", "")

    # Series element
    series = ET.SubElement(root, "series")
    series.set("url", f"{base_url}/mpd/generate-series-xml/")
    series.set("hash", "")
    series.set("changed", "")

    # Warranties element
    warranties = ET.SubElement(root, "warranties")
    warranties.set("url", f"{base_url}/mpd/generate-warranties-xml/")
    warranties.set("hash", "")
    warranties.set("changed", "")

    # Preset element
    preset = ET.SubElement(root, "preset")
    preset.set("url", f"{base_url}/mpd/generate-preset-xml/")
    preset.set("hash", "")
    preset.set("changed", "")

    # Generuj XML
    xmlstr = minidom.parseString(ET.tostring(
        root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return xmlstr.decode("utf-8")


if __name__ == "__main__":
    xml_content = create_test_gateway_xml()

    # Zapisz do pliku
    with open("MPD_test/xml/matterhorn/gateway_test.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✅ Wygenerowano testowy plik gateway.xml z wszystkimi elementami")
    print("📄 Zapisano: MPD_test/xml/matterhorn/gateway_test.xml")

    # Wyświetl zawartość
    print("\n📋 Zawartość pliku:")
    print(xml_content)
