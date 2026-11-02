import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from mosaic_color import run_mosaiccolorpress

IMG_TYPES = [("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")]


def run_job(files, grid_w, max_colors, outdir):
    s = run_mosaiccolorpress(files, outdir, grid_w=grid_w, max_colors=max_colors)
    lines = [f"Photos converted: {s['images']}", f"Total cells: {s['total_cells']}"]
    for p in s["pages"]:
        lines.append(f"  {p['source']}: {p['w']}x{p['h']} grid, "
                     f"{len(p['palette'])} colors, recount PASS")
    lines.append(f"PDF: {s['pdf_path']}")
    return lines


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MosaicColorPress")
        self.geometry("640x540")
        self.resizable(False, False)
        self.files = []
        row = tk.Frame(self); row.pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(row, text="Photos:", width=34, anchor="w").pack(side="left")
        tk.Button(row, text="Add photos...", command=self.add_files).pack(side="left")
        tk.Button(row, text="Clear", command=self.clear_files).pack(side="left", padx=4)
        self.file_label = tk.Label(self, text="No photos chosen yet.", anchor="w")
        self.file_label.pack(fill="x", padx=12)
        self.grid_w = tk.StringVar(value="44")
        self.max_colors = tk.StringVar(value="16")
        for label, var in [("Grid width (cells):", self.grid_w),
                           ("Max colors per page:", self.max_colors)]:
            row = tk.Frame(self); row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=label, width=34, anchor="w").pack(side="left")
            tk.Entry(row, textvariable=var, width=10).pack(side="left")
        tk.Button(self, text="Build the book", font=("Segoe UI", 11, "bold"),
                  command=self.start).pack(pady=10)
        self.log = scrolledtext.ScrolledText(self, width=76, height=13,
                                             font=("Consolas", 9))
        self.log.pack(padx=12, pady=4)
        self.write("Add your photos, build once, get a whole book: a numbered coloring page and a color key with a filled reference for every photo. Every page is recounted cell by cell before it prints.")

    def write(self, msg):
        self.log.insert(tk.END, str(msg) + "\n")
        self.log.see(tk.END)
        self.update_idletasks()

    def add_files(self):
        paths = filedialog.askopenfilenames(filetypes=IMG_TYPES)
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self.refresh_label()

    def clear_files(self):
        self.files = []
        self.refresh_label()

    def refresh_label(self):
        if self.files:
            self.file_label.config(
                text=f"{len(self.files)} photo(s): " +
                     ", ".join(os.path.basename(f) for f in self.files[:4]) +
                     (" ..." if len(self.files) > 4 else ""))
        else:
            self.file_label.config(text="No photos chosen yet.")

    def collect(self):
        if not self.files:
            raise ValueError("Add at least one photo first.")
        gw = int(self.grid_w.get())
        mc = int(self.max_colors.get())
        if not (16 <= gw <= 80):
            raise ValueError("Grid width must be between 16 and 80 cells.")
        if not (4 <= mc <= 24):
            raise ValueError("Max colors must be between 4 and 24.")
        return (list(self.files), gw, mc,
                os.path.join(os.getcwd(), "mosaiccolorpress_out"))

    def start(self):
        try:
            args = self.collect()
        except Exception as e:
            messagebox.showerror("MosaicColorPress", str(e))
            return

        def work():
            try:
                for ln in run_job(*args):
                    self.write(ln)
            except Exception as e:
                self.write(f"ERROR: {e}")

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
