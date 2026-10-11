#!/usr/bin/env python3
"""Genera ~/items.json (ID -> nombre en español) a partir de la página
"IDs de objetos" de la wiki de Terraria, guardada con el navegador.

Uso:
    python generar_items.py [archivo]

Si no indicas archivo, busca en Descargas uno que contenga "IDs de objetos".
"""
import email
import glob
import html as H
import json
import os
import re
import sys
from email import policy

DESTINO = os.path.expanduser("~/items.json")


def buscar_archivo():
    for carpeta in ("/storage/emulated/0/Download", os.path.expanduser("~/storage/downloads")):
        for f in glob.glob(os.path.join(carpeta, "*IDs de objetos*")):
            return f
    return None


def leer_html(ruta):
    raw = open(ruta, "rb").read()
    txt = ""
    try:  # el navegador puede guardar la página como MHTML
        msg = email.message_from_bytes(raw, policy=policy.default)
        for p in msg.walk():
            if p.get_content_type() == "text/html":
                txt += p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "ignore")
    except Exception:
        pass
    return txt or raw.decode("utf-8", "ignore")


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else buscar_archivo()
    if not ruta or not os.path.isfile(ruta):
        print("✖ No encuentro la página guardada. Indica la ruta: python generar_items.py RUTA")
        return 1
    txt = leer_html(ruta)
    items = {}
    for fila in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S):
        c = [H.unescape(re.sub(r"<[^>]+>", "", x)).strip()
             for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", fila, re.S)]
        if len(c) >= 4 and c[0].isdigit() and c[1]:
            items[int(c[0])] = c[1]
    print("Filas leídas:", len(items))
    if len(items) < 4000:
        print("✖ Muy pocas filas; no se guardó. ¿Es la página correcta?")
        return 1
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    print("✔ Guardado", DESTINO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
