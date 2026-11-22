"""
Walidacja i „czyszczenie” przesyłanych obrazów (avatar, zdjęcia w postach).

  * rozmiar ≤ 5 MB (settings.MAKS_ROZMIAR_OBRAZU),
  * typ rozpoznany z ZAWARTOŚCI pliku (Pillow), nie z rozszerzenia ani Content-Type,
  * tylko JPEG / PNG / WebP, limit pikseli (ochrona przed „bombą dekompresyjną”),
  * plik jest PRZEKODOWANY do WebP – usuwa to metadane EXIF (np. GPS) i ewentualny
    doklejony ładunek (polyglot), a nazwa pliku jest losowa.
"""

import io
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

DOZWOLONE_FORMATY = {"JPEG", "PNG", "WEBP"}
MAKS_PIKSELI = 40_000_000
MAKS_BOK = 8000


def przetworz_obraz(plik, maks_bok: int = 2048) -> ContentFile:
    if plik.size > settings.MAKS_ROZMIAR_OBRAZU:
        raise ValidationError("Plik jest za duży (maksymalnie 5 MB).")
    try:
        plik.seek(0)
        with Image.open(plik) as obraz:
            obraz.verify()
        plik.seek(0)
        with Image.open(plik) as obraz:
            if obraz.format not in DOZWOLONE_FORMATY:
                raise ValidationError("Dozwolone są tylko obrazy JPG, PNG i WebP.")
            szer, wys = obraz.size
            if szer * wys > MAKS_PIKSELI or max(szer, wys) > MAKS_BOK:
                raise ValidationError("Obraz ma zbyt duże wymiary.")
            obraz.load()
            obraz = obraz.convert("RGBA" if obraz.mode in ("RGBA", "LA", "P") else "RGB")
            obraz.thumbnail((maks_bok, maks_bok))
            bufor = io.BytesIO()
            obraz.save(bufor, format="WEBP", quality=85)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise ValidationError("To nie jest poprawny obraz JPG, PNG ani WebP.")
    return ContentFile(bufor.getvalue(), name=f"{uuid.uuid4().hex}.webp")
