#!/usr/bin/env python3
"""Editor de inventario para Terraria (Android), pensado para Termux.

Descifra el .plr, localiza el bloque de inventario (58 casillas), permite
ver/editar/añadir ítems con nombre e ID, y guarda con respaldo y verificación.

Ctrl+C:
  - En cualquier pregunta: cancela esa acción y vuelve al menú.
  - En el menú: pide confirmación si hay cambios sin guardar.
  - Mientras guarda: restaura el respaldo para no dejar el archivo a medias.
"""
import glob
import json
import os
import shutil
import struct
import sys
import time
import unicodedata

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = "h3y_gUyZ".encode("utf-16le")  # clave pública conocida de los .plr
HOME = os.path.expanduser("~")
AQUI = os.path.dirname(os.path.abspath(__file__))
RESPALDOS = os.path.join(HOME, "respaldos_terraria")

R, G, Y, C, B, X = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"
D = "\033[2m"  # tenue
M = "\033[95m"  # magenta

BASICOS = {1: "Pico de hierro", 2: "Bloque de tierra", 3: "Bloque de piedra",
           8: "Antorcha", 9: "Madera", 22: "Lingote de hierro", 23: "Gel",
           71: "Moneda de cobre", 72: "Moneda de plata", 73: "Moneda de oro",
           74: "Moneda de platino"}

ITEMS = {}
MAX_ID = 6000
SUCIO = [False]  # True si hay cambios sin guardar

PATRONES = [
    "/storage/emulated/0/Android/data/com.and.games505.*/Players/*.plr",
    "/storage/emulated/0/Android/data/com.and.games505.*/files/Players/*.plr",
    "/storage/*/Android/data/com.and.games505.*/Players/*.plr",
    "/storage/*/com.and.games505.*/Players/*.plr",
]

INTERRUPCION = (KeyboardInterrupt, EOFError)


# ---------- Lista de ítems ----------
def buscar_items():
    """Busca items.json o items-1.json en ~/ y en la carpeta del script."""
    for carpeta in (HOME, AQUI):
        for nombre in ("items.json", "items-1.json"):
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta):
                return ruta
    return os.path.join(HOME, "items.json")


NORM = {}  # nombre sin tildes/mayúsculas por ID (búsqueda rápida)
TTY = sys.stdout.isatty()
ESPIRAL = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
BARRA_W = 18


def barra(frac):
    """Barra tipo pip/rich: ━━━━━╸━━━━"""
    frac = max(0.0, min(1.0, frac))
    if frac >= 1:
        return f"{G}{'━' * BARRA_W}{X}"
    lleno = int(frac * BARRA_W)
    resto = BARRA_W - lleno - 1
    return f"{C}{'━' * lleno}╸{X}{D}{'━' * resto}{X}"


def progreso(frac, hecho, total, paso):
    esp = ESPIRAL[paso % len(ESPIRAL)] if frac < 1 else "✔"
    col = C if frac < 1 else G
    sys.stdout.write(f"\r {col}{esp}{X} {barra(frac)} {B}{int(frac * 100):>3}%{X} "
                     f"{D}{hecho}/{total}{X}\033[K")
    sys.stdout.flush()


def cargar_items():
    ruta = buscar_items()
    if not os.path.isfile(ruta):
        print(f"{Y}⚠ No hay lista de ítems ({ruta}). Solo verás IDs.")
        print(f"  Para tener nombres, ejecuta: python generar_items.py{X}")
        return dict(BASICOS)
    try:
        print(f" {C}◈{X} {B}Cargando lista de ítems{X} {D}· {os.path.basename(ruta)}{X}")
        with open(ruta, encoding="utf-8") as f:
            crudo = json.load(f)
        total = len(crudo)
        items = {}
        cada = max(1, total // 40)
        paso = 0
        if TTY:
            sys.stdout.write("\033[?25l")  # oculta el cursor mientras carga
        try:
            for n, (k, v) in enumerate(crudo.items(), 1):
                items[int(k)] = v
                if TTY and (n % cada == 0 or n == total):
                    progreso(n / total, n, total, paso)
                    paso += 1
                    time.sleep(0.012)
        finally:
            if TTY:
                sys.stdout.write("\033[?25h\n")
                sys.stdout.flush()
        print(f" {G}✔ {len(items)} ítems listos{X}")
        return items
    except Exception as e:
        print(f"{Y}⚠ No pude leer la lista de ítems ({e}). Solo verás IDs.")
        print(f"  Para tener nombres, ejecuta: python generar_items.py{X}")
        return dict(BASICOS)


def recargar_items():
    global MAX_ID
    ITEMS.clear()
    ITEMS.update(cargar_items())
    NORM.clear()
    NORM.update({i: norm(n) for i, n in ITEMS.items()})
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
    SUCIO[0] = True


def vacio(d, base):
    return not any(get(d, base, k)[0] for k in range(58))


# ---------- Vista del inventario ----------
ANCHO = 38  # ancho total de cada recuadro (cabe en un móvil vertical)
INNER = ANCHO - 2
NOMBRE_W = 19

# (título, color, desde, hasta, mostrar casillas vacías)
ZONAS = [
    ("✿ Barra rápida", Y, 0, 10, True),
    ("❑ Inventario", C, 10, 50, False),
    ("❁ Monedas", M, 50, 54, False),
    ("✦ Munición", G, 54, 58, False),
]

VALOR_MONEDA = {71: 1, 72: 100, 73: 10000, 74: 1000000}


def recortar(t, w):
    return t if len(t) <= w else t[:w - 1] + "…"


def caja_arriba(titulo, color):
    relleno = INNER - len(titulo) - 3
    return f"{color}╭─ {B}{titulo}{X}{color} {'─' * relleno}╮{X}"


def caja_abajo(texto, color):
    relleno = INNER - len(texto) - 3
    return f"{color}╰─ {D}{texto}{X}{color} {'─' * relleno}╯{X}"


def fila(k, i, s, color):
    nombre = recortar(ITEMS.get(i, "???"), NOMBRE_W)
    return (f"{color}│{X}{D}{k:>3}{X} {nombre:<{NOMBRE_W}} "
            f"{D}#{i:<4}{X} {G}×{s:>4}{X}{color} │{X}")


def fila_vacia(k, color):
    return f"{color}│{X}{D}{k:>3} · vacío{' ' * (INNER - 11)}{X}{color}│{X}"


def dinero(d, base):
    total = 0
    for k in range(50, 54):
        i, s = get(d, base, k)
        total += VALOR_MONEDA.get(i, 0) * s
    pt, resto = divmod(total, 1000000)
    oro, resto = divmod(resto, 10000)
    plata, cobre = divmod(resto, 100)
    partes = [f"{v} {n}" for v, n in ((pt, "platino"), (oro, "oro"),
                                      (plata, "plata"), (cobre, "cobre")) if v]
    return " · ".join(partes) if partes else "sin monedas"


def mostrar(d, base):
    ocupadas = sum(1 for k in range(58) if get(d, base, k)[0])
    libres_inv = sum(1 for k in range(10, 50) if get(d, base, k)[0] == 0)
    print(f"\n{C}{B}╔{'═' * INNER}╗")
    print(f"║{'❑  TU INVENTARIO':^{INNER}}║")
    print(f"╚{'═' * INNER}╝{X}")
    print(f" {D}Casillas con ítem:{X} {B}{ocupadas}/58{X}   "
          f"{D}Libres (10-49):{X} {B}{libres_inv}{X}")
    print(f" {Y}${X} {dinero(d, base)}")

    for titulo, color, a, b, con_vacias in ZONAS:
        print(f"\n{caja_arriba(titulo, color)}")
        libres = 0
        hay = False
        for k in range(a, b):
            i, s = get(d, base, k)
            if i:
                hay = True
                print(fila(k, i, s, color))
            else:
                libres += 1
                if con_vacias:
                    print(fila_vacia(k, color))
        if not hay and not con_vacias:
            print(f"{color}│{X}{D}{'(sin ítems)':^{INNER}}{X}{color}│{X}")
        print(caja_abajo(f"{libres} libres", color))


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
    res = [(i, n) for i, n in sorted(ITEMS.items()) if q in NORM.get(i, "")][:15]
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


def editar(d, base):
    k = pedir_int("Casilla (0-57): ", 0, 57)
    if k is None:
        return
    i0, s0 = get(d, base, k)
    actual = f"{nom(i0)} ✕{s0}" if i0 else "vacía"
    print(f"{D}  Ahora: {actual}{X}")
    i = elegir_item(cero=True)
    if i is None:
        return
    s = pedir_int("Cantidad (1-9999): ", 1, 9999) if i else 0
    if s is None:
        return
    put(d, base, k, i, s)
    print(f"{G}✔ Hecho (sin guardar aún){X}")


# ---------- Archivos ----------
def origen(f):
    """Texto corto que indica dónde está el archivo."""
    if f.startswith("/storage/emulated/"):
        return "Almacenamiento interno"
    partes = f.split("/")
    if len(partes) > 2 and partes[1] == "storage":
        return f"Tarjeta SD ({partes[2]})"
    return os.path.dirname(f)


def elegir_plr():
    fs = sorted({f for q in PATRONES for f in glob.glob(q)})
    if fs:
        print(f"\n{Y}Personajes encontrados:{X}")
        for n, f in enumerate(fs, 1):
            fecha = time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(f)))
            estado = f"{G}✔ editable{X}" if os.access(f, os.W_OK) else f"{R}✖ solo lectura{X}"
            print(f" {B}{n}{X} ▸ {os.path.basename(f)}  ({fecha})  {estado}")
            print(f"     {D}{origen(f)}{X}")
        print(f" {B}0{X} ▸ Escribir la ruta a mano")
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


def guardar(ruta, data, resp, base):
    if vacio(data, base):
        print(f"{R}✖ Inventario vacío: no guardo.{X}")
        return False
    ok = False
    motivo = ""
    try:
        with open(ruta, "wb") as f:
            f.write(encrypt(data))
        with open(ruta, "rb") as f:
            ok = decrypt(f.read()) == data
    except BaseException as e:  # incluye Ctrl+C a mitad de escritura
        motivo = "interrumpido" if isinstance(e, KeyboardInterrupt) else str(e)
        print(f"{R}✖ Error al guardar: {motivo}{X}")
        ok = False
    if ok:
        SUCIO[0] = False
        print(f"{G}✔ Guardado y verificado. ¡A jugar!{X}")
        return True
    try:
        shutil.copy(resp, ruta)
        print(f"{R}✖ No se guardó bien: restauré el respaldo.{X}")
    except BaseException as e:
        print(f"{R}✖ No pude restaurar automáticamente ({e}). Usa restaurar.py{X}")
    return False


def degradado(texto, colores=(51, 45, 39, 33, 99, 135, 171)):
    """Colorea cada letra con un degradado (colores 256 de ANSI)."""
    n = max(1, len(texto) - 1)
    out = []
    for k, ch in enumerate(texto):
        if ch == " ":
            out.append(ch)
            continue
        c = colores[round(k / n * (len(colores) - 1))]
        out.append(f"\033[38;5;{c}m{ch}")
    return "".join(out) + X


def centrar(plano, coloreado):
    izq = (INNER - len(plano)) // 2
    der = INNER - len(plano) - izq
    return f"{C}║{X}{' ' * izq}{coloreado}{' ' * der}{C}║{X}"


def banner():
    titulo = "✰  T E R R A R I A  ✰"
    sub = "EDITOR DE INVENTARIO"
    info = "Android · Termux"
    vacio_ = f"{C}║{X}{' ' * INNER}{C}║{X}"
    print(f"\n{C}╔{'═' * INNER}╗{X}")
    print(vacio_)
    print(centrar(titulo, f"{B}{degradado(titulo)}"))
    print(centrar(sub, f"{B}{sub}{X}"))
    print(centrar(info, f"{D}{info}{X}"))
    print(vacio_)
    print(f"{C}╚{'═' * INNER}╝{X}")


MENU = [
    ("1", "◈", "Ver inventario", C),
    ("2", "✎", "Editar casilla", C),
    ("3", "✚", "Añadir ítem", C),
    ("4", "✔", "Guardar y salir", G),
    ("5", "✖", "Salir sin guardar", R),
    ("6", "↻", "Recargar lista de ítems", Y),
]


def menu():
    print(f"\n{C}╭─ {B}MENÚ{X}{C} {'─' * (INNER - 7)}╮{X}")
    for num, icono, texto, col in MENU:
        plano = f" {num}  {icono}  {texto}"
        relleno = ' ' * (INNER - len(plano))
        print(f"{C}│{X} {col}{B}{num}{X}  {col}{icono}{X}  {texto}{relleno}{C}│{X}")
    print(f"{C}├{'─' * INNER}┤{X}")
    if SUCIO[0]:
        estado_plano, estado = " ● Cambios sin guardar", f" {Y}●{X} {Y}Cambios sin guardar{X}"
    else:
        estado_plano, estado = " ○ Sin cambios", f" {D}○ Sin cambios{X}"
    print(f"{C}│{X}{estado}{' ' * (INNER - len(estado_plano))}{C}│{X}")
    print(caja_abajo("Ctrl+C cancela la acción", C))


def confirmar_salida():
    """Devuelve True si se debe salir."""
    if not SUCIO[0]:
        return True
    try:
        r = input(f"\n{Y}Hay cambios sin guardar. ¿Salir sin guardar? (s/n): {X}")
    except INTERRUPCION:
        return True
    return r.strip().lower() == "s"


def main():
    banner()
    print()
    recargar_items()
    print(f"\n{Y}⚠ Cierra Terraria por completo antes de continuar.{X}")

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
    resp = respaldar(ruta)

    while True:
        menu()
        try:
            op = input("› ").strip()
        except INTERRUPCION:
            print()
            if confirmar_salida():
                print("❖ Saliendo sin cambios.")
                break
            continue
        try:
            if op == "1":
                mostrar(data, base)
            elif op == "2":
                editar(data, base)
            elif op == "3":
                anadir(data, base)
            elif op == "4":
                if guardar(ruta, data, resp, base):
                    break
            elif op == "5":
                if confirmar_salida():
                    print("❖ Saliendo sin cambios.")
                    break
            elif op == "6":
                recargar_items()
        except INTERRUPCION:
            print(f"\n{Y}↩ Acción cancelada.{X}")


if __name__ == "__main__":
    try:
        main()
    except INTERRUPCION:
        print(f"\n{Y}✖ Cancelado. El personaje no se modificó.{X}")
        sys.exit(130)
