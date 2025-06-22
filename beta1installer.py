"""
steam_setup_wizard.py – pixel-perfect clone of the classic Steam Setup wizard
Python 3.9 / Tkinter
"""

import os, sys, threading, time, tkinter as tk
from tkinter import filedialog, messagebox
import base64
from tkinter import ttk
from tkinter import PhotoImage

def resource_path(rel_path):
    """Return absolute path to resource, works for PyInstaller."""
    base = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, rel_path)
import ctypes
import platform
# ────────────────────────────────────────────────────────────────────
# Classic Browse-for-Folder dialog (Win95-XP look) via SHBrowseForFolder
# ────────────────────────────────────────────────────────────────────
from ctypes import wintypes

# ────────────────────────────────────────────────────────────────
# Embedded 16×16 classic Windows icons  (complete base-64 strings)
# ────────────────────────────────────────────────────────────────
_DRIVE_GIF = """
R0lGODdhEAAQAIEAAAAAAObm5gAAAMDAwCwAAAAAEAAQAEAIRwABCBxIsKBAAQMCKFzIcICAgwIiSpwoESLFiw8NaiSIkKHHAA4PJvy4MOTGkyhTpkQ4oKXLlyY7klQYc+TMmjBzZlTJ02BAADs=
"""

_FLD_CLOSED_GIF = """
R0lGODdhEAAQAIEAAP/IAICAAAAAAP/cMCwAAAAAEAAQAEAITwAFCBxIsKCAAAASKly4MIDAAAMiShzgkCBChhgTVgzAsWPHggg9imx4MSNDjiYxVjTIciDEiRFXPuQIM6bIkik14syJMqfCnj4B3BzqMSAAOw==
"""
_FLD_OPEN_GIF = """
R0lGODdhEAAQAIEAAAAAAICAAP/IAP/cMCwAAAAAEAAQAEAISAABCBxIsKDAAAgTKlw4MMCAhw8DGDwooKLFiwIkNlyocSLHjgUDYBwJ8qPCiSgNOoQ4AGRIli1TyiQociRJijYtlsyZcebEgAA7
"""


# ── tiny yellow/grey 16×16 fallback images ─────────────────────────
def _make_fallback(master, colour):
    img = PhotoImage(master=master, width=16, height=16)
    img.put(colour, to=(0, 0, 15, 15))
    return img

def _p(master, b64_or_none):
    """
    Create a PhotoImage from a full base-64 GIF string.
    If that fails (truncated data), return a flat 16×16 placeholder
    so Tk never raises TclError.
    """
    try:
        return PhotoImage(master=master, data="".join(b64_or_none.split()))
    except Exception:
        # yellow = folder, grey = drive
        fallback = "#F0C000" if "FLD" in b64_or_none else "#808080"
        return _make_fallback(master, fallback)


# ────────────────────────────────────────────────────────────────────────────────
# GEOMETRY & VISUAL CONSTANTS  ── all figures are from the Window-Detective XML
#                                 dumps of the genuine wizard.
# ────────────────────────────────────────────────────────────────────────────────
OUTER_W, OUTER_H      = 480, 361            # 480 × 335 client  +22-px caption
CLIENT_W, CLIENT_H    = 480, 335
BG, LINE_CLR          = "#f0f0f0", "#c0c0c0"
BODY_FONT             = ("Helv", -11)              # Helv -11 px :contentReference[oaicite:7]{index=7}

# Client-relative rects (x, y, w, h)
LEFT_PAD              = 16
WELCOME_RECT          = (157,  16, 298,  55)              # :contentReference[oaicite:8]{index=8}
BODY_RECT             = (157,  73, 298, 211)              # :contentReference[oaicite:9]{index=9}
DIVIDER_RECT          = (LEFT_PAD, 288, 444,   2)         # :contentReference[oaicite:10]{index=10}
BTN_Y                 = 301
BACK_RECT             = (214, BTN_Y, 73, 23)
NEXT_RECT             = (301, BTN_Y, 73, 23)              # :contentReference[oaicite:11]{index=11}
CANCEL_RECT           = (388, BTN_Y, 74, 23)              # :contentReference[oaicite:12]{index=12}

class DriveComboBox(ttk.Frame):
    """Drop-down with icon + drive letter + volume label (read-only)."""
    def __init__(self, master, icon, *, width=120, font=None):
        super().__init__(master)
        self._icon = icon
        self._font = font or ("Helv", -11)

        # A true ttk.Combobox (read-only) for native look
        self._var = tk.StringVar()
        self._cb  = ttk.Combobox(self, textvariable=self._var,
                                 font=self._font, state="readonly",
                                 width=30,           # ≈ 250 px, matches tree
                                 justify="left")
        self._cb.pack(fill="x")
        self._cb.bind("<<ComboboxSelected>>", lambda _e: self.event_generate("<<DriveChanged>>"))

        # collect drives + names, then fill list
        self._drives, self._names = self._scan_drives()
        self._cb["values"] = [f"{d}  –  {self._names[d]}" for d in self._drives]

        self.set(self._drives[0])        # default C:

    @property
    def root_path(self):              # e.g. 'C:\\'
        d = self.get().rstrip(":")
        return d + ":\\"

    def _scan_drives(self):
        drives = [f"{d}:" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  if os.path.exists(f"{d}:\\")]
        names  = {d: "Local Disk" for d in drives}
        try:
            import ctypes
            GetVol = ctypes.windll.kernel32.GetVolumeInformationW
            buf = ctypes.create_unicode_buffer(261)
            for d in drives:
                if GetVol(f"{d}\\", buf, 260, None, None, None, None, 0):
                    if buf.value: names[d] = buf.value
        except Exception: pass
        return drives, names

    # API
    def set(self, drive):
        d = drive.rstrip(":\\")
        display = f"{d}  –  {self._names.get(d+':','')}"
        self._cb.set(display)                               # show in widget
        if d + ":" in self._drives:                         # keep index
            self._cb.current(self._drives.index(d + ":"))

    def get(self):                # returns 'C' .. 'Z'
        return self._var.get().split()[0]


    # pop-down via tk.Menu (supports images)
    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.unpost(); return
        self._popup = tk.Menu(self, tearoff=0, font=self._font)
        for d in self._drives:
            self._popup.add_command(image=self._icon, compound="left",
                                    label=f"{d}  –  {self._names[d]}",
                                    command=lambda dd=d: self._choose(dd))
        x = self.winfo_rootx(); y = self.winfo_rooty()+self.winfo_height()
        self._popup.post(x, y)

    def _choose(self, d):
        self.set(d); self.event_generate("<<DriveChanged>>")
        self._popup.unpost()

# ────────────────────────────────────────────────────────────────
class FolderList(ttk.Treeview):
    """Single-column tree that shows closed/open folder icons & a '..' line."""
    def __init__(self, master, root_dir, closed_ic, open_ic, **kw):
        super().__init__(master, show="tree", selectmode="browse", **kw)
        self.column("#0", width=230, stretch=False)
        self._closed, self._open = closed_ic, open_ic
        self.root_dir = None
        self.bind("<<TreeviewOpen>>",  self._refresh)
        self.bind("<<TreeviewClose>>", self._refresh)
        self.change_root(root_dir)
        self.bind("<Double-1>", lambda e: self.event_generate("<<TreeActivate>>"))
        self.bind("<<TreeviewSelect>>", lambda _e: self.focus_set())
        self.bind("<<TreeviewOpen>>",
                          lambda e: self._populate(self.focus()))
    def _go_into(self, _e=None):
        sel = self.focus()
        if not sel:
            return
        tgt = self.item(sel, "values")[0]
        # if user double-clicked “..”, tgt is the parent path that was stored
        self.event_generate("<<FolderChosen>>", data=tgt)

    # public
    def change_root(self, path):
        self.root_dir = os.path.abspath(path)
        self.delete(*self.get_children())
        self._build()


    # internal
    def _build(self):
        cur = self.root_dir
        drive_root = os.path.splitdrive(cur)[0] + os.sep
        at_root = os.path.abspath(cur) == os.path.abspath(drive_root)

        if not at_root:
            self.insert("", "end", text="..", image=self._closed,
                        values=(os.path.dirname(cur),), tags=("dotdot",))

        if at_root:
            root_iid = self.insert("", "end", text=drive_root,
                                   image=self._open, open=True,
                                   values=(cur,))
            self.insert(root_iid, "end")
            self._populate(root_iid)
            self.selection_set(root_iid)
        else:
            for name in sorted(os.listdir(cur)):
                full = os.path.join(cur, name)
                if os.path.isdir(full):
                    iid = self.insert("", "end", text=name,
                                      image=self._closed, values=(full,))
                    self.insert(iid, "end")
                    if full == cur:
                        self._current_iid = iid


    def _refresh(self, _=None):
        for iid in self.get_children(""):
            self._set_icon_recursive(iid)

    def _set_icon_recursive(self, iid):
        open_now = self.item(iid, "open") and "no-open" not in self.item(iid,"tags")
        self.item(iid, image=self._open if open_now else self._closed)
        if open_now:
            self._populate(iid)
        for c in self.get_children(iid):
            self._set_icon_recursive(c)

    def _populate(self, iid):

        # populate once, replacing the dummy child
        kids = self.get_children(iid)
        if (len(kids) == 0) or (len(kids) == 1 and
                                 not self.item(kids[0], "values")):
            self.delete(kids[0])
            path = self.item(iid,"values")[0]
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    cid = self.insert(iid, "end", text=name,
                                      image=self._closed, values=(full,))
                    self.insert(cid, "end")          # ← keep dummy child


# ────────────────────────────────────────────────────────────────────────────────
# Thin caption bar mix-in
# ────────────────────────────────────────────────────────────────────────────────
class ThinTitleMixin:
    BAR_H      = 26
    BORDER_CLR = "#a0a0a0"
    TXT_FONT   = ("MS Sans Serif", 8, "bold")

    # ── helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _rgb_to_hex(r, g, b):          # 0-255 ints ➜ “#rrggbb”
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _is_dark(r, g, b):             # simple luminance check
        return (0.299 * r + 0.587 * g + 0.114 * b) < 128

    @classmethod
    def _get_caption_colours(cls):
        """
        Returns (active_bg, inactive_bg) as '#rrggbb' strings matched to the
        current Windows theme.  Falls back cleanly on very old systems.
        """
        if not sys.platform.startswith("win"):
            return "#008000", BG        # non-Windows → keep original green

        from ctypes import windll, wintypes, byref
        # --- try the DWM accent colour first (Vista+ with Aero) -------------
        try:
            color_dword   = wintypes.DWORD()
            is_opaque     = wintypes.BOOL()
            if windll.dwmapi.DwmGetColorizationColor(
                    byref(color_dword), byref(is_opaque)) == 0:
                c = color_dword.value   # ARGB
                b, g, r = (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF
                active = cls._rgb_to_hex(r, g, b)
                # inactive: GetSysColor still gives a good desaturated colour
                inac_rgb = windll.user32.GetSysColor(3)     # COLOR_INACTIVECAPTION
                b_i, g_i, r_i = (inac_rgb >> 16) & 0xFF, (inac_rgb >> 8) & 0xFF, inac_rgb & 0xFF
                inactive = cls._rgb_to_hex(r_i, g_i, b_i)
                return active, inactive
        except Exception:
            pass  # dwmapi.dll not present (XP/2k/98) or call failed

        # --- classic / Luna themes -----------------------------------------
        COLOR_ACTIVECAPTION   = 2
        COLOR_INACTIVECAPTION = 3
        act_rgb  = windll.user32.GetSysColor(COLOR_ACTIVECAPTION)
        inac_rgb = windll.user32.GetSysColor(COLOR_INACTIVECAPTION)
        b_a, g_a, r_a = (act_rgb  >> 16) & 0xFF, (act_rgb  >> 8) & 0xFF, act_rgb  & 0xFF
        b_i, g_i, r_i = (inac_rgb >> 16) & 0xFF, (inac_rgb >> 8) & 0xFF, inac_rgb & 0xFF
        return (cls._rgb_to_hex(r_a, g_a, b_a),
                cls._rgb_to_hex(r_i, g_i, b_i))

    # ── main installer ─────────────────────────────────────────────────────
    def _install_thin_title(self, ico="steam.ico"):
        # grab colours once up front
        self.ACTIVE_BG, _sys_inactive = self._get_caption_colours()
        self.INACTIVE_BG   = "#ffffff"                 # ← always white off-focus
        self.ACTIVE_FG     = "#ffffff" if self._is_dark(*bytes.fromhex(self.ACTIVE_BG[1:])) else "#000000"
        self.INACTIVE_FG   = "#000000"                 # black text on white

        self.overrideredirect(True)

        # 1-px outer border
        self._border = tk.Frame(self, bg=self.BORDER_CLR)
        self._border.pack(fill=tk.BOTH, expand=True)

        # caption bar
        self._cap = tk.Frame(self._border, bg=self.ACTIVE_BG, height=self.BAR_H)
        self._cap.pack(fill=tk.X, side=tk.TOP)

        # icon  --------------------------------------------------------------
        ico_path = resource_path(ico)
        try:
            self.iconbitmap(ico_path)
            icon = tk.PhotoImage(file=ico_path)
        except Exception:
            icon = tk.PhotoImage(width=16, height=16)
            icon.put(("black",), to=(0, 0, 15, 15))
        tk.Label(self._cap, image=icon, bg=self.ACTIVE_BG
                 ).pack(side=tk.LEFT, padx=2, pady=2)
        self._cap.icon = icon

        # title text ---------------------------------------------------------
        self._title_var = tk.StringVar(value=self.title())
        self._title_lbl = tk.Label(self._cap, textvariable=self._title_var,
                                   fg=self.ACTIVE_FG, bg=self.ACTIVE_BG,
                                   font=self.TXT_FONT)
        self._title_lbl.pack(side=tk.LEFT, pady=2)

        # close button (full-height) ----------------------------------------
        self._close = tk.Canvas(self._cap, width=40, height=self.BAR_H,
                                highlightthickness=0, bg=self.ACTIVE_BG,
                                bd=0)
        self._close.pack(side=tk.RIGHT, padx=0, fill=tk.Y)
        self._close_text_id = self._close.create_text(
            20, self.BAR_H // 2, text="×",
            font=("Marlett", 16), anchor="center",
            fill=self.ACTIVE_FG)

        # hover / leave ------------------------------------------------------
        def on_close_hover(is_hover):
            bg = "#d80000" if is_hover else self._cap["bg"]
            fg = "#ffffff" if is_hover else (
                 self.ACTIVE_FG if self._has_focus else self.INACTIVE_FG)
            self._close.configure(bg=bg)
            self._close.itemconfig(self._close_text_id, fill=fg)

        self._close.bind("<Enter>", lambda e: on_close_hover(True))
        self._close.bind("<Leave>", lambda e: on_close_hover(False))
        self._close.bind("<Button-1>", lambda e: self.destroy())
        self._close.config(cursor="hand2")

        # drag window --------------------------------------------------------
        def start(e):                      # remember where the drag began
            self._drag = (e.x_root, e.y_root)

        def move(e):                       # update window position
            if self._drag:
                dx = e.x_root - self._drag[0]
                dy = e.y_root - self._drag[1]
                self.geometry(f"+{self.winfo_x()+dx}+{self.winfo_y()+dy}")
                self._drag = (e.x_root, e.y_root)

        def bind_drag(widget):             # helper to bind the trio of events
            widget.bind("<ButtonPress-1>", start)
            widget.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_drag", None))
            widget.bind("<B1-Motion>", move)

        bind_drag(self._cap)               # already there before…
        bind_drag(self._title_lbl)         # ➊ NEW – click-and-hold on the caption text works now

        # focus colouring ----------------------------------------------------
        def set_active(active: bool):
            bg = self.ACTIVE_BG if active else self.INACTIVE_BG
            fg = self.ACTIVE_FG if active else self.INACTIVE_FG
            self._cap.configure(bg=bg)
            for child in self._cap.winfo_children():
                child.configure(bg=bg, fg=fg if isinstance(child, tk.Label) else None)
            self._close.configure(bg=bg)
            self._close.itemconfig(self._close_text_id, fill=fg)
            self._has_focus = active

        self.bind("<FocusIn>",  lambda e: set_active(True))
        self.bind("<FocusOut>", lambda e: set_active(False))
        self._has_focus = True   # initial state

        # keep Alt+F4 etc. ---------------------------------------------------
        if sys.platform.startswith("win"):
            import platform, ctypes
            hwnd       = self.winfo_id()
            GWL_STYLE  = -16
            WS_SYSMENU = 0x80000
            is_64      = platform.architecture()[0] == "64bit"
            GetWindowLong = (ctypes.windll.user32.GetWindowLongPtrW
                             if is_64 else ctypes.windll.user32.GetWindowLongW)
            SetWindowLong = (ctypes.windll.user32.SetWindowLongPtrW
                             if is_64 else ctypes.windll.user32.SetWindowLongW)
            style = GetWindowLong(hwnd, GWL_STYLE) | WS_SYSMENU
            SetWindowLong(hwnd, GWL_STYLE, style)

        # body / client area -------------------------------------------------
        self._body = tk.Frame(self._border, bg=BG,
                              width=CLIENT_W, height=CLIENT_H)
        self._body.pack(fill=tk.BOTH, expand=True)

        # keep caption text in sync -----------------------------------------
        orig_title = self.title
        def new_title(*args):
            if args:                                   # called as setter
                orig_title(args[0])
                self._title_var.set(args[0])
            else:                                      # called as getter
                return orig_title()

        self.title = new_title

# ────────────────────────────────────────────────────────────────
# Classic-looking folder browser built with Tk + ThinTitleMixin
# ────────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────────
# Classic-looking folder browser built with Tk + ThinTitleMixin
# ────────────────────────────────────────────────────────────────
class _FolderDialog(ThinTitleMixin, tk.Toplevel):
    WIDTH, HEIGHT = 382, 276
    def __init__(self, parent, initialdir):
        super().__init__(parent)
        self.title("Select Destination Directory")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self._install_thin_title(); self.resizable(False, False)
        self._border.config(width=self.WIDTH, height=self.HEIGHT)
        self._body.config(width=self.WIDTH,
                          height=self.HEIGHT - self.BAR_H)

        # centre on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()-self.WIDTH)//2
        y = parent.winfo_rooty() + (parent.winfo_height()-self.HEIGHT)//2
        self.geometry(f"+{x}+{y}")

        self.transient(parent); self.grab_set()

        # icons (now safe – window exists)
        drv_ic  = _p(self, _DRIVE_GIF)
        cl_ic   = _p(self, _FLD_CLOSED_GIF)
        op_ic   = _p(self, _FLD_OPEN_GIF)

        # current path variable
        self._cur = tk.StringVar(value=os.path.abspath(initialdir))

        tk.Entry(self._body, textvariable=self._cur, bd=1, relief=tk.SUNKEN).place(x=8, y=8, width=250)      # same width as folder tree

        # ---- widgets --------------------------------------------------
        # frame for tree + scrollbar -----------------------------------------
        tv_frame = tk.Frame(self._body, width=250, height=170)
        tv_frame.place(x=8, y=35)

        self._tree = FolderList(tv_frame, self._cur.get(),
                             cl_ic, op_ic, height=8)
        self._tree.pack(side="left", fill="both", expand=True)

        vbar = ttk.Scrollbar(tv_frame, command=self._tree.yview)
        vbar.pack(side="right", fill="y")
        def _y_sync(lo, hi):
            vbar.set(lo, hi)
            if lo == "0.0" and hi == "1.0":
                vbar.pack_forget()          # nothing to scroll
            else:
                vbar.pack(side="right", fill="y")
        self._tree.configure(yscrollcommand=_y_sync)
        def _on_tree_activate(_e):
            vals = self._tree.item(self._tree.focus(), "values")
            if vals:                # ignore clicks on rows that carry no path
                self._select_path(vals[0])
        self._tree.bind("<<TreeActivate>>", _on_tree_activate)

        self._dcombo = DriveComboBox(self._body, drv_ic,
                                     width=115, font=BODY_FONT)

        self._dcombo.place(x=8, y=215, width=250)                     # same width as tree

        self._dcombo.bind("<<DriveChanged>>",
                           lambda _e: self._select_path(self._dcombo.root_path))
        tk.Button(self._body, text="Select Folder", width=10, font=BODY_FONT,
               command=self._ok)\
         .place(x=268, y=6, width=100, height=23)   # align with entry
        tk.Button(self._body, text="Cancel", width=10, font=BODY_FONT,
               command=self.destroy)\
         .place(x=268, y=34, width=100, height=23)  # just below

        self.result=""; self.wait_window()

    def _ok(self):
        self.result = self._cur.get(); self.destroy()

    def _select_path(self, path):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return
        self._cur.set(path)               # ④ updates the entry automatically
        self._tree.change_root(path)      # rebuild tree
        self._dcombo.set(os.path.splitdrive(path)[0] + ":")   # ② keep combo

def classic_folder_dialog(title, initialdir, hwnd_owner):
    return _FolderDialog(tk._default_root, initialdir).result

# ────────────────────────────────────────────────────────────────────────────────
# helper – Valve logo substitute
# ────────────────────────────────────────────────────────────────────────────────
def valve_logo(parent):
    try:
        from PIL import Image, ImageTk
        img = Image.open("valve_logo.png").resize((128, 48), Image.NEAREST)
        ph  = ImageTk.PhotoImage(img)
        lbl = tk.Label(parent, image=ph, borderwidth=0); lbl.image = ph
    except Exception:
        lbl = tk.Label(parent, text="VALVE", fg="#f0b000", bg="black",
                       font=("Arial", 18, "bold"), width=12, height=2)
    return lbl
def _short_path(full, max_len=26):
    drive, tail = os.path.splitdrive(full)
    if len(full) <= max_len:
        return full
    parts = tail.split(os.sep)
    while parts and len(os.path.join(drive, '…', *parts)) > max_len:
        parts.pop(0)                       # drop middle folders
    return os.path.join(drive, '…', *parts)


# ────────────────────────────────────────────────────────────────────────────────
class SetupWizard(ThinTitleMixin, tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Welcome")
        self.geometry(f"{OUTER_W}x{OUTER_H}")
        self._install_thin_title()
        self.resizable(False, False)

        self.install_dir = tk.StringVar(value=os.getcwd())
        self.install_dir.trace_add("write", lambda *_: self._update_path_label())


        self.pages = {}
        self._build_pages()
        self._update_path_label()          # initial display
        self._show("welcome")

    def _update_path_label(self):
        self._path_lbl.config(text=_short_path(self.install_dir.get()))


    # ----- common widgets ------------------------------------------------------
    def _xp_btn(self, master, txt, cmd):
        return tk.Button(master, text=txt, command=cmd,
                         font=BODY_FONT, relief=tk.RAISED,
                         bd=2, highlightthickness=0)

    def _divider(self, parent):
        tk.Frame(parent, bg=LINE_CLR, height=2)\
          .place(x=DIVIDER_RECT[0], y=DIVIDER_RECT[1],
                 width=DIVIDER_RECT[2], height=DIVIDER_RECT[3])

    def _button_bar(self, page, back=None, nxt=None, show_back=True):
        self._divider(page)
        # Cancel
        tk.Button(page, text="Cancel", width=10, font=BODY_FONT, command=self.destroy)\
            .place(x=CANCEL_RECT[0], y=CANCEL_RECT[1],
                   width=CANCEL_RECT[2], height=CANCEL_RECT[3])
        # Next
        tk.Button(page, text="Next >", width=10, font=BODY_FONT, command=nxt)\
            .place(x=NEXT_RECT[0], y=NEXT_RECT[1],
                   width=NEXT_RECT[2], height=NEXT_RECT[3])
        # Back
        if show_back:
            tk.Button(page, text="< Back", width=10, font=BODY_FONT, command=back)\
                .place(x=BACK_RECT[0], y=BACK_RECT[1],
                       width=BACK_RECT[2], height=BACK_RECT[3])

    def _page(self):
        return tk.Frame(self._body, bg=BG, width=CLIENT_W, height=CLIENT_H)

    def _browse_dir(self):
        sel = classic_folder_dialog(
                title="Select Destination Directory",
                initialdir=self.install_dir.get(),
                hwnd_owner=self.winfo_id())
        if sel:
            self.install_dir.set(sel)
            self._update_path_label()



    # ----- build pages ---------------------------------------------------------
    def _build_pages(self):
        # ── Welcome page ────────────────────────────────────────────────────
        p1 = self._page(); self.pages["welcome"] = p1
        valve_logo(p1).place(x=LEFT_PAD+2, y=34)

        # welcome headline
        tk.Label(p1, text=("Welcome to the Steam Setup program. "
                           "This program will install Steam on your computer."),
                 anchor="nw", justify="left", wraplength=WELCOME_RECT[2],
                 font=BODY_FONT, bg=BG)\
            .place(x=WELCOME_RECT[0], y=WELCOME_RECT[1],
                   width=WELCOME_RECT[2], height=WELCOME_RECT[3])

        # body block
        tk.Label(p1, text=("It is strongly recommended that you exit all Windows "
                           "programs before running this Setup Program.\n\n"
                           "Click Cancel to quit Setup and close any programs you "
                           "have running.  Click Next to continue with the Setup "
                           "program .\n\n"
                           "WARNING: This program is protected by copyright law "
                           "and international treaties.\n\n"
                           "Unauthorized reproduction or distribution of this "
                           "program, or any portion of it, may result in severe "
                           "civil and criminal penalties, and will be prosecuted "
                           "to the maximum extent possible under law."),
                 anchor="nw", justify="left", wraplength=BODY_RECT[2],
                 font=BODY_FONT, bg=BG)\
            .place(x=BODY_RECT[0], y=BODY_RECT[1],
                   width=BODY_RECT[2], height=BODY_RECT[3])

        self._button_bar(p1, nxt=lambda: self._show("dest"), show_back=False)

        # ── Destination page ───────────────────────────────────────────────
        p2 = self._page(); self.pages["dest"] = p2
        valve_logo(p2).place(x=LEFT_PAD+2, y=34)

        body = ("Setup will install Steam in the following folder.\n\n"
                "To install into a different folder, click Browse, and select \n"
                "another folder.\n\n"
                "You can choose not to install Steam by clicking Cancel to exit \n"
                "Setup.")
        tk.Label(p2, text=body, justify="left", bg=BG,
                 font=BODY_FONT).place(x=157, y=16)

        grp = tk.LabelFrame(p2, text="Destination Folder", font=BODY_FONT,
                            bg=BG, fg="black", bd=2.2, relief=tk.GROOVE)
        grp.place(x=157, y=218, width=298, height=46)
        self._path_lbl = tk.Label(grp,  # save a reference ➜ self._path_lbl
                                  justify="left", bg=BG,
                                  anchor="w", font=BODY_FONT)
        self._path_lbl.place(x=3, y=4, width=175)   # width for truncation

        tk.Button(grp, text="Browse...", width=10, font=BODY_FONT,
                  command=self._browse_dir).place(x=216.5, y=0)

        self._button_bar(p2, back=lambda: self._show("welcome"),
                         nxt=lambda: self._show("start"))

        # ── Start page ─────────────────────────────────────────────────────
        p3 = self._page(); self.pages["start"] = p3
        valve_logo(p3).place(x=LEFT_PAD+2, y=34)
        tk.Label(p3, text=("You are now ready to install Steam.\n\n"
                           "Press the Next button to begin the installation or "
                           "the Back button to re-enter the installation "
                           "information."),
                 justify="left", bg=BG, font=BODY_FONT).place(x=157, y=34)
        self._button_bar(p3, back=lambda: self._show("dest"),
                         nxt=self._begin_install)

        # ── Installing page (unchanged layout except divider) ──────────────
        p4 = self._page(); self.pages["install"] = p4
        valve_logo(p4).place(x=LEFT_PAD+2, y=20)
        for i, sym in enumerate(("🕹", "💾", "📂")):
            tk.Label(p4, text=sym, bg=BG, font=("Arial", 15)
                     ).place(x=157 + i*40, y=25)

        cur_box = tk.LabelFrame(p4, text="Current File", font=BODY_FONT,
                                bg=BG, fg="black", bd=1, relief=tk.GROOVE)
        cur_box.place(x=157, y=65, width=310, height=88)
        self.cur_lbl = tk.Label(cur_box, text="Copying file:\n", anchor="w",
                                justify="left", bg=BG, font=BODY_FONT)
        self.cur_lbl.place(x=6, y=0)
        self.cur_prog = tk.Canvas(cur_box, width=290, height=18,
                                  bd=1, relief=tk.SUNKEN, bg="white")
        self.cur_prog.place(x=6, y=45)

        all_box = tk.LabelFrame(p4, text="All Files", font=BODY_FONT,
                                bg=BG, fg="black", bd=1, relief=tk.GROOVE)
        all_box.place(x=157, y=160, width=310, height=88)
        tk.Label(all_box, text="Time Remaining 0 minutes 0 seconds",
                 anchor="w", bg=BG, font=BODY_FONT).place(x=6, y=0)
        self.all_prog = tk.Canvas(all_box, width=290, height=18,
                                  bd=1, relief=tk.SUNKEN, bg="white")
        self.all_prog.place(x=6, y=45)

        # divider + Cancel
        self._divider(p4)
        tk.Button(p4, text="Cancel", width=10, font=BODY_FONT, command=self.destroy)\
            .place(x=CANCEL_RECT[0], y=CANCEL_RECT[1],
                   width=CANCEL_RECT[2], height=CANCEL_RECT[3])


    # ----- nav helpers ---------------------------------------------------------
    def _show(self, key):
        for f in self.pages.values():
            f.pack_forget()
        self.pages[key].pack(fill=tk.BOTH, expand=True)
        self.title({"welcome": "Welcome",
                    "dest":    "Choose Destination Location",
                    "start":   "Start Installation",
                    "install": "Installing"}[key])



    def _progress(self, cvs, frac):
        cvs.delete("bar")
        w = cvs.winfo_width()
        cvs.create_rectangle(0, 0, w*frac, cvs.winfo_height(),
                             fill="#0b51ff", width=0, tags="bar")

    def _begin_install(self):
        self._show("install")
        def run():
            src = resource_path("steam.exe")
            dest_dir = self.install_dir.get()
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, "steam.exe")

            try:
                total_size = os.path.getsize(src)
            except OSError:
                messagebox.showerror("Error", "steam.exe not found")
                self.destroy()
                return

            copied = 0
            chunk = 4096
            self.cur_lbl.config(text=f"Copying file:\n{dest}")
            with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
                while True:
                    data = fsrc.read(chunk)
                    if not data:
                        break
                    fdst.write(data)
                    copied += len(data)
                    frac = copied / total_size
                    self._progress(self.cur_prog, frac)
                    self._progress(self.all_prog, frac)
                    time.sleep(0.01)

            messagebox.showinfo("Install complete",
                                "Steam installation finished.")
            self.destroy()
        threading.Thread(target=run, daemon=True).start()

# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SetupWizard().mainloop()
