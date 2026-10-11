#!/usr/bin/env python3
"""Restaura un respaldo creado por editor.py. Cierra Terraria antes."""
import glob
import os
import shutil
import time

HOME = os.path.expanduser("~")
RESPALDOS = os.path.join(HOME, "respaldos_terraria")
PATRONES = [
    "/storage/emulated/*/Android/data/com.and.games505.*/Players",
    "/storage/emulated/*/Android/data/com.and.games505.*/files/Players",
    "/storage/*/Android/data/com.and.games505.*/Players",
    "/storage/*/com.and.games505.*/Players",
]


def carpeta_destino():
    cands = sorted({d for q in PATRONES for d in glob.glob(q) if os.path.isdir(d)})
    escribibles = [d for d in cands if os.access(d, os.W_OK)]
    if len(escribibles) == 1:
        return escribibles[0]
    if escribibles:
        for n, d in enumerate(escribibles, 1):
            print(f" {n} ▸ {d}")
        try:
            return escribibles[int(input("Carpeta destino: ")) - 1]
        except (ValueError, IndexError):
            pass
    while True:
        d = os.path.expanduser(input("Ruta de la carpeta Players: ").strip().strip("'\""))
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
        print("✖ No existe o no se puede escribir en ella")


def main():
    fs = sorted(glob.glob(os.path.join(RESPALDOS, "*")), reverse=True)
    if not fs:
        print("No hay respaldos en", RESPALDOS)
        return
    for n, f in enumerate(fs):
        print(n, os.path.basename(f), os.path.getsize(f), "bytes")
    try:
        k = int(input("Número a restaurar: "))
        elegido = fs[k]
    except (ValueError, IndexError):
        print("Valor no válido")
        return
    b = os.path.basename(elegido)
    nombre = b[len("ORIGINAL_"):] if b.startswith("ORIGINAL_") else b.split("_", 2)[2]
    dest = carpeta_destino()
    actual = os.path.join(dest, nombre)
    if input(f"Restaurar {b} como {nombre}? Terraria debe estar cerrado (s/n): ").lower() != "s":
        print("Cancelado.")
        return
    if os.path.exists(actual):  # guarda el estado actual por si te arrepientes
        seguro = os.path.join(RESPALDOS, time.strftime("%Y%m%d_%H%M%S") + "_" + nombre)
        shutil.copy(actual, seguro)
        print("Estado anterior guardado en", seguro)
    shutil.copy(elegido, actual)
    shutil.copy(elegido, actual + ".bak")
    print("✔ Restaurado")


if __name__ == "__main__":
    main()
