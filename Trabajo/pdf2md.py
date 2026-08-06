"""
PDF2MD - Convertidor de PDF a Markdown (uso personal, manuales técnicos).

Motor: pymupdf4llm.to_markdown() -> jerarquía de encabezados por tamaño de
fuente, tablas como Markdown, orden de lectura correcto en layouts multi-columna.

Conversión página a página: permite seguir si una página concreta falla
(no todo-o-nada) y evita colisiones de nombre de imagen entre páginas.

Imágenes: write_images=True de pymupdf4llm, sin reencode manual con PIL.
Se escriben primero en una carpeta temporal y, tras la conversión, se copian
junto al .md elegido, reescribiendo los enlaces relativos en el texto.

UI de 3 botones: "Seleccionar PDF", "Texto MD+Imágenes" y "Texto MD". La
conversión ocurre dentro del propio botón pulsado, justo antes de escribir el
archivo, no como paso independiente. Ambos botones de guardado comparten la
lógica común (bucle página a página, manejo de errores, diálogo de guardado)
en `_convert()`; solo difieren en si se pide a pymupdf4llm que extraiga
imágenes (`write_images=True` + carpeta temporal) o no (por defecto,
`write_images=False`, sin enlaces `![]` en el resultado).
"""

import os
import re
import shutil
import tempfile
import traceback
from pathlib import Path

import fitz
import pymupdf4llm
import customtkinter as ctk
from tkinter import filedialog, messagebox


class PDF2MDApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF a Markdown")
        self.geometry("520x260")
        self.resizable(False, False)

        self.pdf_path = None
        self.markdown_text = None
        self.temp_images_dir = None
        self.page_errors = []

        ctk.set_appearance_mode("System")

        self.label_pdf = ctk.CTkLabel(self, text="Ningún PDF seleccionado", wraplength=460)
        self.label_pdf.pack(pady=(20, 10))

        self.btn_select = ctk.CTkButton(self, text="Seleccionar PDF", command=self.select_pdf)
        self.btn_select.pack(pady=5)

        self.btn_save_images = ctk.CTkButton(
            self,
            text="Texto MD+Imágenes",
            command=self.save_markdown_with_images,
            state="disabled",
        )
        self.btn_save_images.pack(pady=5)

        self.btn_save_text = ctk.CTkButton(
            self, text="Texto MD", command=self.save_markdown_text_only, state="disabled"
        )
        self.btn_save_text.pack(pady=5)

        self.label_status = ctk.CTkLabel(self, text="", wraplength=460, justify="left")
        self.label_status.pack(pady=(15, 10))

    def select_pdf(self):
        path = filedialog.askopenfilename(
            title="Selecciona un PDF",
            filetypes=[("Archivos PDF", "*.pdf")],
        )
        if not path:
            return
        self.pdf_path = Path(path)
        self.markdown_text = None
        self.page_errors = []
        self.label_pdf.configure(text=f"PDF: {self.pdf_path.name}")
        self.btn_save_images.configure(state="normal")
        self.btn_save_text.configure(state="normal")
        self.label_status.configure(text="Listo para guardar.")

    def save_markdown_with_images(self):
        self._convert(with_images=True)

    def save_markdown_text_only(self):
        self._convert(with_images=False)

    def _convert(self, with_images):
        if not self.pdf_path:
            return

        out_path = filedialog.asksaveasfilename(
            title="Guardar Markdown",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialfile=(self.pdf_path.stem + ".md") if self.pdf_path else "documento.md",
        )
        if not out_path:
            return

        out_path = Path(out_path)

        self.label_status.configure(text="Convirtiendo, por favor espera...")
        self.update_idletasks()

        temp_images_dir = None
        if with_images:
            if self.temp_images_dir and os.path.isdir(self.temp_images_dir):
                shutil.rmtree(self.temp_images_dir, ignore_errors=True)
            temp_images_dir = tempfile.mkdtemp(prefix="pdf2md_img_")
            self.temp_images_dir = temp_images_dir

        self.page_errors = []
        md_parts = []

        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF:\n{e}")
            self.label_status.configure(text="Error al abrir el PDF.")
            return

        try:
            for page_num in range(doc.page_count):
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
                        page_md = pymupdf4llm.to_markdown(
                            doc,
                            pages=[page_num],
                            write_images=False,
                        )
                except Exception as e:
                    self.page_errors.append((page_num + 1, str(e)))
                    page_md = f"\n\n<!-- No se pudo convertir la página {page_num + 1}: {e} -->\n\n"
                    traceback.print_exc()
                md_parts.append(page_md)
        finally:
            doc.close()

        self.markdown_text = "\n\n".join(md_parts)
        final_text = self.markdown_text

        if with_images:
            has_images = bool(temp_images_dir) and any(Path(temp_images_dir).iterdir())
            if has_images:
                safe_stem = re.sub(r"[^A-Za-z0-9_-]", "_", out_path.stem)
                images_folder_name = safe_stem + "_images"
                images_dest = out_path.parent / images_folder_name
                try:
                    if images_dest.exists():
                        shutil.rmtree(images_dest)
                    shutil.copytree(temp_images_dir, images_dest)
                    final_text = final_text.replace(
                        temp_images_dir.replace("\\", "/"), images_folder_name
                    )
                    # pymupdf4llm incrusta ".pdf" en medio del nombre de imagen
                    # (p.ej. "doc.pdf-0001-06.png"), lo que confunde a visores/parsers
                    # que detectan el tipo por el primer punto en vez del último.
                    for img_file in list(images_dest.iterdir()):
                        if ".pdf" in img_file.stem:
                            new_name = img_file.stem.replace(".pdf", "") + img_file.suffix
                            img_file.rename(img_file.with_name(new_name))
                            final_text = final_text.replace(img_file.name, new_name)
                except Exception as e:
                    messagebox.showwarning(
                        "Aviso",
                        f"El markdown se guardará, pero no se pudieron copiar las imágenes:\n{e}",
                    )

        try:
            out_path.write_text(final_text, encoding="utf-8")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")
            return

        if temp_images_dir and os.path.isdir(temp_images_dir):
            shutil.rmtree(temp_images_dir, ignore_errors=True)
            self.temp_images_dir = None

        msg = f"Guardado en {out_path}"
        if self.page_errors:
            msg += f"\n({len(self.page_errors)} página(s) con problemas, ver detalle en el .md)"
        messagebox.showinfo("Guardado", msg)
        self.label_status.configure(text=msg)


if __name__ == "__main__":
    app = PDF2MDApp()
    app.mainloop()
