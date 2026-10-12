#!/usr/bin/env python3
"""Editor de inventario para Terraria (Android), pensado para Termux.

Descifra el .plr, localiza el bloque de inventario (58 casillas), permite
ver/editar/añadir ítems con nombre e ID, y guarda con respaldo y verificación.
"""
import glob
import json
import os
import shutil
import struct
import time
import unicodedata

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = "h3y_gUyZ".encode("utf-16le")  # clave pública conocida de los .plr
HOME = os.path.expanduser("~")
ITEMS_JSON = os.path.join(HOME, "items-1.json")
RESPALDOS = os.path.join(HOME, "respaldos_terraria")

R, G, Y, C, B, X = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

BASICOS = {1: "Pico de hierro", 2: "Bloque de tierra", 3: "Bloque de piedra",
           8: "Antorcha", 9: "Madera", 22: "Lingote de hierro", 23: "Gel",
           71: "Moneda de cobre", 72: "Moneda de plata", 73: "Moneda de oro",
           74: "Moneda de platino"}

ITEMS = {}
MAX_ID = 6000

PATRONES = [
    "/storage/emulated/0/Android/data/com.and.games505.*/Players/*.plr",
    "/storage/emulated/0/Android/data/com.and.games505.*/files/Players/*.plr",
    "/storage/*/Android/data/com.and.games505.*/Players/*.plr",
    "/storage/*/com.and.games505.*/Players/*.plr",
]


# ---------- Lista de ítems ----------
def cargar_items():
    try:
        with open(ITEMS_JSON, encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception:
        print(f"{Y}⚠ No hay lista de ítems ({ITEMS_JSON}). Solo verás IDs.")
        print(f"  Para tener nombres, ejecuta: python generar_items.py{X}")
        return dict(BASICOS)


def recargar_items():
    global MAX_ID
    ITEMS.clear()
    ITEMS.update(cargar_items())
    MAX_ID = max(6000, max(ITEMS))


def nom(i):
    return f"{ITEMS.get(i, '???')} ({i})"


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ---------- Cifrado ----------
def decrypt(b):
    d = Cipher(algorithms.AES(KEY), modes.CBC(KEY)).decryptor()
    o = d.update(b) + d.finalize()
    p = o[-1]
    if not 1 <= p <= 16:
        raise ValueError("Relleno inválido: clave o formato distintos")
    return bytearray(o[:-p])


def encrypt(b):
    p = 16 - len(b) % 16
    b = bytes(b) + bytes([p]) * p
    e = Cipher(algorithms.AES(KEY), modes.CBC(KEY)).encryptor()
    return e.update(b) + e.finalize()


# ---------- Inventario ----------
def slot_ok(d, o):
    if o + 10 > len(d):
        return False
    i, s, p, f = struct.unpack_from("<iiBB", d, o)
    if i == 0 and s == 0:
        return True
    return 1 <= i <= MAX_ID and 1 <= s <= 9999 and p <= 100 and f in (0, 1)


def buscar_inventario(d):
    mejor = (0, -1)
    for ini in range(len(d) - 10):
        n, o = 0, ini
        while slot_ok(d, o) and n < 58:
            n += 1
            o += 10
        if n > mejor[0]:
            mejor = (n, ini)
        if n == 58:
            break
    return mejor


def get(d, base, k):
    return struct.unpack_from("<ii", d, base + k * 10)


def put(d, base, k, i, s):
    struct.pack_into("<iiBB", d, base + k * 10, i, s, 0, 0)


def vacio(d, base):
    return not any(get(d, base, k)[0] for k in range(58))


ZONAS = [("✿ Barra rápida", 0, 10), ("❑ Inventario", 10, 50),
         ("❁ Monedas", 50, 54), ("✦ Munición", 54, 58)]


def mostrar(d, base):
    print(f"\n{C}╔{'═' * 38}╗\n║{B}{'❑  TU INVENTARIO':^38}{X}{C}║\n╚{'═' * 38}╝{X}")
    for nombre, a, b in ZONAS:
        print(f"\n{Y}{nombre}{X}")
        print(f"{C}┌{'─' * 36}┐{X}")
        libres = 0
        for k in range(a, b):
            i, s = get(d, base, k)
            if i:
                print(f"{C}│{X} {k:>2} ▸ {G}{nom(i)}{X} ✕{s}")
            else:
                libres += 1
        print(f"{C}└{'─' * 36}┘{X} {libres} libres")


# ---------- Entrada de datos ----------
def pedir_int(txt, lo, hi):
    try:
        v = int(input(txt))
        if lo <= v <= hi:
            return v
    except ValueError:
        pass
    print(f"{R}✘ Valor no válido{X}")
    return None


def elegir_item(cero=False):
    extra = " (0 = vaciar)" if cero else ""
    t = input(f"↺ Nombre o ID del ítem{extra}: ").strip()
    if t.isdigit():
        i = int(t)
        if i == 0 and cero:
            return 0
        if not 1 <= i <= MAX_ID:
            print(f"{R}✘ ID fuera de rango (1-{MAX_ID}){X}")
            return None
        if i not in ITEMS and len(ITEMS) > 1000:
            r = input(f"{Y}El ID {i} no está en la lista. ¿Usarlo igual? (s/n): {X}")
            if r.lower() != "s":
                return None
        print(f"  → {nom(i)}")
        return i
    if len(t) < 2:
        print(f"{R}✘ Escribe al menos 2 letras{X}")
        return None
    q = norm(t)
    res = [(i, n) for i, n in sorted(ITEMS.items()) if q in norm(n)][:15]
    if not res:
        print(f"{R}✘ Sin resultados{X}")
        return None
    for k, (i, n) in enumerate(res, 1):
        print(f" {k:>2}) {n} ({i})")
    k = pedir_int("Elige número: ", 1, len(res))
    return res[k - 1][0] if k else None


def anadir(d, base):
    libre = next((k for k in range(10, 50) if get(d, base, k)[0] == 0), None)
    if libre is None:
        print(f"{R}⚠ Inventario lleno (casillas 10-49).{X}")
        libre = pedir_int("Casilla a sobrescribir (10-49): ", 10, 49)
        if libre is None:
            return
        i0, s0 = get(d, base, libre)
        if input(f"{Y}Se perderá {nom(i0)} ✕{s0}. ¿Seguro? (s/n): {X}").lower() != "s":
            print("Cancelado.")
            return
    i = elegir_item()
    if i is None:
        return
    s = pedir_int("❈ Cantidad (1-9999): ", 1, 9999)
    if s is None:
        return
    put(d, base, libre, i, s)
    print(f"{G}✔ Casilla {libre}: {nom(i)} ✕{s} (sin guardar aún){X}")


# ---------- Archivos ----------
def elegir_plr():
    fs = sorted({f for q in PATRONES for f in glob.glob(q)})
    if fs:
        print(f"\n{Y}Personajes encontrados:{X}")
        for n, f in enumerate(fs, 1):
            fecha = time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(f)))
            estado = f"{G}✔ editable{X}" if os.access(f, os.W_OK) else f"{R}✖ solo lectura{X}"
            print(f" {n} ▸ {os.path.basename(f)}  ({fecha})  {f.split('/Android')[0]}  {estado}")
        print(" 0 ▸ Escribir la ruta a mano")
        k = pedir_int("Elige: ", 0, len(fs))
        if k:
            return fs[k - 1]
    else:
        print(f"{Y}No encontré personajes automáticamente.{X}")
    while True:
        r = input("❑ Ruta del .plr: ").strip().strip("'\"")
        r = os.path.expanduser(r)
        if os.path.isfile(r):
            return r
        print(f"{R}✖ Ese archivo no existe{X}")


def respaldar(ruta):
    os.makedirs(RESPALDOS, exist_ok=True)
    nombre = os.path.basename(ruta)
    orig = os.path.join(RESPALDOS, "ORIGINAL_" + nombre)
    if not os.path.exists(orig):
        shutil.copy(ruta, orig)
        print(f"{G}★ Original guardado (no se sobrescribe nunca): {orig}{X}")
    resp = os.path.join(RESPALDOS, time.strftime("%Y%m%d_%H%M%S") + "_" + nombre)
    shutil.copy(ruta, resp)
    print(f"{G}◈ Respaldo: {resp}{X}")
    return resp


def guardar(ruta, data, resp):
    if vacio(data, BASE[0]):
        print(f"{R}✖ Inventario vacío: no guardo.{X}")
        return False
    try:
        with open(ruta, "wb") as f:
            f.write(encrypt(data))
        with open(ruta, "rb") as f:
            ok = decrypt(f.read()) == data
    except Exception as e:
        print(f"{R}✖ Error al guardar: {e}{X}")
        ok = False
    if ok:
        print(f"{G}✔ Guardado y verificado. ¡A jugar!{X}")
        return True
    try:
        shutil.copy(resp, ruta)
        print(f"{R}✖ Falló la verificación: restauré el respaldo.{X}")
    except Exception as e:
        print(f"{R}✖ No pude restaurar automáticamente ({e}). Usa restaurar.py{X}")
    return False


BASE = [0]


def main():
    recargar_items()
    print(f"{C}{B}╔{'═' * 38}╗\n║{'✰  EDITOR DE TERRARIA':^38}║\n╚{'═' * 38}╝{X}")
    print(f"◈ Ítems cargados: {len(ITEMS)}")
    print(f"{Y}Cierra Terraria por completo antes de continuar.{X}")

    ruta = elegir_plr()
    if not os.access(ruta, os.W_OK):
        print(f"{R}✖ Sin permiso de escritura en ese archivo. Elige otra copia.{X}")
        return
    try:
        with open(ruta, "rb") as f:
            data = decrypt(f.read())
    except Exception as e:
        print(f"{R}✖ No se pudo descifrar: {e}{X}")
        return

    print("❑ Versión del archivo:", struct.unpack_from("<i", data, 0)[0])
    n, base = buscar_inventario(data)
    print(f"• Inventario: {n}/58 casillas válidas (offset {base})")
    if n < 50:
        print(f"{R}✖ No localicé el inventario. No modifico nada.{X}")
        with open(os.path.join(HOME, "dump.bin"), "wb") as f:
            f.write(data[:600])
        print("  Se guardó ~/dump.bin con el inicio del archivo (para reportar el problema).")
        return
    if vacio(data, base):
        print(f"{R}✖ El inventario sale vacío: no edito nada.{X}")
        print("  Si no esperabas esto, restaura con: python restaurar.py")
        return
    BASE[0] = base
    resp = respaldar(ruta)

    while True:
        print(f"\n{B}━━━━━━━━ MENÚ ━━━━━━━━{X}")
        print("1 ▸ Ver inventario")
        print("2 ▸ Editar casilla")
        print("3 ▸ Añadir ítem")
        print("4 ▸ Guardar y salir")
        print("5 ▸ Salir sin guardar")
        print("6 ▸ Recargar lista de ítems")
        op = input("› ").strip()
        if op == "1":
            mostrar(data, base)
        elif op == "2":
            k = pedir_int("Casilla (0-57): ", 0, 57)
            if k is None:
                continue
            i = elegir_item(cero=True)
            if i is None:
                continue
            s = pedir_int("Cantidad (1-9999): ", 1, 9999) if i else 0
            if s is None:
                continue
            put(data, base, k, i, s)
            print(f"{G}✔ Hecho (sin guardar aún){X}")
        elif op == "3":
            anadir(data, base)
        elif op == "4":
            if guardar(ruta, data, resp):
                break
        elif op == "5":
            print("❖ Saliendo sin cambios.")
            break
        elif op == "6":
            recargar_items()
            print(f"◈ Ítems cargados: {len(ITEMS)}")


if __name__ == "__main__":
    main()
