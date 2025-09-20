# src/tabs/tab_expressions.py

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageTk
import os
import ast
from .tab_base import TabBase

class ExpressionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_id="", initial_name="", id_editable=True):
        self.app = parent.app
        self.id_var = tk.StringVar(parent, value=initial_id)
        self.name_var = tk.StringVar(parent, value=initial_name)
        self.id_editable = id_editable
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="英語ID (半角英数字):", font=self.app.font_normal).grid(row=0, sticky="w")
        self.id_entry = ttk.Entry(master, textvariable=self.id_var, font=self.app.font_normal)
        self.id_entry.grid(row=1, sticky="ew", pady=(0, self.app.padding_normal))
        if not self.id_editable: self.id_entry.config(state="readonly")
        ttk.Label(master, text="日本語名:", font=self.app.font_normal).grid(row=2, sticky="w")
        self.name_entry = ttk.Entry(master, textvariable=self.name_var, font=self.app.font_normal)
        self.name_entry.grid(row=3, sticky="ew")
        return self.id_entry

    def apply(self):
        self.result = (self.id_var.get(), self.name_var.get())

    def validate(self):
        expr_id, expr_name = self.id_var.get(), self.name_var.get()
        if not expr_id or not expr_name:
            messagebox.showwarning("入力エラー", "IDと名前の両方を入力してください。", parent=self); return 0
        if not expr_id.isalnum():
            messagebox.showwarning("入力エラー", "IDは半角英数字で入力してください。", parent=self); return 0
        return 1

class EmotionVoiceSettingDialog(simpledialog.Dialog):
    def __init__(self, parent, title, character_data, expression_id, editor_instance):
        self.editor = editor_instance
        self.app = editor_instance.app
        self.character_data = character_data
        self.expression_id = expression_id
        self.param_widgets = {}
        self.result_params = {}
        self.params_info = {
            "speedScale": {"name": "話速", "abs_min": 0.5, "abs_max": 2.0, "default": 1.0},
            "pitchScale": {"name": "高さ", "abs_min": -0.15, "abs_max": 0.15, "default": 0.0},
            "intonationScale": {"name": "抑揚", "abs_min": 0.0, "abs_max": 2.0, "default": 1.0},
            "volumeScale": {"name": "音量", "abs_min": 0.0, "abs_max": 2.0, "default": 1.0}
        }
        self.normal_params = self.character_data.get_voice_param('normal')
        self.emotion_params = self.character_data.get_voice_param(self.expression_id, fallback=self.normal_params)
        super().__init__(parent, title=f"音声設定: {expression_id}")

    def body(self, master):
        style = ttk.Style(self)
        style.configure("Dialog.TLabel", font=self.app.font_normal)
        style.configure("Dialog.TButton", font=self.app.font_normal)

        top_frame = ttk.Frame(master)
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, self.app.padding_normal))
        info_label = ttk.Label(top_frame, text="「基本の声質(normal)」からの差分を設定します。", style="Dialog.TLabel")
        info_label.pack(side="left", anchor="w")
        reset_button = ttk.Button(top_frame, text="オフセットをリセット", command=self.reset_offsets_to_zero, style="Dialog.TButton")
        reset_button.pack(side="right", anchor="e")
        top_frame.columnconfigure(0, weight=1)

        row_count = 1
        for key, info in self.params_info.items():
            base_value = self.normal_params.get(key, info['default'])
            min_offset, max_offset = round(info['abs_min'] - base_value, 2), round(info['abs_max'] - base_value, 2)
            current_emotion_value = self.emotion_params.get(key, base_value)
            current_offset = max(min_offset, min(max_offset, round(current_emotion_value - base_value, 2)))
            
            ttk.Label(master, text=info["name"], style="Dialog.TLabel").grid(row=row_count, column=0, sticky="w", padx=(0, self.app.padding_normal))
            entry_var = tk.StringVar(value=f"{current_offset:+.2f}")
            def on_scale_change(value, e_var=entry_var): e_var.set(f"{float(value):+.2f}")
            scale = ttk.Scale(master, from_=min_offset, to=max_offset, orient="horizontal", command=on_scale_change)
            scale.set(current_offset)
            scale.grid(row=row_count, column=1, sticky="ew")
            def make_entry_callback(s, e_var, min_o, max_o):
                def on_entry_change(*args):
                    try:
                        val = float(e_var.get())
                        clamped_val = max(min_o, min(max_o, val))
                        s.set(clamped_val)
                        if val != clamped_val: e_var.set(f"{clamped_val:+.2f}")
                    except (ValueError, tk.TclError): pass
                return on_entry_change
            entry_var.trace_add("write", make_entry_callback(scale, entry_var, min_offset, max_offset))
            value_entry = ttk.Entry(master, textvariable=entry_var, width=7, font=self.app.font_normal)
            value_entry.grid(row=row_count, column=2, padx=(self.app.padding_small, 0))
            self.param_widgets[key] = entry_var
            row_count += 1

        test_frame = ttk.Frame(master)
        test_frame.grid(row=row_count + 2, column=0, columnspan=3, sticky="ew", pady=self.app.padding_large)
        test_frame.columnconfigure(0, weight=1)
        self.test_entry = ttk.Entry(test_frame, font=self.app.font_normal)
        self.test_entry.insert(0, "この声で感情を表現します。")
        self.test_entry.grid(row=0, column=0, sticky="ew", padx=(0, self.app.padding_normal))
        self.test_button = ttk.Button(test_frame, text="テスト再生", command=self._execute_test_speech, style="Dialog.TButton")
        self.test_button.grid(row=0, column=1)
        master.columnconfigure(1, weight=1)
        return info_label

    def _execute_test_speech(self):
        final_params = {}
        for key, entry_var in self.param_widgets.items():
            try:
                offset_value = float(entry_var.get())
                base_value = self.normal_params.get(key, self.params_info[key]['default'])
                final_value = base_value + offset_value
                info = self.params_info[key]
                final_params[key] = max(info["abs_min"], min(info["abs_max"], final_value))
            except ValueError:
                final_params[key] = self.normal_params.get(key, self.params_info[key]['default'])
        self.test_button.config(state="disabled", text="生成中...")
        self.editor.trigger_test_speech(text=self.test_entry.get(), params_override=final_params, on_finish_callback=self._on_test_finished)
    
    def _on_test_finished(self):
        if self.winfo_exists(): self.test_button.config(state="normal", text="テスト再生")

    def reset_offsets_to_zero(self):
        for entry_var in self.param_widgets.values(): entry_var.set("+0.00")

    def apply(self):
        final_params = {}
        for key, entry_var in self.param_widgets.items():
            try:
                offset_value = float(entry_var.get())
                base_value = self.normal_params.get(key, self.params_info[key]['default'])
                final_value = base_value + offset_value
                info = self.params_info[key]
                final_params[key] = round(max(info["abs_min"], min(info["abs_max"], final_value)), 4)
            except ValueError:
                final_params[key] = self.normal_params.get(key, self.params_info[key]['default'])
        self.result = final_params

class TabExpressions(TabBase):
    def __init__(self, parent, editor_instance):
        self.is_standby_separated_mode = False # UIが分離モードかどうかを管理する状態変数
        super().__init__(parent, editor_instance)

    def create_widgets(self):
        parent = self.scrollable_frame
        # 左列(リスト)は伸縮、右列(プレビュー)は固定にする
        parent.columnconfigure(0, weight=1)
        # 右列は伸縮させないので weight は設定しない
        parent.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.configure("Tab.TButton", font=self.app.font_normal, padding=self.app.padding_small)
        style.configure("Expressions.Treeview.Heading", font=self.app.font_normal)
        style.configure("Expressions.Treeview", font=self.app.font_normal, rowheight=int(self.app.font_normal[1] * 1.8))

        # --- 左パネル (変更なし) ---
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, self.app.padding_normal))
        list_frame.rowconfigure(1, weight=1); list_frame.columnconfigure(0, weight=1)
        
        list_button_frame = ttk.Frame(list_frame)
        list_button_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        button_padx = self.app.padding_small / 2
        ttk.Button(list_button_frame, text="表情を追加", command=self.add_expression, style="Tab.TButton").pack(side="left", padx=(0,button_padx))
        ttk.Button(list_button_frame, text="編集", command=self.edit_expression, style="Tab.TButton").pack(side="left", padx=button_padx)
        ttk.Button(list_button_frame, text="削除", command=self.delete_expression, style="Tab.TButton").pack(side="left", padx=button_padx)
        self.voice_setting_button = ttk.Button(list_button_frame, text="音声設定...", command=self.edit_voice_settings, state="disabled", style="Tab.TButton")
        self.voice_setting_button.pack(side="left", padx=(self.app.padding_normal, 0))

        self.separate_standby_button = ttk.Button(list_button_frame, text="待機画像を分離...", command=self.toggle_standby_separation, style="Tab.TButton")
        self.separate_standby_button.pack(side="right")

        self.tree = ttk.Treeview(list_frame, columns=("id", "name"), show="headings", style="Expressions.Treeview")
        self.tree.heading("id", text="英語ID"); self.tree.heading("name", text="日本語名")
        self.tree.column("id", width=int(self.app.base_font_size*10))
        self.tree.column("name", width=int(self.app.base_font_size*15))
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_expression_select)

        # --- 右パネル：D&Dエリア ---
        # 画面幅から固定幅を計算
        fixed_width = int(self.app.winfo_screenwidth() * 0.18)

        self.dnd_frame = ttk.Frame(parent, width=fixed_width)
        self.dnd_frame.grid(row=0, column=1, sticky="nsew")
        # このフレームのサイズが内部ウィジェットによって変更されないようにする
        self.dnd_frame.grid_propagate(False)

        self.dnd_frame.rowconfigure(0, weight=1)
        self.dnd_frame.columnconfigure(0, weight=1)

        # D&Dエリアを格納する専用のコンテナフレーム
        self.dnd_container = ttk.Frame(self.dnd_frame)
        self.dnd_container.grid(row=0, column=0, sticky="nsew")
        self.dnd_container.columnconfigure(0, weight=1)
        
        # 3つの行すべてに伸縮性を持たせる
        self.dnd_container.rowconfigure(0, weight=1)
        self.dnd_container.rowconfigure(1, weight=1)
        self.dnd_container.rowconfigure(2, weight=1)

        # 3つのD&Dエリアフレームを、dnd_containerの子として配置する
        # rowを明示的に指定
        self.standby_frame = ttk.Frame(self.dnd_container, relief="solid", borderwidth=self.app.border_width_normal)
        self.standby_frame.grid(row=0, column=0, sticky="nsew", pady=(0, self.app.padding_small))
        standby_label = ttk.Label(self.standby_frame, text="待機画像 (専用)\nをここにD&D", anchor="center", font=self.app.font_normal)
        standby_label.pack(expand=True, fill="both")
        standby_label.drop_target_register(DND_FILES)
        standby_label.dnd_bind('<<Drop>>', lambda e: self.on_image_drop(e, 'standby'))

        self.close_label_var = tk.StringVar(value="口閉じ画像(基準)\nをここにD&D")
        self.close_frame = ttk.Frame(self.dnd_container, relief="solid", borderwidth=self.app.border_width_normal)
        self.close_frame.grid(row=1, column=0, sticky="nsew", pady=(0, self.app.padding_small))
        close_label = ttk.Label(self.close_frame, textvariable=self.close_label_var, anchor="center", font=self.app.font_normal)
        close_label.pack(expand=True, fill="both")
        close_label.drop_target_register(DND_FILES)
        close_label.dnd_bind('<<Drop>>', lambda e: self.on_image_drop(e, 'close'))

        self.open_frame = ttk.Frame(self.dnd_container, relief="solid", borderwidth=self.app.border_width_normal)
        self.open_frame.grid(row=2, column=0, sticky="nsew", pady=(self.app.padding_small, 0))
        open_label = ttk.Label(self.open_frame, text="口開き画像(口パク)\nをここにD&D", anchor="center", font=self.app.font_normal)
        open_label.pack(expand=True, fill="both")
        open_label.drop_target_register(DND_FILES)
        open_label.dnd_bind('<<Drop>>', lambda e: self.on_image_drop(e, 'open'))

        self.widgets = {
            'tree': self.tree,
            'standby_label': standby_label,
            'close_label': close_label,
            'open_label': open_label,
            'voice_setting_button': self.voice_setting_button,
            'separate_standby_button': self.separate_standby_button
        }

    def load_data(self):
        costume_id = self.editor.current_costume_id.get()
        for item in self.tree.get_children(): self.tree.delete(item)
        expressions = self.character_data.get_expressions_for_costume(costume_id)
        for expr in expressions: self.tree.insert("", "end", values=(expr['id'], expr['name']))
        if self.tree.get_children():
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item); self.tree.focus(first_item)
            self.update_dnd_previews()

    def collect_data(self):
        costume_id = self.editor.current_costume_id.get()
        expressions = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            expressions.append({'id': values[0], 'name': values[1]})
        self.character_data.update_expressions_for_costume(costume_id, expressions)

    def add_expression(self):
        dialog = ExpressionDialog(self, title="表情の追加")
        if dialog.result:
            expr_id, expr_name_raw = dialog.result
            # サニタイズ処理
            expr_name = self.editor.sanitize_string(expr_name_raw, max_length=50)

            for item_id in self.tree.get_children():
                if self.tree.item(item_id, 'values')[0] == expr_id:
                    messagebox.showerror("エラー", f"ID '{expr_id}' は既に使用されています。", parent=self); return
            self.tree.insert("", "end", values=(expr_id, expr_name))

    def edit_expression(self):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("警告", "編集する表情を選択してください。", parent=self); return
        old_id, old_name = self.tree.item(selected_item, 'values')
        dialog = ExpressionDialog(self, title="表情の編集", initial_id=old_id, initial_name=old_name, id_editable=(old_id != 'normal'))
        if dialog.result:
            new_id, new_name_raw = dialog.result
            # サニタイズ処理
            new_name = self.editor.sanitize_string(new_name_raw, max_length=50)

            if old_id != new_id:
                for item_id in self.tree.get_children():
                    if item_id != selected_item and self.tree.item(item_id, 'values')[0] == new_id:
                        messagebox.showerror("エラー", f"ID '{new_id}' は既に使用されています。", parent=self); return
            self.tree.item(selected_item, values=(new_id, new_name))
        
    def delete_expression(self):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("警告", "削除する表情を選択してください。", parent=self); return
        values = self.tree.item(selected_item, 'values')
        if values[0] == 'normal': messagebox.showerror("エラー", "'normal'表情は削除できません。", parent=self); return
        if messagebox.askyesno("確認", f"本当に表情 '{values[1]}' を削除しますか？\n関連する画像ファイルや音声設定も削除されます。", parent=self):
            expr_id = values[0]
            costume_id = self.editor.current_costume_id.get()
            base_path = self.character_data.base_path
            
            paths_to_delete = [
                os.path.join(base_path, costume_id, f"{expr_id}.png"),
                os.path.join(base_path, costume_id, f"{expr_id}_standby.png"),
                os.path.join(base_path, costume_id, f"{expr_id}_close.png"),
                os.path.join(base_path, costume_id, f"{expr_id}_open.png"),
            ]
            for path in paths_to_delete:
                if os.path.exists(path):
                    os.remove(path)
            self.character_data.remove_voice_param(expr_id)
            self.tree.delete(selected_item)
            self.update_dnd_previews()

    def edit_voice_settings(self):
        selected_item = self.tree.focus()
        if not selected_item: return
        expression_id = self.tree.item(selected_item, 'values')[0]
        dialog = EmotionVoiceSettingDialog(self, title=f"音声設定: {expression_id}", character_data=self.character_data, expression_id=expression_id, editor_instance=self.editor)
        if dialog.result:
            self.character_data.set('VOICE_PARAMS', expression_id, str(dialog.result))
            messagebox.showinfo("成功", f"表情 '{expression_id}' の音声パラメータを更新しました。", parent=self.editor)

    def on_image_drop(self, event, image_type: str):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("警告", "画像を登録する表情をリストから選択してください。", parent=self); return
        expr_id = self.tree.item(selected_item, 'values')[0]
        costume_id = self.editor.current_costume_id.get()
        filepath = event.data.strip('{}')
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            messagebox.showwarning("ファイル形式エラー", "画像ファイルを選択してください。", parent=self); return
        try:
            img = Image.open(filepath)
            
            if image_type == 'standby':
                target_filename = f"{expr_id}_standby.png"
            elif image_type == 'close':
                target_filename = f"{expr_id}_close.png"
            elif image_type == 'open':
                target_filename = f"{expr_id}_open.png"
            else:
                return

            target_path = os.path.join(self.character_data.base_path, costume_id, target_filename)
            img.save(target_path, "PNG")
            
            if image_type == 'standby':
                self.is_standby_separated_mode = True
                self.update_ui_for_standby_mode()

            messagebox.showinfo("成功", f"画像を '{target_filename}' として保存しました。", parent=self)
            self.update_dnd_previews()
        except Exception as e:
            messagebox.showerror("保存エラー", f"画像の保存に失敗しました:\n{e}", parent=self)

    def on_expression_select(self, event):
        selected_item = self.tree.focus()
        if selected_item:
            expression_id = self.tree.item(selected_item, 'values')[0]
            self.voice_setting_button.config(state="normal" if expression_id != 'normal' else "disabled")

            # 表情が切り替わったタイミングで、ファイルの存在有無を正として状態をリセットする
            costume_id = self.editor.current_costume_id.get()
            standby_path = os.path.join(self.character_data.base_path, costume_id, f"{expression_id}_standby.png")
            self.is_standby_separated_mode = os.path.exists(standby_path)

        else:
            self.voice_setting_button.config(state="disabled")
            self.is_standby_separated_mode = False # 何も選択されていなければ非分離モード

        self.update_ui_for_standby_mode()
        self.update_dnd_previews()

    def update_dnd_previews(self):
        available_height = self.editor.get_available_tab_height()
        # 利用可能な高さがまだ計算できない（小さすぎる）場合は、少し待ってから再試行
        if available_height < 50:
            self.after(50, self.update_dnd_previews)
            return

        selected_item = self.tree.focus()
        padding = self.app.padding_small
        
        if self.is_standby_separated_mode:
            area_height = (available_height - (padding * 2) - self.app.padding_normal) // 3
        else:
            area_height = (available_height - padding - self.app.padding_normal) // 2

        if not selected_item:
            self._update_single_dnd_label('standby', None, area_height)
            self._update_single_dnd_label('close', None, area_height)
            self._update_single_dnd_label('open', None, area_height)
            return
            
        expr_id = self.tree.item(selected_item, 'values')[0]
        costume_id = self.editor.current_costume_id.get()
        base_path = self.character_data.base_path
        img_dir = os.path.join(base_path, costume_id)

        standby_path = os.path.join(img_dir, f"{expr_id}_standby.png")
        close_path = os.path.join(img_dir, f"{expr_id}_close.png")
        open_path = os.path.join(img_dir, f"{expr_id}_open.png")
        base_png_path = os.path.join(img_dir, f"{expr_id}.png")

        final_close_path = close_path if os.path.exists(close_path) else base_png_path if os.path.exists(base_png_path) else None

        self._update_single_dnd_label('standby', standby_path if os.path.exists(standby_path) else None, area_height)
        self._update_single_dnd_label('close', final_close_path, area_height)
        self._update_single_dnd_label('open', open_path if os.path.exists(open_path) else None, area_height)


    def toggle_standby_separation(self):
        """「待機画像を分離/統合」ボタンが押されたときの処理"""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("操作エラー", "操作対象の表情をリストから選択してください。", parent=self)
            return
        
        # 1. まず状態変数を反転させる
        self.is_standby_separated_mode = not self.is_standby_separated_mode

        # 2. 状態変数が False になった場合（統合モードへの切り替え）のみ、ファイル削除処理を行う
        if not self.is_standby_separated_mode:
            expr_id = self.tree.item(selected_item, 'values')[0]
            costume_id = self.editor.current_costume_id.get()
            standby_path = os.path.join(self.character_data.base_path, costume_id, f"{expr_id}_standby.png")

            # ファイルが存在する場合のみ、確認ダイアログを表示して削除
            if os.path.exists(standby_path):
                if messagebox.askyesno("確認", f"専用の待機画像 ({os.path.basename(standby_path)}) を削除し、\n口閉じ画像を待機画像として使用するように戻しますか？", parent=self):
                    try:
                        os.remove(standby_path)
                        print(f"削除しました: {standby_path}")
                    except Exception as e:
                        messagebox.showerror("エラー", f"ファイルの削除に失敗しました:\n{e}", parent=self)
                        # 削除に失敗した場合は、モードを元に戻す
                        self.is_standby_separated_mode = True
                else:
                    # ユーザーがキャンセルした場合は、モードを元に戻す
                    self.is_standby_separated_mode = True
        
        # 3. 最終的な状態変数の状態に基づいてUIを更新
        self.update_ui_for_standby_mode()
        self.update_dnd_previews()

    def update_ui_for_standby_mode(self):
        """状態変数に応じてUIの状態を切り替え、コンテナの行の伸縮性を変更する"""

        # D&Dエリアの高さの手動計算と設定をすべて削除
        
        if self.is_standby_separated_mode:
            # 3エリア表示
            # standby_frameが配置されている0行目の伸縮性を有効にする
            self.dnd_container.rowconfigure(0, weight=1)
            # 念のためウィジェットをgridに戻す
            self.standby_frame.grid() 
            
            self.separate_standby_button.config(text="待機画像を統合...")
            self.close_label_var.set("口閉じ画像 (口パク用)\nをここにD&D")
        else:
            # 2エリア表示
            # standby_frameが配置されている0行目の伸縮性を無効にし、スペースを詰める
            self.dnd_container.rowconfigure(0, weight=0)
            # レイアウトからウィジェットを非表示にする
            self.standby_frame.grid_remove()
            
            self.separate_standby_button.config(text="待機画像を分離...")
            self.close_label_var.set("口閉じ画像 (基準)\nをここにD&D")

    def _update_single_dnd_label(self, image_type: str, image_path: str | None, target_height: int):
        label = self.widgets[f'{image_type}_label']
        text_map = {
            'standby': "待機画像 (専用)\nをここにD&D",
            'close': "口閉じ画像(基準)\nをここにD&D",
            'open': "口開き画像(口パク)\nをここにD&D"
        }
        if image_type == 'close':
             self.close_label_var.set(text_map[image_type])
        else:
            label.config(text=text_map[image_type])
        
        self.after(10, self._process_image_for_label, label, image_path, target_height)


    def _process_image_for_label(self, label, image_path, target_height):
        parent_frame = label.master
        frame_width = parent_frame.winfo_width()
        
        # ウィジェットが非表示などでサイズが取得できない（極小値）場合は、
        # 不正なリサイズ処理を試みる前に処理を中断する。
        if target_height < 20 or frame_width < 20:
            label.image = None
            label.config(image="")
            return

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail((frame_width - 10, target_height - 10), Image.Resampling.LANCZOS)
                
                tk_img = ImageTk.PhotoImage(img)
                label.image = tk_img
                label.config(image=tk_img, text="")
            except Exception as e:
                label.image = None
                label.config(image="", text="画像読込\nエラー")
        else:
            label.image = None
            label.config(image="")
