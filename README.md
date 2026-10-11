# TerraItemGiver

Editor de inventario para **Terraria en Android**, escrito en Python y pensado para ejecutarse desde **Termux**. Permite ver y modificar el inventario de un personaje con un menú sencillo, nombres de ítems en español y respaldos automáticos.

> [!CAUTION]
> **Experimental.** Probado solo en un dispositivo (Android 10, Terraria 1.4.x de Android). Haz siempre copia de seguridad. Úsalo solo en tus partidas de un jugador: modificar personajes en servidores ajenos puede causar baneos.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Plataforma](https://img.shields.io/badge/Plataforma-Android%20%2F%20Termux-green)
![Licencia](https://img.shields.io/badge/C%C3%B3digo-MIT-yellow)

## Índice

- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Restaurar una copia](#restaurar-una-copia)
- [Lista de ítems (nombres en español)](#lista-de-ítems-nombres-en-español)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Cómo funciona](#cómo-funciona)
- [Seguridad y respaldos](#seguridad-y-respaldos)
- [Solución de problemas](#solución-de-problemas)
- [Problemas conocidos](#problemas-conocidos)
- [Contribuir](#contribuir)
- [Aviso legal](#aviso-legal)
- [Licencia y créditos](#licencia-y-créditos)

## Características

- Detecta automáticamente tus personajes (`.plr`) en `Android/data/com.and.games505.*` e indica cuáles se pueden editar.
- Muestra el inventario completo (barra rápida, inventario, monedas y munición) con formato **Nombre (ID)**.
- Añade o edita ítems buscando por **nombre** (sin importar las tildes) o por **ID**.
- **Respaldos automáticos** en `~/respaldos_terraria/`. La primera copia de cada personaje (`ORIGINAL_...`) nunca se sobrescribe.
- Se niega a guardar un inventario vacío.
- **Verifica** lo guardado y, si algo falla, restaura el respaldo automáticamente.
- Incluye `restaurar.py` para volver a cualquier copia anterior.
- Nombres de ítems en español mediante `items.json` (opcional).

## Requisitos

- Android con [Termux](https://termux.dev) instalado.
- Permiso de almacenamiento para Termux:

  ```
  termux-setup-storage
  ```

- **Android 10 o anterior** para acceder a `Android/data/` sin root. En Android 11 o superior el acceso está restringido y puede no funcionar.
- Python 3 y la librería `cryptography`.

> [!NOTE]
> En PC no hay restricción de carpetas, pero tendrás que indicar manualmente la ubicación de tus archivos `.plr`.

## Instalación

1. Instala las dependencias en Termux:

   ```
   pkg install python python-cryptography git
   ```

2. Clona el repositorio:

   ```
   git clone https://github.com/TU_USUARIO/TerraItemGiver.git
   cd TerraItemGiver
   ```

3. Copia la lista de ítems a tu carpeta personal (opcional, pero recomendado):

   ```
   cp items.json ~/
   ```

**En un PC** basta con:

```
pip install -r requirements.txt
```

## Uso

1. **Cierra Terraria por completo** (forzar detención desde los ajustes de Android).
2. Asegúrate de tener `items.json` en `~/` (ver [Lista de ítems](#lista-de-ítems-nombres-en-español)).
3. Ejecuta el editor:

   ```
   python editor.py
   ```

4. Elige el personaje que diga *editable*.
5. Usa el menú para ver, añadir o modificar ítems.
6. Termina con **Guardar y salir**.
7. Abre el juego y comprueba que el personaje carga correctamente.

> [!IMPORTANT]
> Si Terraria está abierto o en segundo plano mientras editas, el juego puede reescribir el archivo y deshacer tus cambios.

## Restaurar una copia

Para volver a cualquier respaldo guardado:

```
python restaurar.py
```

Elige el personaje y la copia que quieres recuperar. Los respaldos están en `~/respaldos_terraria/`.

> [!TIP]
> Si algo sale mal, restaura la copia `ORIGINAL_...`: es la versión del personaje antes de tu primera edición y nunca se sobrescribe.

## Lista de ítems (nombres en español)

El repositorio incluye `items.json` ya generado: cópialo a tu carpeta personal (`cp items.json ~/`) y listo.

Si prefieres generarlo tú (por ejemplo, para actualizarlo), la wiki bloquea las descargas automáticas, así que hay que guardar la página con el navegador:

1. En Chrome abre `https://terraria.wiki.gg/es/wiki/IDs_de_objetos`.
2. Menú ⋮ → **Descargar** → **Descargar página**.
3. Ejecuta:

   ```
   python generar_items.py
   ```

   Esto crea `~/items.json`.

Si el archivo no está en Descargas, indica la ruta:

```
python generar_items.py RUTA
```

Sin `items.json` el editor funciona igual, pero solo muestra IDs.

## Estructura del proyecto

```
TerraItemGiver/
├── editor.py          # Editor principal con menú
├── restaurar.py       # Restaura respaldos
├── generar_items.py   # Genera items.json desde la wiki guardada
├── items.json         # IDs y nombres de ítems en español
├── requirements.txt   # Dependencias para PC
└── README.md
```

## Cómo funciona

El archivo `.plr` está cifrado con **AES-CBC** usando una clave pública conocida de la comunidad. El script:

1. Descifra el archivo.
2. Busca 58 casillas consecutivas con la estructura:

   | Campo     | Tamaño  |
   |-----------|---------|
   | ID        | 4 bytes |
   | Cantidad  | 4 bytes |
   | Prefijo   | 1 byte  |
   | Favorito  | 1 byte  |

3. Edita ese bloque.
4. Vuelve a cifrar y guarda.

Solo toca el **inventario principal**: no modifica el cerdito, la caja fuerte ni el equipo.

## Seguridad y respaldos

- Antes de cada edición se crea un respaldo con marca de tiempo.
- La primera copia de cada personaje (`ORIGINAL_...`) se conserva para siempre.
- Tras guardar, el script relee el archivo y comprueba que el inventario es válido.
- Si la verificación falla, restaura automáticamente el respaldo.
- No se permite guardar ni editar inventarios vacíos.

## Solución de problemas

**No aparece ningún personaje.**
Comprueba que diste permiso de almacenamiento (`termux-setup-storage`) y que tu versión de Android permite acceder a `Android/data/`. En Android 11 o superior puede no ser posible sin root.

**El personaje no aparece como *editable*.**
El script no pudo localizar el bloque del inventario en ese archivo. No se modifica nada y se guarda `~/dump.bin` para diagnóstico.

**Solo veo IDs, sin nombres.**
Falta `items.json` en tu carpeta personal. Cópialo con `cp items.json ~/`.

**Mis cambios desaparecieron al abrir el juego.**
Asegúrate de haber cerrado Terraria por completo antes de editar. Si ocurrió igualmente, restaura una copia con `python restaurar.py`.

**El personaje no carga después de editar.**
Puede que hayas usado un ID inexistente. Restaura una copia y comprueba los IDs en la [wiki](https://terraria.wiki.gg/es/wiki/IDs_de_objetos).

**Las alertas (`> [!NOTE]`) de este README se ven como texto en la app de GitHub.**
Es una limitación del renderizado de la app móvil. Ábrelo desde el navegador en github.com.

## Problemas conocidos

- La localización del inventario es heurística. Si no encuentra el bloque, no modifica nada y guarda `~/dump.bin`.
- Una vez, tras editar, el editor mostró el inventario vacío al reabrirlo. No se determinó la causa: el juego pudo reescribir el archivo. Por eso ahora se niega a editar o guardar inventarios vacíos y conserva el original.
- Un ID que no exista en el juego podría dar problemas al cargar el personaje.
- Cantidades muy altas en ítems no apilables pueden causar comportamientos raros.
- Probado únicamente en Android 10 con Terraria 1.4.x.

## Contribuir

Las contribuciones son bienvenidas, sobre todo pruebas en otras versiones de Android o de Terraria.

1. Haz un fork del repositorio.
2. Crea una rama: `git checkout -b mi-mejora`.
3. Haz tus cambios y commit.
4. Abre un pull request describiendo qué probaste y en qué dispositivo.

Si encuentras un fallo, abre un *issue* indicando versión de Android, versión de Terraria y el mensaje de error.

## Aviso legal

Proyecto no oficial, sin relación con Re-Logic ni 505 Games. Se ofrece tal cual, sin garantías. Úsalo bajo tu responsabilidad.

## Licencia y créditos

- **Código:** licencia MIT.
- **Datos de ítems:** `items.json` contiene IDs y nombres de ítems de Terraria, extraídos de la wiki oficial ([IDs de objetos](https://terraria.wiki.gg/es/wiki/IDs_de_objetos)). Fuente: Terraria Wiki, licencia [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Este archivo se redistribuye bajo la misma licencia.
