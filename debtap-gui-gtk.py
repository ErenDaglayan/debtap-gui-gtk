#!/usr/bin/env python3

import gi
import subprocess
import os
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

# ==========================================
# DİL SÖZLÜĞÜ (GÜNCELLEME EKLENDİ)
# ==========================================
LANGS = {
    "tr": {
        "title": "Debtap Arayüzü",
        "desc": ".deb dosyasını seçin veya buraya sürükleyin",
        "btn_select": "Dosya Seç",
        "update_db": "Veritabanını Güncelle",
        "loading": "İşlem yapılıyor...\nLütfen bekleyin.",
        "success": "Başarılı! İşlem tamamlandı.",
        "err_deb": "Hata: Sadece .deb dosyaları!",
        "err_cmd": "Hata: Debtap bulunamadı.",
        "dialog_title": "Bilgi"
    },
    "en": {
        "title": "Debtap GUI",
        "desc": "Select a .deb file or drag and drop",
        "btn_select": "Select File",
        "update_db": "Update Database",
        "loading": "Processing...\nPlease wait.",
        "success": "Success! Task completed.",
        "err_deb": "Error: Only .deb files!",
        "err_cmd": "Error: Debtap not found.",
        "dialog_title": "Information"
    }
}

class DebtapWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_lang = "tr"

        self.set_title(LANGS[self.current_lang]["title"])
        self.set_default_size(500, 400)

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        view = Adw.ToolbarView()
        self.toast_overlay.set_child(view)

        # --- HEADER BAR ---
        header = Adw.HeaderBar()

        # 1. Veritabanı Güncelleme Butonu (Sol)
        self.btn_update = Gtk.Button()
        self.btn_update.set_icon_name("view-refresh-symbolic")
        self.btn_update.set_tooltip_text("Veritabanını Güncelle / Update Database")
        self.btn_update.connect("clicked", self.on_update_db_clicked)
        header.pack_start(self.btn_update)

        # 2. Dil Seçici (Sağ)
        self.lang_model = Gtk.StringList.new(["TR", "EN"])
        self.lang_dropdown = Gtk.DropDown.new(model=self.lang_model, expression=None)
        self.lang_dropdown.set_valign(Gtk.Align.CENTER)
        self.lang_dropdown.connect("notify::selected", self.on_lang_changed)
        header.pack_end(self.lang_dropdown)

        view.add_top_bar(header)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        view.set_content(self.stack)

        # --- SAYFALAR ---
        self.page_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.page_main.set_valign(Gtk.Align.CENTER)

        self.status_page = Adw.StatusPage()
        self.status_page.set_icon_name("system-software-install")
        self.page_main.append(self.status_page)

        self.btn_select = Gtk.Button()
        self.btn_select.add_css_class("suggested-action")
        self.btn_select.add_css_class("pill")
        self.btn_select.set_halign(Gtk.Align.CENTER)
        self.btn_select.connect("clicked", self.on_open_file_dialog)
        self.page_main.append(self.btn_select)

        # Sürükle Bırak
        drop_target = Gtk.DropTarget.new(type=Gio.File.__gtype__, actions=Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_drop)
        self.page_main.add_controller(drop_target)

        self.stack.add_named(self.page_main, "main")

        # Yükleniyor Sayfası
        self.page_loading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.page_loading.set_valign(Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(64, 64)
        self.page_loading.append(self.spinner)
        self.loading_label = Gtk.Label()
        self.page_loading.append(self.loading_label)
        self.stack.add_named(self.page_loading, "loading")

        self.update_ui_text()

    def update_ui_text(self):
        l = LANGS[self.current_lang]
        self.set_title(l["title"])
        self.status_page.set_title(l["title"])
        self.status_page.set_description(l["desc"])
        self.btn_select.set_label(l["btn_select"])
        self.loading_label.set_text(l["loading"])

    def on_lang_changed(self, dropdown, pspec):
        self.current_lang = "tr" if dropdown.get_selected() == 0 else "en"
        self.update_ui_text()

    # --- VERİTABANI GÜNCELLEME MANTIĞI ---
    def on_update_db_clicked(self, button):
        # Güncelleme şifre gerektirdiği için bir terminalde açmak en güvenlisi
        # Böylece kullanıcı şifresini girip süreci görebilir
        terminals = ["kgx", "gnome-terminal", "konsole", "kitty", "alacritty", "xterm" , "xfce4-terminal" , "mate-terminal" , "lxterminal" ,"termite" , "urxvt"]
        found = False
        for t in terminals:
            if subprocess.run(["which", t], capture_output=True).returncode == 0:
                if t in ["kgx", "gnome-terminal"]:
                    subprocess.Popen([t, "--", "sudo", "debtap", "-u"])
                else:
                    subprocess.Popen([t, "-e", "sudo", "debtap", "-u"])
                found = True
                break

        if not found:
            self.show_error_dialog("Terminal bulunamadı! Lütfen manuel: sudo debtap -u")
        else:
            self.show_toast(LANGS[self.current_lang]["update_db"] + "...")

    def on_file_drop(self, drop_target, value, x, y):
        path = value.get_path()
        if path.lower().endswith(".deb"): self.start_conversion(path)
        else: self.show_toast(LANGS[self.current_lang]["err_deb"])
        return True

    def on_open_file_dialog(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file: self.start_conversion(file.get_path())
        except: pass

    def start_conversion(self, path):
        self.spinner.start()
        self.stack.set_visible_child_name("loading")
        threading.Thread(target=self.run_debtap_thread, args=(path,), daemon=True).start()

    def run_debtap_thread(self, path):
        try:
            work_dir = os.path.dirname(path)
            # -q sessiz mod, y ise tüm sorulara evet der
            process = subprocess.run(["debtap", "-q", path], cwd=work_dir, capture_output=True, text=True, input="y\n")
            success = (process.returncode == 0)
            msg = LANGS[self.current_lang]["success"] if success else process.stderr
            GLib.idle_add(self.on_conversion_done, success, msg)
        except:
            GLib.idle_add(self.on_conversion_done, False, LANGS[self.current_lang]["err_cmd"])

    def on_conversion_done(self, success, message):
        self.spinner.stop()
        self.stack.set_visible_child_name("main")
        if success: self.show_toast(message)
        else: self.show_error_dialog(message)

    def show_toast(self, text):
        self.toast_overlay.add_toast(Adw.Toast.new(text))

    def show_error_dialog(self, text):
        Adw.MessageDialog.new(self, LANGS[self.current_lang]["dialog_title"], text[:500]).add_response("ok", "OK").present()

class DebtapApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.eren.debtapgui")
    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        DebtapWindow(application=self).present()

app = DebtapApp()
app.run(None)
