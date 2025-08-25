#!/usr/bin/env python3
"""
Prosty skrypt do odświeżenia gateway.xml bez Django.
Tylko odczytuje pliki lokalne i aktualizuje hash/changed.
"""

import os
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime


def refresh_gateway_simple():
    """
    Prosta funkcja do odświeżenia gateway.xml bez bazy danych.
    Tylko odczytuje pliki lokalne i aktualizuje hash/changed.
    """
    try:
        print("🔄 Odświeżam gateway.xml (prosta metoda)...")

        # Sprawdź pliki lokalne
        local_dir = 'MPD_test/xml/matterhorn/'
        full_path = os.path.join(local_dir, 'full.xml')

        if not os.path.exists(full_path):
            print("❌ Plik full.xml nie istnieje lokalnie")
            return False

        # Oblicz nowy hash i datę dla full.xml
        with open(full_path, 'rb') as f:
            file_content = f.read()
            new_hash = hashlib.md5(file_content).hexdigest()

        mtime = os.path.getmtime(full_path)
        new_changed = datetime.fromtimestamp(
            mtime).strftime('%Y-%m-%d %H:%M:%S')

        print(f"📄 full.xml - hash: {new_hash}, changed: {new_changed}")

        # Odczytaj aktualny gateway.xml
        gateway_path = os.path.join(local_dir, 'gateway.xml')
        if not os.path.exists(gateway_path):
            print("❌ Plik gateway.xml nie istnieje lokalnie")
            return False

        # Zaktualizuj gateway.xml
        tree = ET.parse(gateway_path)
        root = tree.getroot()

        # Znajdź element <full> i zaktualizuj jego atrybuty
        for full_elem in root.findall('full'):
            old_hash = full_elem.get('hash', '')
            old_changed = full_elem.get('changed', '')

            full_elem.set('hash', new_hash)
            full_elem.set('changed', new_changed)

            print(f"🔄 Zaktualizowano: hash '{old_hash}' -> '{new_hash}'")
            print(
                f"🔄 Zaktualizowano: changed '{old_changed}' -> '{new_changed}'")

            # Zaktualizuj również timestamp w głównym elemencie
            root.set('generated', new_changed)
            print(f"🔄 Zaktualizowano: generated -> '{new_changed}'")
            break

        # Zapisz zaktualizowany plik
        tree.write(gateway_path, encoding='utf-8', xml_declaration=True)
        print(f"✅ Gateway.xml zaktualizowany i zapisany: {gateway_path}")

        return True

    except Exception as e:
        print(f"❌ Błąd podczas odświeżania gateway.xml: {str(e)}")
        return False


if __name__ == "__main__":
    refresh_gateway_simple()
