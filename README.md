# TerraItemGiver
Repositorio para un script Terraria que da items al jugador.

# Editor de inventario para Terraria (Android / Termux)

Script en Python para ver y modificar el inventario de un personaje de **Terraria en Android**, desde Termux, con menú, nombres de ítems en español y respaldos automáticos.

> [WARN] **Experimental.** Probado solo en un dispositivo (Android 10, Terraria 1.4.x de Android). Haz siempre copia de seguridad. Úsalo solo en tus partidas de un jugador: modificar personajes en servidores ajenos puede causar baneos.

## Qué hace

- Busca solos tus personajes (`.plr`) en `Android/data/com.and.games505.*` y marca cuáles se pueden editar.
- Muestra el inventario (barra rápida, inventario, monedas, munición) con **Nombre (ID)**.
- Añade o edita ítems buscando por nombre (sin importar tildes) o por ID.
- **Respaldos automáticos** en `~/respaldos_terraria/`. La primera copia de cada personaje (`ORIGINAL_...`) no se sobrescribe nunca.
- Se niega a guardar un inventario vacío y **verifica** lo guardado; si falla, restaura el respaldo.
- `restaurar.py` para volver a cualquier copia.

## Requisitos

- Android con [Termux](https://termux.dev) y permiso de almacenamiento (`termux-setup-storage`).
- Android 10 o anterior para llegar a `Android/data/` sin root. En Android 11+ el acceso está restringido y puede no funcionar.

```
pkg install python python-cryptography
```

(En un PC basta `pip install -r requirements.txt`.)

## Uso

1. **Cierra Terraria por completo** (forzar detención).
2. Genera la lista de ítems (solo la primera vez, ver abajo).
3. Ejecuta:

```
python editor.py
```

4. Elige el personaje (el que diga *editable*), usa el menú y termina con **Guardar y salir**.
5. Abre el juego y comprueba que el personaje carga.

Para restaurar una copia:

```
python restaurar.py
```

## Lista de ítems (nombres en español)

El repositorio incluye `items.json` ya generado. Cópialo a tu carpeta personal de Termux (`cp items.json ~/`) y listo. Si prefieres generarlo tú (por ejemplo para actualizarlo), la wiki bloquea las descargas automáticas, así que hay que guardar la página con el navegador:

1. En Chrome abre `https://terraria.wiki.gg/es/wiki/IDs_de_objetos`.
2. Menú ⋮ → **Descargar** → **Descargar página**.
3. Ejecuta `python generar_items.py`. Crea `~/items.json`.

Si el archivo no está en Descargas, indica la ruta: `python generar_items.py RUTA`.

Sin `items.json` el editor funciona igual, pero solo muestra IDs.

## Cómo funciona

El `.plr` está cifrado con AES-CBC con una clave pública conocida de la comunidad. El script lo descifra, busca 58 casillas consecutivas con la estructura `ID (4 bytes) · cantidad (4) · prefijo (1) · favorito (1)`, edita ese bloque y vuelve a cifrar. Solo toca el inventario principal (no el cerdito, la caja fuerte ni el equipo).

## Problemas conocidos

- La localización del inventario es heurística. Si no encuentra el bloque, no modifica nada y guarda `~/dump.bin` para diagnosticar.
- Una vez, tras editar, el editor mostró el inventario vacío al reabrirlo. No se determinó la causa: el juego pudo reescribir el archivo. Por eso ahora se niega a editar o guardar inventarios vacíos y conserva el original.
- Un ID que no exista en el juego podría dar problemas al cargar el personaje. Comprueba los IDs en la wiki.
- Cantidades muy altas en ítems no apilables pueden causar comportamientos raros.

## Aviso

Proyecto no oficial, sin relación con Re-Logic ni 505 Games. Se ofrece tal cual, sin garantías. Úsalo bajo tu responsabilidad.

## Datos de ítems

`items.json` contiene IDs y nombres de ítems de Terraria, extraídos de la
wiki oficial (https://terraria.wiki.gg/es/wiki/IDs_de_objetos).
Fuente: Terraria Wiki, licencia CC BY-SA 4.0
(https://creativecommons.org/licenses/by-sa/4.0/).
Este archivo se redistribuye bajo la misma licencia; el código sigue bajo MIT.
