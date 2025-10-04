# src/tabs/tab_favorability.py

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageTk
import os
from .tab_base import TabBase

class DefaultHeartSelector(tk.Toplevel):
    def __init__(self, parent, default_hearts_dir):
        super().__init__(parent)
        self.app = parent.app
        self.title("デフォルトのハート画像を選択")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        win_width = int(screen_width * 0.3)
        win_height = int(screen_height * 0.4)
        self.geometry(f"{win_width}x{win_height}")
        self.transient(parent); self.grab_set()

        self.selected_filename = None
        self.image_references = []

        main_frame = ttk.Frame(self, padding=self.app.padding_normal)
        main_frame.pack(expand=True, fill="both")
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        try:
            image_files = sorted([f for f in os.listdir(default_hearts_dir) if f.lower().endswith('.png')])
            thumbnail_size = int(self.app.base_font_size * 5)
            for i, filename in enumerate(image_files):
                filepath = os.path.join(default_hearts_dir, filename)
                img = Image.open(filepath)
                img.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.image_references.append(photo_img)
                btn = ttk.Button(scrollable_frame, image=photo_img, text=filename, compound="top", command=lambda f=filename: self.select_and_close(f))
                btn.grid(row=i // 5, column=i % 5, padx=self.app.padding_small, pady=self.app.padding_small)
        except Exception as e:
            ttk.Label(scrollable_frame, text=f"画像の読み込みに失敗しました:\n{e}", font=self.app.font_normal).pack()
        self.wait_window()

    def select_and_close(self, filename):
        self.selected_filename = filename; self.destroy()

class StageDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_threshold="", initial_name=""):
        self.app = parent.app
        self.threshold_var = tk.StringVar(parent, value=initial_threshold)
        self.name_var = tk.StringVar(parent, value=initial_name)
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="好感度の閾値 (整数):", font=self.app.font_normal).grid(row=0, sticky="w")
        self.threshold_entry = ttk.Entry(master, textvariable=self.threshold_var, font=self.app.font_normal)
        self.threshold_entry.grid(row=1, sticky="ew", pady=(0, self.app.padding_normal))
        ttk.Label(master, text="ユーザーへの認識名:", font=self.app.font_normal).grid(row=2, sticky="w")
        self.name_entry = ttk.Entry(master, textvariable=self.name_var, font=self.app.font_normal)
        self.name_entry.grid(row=3, sticky="ew")
        return self.threshold_entry

    def apply(self):
        try: self.result = (int(self.threshold_var.get()), self.name_var.get())
        except ValueError: self.result = None

    def validate(self):
        if not self.name_var.get().strip():
            messagebox.showwarning("入力エラー", "認識名を入力してください。", parent=self); return 0
        try: int(self.threshold_var.get())
        except ValueError:
            messagebox.showwarning("入力エラー", "閾値には整数を入力してください。", parent=self); return 0
        return 1

class TabFavorability(TabBase):
    def create_widgets(self):
        parent = self.scrollable_frame
        parent.columnconfigure(0, weight=1); parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.configure("Tab.TButton", font=self.app.font_normal, padding=self.app.padding_small)
        style.configure("Fav.Treeview.Heading", font=self.app.font_normal)
        style.configure("Fav.Treeview", font=self.app.font_normal, rowheight=int(self.app.base_font_size * 1.8))
        style.configure("Heart.Treeview", font=self.app.font_normal, rowheight=int(self.app.base_font_size * 3.5))

        stages_frame = ttk.LabelFrame(parent, text="好感度の段階設定", padding=self.app.padding_normal)
        stages_frame.grid(row=0, column=0, sticky="nsew", padx=(0, self.app.padding_small))
        stages_frame.columnconfigure(0, weight=1); stages_frame.rowconfigure(1, weight=1)

        stages_buttons = ttk.Frame(stages_frame)
        stages_buttons.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        btn_padx = self.app.padding_small / 2
        ttk.Button(stages_buttons, text="段階を追加", command=self.add_stage, style="Tab.TButton").pack(side="left", padx=(0, btn_padx))
        ttk.Button(stages_buttons, text="編集", command=self.edit_stage, style="Tab.TButton").pack(side="left", padx=btn_padx)
        ttk.Button(stages_buttons, text="削除", command=self.delete_stage, style="Tab.TButton").pack(side="left", padx=btn_padx)

        self.stages_tree = ttk.Treeview(stages_frame, columns=("threshold", "name"), show="headings", style="Fav.Treeview")
        self.stages_tree.heading("threshold", text="閾値"); self.stages_tree.heading("name", text="ユーザーへの認識名")
        self.stages_tree.column("threshold", width=int(self.app.base_font_size * 8), anchor="center")
        self.stages_tree.grid(row=1, column=0, sticky="nsew")

        hearts_frame = ttk.LabelFrame(parent, text="好感度ハート画像設定", padding=self.app.padding_normal)
        hearts_frame.grid(row=0, column=1, sticky="nsew", padx=(self.app.padding_small, 0))
        hearts_frame.columnconfigure(0, weight=1); hearts_frame.rowconfigure(1, weight=1)

        hearts_buttons = ttk.Frame(hearts_frame)
        hearts_buttons.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        ttk.Button(hearts_buttons, text="設定を追加", command=self.add_heart, style="Tab.TButton").pack(side="left", padx=(0, btn_padx))
        ttk.Button(hearts_buttons, text="デフォルト画像から選択...", command=self.select_default_heart, style="Tab.TButton").pack(side="left", padx=btn_padx)
        ttk.Button(hearts_buttons, text="削除", command=self.delete_heart, style="Tab.TButton").pack(side="left", padx=btn_padx)

        self.hearts_tree = ttk.Treeview(hearts_frame, columns=("threshold", "filename"), show="tree headings", style="Heart.Treeview")
        self.hearts_tree.heading("#0", text="プレビュー"); self.hearts_tree.heading("threshold", text="閾値"); self.hearts_tree.heading("filename", text="画像ファイル名")
        self.hearts_tree.column("#0", width=int(self.app.base_font_size * 5), stretch=tk.NO, anchor="center")
        self.hearts_tree.column("threshold", width=int(self.app.base_font_size * 7), anchor="center")
        self.hearts_tree.grid(row=1, column=0, sticky="nsew")
        self.hearts_tree.drop_target_register(DND_FILES); self.hearts_tree.dnd_bind("<<Drop>>", self.on_heart_drop)
        self.hearts_tree.bind("<<TreeviewSelect>>", self.on_heart_select)

        heart_ui_frame = ttk.LabelFrame(hearts_frame, text="ハートUI設定 (全てのハートで共通)", padding=self.app.padding_normal)
        heart_ui_frame.grid(row=2, column=0, sticky="ew", pady=(self.app.padding_normal, 0))
        heart_ui_frame.columnconfigure(1, weight=1)

        self.heart_transparency_mode_var = tk.StringVar(value="color_key")
        
        mode_frame = ttk.Frame(heart_ui_frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, self.app.padding_small))
        ttk.Label(mode_frame, text="透過方式:", font=self.app.font_normal).pack(side="left")
        ttk.Radiobutton(mode_frame, text="透明度維持", variable=self.heart_transparency_mode_var, value="alpha", command=self._toggle_heart_color_settings).pack(side="left", padx=self.app.padding_small)
        ttk.Radiobutton(mode_frame, text="色指定", variable=self.heart_transparency_mode_var, value="color_key", command=self._toggle_heart_color_settings).pack(side="left")

        self.heart_color_settings_frame = ttk.Frame(heart_ui_frame)
        self.heart_color_settings_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        ui_pady = self.app.padding_small
        ttk.Label(self.heart_color_settings_frame, text="透過色:", font=self.app.font_normal).grid(row=0, column=0, sticky="w")
        trans_color_frame = ttk.Frame(self.heart_color_settings_frame)
        trans_color_frame.grid(row=0, column=1, sticky="w")
        trans_color_preview = tk.Label(trans_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
        trans_color_preview.pack(side="left", padx=(0, ui_pady))
        trans_color_btn = ttk.Button(trans_color_frame, text="選択", command=lambda: self.editor.pick_color(trans_color_preview), style="Tab.TButton")
        trans_color_btn.pack(side="left")
        trans_color_eyedropper = ttk.Button(trans_color_frame, text="取得", command=lambda: self.editor.enter_eyedropper_mode(trans_color_preview), style="Tab.TButton")
        trans_color_eyedropper.pack(side="left", padx=ui_pady)
        
        ttk.Label(self.heart_color_settings_frame, text="縁色:", font=self.app.font_normal).grid(row=1, column=0, sticky="w", pady=(ui_pady,0))
        edge_color_frame = ttk.Frame(self.heart_color_settings_frame)
        edge_color_frame.grid(row=1, column=1, sticky="w", pady=(ui_pady,0))
        edge_color_preview = tk.Label(edge_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
        edge_color_preview.pack(side="left", padx=(0, ui_pady))
        edge_color_btn = ttk.Button(edge_color_frame, text="選択", command=lambda: self.editor.pick_color(edge_color_preview), style="Tab.TButton")
        edge_color_btn.pack(side="left")
        edge_color_eyedropper = ttk.Button(edge_color_frame, text="取得", command=lambda: self.editor.enter_eyedropper_mode(edge_color_preview), style="Tab.TButton")
        edge_color_eyedropper.pack(side="left", padx=ui_pady)

        self.widgets = {
            'stages_tree': self.stages_tree, 'hearts_tree': self.hearts_tree,
            'HEART_TRANSPARENCY_MODE': self.heart_transparency_mode_var,
            'HEART_TRANSPARENT_COLOR': trans_color_preview, 'HEART_EDGE_COLOR': edge_color_preview,
            'heart_trans_color_btn': trans_color_btn, 'heart_trans_color_eyedropper': trans_color_eyedropper,
            'heart_edge_color_btn': edge_color_btn, 'heart_edge_color_eyedropper': edge_color_eyedropper,
        }
        self.heart_images = {}

    def _toggle_heart_color_settings(self):
        """ハートUIの透過モードに応じて色指定UIの有効/無効を切り替える"""
        state = "disabled" if self.heart_transparency_mode_var.get() == "alpha" else "normal"
        
        for key in ['heart_trans_color_btn', 'heart_trans_color_eyedropper', 'heart_edge_color_btn', 'heart_edge_color_eyedropper']:
            if key in self.widgets:
                self.widgets[key].config(state=state)

    def load_data(self):
        for item in self.stages_tree.get_children(): self.stages_tree.delete(item)
        for stage in self.character_data.get_favorability_stages(): self.stages_tree.insert("", "end", values=(stage['threshold'], stage['name']))
        self.load_hearts_data()
        
        colors = self.character_data.get_heart_ui_colors()
        self.heart_transparency_mode_var.set(colors['TRANSPARENCY_MODE'])
        self.widgets['HEART_TRANSPARENT_COLOR'].config(background=colors['TRANSPARENT_COLOR'] or "#FF00FF")
        self.widgets['HEART_EDGE_COLOR'].config(background=colors['EDGE_COLOR'] or "#000000")
        self._toggle_heart_color_settings()

    def load_hearts_data(self):
        for item in self.hearts_tree.get_children(): self.hearts_tree.delete(item)
        self.heart_images.clear()
        for heart in self.character_data.get_favorability_hearts():
            item_id = self.hearts_tree.insert("", "end", text="", values=(heart['threshold'], heart['filename']))
            self._load_heart_preview(item_id, heart['filename'])

    def _load_heart_preview(self, item_id, filename):
        char_hearts_dir = os.path.join(self.character_data.base_path, "hearts")
        default_hearts_dir = os.path.join(self.app.base_path, "images", "hearts")
        path_to_load = None
        if os.path.exists(os.path.join(char_hearts_dir, filename)): path_to_load = os.path.join(char_hearts_dir, filename)
        elif os.path.exists(os.path.join(default_hearts_dir, filename)): path_to_load = os.path.join(default_hearts_dir, filename)
        if path_to_load:
            try:
                img = Image.open(path_to_load)
                thumbnail_size = int(self.app.base_font_size * 3)
                img.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.heart_images[item_id] = photo_img
                self.hearts_tree.item(item_id, image=photo_img)
            except Exception as e: print(f"ハートプレビュー読込エラー: {e}")

    def collect_data(self):
        stages, hearts = [], []
        for item_id in self.stages_tree.get_children():
            threshold, name = self.stages_tree.item(item_id, 'values')
            stages.append({'threshold': int(threshold), 'name': name})
        self.character_data.update_favorability_stages(stages)
        for item_id in self.hearts_tree.get_children():
            threshold, filename = self.hearts_tree.item(item_id, 'values')
            hearts.append({'threshold': int(threshold), 'filename': filename})
        self.character_data.update_favorability_hearts(hearts)

        mode = self.widgets['HEART_TRANSPARENCY_MODE'].get()
        trans_color = self.widgets['HEART_TRANSPARENT_COLOR'].cget("background")
        edge_color = self.widgets['HEART_EDGE_COLOR'].cget("background")
        self.character_data.update_heart_ui_colors(mode, trans_color, edge_color)

    def add_stage(self):
        dialog = StageDialog(self, "段階の追加")
        if dialog.result:
            threshold, name_raw = dialog.result
            # サニタイズ処理
            name = self.editor.sanitize_string(name_raw, max_length=70)
            self.stages_tree.insert("", "end", values=(threshold, name))
            self._sort_stages()

    def edit_stage(self):
        selected_item = self.stages_tree.focus()
        if not selected_item: messagebox.showwarning("警告", "編集する段階を選択してください。", parent=self); return
        old_threshold, old_name = self.stages_tree.item(selected_item, 'values')
        dialog = StageDialog(self, "段階の編集", initial_threshold=old_threshold, initial_name=old_name)
        if dialog.result:
            new_threshold, new_name_raw = dialog.result
            # サニタイズ処理を追加
            name = self.editor.sanitize_string(new_name_raw, max_length=70)
            self.stages_tree.item(selected_item, values=(new_threshold, name))
            self._sort_stages()

    def delete_stage(self):
        selected_item = self.stages_tree.focus()
        if not selected_item: messagebox.showwarning("警告", "削除する段階を選択してください。", parent=self); return
        self.stages_tree.delete(selected_item)
        
    def _sort_stages(self):
        items = [(self.stages_tree.set(k, "threshold"), k) for k in self.stages_tree.get_children("")]
        items.sort(key=lambda x: int(x[0]), reverse=True)
        for index, (val, k) in enumerate(items): self.stages_tree.move(k, "", index)

    def add_heart(self):
        threshold = simpledialog.askinteger("閾値の入力", "ハート画像を表示する好感度の閾値を入力してください:", parent=self)
        if threshold is not None: self.hearts_tree.insert("", "end", values=(threshold, "(画像をD&Dしてください)"))

    def select_default_heart(self):
        selected_item = self.hearts_tree.focus()
        if not selected_item: messagebox.showwarning("警告", "画像を割り当てる閾値を選択してください。", parent=self); return
        default_hearts_dir = os.path.join(self.app.base_path, "images", "hearts")
        if not os.path.isdir(default_hearts_dir): messagebox.showerror("エラー", f"デフォルトのハート画像フォルダが見つかりません:\n{os.path.abspath(default_hearts_dir)}", parent=self); return
        dialog = DefaultHeartSelector(self, default_hearts_dir)
        if dialog.selected_filename:
            values = list(self.hearts_tree.item(selected_item, 'values'))
            values[1] = dialog.selected_filename
            self.hearts_tree.item(selected_item, values=values)
            self._load_heart_preview(selected_item, dialog.selected_filename)

    def delete_heart(self):
        selected_item = self.hearts_tree.focus()
        if not selected_item: messagebox.showwarning("警告", "削除する設定を選択してください。", parent=self); return
        self.hearts_tree.delete(selected_item)

    def on_heart_drop(self, event):
        y_in_widget = event.y_root - self.hearts_tree.winfo_rooty()
        item_id = self.hearts_tree.identify_row(y_in_widget)
        if not item_id: return
        filepath = event.data.strip('{}')
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            messagebox.showwarning("ファイル形式エラー", "画像ファイルを選択してください。", parent=self); return
        try:
            filename = os.path.basename(filepath)
            save_dir = os.path.join(self.character_data.base_path, "hearts")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            Image.open(filepath).save(save_path, "PNG")
            values = list(self.hearts_tree.item(item_id, 'values'))
            values[1] = filename
            self.hearts_tree.item(item_id, values=values)
            self._load_heart_preview(item_id, filename)
        except Exception as e: messagebox.showerror("エラー", f"画像のコピーに失敗しました:\n{e}", parent=self)

    def on_heart_select(self, event=None):
        selected_item = self.hearts_tree.focus()
        
        # 何も選択されていない場合（タブ切り替え直後など）は、
        # キャラクターの基準画像にフォールバックする
        if not selected_item:
            self.editor.set_preview_to_character_base(self.editor.current_costume_id.get())
            return
            
        filename = self.hearts_tree.item(selected_item, "values")[1]
        filepath = self._find_heart_image_path(filename)
        
        if filepath:
            self.editor.set_preview_to_heart_image(filename, filepath)
        else:
            # ファイルが見つからない場合も基準画像にフォールバック
            self.editor.set_preview_to_character_base(self.editor.current_costume_id.get())

    def _find_heart_image_path(self, filename):
        char_path = os.path.join(self.character_data.base_path, "hearts", filename)
        default_path = os.path.join("images/hearts", filename)
        if os.path.exists(char_path): return char_path
        if os.path.exists(default_path): return default_path
        return None
