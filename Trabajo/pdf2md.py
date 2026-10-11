"""
PDF2MD - Convertidor de PDF a Markdown (uso personal, manuales técnicos).

Versión 1.3 — cola de conversión por lotes. Decisiones completas en
`00_NOTAS_PROYECTO.md` ("Versión 1.3 — cola por lotes"); resumen aquí:

Motor: una sola llamada a pymupdf4llm.to_markdown() sobre el documento
completo (más rápido, sin colisión de nombres de imagen entre páginas ya
que pymupdf4llm incluye el número de página en cada nombre). Si esa llamada
falla, fallback automático página a página (pages=[i] en bucle) para aislar
y reportar qué página concreta está rota (comentario HTML + resumen), sin
abortar el resto del documento.

Cola y threading: la cola de archivos se procesa de uno en uno en un hilo
de trabajo aparte (antes: sin threading, justificado por "uso personal,
PDFs de tamaño razonable" — ya no es válido con una cola de varios
archivos, donde bloquear la UI minutos sería mala experiencia). La UI
(tkinter/customtkinter) solo se toca desde el hilo principal; el hilo de
trabajo comunica progreso y resultados exclusivamente vía una
queue.Queue(), consumida por polling con self.after() en el hilo principal.

Conversión pura: `convertir_pdf()` hace todo el trabajo de un archivo
(motor, imágenes vía carpeta temporal, copia a `<stem>_images`, reescritura
de enlaces, limpieza de ".pdf" incrustado en nombres de imagen,
sanitización del nombre de carpeta) sin tocar ningún widget de UI ni abrir
diálogos — así se puede probar directamente en Python y la reutiliza tanto
el hilo de trabajo como cualquier prueba.

Reglas de conflicto: si el .md de destino ya existe, o si existe ya su
carpeta "<stem>_images" en modo con imágenes, el archivo se SALTA sin
tocar nada existente del usuario (nunca se sobrescribe ni se borra una
carpeta de imágenes preexistente — a diferencia de versiones anteriores).

UI: lista de archivos con estado (pendiente/convirtiendo/hecho/saltado/
error), arrastrar y soltar (tkinterdnd2, si está disponible), modo global
(con/sin imágenes) y destino global (junto al PDF / carpeta de salida)
para toda la cola, barra de progreso y resumen final.

Cancelar: termina tras el archivo en curso (no se puede interrumpir la
llamada única de pymupdf4llm, que obtiene su resultado real); los archivos
aún no tocados se quedan en "pendiente" — pulsar Iniciar de nuevo continúa
la cola donde se quedó. No existe un estado "cancelado" propio: no hay
ningún archivo al que aplicarle ese estado una vez el actual termina con
normalidad y el resto simplemente no se ha tocado todavía.

Selección múltiple: el Treeview admite selección de varios elementos a la
vez; "Quitar", "Subir" y "Bajar" operan sobre todos los seleccionados que
estén "pendiente" (el resto de la selección se ignora). "Subir"/"Bajar"
mueven el bloque seleccionado como unidad, conservando su orden relativo
(`ConversionQueue.move_many`), en vez de requerir una selección de un solo
elemento como en versiones anteriores.

"Limpiar completados": quita de la lista los elementos "hecho" (y solo
esos) sin tocar disco; usable en cualquier momento, también con la cola en
marcha, porque nunca afecta al elemento en curso (`ConversionQueue.
clear_done`).

"Reiniciar": vuelve a procesar los elementos seleccionados en estado
"hecho", "saltado" o "error" (los pendientes seleccionados se ignoran; el
elemento en curso nunca se toca), sobrescribiendo su salida existente.
Los elementos afectados pasan a "pendiente" con una marca
`allow_overwrite=True` (visible en la columna de detalle como "Se
sobrescribirá al convertir.") que se evalúa contra el destino vigente en
el momento de procesarse (si Pedro cambia el destino/modo después de
marcar, se usa el nuevo) y se limpia en cuanto el elemento termina (hecho
o error). Antes de aplicar la marca, si alguno de los destinos actuales ya
tiene su salida escrita, se muestra un único diálogo de confirmación con el
recuento; cancelarlo no cambia nada. La sobrescritura en sí
(`convertir_pdf(..., allow_overwrite=True)`) es segura: convierte primero a
archivos/carpetas temporales junto al destino y solo sustituye el `.md` y
la carpeta "_images" existentes si la conversión completa termina bien; si
falla, la salida anterior queda intacta y el elemento pasa a "error".
"""

import os
import re
import shutil
import tempfile
import threading
import queue
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import fitz
import pymupdf4llm
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False


# ---------------------------------------------------------------------------
# Motor de conversión puro (sin UI)
# ---------------------------------------------------------------------------

def _sanitize_folder_name(stem: str) -> str:
    """Sanitiza un nombre de archivo (sin extensión) para usarlo como nombre
    de carpeta en enlaces Markdown: solo alfanuméricos, '_' y '-'.

    Evita espacios sin codificar (muchos visores Markdown estrictos no
    resuelven rutas con espacios sin %20 o <...>) y cualquier otro carácter
    problemático en un enlace relativo.
    """
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem)


def _strip_embedded_pdf_extension(images_dest: Path, text: str) -> str:
    """Renombra imágenes cuyo nombre contiene ".pdf" incrustado antes de la
    extensión real (pymupdf4llm nombra "<origen>.pdf-0001-06.png") y
    reescribe los enlaces correspondientes en `text`.

    Algunos visores/parsers determinan el tipo de archivo por el primer
    punto en vez del último y tratan la imagen como si fuera un PDF.
    """
    for img_file in list(images_dest.iterdir()):
        if ".pdf" in img_file.stem:
            new_name = img_file.stem.replace(".pdf", "") + img_file.suffix
            img_file.rename(img_file.with_name(new_name))
            text = text.replace(img_file.name, new_name)
    return text


def _convertir_pagina_a_pagina(doc, with_images: bool, temp_images_dir: Optional[str],
                                progress_cb: Optional[Callable[[str], None]] = None):
    """Fallback: convierte página a página, aislando errores por página.

    Más lento que la conversión de documento completo (pymupdf4llm reanaliza
    layout/fuentes/tablas en cada llamada), pero permite identificar qué
    página concreta está rota en vez de perder el documento entero.

    Devuelve (texto_markdown, lista_de_errores_por_pagina).
    """
    md_parts = []
    page_errors = []
    total = doc.page_count
    for page_num in range(total):
        if progress_cb:
            progress_cb(f"Fallback página a página: {page_num + 1}/{total}")
        try:
            if with_images:
                page_md = pymupdf4llm.to_markdown(
                    doc,
                    pages=[page_num],
                    write_images=True,
                    image_path=temp_images_dir.replace("\\", "/"),
                    image_format="png",
                    dpi=150,
                )
            else:
                page_md = pymupdf4llm.to_markdown(doc, pages=[page_num], write_images=False)
        except Exception as e:
            page_errors.append((page_num + 1, str(e)))
            page_md = f"\n\n<!-- No se pudo convertir la página {page_num + 1}: {e} -->\n\n"
            traceback.print_exc()
        md_parts.append(page_md)

    result = "\n\n".join(md_parts)
    if page_errors:
        resumen = ", ".join(str(n) for n, _ in page_errors)
        result += f"\n\n<!-- {len(page_errors)} página(s) con problemas: {resumen} -->\n"
    return result, page_errors


def convertir_pdf(
    pdf_path: Path,
    out_md_path: Path,
    with_images: bool,
    progress_cb: Optional[Callable[[str], None]] = None,
    allow_overwrite: bool = False,
) -> dict:
    """Convierte un PDF a Markdown y lo escribe en `out_md_path`.

    Función pura (sin diálogos ni widgets): hace todo lo que antes hacía
    `_convert()` salvo la interacción con el usuario. Pensada para poder
    probarse directamente en Python y para que la reutilice el hilo de
    trabajo de la cola de la UI.

    Motor: intenta primero una única llamada a `pymupdf4llm.to_markdown()`
    sobre el documento completo. Si esa llamada lanza una excepción, cae a
    conversión página a página (`_convertir_pagina_a_pagina`) para aislar y
    reportar qué página concreta está rota, sin abortar el resto.

    Reglas de conflicto (nunca se sobrescribe ni se borra nada existente del
    usuario, salvo que se pida explícitamente con `allow_overwrite`):
    - Si `out_md_path` ya existe -> se salta (status "saltado").
    - Si `with_images` y ya existe la carpeta "<stem_sanitizado>_images"
      junto a `out_md_path` -> se salta (status "saltado"), sin intentar la
      conversión siquiera.

    Sobrescritura segura (`allow_overwrite=True`, usada por "Reiniciar" en
    la UI): se omiten las dos comprobaciones de arriba y se convierte igual
    que siempre, pero el resultado se escribe primero en archivos/carpetas
    temporales junto al destino; solo si la conversión completa termina
    bien se sustituye el `.md` (vía `os.replace`, reemplazo atómico en el
    mismo volumen) y, si procede, se borra la carpeta "<stem>_images"
    antigua y se mueve la nueva en su lugar. Si la conversión falla en
    cualquier punto anterior a ese reemplazo, no se toca nada de la salida
    existente y el estado resultante es "error" — igual que en una
    conversión sin `allow_overwrite`. Este mismo camino (temporal ->
    reemplazo) se usa también cuando `allow_overwrite=False` y el destino
    no existe todavía: en ese caso el "reemplazo" es sencillamente una
    creación normal, así que no hay dos rutas de código distintas para el
    caso con y sin conflicto previo.

    Args:
        pdf_path: ruta del PDF de origen.
        out_md_path: ruta del .md de destino.
        with_images: si True, extrae imágenes a "<stem>_images" junto al
            .md y reescribe los enlaces; si False, solo texto.
        progress_cb: callback opcional `(mensaje: str) -> None` para
            reportar progreso de grano fino (p. ej. durante el fallback
            página a página). No se requiere para el uso básico.
        allow_overwrite: si True, permite sustituir una salida existente
            (ver "Sobrescritura segura" arriba). Pensado para que lo active
            únicamente el botón "Reiniciar" de la UI, archivo por archivo.

    Returns:
        dict con claves:
        - "status": "hecho" | "saltado" | "error"
        - "detail": motivo (saltado/error) o resumen (hecho)
        - "chars": nº de caracteres del .md generado (solo si "hecho"),
          None en otro caso.
    """
    def report(msg: str):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    pdf_path = Path(pdf_path)
    out_md_path = Path(out_md_path)

    images_folder_name = None
    images_dest = None
    if with_images:
        images_folder_name = _sanitize_folder_name(out_md_path.stem) + "_images"
        images_dest = out_md_path.parent / images_folder_name

    # --- Comprobación de conflictos ANTES de hacer ningún trabajo ---
    # (se omite por completo si allow_overwrite=True: ver docstring)
    if not allow_overwrite:
        if out_md_path.exists():
            return {"status": "saltado", "detail": f"Ya existe {out_md_path.name}, no se sobrescribe.", "chars": None}
        if with_images and images_dest.exists():
            return {
                "status": "saltado",
                "detail": f"Ya existe la carpeta {images_folder_name}, no se sobrescribe.",
                "chars": None,
            }

    temp_images_dir = None
    if with_images:
        temp_images_dir = tempfile.mkdtemp(prefix="pdf2md_img_")

    try:
        report("Abriendo PDF...")
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            return {"status": "error", "detail": f"No se pudo abrir el PDF: {e}", "chars": None}

        page_errors = []
        try:
            report("Convirtiendo documento completo...")
            kwargs = (
                dict(write_images=True, image_path=temp_images_dir.replace("\\", "/"),
                     image_format="png", dpi=150)
                if with_images else dict(write_images=False)
            )
            try:
                md_text = pymupdf4llm.to_markdown(doc, **kwargs)
            except Exception as e:
                report(f"La conversión completa falló ({e}); usando fallback página a página...")
                md_text, page_errors = _convertir_pagina_a_pagina(
                    doc, with_images, temp_images_dir, progress_cb
                )
        finally:
            doc.close()

        final_text = md_text

        has_images = False
        if with_images:
            has_images = bool(temp_images_dir) and any(Path(temp_images_dir).iterdir())
            if has_images:
                # Se renombra y reescribe el enlace mientras las imágenes
                # todavía están en la carpeta temporal (antes de moverla a
                # su destino final) — el resultado es idéntico, ya que esta
                # función solo necesita un directorio de imágenes y el texto
                # a reescribir, sin importar su ubicación.
                final_text = final_text.replace(temp_images_dir.replace("\\", "/"), images_dest.name)
                final_text = _strip_embedded_pdf_extension(Path(temp_images_dir), final_text)

        # --- Escritura a ubicación temporal junto al destino ---
        report("Guardando .md (temporal)...")
        temp_md_path = out_md_path.parent / (out_md_path.stem + ".pdf2md_tmp" + out_md_path.suffix)
        try:
            temp_md_path.write_text(final_text, encoding="utf-8")
        except Exception as e:
            return {"status": "error", "detail": f"No se pudo guardar el .md: {e}", "chars": None}

        # --- Sustitución final: solo se llega aquí si la conversión
        # completa (texto + imágenes) terminó bien. ---
        try:
            if with_images and has_images:
                report("Copiando imágenes...")
                if images_dest.exists():
                    shutil.rmtree(images_dest)
                shutil.move(temp_images_dir, str(images_dest))
                temp_images_dir = None  # ya movida; no limpiar en el finally
            os.replace(temp_md_path, out_md_path)
        except Exception as e:
            try:
                if temp_md_path.exists():
                    temp_md_path.unlink()
            except Exception:
                pass
            return {"status": "error", "detail": f"Fallo al sustituir la salida existente: {e}", "chars": None}

        detail = "Convertido correctamente."
        if page_errors:
            detail = f"Convertido con {len(page_errors)} página(s) con problemas (ver comentarios en el .md)."
        return {"status": "hecho", "detail": detail, "chars": len(final_text)}
    finally:
        if temp_images_dir and os.path.isdir(temp_images_dir):
            shutil.rmtree(temp_images_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Cola de conversión (modelo de datos, sin UI)
# ---------------------------------------------------------------------------

ESTADOS_TERMINALES = ("hecho", "saltado", "error")

# Estados desde los que "Reiniciar" puede volver a poner un elemento en
# "pendiente" (con allow_overwrite=True). "convirtiendo" y "pendiente"
# nunca son elegibles: el primero porque el elemento en curso no se toca
# nunca, el segundo porque ya está donde tiene que estar.
RESTARTABLE_STATUSES = ("hecho", "saltado", "error")

# Texto de detalle que marca, de forma visible en la UI, que un elemento
# pendiente va a sobrescribir una salida existente la próxima vez que se
# procese (botón "Reiniciar"). Se limpia en cuanto el elemento termina.
OVERWRITE_MARK_DETAIL = "Se sobrescribirá al convertir."


@dataclass
class QueueItem:
    id: int
    path: Path
    status: str = "pendiente"  # pendiente, convirtiendo, hecho, saltado, error
    detail: str = ""
    allow_overwrite: bool = False


class ConversionQueue:
    """Modelo de la cola de conversión, independiente de tkinter.

    Se probó sin UI (ver pruebas en 00_NOTAS_PROYECTO.md): mantiene el
    estado de cada archivo, las operaciones de añadir/quitar/reordenar/
    reintentar, y ejecuta la conversión de uno en uno vía `convertir_pdf`.
    El hilo de trabajo real (`threading.Thread`) y el polling con
    `self.after()` viven en `PDF2MDApp`; esta clase solo encapsula la lógica
    que se puede probar de forma aislada.
    """

    def __init__(self):
        self.items: list[QueueItem] = []
        self._next_id = 1
        self.lock = threading.Lock()
        self.cancel_event = threading.Event()

    # -- gestión de la lista --

    def add_paths(self, paths) -> int:
        """Añade PDFs sueltos y/o PDFs directos de carpetas (sin subcarpetas),
        ignorando lo que no sea PDF y evitando duplicados (por ruta resuelta).
        Devuelve cuántos elementos nuevos se añadieron."""
        added = 0
        with self.lock:
            existing = {it.path.resolve() for it in self.items}
            for raw in paths:
                p = Path(raw)
                if p.is_dir():
                    try:
                        children = sorted(p.iterdir())
                    except OSError:
                        continue
                    for child in children:
                        if child.is_file() and child.suffix.lower() == ".pdf":
                            try:
                                crp = child.resolve()
                            except OSError:
                                continue
                            if crp not in existing:
                                self.items.append(QueueItem(id=self._next_id, path=child))
                                self._next_id += 1
                                existing.add(crp)
                                added += 1
                elif p.is_file() and p.suffix.lower() == ".pdf":
                    try:
                        rp = p.resolve()
                    except OSError:
                        continue
                    if rp not in existing:
                        self.items.append(QueueItem(id=self._next_id, path=p))
                        self._next_id += 1
                        existing.add(rp)
                        added += 1
                # cualquier otra cosa (archivo no-PDF, ruta inexistente) se ignora
        return added

    def remove(self, ids) -> int:
        """Quita los elementos indicados cuyo estado sea 'pendiente'. Nunca
        quita el que esté 'convirtiendo' ni elementos ya terminados (esto
        último es una decisión de limpieza: solo se reordena/quita lo que
        todavía no se ha procesado). Devuelve cuántos se quitaron."""
        ids = set(ids)
        with self.lock:
            removable = {it.id for it in self.items if it.id in ids and it.status == "pendiente"}
            if removable:
                self.items = [it for it in self.items if it.id not in removable]
            return len(removable)

    def move(self, item_id: int, delta: int) -> bool:
        """Mueve un elemento 'pendiente' una posición arriba (-1) o abajo (+1).
        Devuelve True si se movió. Caso particular de `move_many` con un
        único id; se conserva por comodidad para quien solo mueve uno."""
        return self.move_many([item_id], delta) > 0

    def move_many(self, ids, delta: int) -> int:
        """Mueve varios elementos 'pendiente' a la vez, una posición arriba
        (-1) o abajo (+1), moviendo el bloque seleccionado como unidad y
        conservando su orden relativo (igual que "mover selección" en
        cualquier lista reordenable: los elementos adyacentes seleccionados
        se desplazan juntos, sin intercambiarse entre ellos).

        Ids que no correspondan a un elemento 'pendiente' se ignoran sin
        error (p. ej. si la selección incluye también algo ya terminado).
        Un elemento que ya esté en el límite de la lista simplemente no se
        mueve (no es un error); el resto de la selección sigue moviéndose.

        Devuelve cuántos elementos se movieron efectivamente.
        """
        ids = set(ids)
        with self.lock:
            # Orden de procesado: ascendente para subir, descendente para
            # bajar. Así, al recalcular el índice actual de cada elemento
            # en cada paso (que ya refleja los intercambios anteriores de
            # esta misma llamada), el bloque seleccionado se desplaza como
            # unidad en vez de que sus miembros se intercambien entre sí.
            ordered_ids = [it.id for it in self.items if it.id in ids and it.status == "pendiente"]
            if delta > 0:
                ordered_ids.reverse()

            moved = 0
            for item_id in ordered_ids:
                idx = next((i for i, it in enumerate(self.items) if it.id == item_id), None)
                if idx is None:
                    continue
                new_idx = idx + delta
                if 0 <= new_idx < len(self.items):
                    self.items[idx], self.items[new_idx] = self.items[new_idx], self.items[idx]
                    moved += 1
            return moved

    def retry_failed(self) -> int:
        """Pasa todos los elementos 'error' a 'pendiente'.
        Devuelve cuántos se reintentaron."""
        with self.lock:
            n = 0
            for it in self.items:
                if it.status == "error":
                    it.status = "pendiente"
                    it.detail = ""
                    n += 1
            return n

    def clear_done(self) -> int:
        """Quita de la lista los elementos en estado 'hecho' (y solo esos);
        no toca disco en absoluto. 'saltado', 'error', 'pendiente' y el que
        esté 'convirtiendo' se quedan tal cual. Se puede llamar en cualquier
        momento, también con la cola corriendo en otro hilo, porque nunca
        quita el elemento en curso (nunca está en 'hecho' mientras corre).
        Devuelve cuántos se quitaron."""
        with self.lock:
            before = len(self.items)
            self.items = [it for it in self.items if it.status != "hecho"]
            return before - len(self.items)

    def restart_items(self, ids) -> int:
        """Vuelve a poner en 'pendiente', con `allow_overwrite=True`, los
        elementos indicados cuyo estado sea 'hecho', 'saltado' o 'error'
        (`RESTARTABLE_STATUSES`). Los ids 'pendiente' ya están donde tienen
        que estar (se ignoran, no es un error) y el que esté 'convirtiendo'
        nunca se toca. Marca el detalle con `OVERWRITE_MARK_DETAIL` para que
        sea visible en la UI. Devuelve cuántos elementos se marcaron."""
        ids = set(ids)
        with self.lock:
            n = 0
            for it in self.items:
                if it.id in ids and it.status in RESTARTABLE_STATUSES:
                    it.status = "pendiente"
                    it.allow_overwrite = True
                    it.detail = OVERWRITE_MARK_DETAIL
                    n += 1
            return n

    def restartable_snapshot(self, ids):
        """Copia ligera (id, path) de los elementos de `ids` que son
        elegibles para 'Reiniciar' en este momento, sin mutar nada. Pensada
        para que la UI calcule cuántos destinos ya existen (y así decidir
        si hace falta el diálogo de confirmación) antes de llamar a
        `restart_items`."""
        ids = set(ids)
        with self.lock:
            return [(it.id, it.path) for it in self.items if it.id in ids and it.status in RESTARTABLE_STATUSES]

    def snapshot(self):
        """Copia ligera (id, nombre, status, detail) para refrescar la UI."""
        with self.lock:
            return [(it.id, it.path.name, it.status, it.detail) for it in self.items]

    def counts(self) -> dict:
        with self.lock:
            c = {"pendiente": 0, "convirtiendo": 0, "hecho": 0, "saltado": 0, "error": 0}
            for it in self.items:
                c[it.status] = c.get(it.status, 0) + 1
            return c

    # -- ejecución --

    @staticmethod
    def resolve_out_path(pdf_path: Path, destino_junto: bool, carpeta_salida: Optional[Path]) -> Path:
        if destino_junto:
            return pdf_path.with_suffix(".md")
        return carpeta_salida / (pdf_path.stem + ".md")

    def run(self, with_images: bool, destino_junto: bool, carpeta_salida: Optional[Path],
            on_event: Callable[[str, object], None]):
        """Procesa los elementos 'pendiente' de uno en uno, en orden de
        lista, hasta agotarlos o hasta que se active `cancel_event`.

        `on_event(kind, payload)` se llama para cada evento ("item_start",
        "item_progress", "item_done", "finished") — pensado para que el
        llamador (hilo de trabajo real o un test) decida qué hacer con cada
        evento sin acoplar esta clase a ningún widget.

        Cancelar: termina tras el archivo en curso (no se puede interrumpir
        la llamada única de pymupdf4llm) — ese archivo obtiene su resultado
        real (hecho/saltado/error). Los elementos que seguían 'pendiente' en
        ese momento se quedan en 'pendiente', sin tocar: volver a llamar a
        `run()` (botón Iniciar) continúa la cola exactamente donde se quedó.
        No hay un estado "cancelado" propio (ver 00_NOTAS_PROYECTO.md).
        """
        while not self.cancel_event.is_set():
            with self.lock:
                item = next((it for it in self.items if it.status == "pendiente"), None)
                if item is None:
                    break
                item.status = "convirtiendo"
                item.detail = ""
            on_event("item_start", item)

            out_path = self.resolve_out_path(item.path, destino_junto, carpeta_salida)

            def progress_cb(msg, _item=item):
                _item.detail = msg
                on_event("item_progress", _item)

            try:
                result = convertir_pdf(
                    item.path, out_path, with_images, progress_cb,
                    allow_overwrite=item.allow_overwrite,
                )
                item.status = result["status"]
                item.detail = result["detail"]
            except Exception as e:
                item.status = "error"
                item.detail = f"Error inesperado: {e}"
                traceback.print_exc()
            finally:
                # Tras procesarse (hecho o error), la marca de sobrescribir
                # se elimina siempre, haya ido bien o mal.
                item.allow_overwrite = False

            on_event("item_done", item)

        # Si se canceló, los elementos que seguían 'pendiente' se dejan tal
        # cual (sin marcar nada): la próxima llamada a run() los recogerá
        # en el mismo orden, como si la tanda nunca se hubiera interrumpido.
        on_event("finished", None)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

if DND_AVAILABLE:
    class _AppBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class _AppBase(ctk.CTk):
        pass


class PDF2MDApp(_AppBase):
    COLUMNS = ("archivo", "estado", "detalle")
    HEADERS = {"archivo": "Archivo", "estado": "Estado", "detalle": "Detalle"}

    def __init__(self):
        super().__init__()

        self.title("PDF a Markdown")
        self.geometry("920x640")
        self.minsize(760, 520)
        self.resizable(True, True)

        ctk.set_appearance_mode("System")

        self.cola = ConversionQueue()
        self._msg_queue: "queue.Queue" = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._run_total = 0
        self._run_done = 0
        self.carpeta_salida: Optional[Path] = None

        self._build_ui()
        self._refresh_treeview()
        self._update_controls_running(False)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- construcción de la UI ----

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # -- Opciones globales --
        opts = ctk.CTkFrame(self)
        opts.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        opts.grid_columnconfigure(1, weight=1)
        opts.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(opts, text="Modo:").grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")
        self.modo_btn = ctk.CTkSegmentedButton(
            opts,
            values=["Texto MD + imágenes", "Solo texto MD"],
            command=self._on_modo_change,
        )
        self.modo_btn.set("Texto MD + imágenes")
        self.modo_btn.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")

        ctk.CTkLabel(opts, text="Destino:").grid(row=0, column=2, padx=(10, 5), pady=8, sticky="w")
        self.destino_btn = ctk.CTkSegmentedButton(
            opts,
            values=["Junto a cada PDF", "Carpeta de salida"],
            command=self._on_destino_change,
        )
        self.destino_btn.set("Junto a cada PDF")
        self.destino_btn.grid(row=0, column=3, padx=(0, 5), pady=8, sticky="w")

        self.btn_choose_folder = ctk.CTkButton(
            opts, text="Elegir carpeta...", width=120, command=self.on_choose_output_folder, state="disabled"
        )
        self.btn_choose_folder.grid(row=0, column=4, padx=(0, 10), pady=8, sticky="w")

        self.label_carpeta_salida = ctk.CTkLabel(opts, text="(sin carpeta de salida elegida)", wraplength=400)
        self.label_carpeta_salida.grid(row=1, column=0, columnspan=5, padx=10, pady=(0, 8), sticky="w")

        # -- Zona principal: lista + botones --
        main = ctk.CTkFrame(self)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(main)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use(style.theme_use())
        except Exception:
            pass
        style.configure("Treeview", rowheight=24)

        self.tree = ttk.Treeview(tree_frame, columns=self.COLUMNS, show="headings", selectmode="extended")
        for col in self.COLUMNS:
            self.tree.heading(col, text=self.HEADERS[col])
        self.tree.column("archivo", width=280, anchor="w")
        self.tree.column("estado", width=110, anchor="center")
        self.tree.column("detalle", width=320, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons_state())

        if DND_AVAILABLE:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

        btns = ctk.CTkFrame(main)
        btns.grid(row=0, column=1, sticky="ns", padx=(5, 0))

        self.btn_add_files = ctk.CTkButton(btns, text="Añadir archivos", command=self.on_add_files)
        self.btn_add_files.pack(fill="x", padx=8, pady=(8, 4))
        self.btn_add_folder = ctk.CTkButton(btns, text="Añadir carpeta", command=self.on_add_folder)
        self.btn_add_folder.pack(fill="x", padx=8, pady=4)
        self.btn_remove = ctk.CTkButton(btns, text="Quitar", command=self.on_remove_selected)
        self.btn_remove.pack(fill="x", padx=8, pady=4)
        self.btn_up = ctk.CTkButton(btns, text="Subir", command=lambda: self.on_move(-1))
        self.btn_up.pack(fill="x", padx=8, pady=4)
        self.btn_down = ctk.CTkButton(btns, text="Bajar", command=lambda: self.on_move(1))
        self.btn_down.pack(fill="x", padx=8, pady=4)
        self.btn_retry = ctk.CTkButton(btns, text="Reintentar fallidos", command=self.on_retry_failed)
        self.btn_retry.pack(fill="x", padx=8, pady=4)
        self.btn_restart = ctk.CTkButton(btns, text="Reiniciar", command=self.on_restart_selected)
        self.btn_restart.pack(fill="x", padx=8, pady=4)
        self.btn_clear_done = ctk.CTkButton(btns, text="Limpiar completados", command=self.on_clear_done)
        self.btn_clear_done.pack(fill="x", padx=8, pady=4)

        sep = ctk.CTkFrame(btns, height=2)
        sep.pack(fill="x", padx=8, pady=8)

        self.btn_start = ctk.CTkButton(btns, text="Iniciar", command=self.on_start, fg_color="#2a7a2a", hover_color="#1f5c1f")
        self.btn_start.pack(fill="x", padx=8, pady=4)
        self.btn_cancel = ctk.CTkButton(btns, text="Cancelar", command=self.on_cancel, fg_color="#8a2a2a", hover_color="#6c1f1f")
        self.btn_cancel.pack(fill="x", padx=8, pady=4)

        if not DND_AVAILABLE:
            ctk.CTkLabel(
                btns, text="(arrastrar y soltar\nno disponible)", text_color="gray", justify="center"
            ).pack(fill="x", padx=8, pady=(10, 4))

        # -- Progreso + resumen --
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        bottom.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(bottom)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=(10, 4))
        self.label_progress = ctk.CTkLabel(bottom, text="0/0")
        self.label_progress.grid(row=0, column=1, padx=(0, 10), pady=(10, 4))

        self.label_resumen = ctk.CTkLabel(bottom, text="", wraplength=860, justify="left")
        self.label_resumen.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

    # ---- helpers de estado de controles ----

    def _modo_with_images(self) -> bool:
        return self.modo_btn.get() == "Texto MD + imágenes"

    def _destino_junto(self) -> bool:
        return self.destino_btn.get() == "Junto a cada PDF"

    def _on_modo_change(self, _value):
        self._update_buttons_state()

    def _on_destino_change(self, value):
        is_carpeta = value == "Carpeta de salida"
        self.btn_choose_folder.configure(state="normal" if (is_carpeta and not self._running) else "disabled")
        self._update_buttons_state()

    def _update_controls_running(self, running: bool):
        self._running = running
        state_idle = "disabled" if running else "normal"
        self.btn_add_files.configure(state=state_idle)
        self.btn_add_folder.configure(state=state_idle)
        self.modo_btn.configure(state=state_idle)
        self.destino_btn.configure(state=state_idle)
        if not running and self._destino_junto() is False:
            self.btn_choose_folder.configure(state="normal")
        else:
            self.btn_choose_folder.configure(state="disabled")
        self.btn_cancel.configure(state=("normal" if running else "disabled"))
        self._update_buttons_state()

    def _selected_pendiente_ids(self):
        with self.cola.lock:
            pendientes = {it.id for it in self.cola.items if it.status == "pendiente"}
        sel = self.tree.selection()
        return [int(iid) for iid in sel if int(iid) in pendientes]

    def _selected_restartable_ids(self):
        """Ids seleccionados en el Treeview cuyo estado permite 'Reiniciar'
        (hecho/saltado/error). Los pendientes seleccionados y el elemento
        en curso (si estuviera seleccionado) quedan fuera."""
        with self.cola.lock:
            restartable = {it.id for it in self.cola.items if it.status in RESTARTABLE_STATUSES}
        sel = self.tree.selection()
        return [int(iid) for iid in sel if int(iid) in restartable]

    def _update_buttons_state(self):
        counts = self.cola.counts()
        sel_pend = self._selected_pendiente_ids()
        sel_restart = self._selected_restartable_ids()

        self.btn_remove.configure(state=("normal" if sel_pend else "disabled"))
        self.btn_up.configure(state=("normal" if sel_pend else "disabled"))
        self.btn_down.configure(state=("normal" if sel_pend else "disabled"))
        self.btn_retry.configure(state=("normal" if counts["error"] > 0 else "disabled"))
        self.btn_restart.configure(state=("normal" if sel_restart else "disabled"))
        self.btn_clear_done.configure(state=("normal" if counts["hecho"] > 0 else "disabled"))

        destino_ok = self._destino_junto() or (self.carpeta_salida is not None)
        puede_iniciar = (not self._running) and counts["pendiente"] > 0 and destino_ok
        self.btn_start.configure(state=("normal" if puede_iniciar else "disabled"))

    def _update_progress_label(self):
        self.label_progress.configure(text=f"{self._run_done}/{self._run_total}")
        if self._run_total > 0:
            self.progress_bar.set(self._run_done / self._run_total)
        else:
            self.progress_bar.set(0)

    # ---- añadir / quitar / reordenar ----

    def _add_paths(self, paths):
        added = self.cola.add_paths(paths)
        if added:
            self._refresh_treeview()
        return added

    def on_add_files(self):
        if self._running:
            return
        paths = filedialog.askopenfilenames(
            title="Selecciona uno o varios PDF", filetypes=[("Archivos PDF", "*.pdf")]
        )
        if paths:
            self._add_paths([Path(p) for p in paths])

    def on_add_folder(self):
        if self._running:
            return
        folder = filedialog.askdirectory(title="Selecciona una carpeta (solo sus PDFs directos)")
        if folder:
            self._add_paths([Path(folder)])

    def _on_drop(self, event):
        if self._running:
            return
        try:
            raw_paths = self.tk.splitlist(event.data)
        except Exception:
            return
        self._add_paths([Path(p) for p in raw_paths])

    def on_remove_selected(self):
        ids = self._selected_pendiente_ids()
        if not ids:
            return
        self.cola.remove(ids)
        self._refresh_treeview()

    def on_move(self, delta):
        ids = self._selected_pendiente_ids()
        if not ids:
            return
        if self.cola.move_many(ids, delta):
            # _refresh_treeview conserva la selección actual (misma por id),
            # así que el bloque movido se ve seguir seleccionado.
            self._refresh_treeview()
            iid = str(ids[0])
            if self.tree.exists(iid):
                self.tree.see(iid)

    def on_retry_failed(self):
        if self.cola.retry_failed():
            self._refresh_treeview()

    def on_clear_done(self):
        """Quita de la lista los elementos 'hecho' (y solo esos); no borra
        nada del disco. Puede pulsarse en cualquier momento, también con la
        cola en marcha — nunca afecta al elemento en curso."""
        if self.cola.clear_done():
            self._refresh_treeview()

    def on_restart_selected(self):
        """Vuelve a procesar los elementos seleccionados que estén en
        'hecho', 'saltado' o 'error' (los pendientes seleccionados se
        ignoran; el elemento en curso nunca se toca), sobrescribiendo su
        salida. Antes de aplicar, si alguno de los destinos actuales ya
        tiene su .md (o su carpeta "_images" en modo con imágenes) escrito,
        se pide confirmación una sola vez con el recuento; si se cancela,
        no cambia nada."""
        ids = self._selected_restartable_ids()
        if not ids:
            return

        candidatos = self.cola.restartable_snapshot(ids)
        if not candidatos:
            return

        destino_junto = self._destino_junto()
        carpeta_salida = self.carpeta_salida
        with_images = self._modo_with_images()

        n_conflict = 0
        if destino_junto or carpeta_salida is not None:
            for _id, path in candidatos:
                out_path = ConversionQueue.resolve_out_path(path, destino_junto, carpeta_salida)
                conflict = out_path.exists()
                if with_images:
                    images_dest = out_path.parent / (_sanitize_folder_name(out_path.stem) + "_images")
                    conflict = conflict or images_dest.exists()
                if conflict:
                    n_conflict += 1

        if n_conflict > 0:
            if not messagebox.askyesno(
                "Confirmar reinicio",
                f"Se sobrescribirán {n_conflict} archivo(s) existente(s) en su destino actual.\n"
                "¿Continuar?",
            ):
                return

        restart_ids = [cid for cid, _ in candidatos]
        n = self.cola.restart_items(restart_ids)
        if n:
            if self._running:
                # Hay elementos nuevos en 'pendiente' que el hilo en marcha
                # recogerá solo (run() busca el siguiente 'pendiente' en
                # cada iteración) — se ajusta el total para que la barra de
                # progreso siga siendo coherente.
                self._run_total += n
                self._update_progress_label()
            self._refresh_treeview()

    def on_choose_output_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if folder:
            self.carpeta_salida = Path(folder)
            self.label_carpeta_salida.configure(text=str(self.carpeta_salida))
            self._update_buttons_state()

    # ---- refresco de la lista ----

    def _refresh_treeview(self):
        sel = self.tree.selection()
        snapshot = self.cola.snapshot()
        self.tree.delete(*self.tree.get_children())
        for iid, name, status, detail in snapshot:
            self.tree.insert("", "end", iid=str(iid), values=(name, status, detail))
        for s in sel:
            if self.tree.exists(s):
                self.tree.selection_add(s)
        self._update_progress_label()
        self._update_buttons_state()

    # ---- arranque / cancelación de la cola ----

    def on_start(self):
        if self._running:
            return
        counts = self.cola.counts()
        if counts["pendiente"] == 0:
            return
        destino_junto = self._destino_junto()
        if not destino_junto and self.carpeta_salida is None:
            return
        with_images = self._modo_with_images()

        self.cola.cancel_event.clear()
        self._run_total = counts["pendiente"]
        self._run_done = 0
        self.label_resumen.configure(text="Convirtiendo...")
        self._update_controls_running(True)
        self._update_progress_label()

        self._worker_thread = threading.Thread(
            target=self._worker_run,
            args=(with_images, destino_junto, self.carpeta_salida),
            daemon=True,
        )
        self._worker_thread.start()
        self.after(150, self._poll_queue)

    def on_cancel(self):
        if not self._running:
            return
        self.cola.cancel_event.set()
        self.label_resumen.configure(text="Cancelando... terminará tras el archivo en curso.")

    def _worker_run(self, with_images, destino_junto, carpeta_salida):
        def on_event(kind, _payload):
            # Fix (v1.3b): el evento "finished" se perdía aquí (se
            # sustituía siempre por "refresh"), así que `_poll_queue` nunca
            # veía terminar la tanda y `self._running` se quedaba en True
            # para siempre tras pulsar "Iniciar" (la UI se quedaba en
            # "Convirtiendo..." indefinidamente aunque la cola ya hubiera
            # terminado de verdad en el hilo de trabajo).
            if kind == "item_done":
                self._msg_queue.put(("tick", None))
            elif kind == "finished":
                self._msg_queue.put(("finished", None))
            self._msg_queue.put(("refresh", None))

        self.cola.run(with_images, destino_junto, carpeta_salida, on_event)

    def _poll_queue(self):
        finished = False
        try:
            while True:
                kind, _payload = self._msg_queue.get_nowait()
                if kind == "tick":
                    self._run_done += 1
                elif kind == "finished":
                    finished = True
        except queue.Empty:
            pass

        self._refresh_treeview()

        if finished:
            self._on_run_finished()
        else:
            self.after(150, self._poll_queue)

    def _on_run_finished(self):
        counts = self.cola.counts()
        resumen = (
            f"Terminado: {counts['hecho']} hecho(s), {counts['saltado']} saltado(s), "
            f"{counts['error']} error(es)."
        )
        if counts["pendiente"] > 0:
            resumen += f" {counts['pendiente']} pendiente(s) sin procesar (cancelado antes de llegar a ellos)."
        self.label_resumen.configure(text=resumen)
        self._update_controls_running(False)

    # ---- cierre de ventana ----

    def _on_close(self):
        if self._running:
            if not messagebox.askyesno(
                "Conversión en curso",
                "Hay una conversión en curso. Se cancelará (terminará el archivo "
                "actual y no se iniciarán los siguientes) y se cerrará la aplicación.\n"
                "¿Continuar?",
            ):
                return
            self.cola.cancel_event.set()
        self.destroy()


if __name__ == "__main__":
    app = PDF2MDApp()
    app.mainloop()
