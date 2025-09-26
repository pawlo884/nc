#!/usr/bin/env python3
"""
Skrypt testowy do sprawdzenia poprawki duplikacji węzła <full> w gateway.xml
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta


def create_test_gateway_xml():
    """Tworzy testowy gateway.xml z poprawioną logiką"""

    root = ET.Element("provider_description")
    root.set("file_format", "IOF")
    root.set("version", "3.0")
    root.set("generated_by", "nc")

    # Użyj czasu z full.xml jako bazowego
    full_time = "2025-08-30 13:26:44"  # Czas z full.xml
    base_time = datetime.strptime(full_time, "%Y-%m-%d %H:%M:%S")

    # Ustaw generated na aktualny czas
    current_time = datetime.now()
    root.set("generated", current_time.strftime("%Y-%m-%d %H:%M:%S"))

    # Meta element
    meta = ET.SubElement(root, "meta")

    # Podstawowe informacje
    long_name = ET.SubElement(meta, "long_name")
    long_name.text = "Matterhorn"
    short_name = ET.SubElement(meta, "short_name")
    short_name.text = "Matterhorn"

    # Time element - użyj full_time jako bazowego
    time_elem = ET.SubElement(meta, "time")
    offer_created = ET.SubElement(time_elem, "offer")
    offer_created.set("created", full_time)  # Użyj czasu z full.xml

    offer_expires = ET.SubElement(time_elem, "offer")
    expires_time = base_time + timedelta(days=7)
    offer_expires.set("expires", expires_time.strftime("%Y-%m-%d %H:%M:%S"))

    # Full element - tylko jeden, z hash i changed
    full = ET.SubElement(root, "full")
    full.set("url", "http://212.127.93.27:8000/mpd/generate-full-xml/")
    full.set("hash", "test_hash_12345")  # Przykładowy hash
    full.set("changed", full_time)  # Użyj czasu z full.xml

    # Light element
    light = ET.SubElement(root, "light")
    light.set("url", "http://212.127.93.27:8000/mpd/generate-light-xml/")
    light.set("hash", "light_hash_12345")
    light.set("changed", "2025-08-30 14:12:11")

    # Categories element
    categories = ET.SubElement(root, "categories")
    categories.set(
        "url", "http://212.127.93.27:8000/mpd/generate-categories-xml/")
    categories.set("hash", "categories_hash_12345")
    categories.set("changed", "2025-08-30 13:26:47")

    # Sizes element
    sizes = ET.SubElement(root, "sizes")
    sizes.set("url", "http://212.127.93.27:8000/mpd/generate-sizes-xml/")
    sizes.set("hash", "sizes_hash_12345")
    sizes.set("changed", "2025-08-30 13:26:48")

    # Producers element
    producers = ET.SubElement(root, "producers")
    producers.set(
        "url", "http://212.127.93.27:8000/mpd/generate-producers-xml/")
    producers.set("hash", "producers_hash_12345")
    producers.set("changed", "2025-08-30 13:26:49")

    # Generuj XML
    xmlstr = minidom.parseString(ET.tostring(
        root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    return xmlstr.decode("utf-8")


if __name__ == "__main__":
    xml_content = create_test_gateway_xml()

    # Zapisz do pliku
    with open("MPD_test/xml/matterhorn/gateway_fixed.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✅ Wygenerowano poprawiony plik gateway.xml")
    print("📄 Zapisano: MPD_test/xml/matterhorn/gateway_fixed.xml")

    # Sprawdź czy nie ma duplikacji
    root = ET.fromstring(xml_content)
    full_elements = root.findall("full")

    if len(full_elements) == 1:
        print("✅ Brak duplikacji węzła <full>")
        full = full_elements[0]
        print(
            f"📋 Węzeł <full>: url={full.get('url')}, hash={full.get('hash')}, changed={full.get('changed')}")
    else:
        print(f"❌ Znaleziono {len(full_elements)} węzłów <full> - duplikacja!")

    # Sprawdź czy created nie jest późniejsze niż changed
    meta = root.find("meta")
    time_elem = meta.find("time")
    created = time_elem.find("offer[@created]").get("created")

    full_changed = root.find("full").get("changed")

    print(f"\n⏰ Czas created w meta: {created}")
    print(f"⏰ Czas changed w full: {full_changed}")

    if created <= full_changed:
        print("✅ Czas created nie jest późniejszy niż changed")
    else:
        print("❌ Czas created jest późniejszy niż changed!")

    print("\n📋 Zawartość pliku:")
    print(xml_content)

