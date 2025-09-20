# src/tabs/tab_touch_areas.py

import os
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .tab_base import TabBase

class TouchAreaDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_action="", initial_cursor="hand"):
        self.app = parent.app
        self.initial_action = initial_action # 初期値を保持
        self.cursor_var = tk.StringVar(parent, value=initial_cursor)
        super().__init__(parent, title)

    def body(self, master):
        # ラベルのテキストを変更
        ttk.Label(master, text="アクション名 (改行可):", font=self.app.font_normal).grid(row=0, sticky="w")
        # EntryからTextウィジェットに変更
        self.action_entry = tk.Text(master, font=self.app.font_normal, height=3, width=40, relief="solid", bd=1)
        self.action_entry.grid(row=1, sticky="ew", pady=(0, self.app.padding_normal))
        # 初期値を挿入
        self.action_entry.insert("1.0", self.initial_action)
        
        # Enterキーの挙動を制御するバインドを追加
        def on_focus_in(event):
            # Textウィジェットにフォーカスがある間、Enterキーでダイアログが閉じないようにする
            self.unbind("<Return>")
        
        def on_focus_out(event):
            # フォーカスが外れたら、Enterキーでダイアログを閉じられるように戻す
            self.bind("<Return>", self.ok)

        self.action_entry.bind("<FocusIn>", on_focus_in)
        self.action_entry.bind("<FocusOut>", on_focus_out)
        
        ttk.Label(master, text="カーソル名:", font=self.app.font_normal).grid(row=2, sticky="w")
        self.cursor_entry = ttk.Entry(master, textvariable=self.cursor_var, font=self.app.font_normal)
        self.cursor_entry.grid(row=3, sticky="ew")
        return self.action_entry

    def apply(self):
        # Textウィジェットから値を取得し、前後の空白を除去
        action_text = self.action_entry.get("1.0", "end-1c").strip()
        cursor_text = self.cursor_var.get().strip()
        self.result = (action_text, cursor_text)

    def validate(self):
        # Textウィジェットから値を取得して検証
        action_text = self.action_entry.get("1.0", "end-1c").strip()
        if not action_text or not self.cursor_var.get().strip():
            messagebox.showwarning("入力エラー", "アクション名とカーソル名の両方を入力してください。", parent=self); return 0
        return 1

class TabTouchAreas(TabBase):
    def create_widgets(self):
        parent = self.scrollable_frame
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1) # Treeviewの行を2に変更

        style = ttk.Style(self)
        style.configure("Tab.TButton", font=self.app.font_normal, padding=self.app.padding_small)
        style.configure("Touch.Treeview.Heading", font=self.app.font_normal)
        style.configure("Touch.Treeview", font=self.app.font_normal, rowheight=int(self.app.font_normal[1] * 1.8))
        # 継承中アイテム用のタグスタイル
        style.configure("Inherited.Treeview", foreground="gray")

        # --- 感情セレクター ---
        emotion_frame = ttk.Frame(parent)
        emotion_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_normal))
        ttk.Label(emotion_frame, text="編集対象の感情:", font=self.app.font_normal).pack(side="left")
        self.emotion_var = tk.StringVar()
        self.emotion_selector = ttk.Combobox(emotion_frame, textvariable=self.emotion_var, state="readonly", font=self.app.font_normal)
        self.emotion_selector.pack(side="left", padx=self.app.padding_small)
        self.emotion_selector.bind("<<ComboboxSelected>>", self.on_emotion_select)

        # --- ボタンフレーム ---
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.app.padding_normal))
        btn_padx = self.app.padding_small / 2
        self.add_button = ttk.Button(button_frame, text="エリアを追加", command=self.add_area, style="Tab.TButton")
        self.add_button.pack(side="left", padx=(0, btn_padx))
        self.edit_button = ttk.Button(button_frame, text="編集", command=self.edit_area, style="Tab.TButton")
        self.edit_button.pack(side="left", padx=btn_padx)
        self.delete_button = ttk.Button(button_frame, text="削除", command=self.delete_area, style="Tab.TButton")
        self.delete_button.pack(side="left", padx=btn_padx)

        # --- 継承状態を操作するボタン ---
        self.override_button = ttk.Button(button_frame, text="この感情専用の設定を作成", command=self.create_override, style="Tab.TButton")
        self.override_button.pack(side="left", padx=(self.app.padding_large, 0))
        self.reset_button = ttk.Button(button_frame, text="基本設定(normal)に戻す", command=self.reset_to_normal, style="Tab.TButton")
        self.reset_button.pack(side="left", padx=(self.app.padding_large, 0))

        # --- Treeview ---
        self.tree = ttk.Treeview(parent, columns=("details"), show="tree headings", style="Touch.Treeview")
        self.tree.heading("#0", text="アクション / 矩形")
        self.tree.heading("details", text="詳細")
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        self.tree.grid(row=2, column=0, sticky="nsew")

        self.widgets = {
            'tree': self.tree, 'emotion_selector': self.emotion_selector,
            'add_button': self.add_button, 'edit_button': self.edit_button,
            'delete_button': self.delete_button, 'override_button': self.override_button,
            'reset_button': self.reset_button
        }

    def load_data(self):
        # 1. 感情セレクターの選択肢を更新
        costume_id = self.editor.current_costume_id.get()
        expressions = self.character_data.get_expressions_for_costume(costume_id)
        
        # 表示名とIDのマップを作成
        self.emotion_map = {"normal (基本)": "normal"}
        for expr in expressions:
            if expr['id'] != 'normal':
                self.emotion_map[f"{expr['name']} ({expr['id']})"] = expr['id']
        
        self.emotion_selector['values'] = list(self.emotion_map.keys())
        self.emotion_var.set("normal (基本)")
        
        # 2. normalのデータを読み込む
        self.on_emotion_select()

    def on_emotion_select(self, event=None):
        display_name = self.emotion_var.get()
        emotion_id = self.emotion_map.get(display_name, 'normal')
        costume_id = self.editor.current_costume_id.get()

        # プレビュー画像を対応する感情のものに更新
        if emotion_id == 'normal':
            self.editor.set_preview_to_character_base(costume_id)
        else:
            filepath = os.path.join(self.character_data.base_path, costume_id, f"{emotion_id}_close.png")
            if not os.path.exists(filepath):
                 filepath = os.path.join(self.character_data.base_path, costume_id, f"{emotion_id}.png")
            self.editor.update_preview_image(filepath)

        # 継承状態をチェック
        specific_areas = self.character_data.get_specific_touch_areas_for_costume(costume_id, emotion_id)
        is_override_mode = specific_areas is not None

        # UIの状態を更新
        self._update_ui_state(is_override_mode or emotion_id == 'normal', emotion_id)

        # Treeviewにデータを表示
        for item in self.tree.get_children(): self.tree.delete(item)
        
        areas_to_display = self.character_data.get_touch_areas_for_costume(costume_id, emotion_id)

        for area in areas_to_display:
            tag = '' if (is_override_mode or emotion_id == 'normal') else 'inherited'
            display_action = area['action'].replace('\n', ' ')
            parent_node = self.tree.insert("", "end", text=display_action, values=(f"カーソル: {area['cursor']}",), open=True, tags=(tag,))
            for i, rect in enumerate(area['rects']):
                self.tree.insert(parent_node, "end", text=f"  矩形 {i+1}", values=(str(rect),), tags=(tag,))
        
        self.update_highlight_from_selection()

    def _update_ui_state(self, is_editable: bool, emotion_id: str):
        """UIのボタンやリストの状態を編集モードに応じて切り替える"""
        if is_editable:
            self.add_button.config(state="normal")
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
            self.override_button.pack_forget() # hide
            if emotion_id != 'normal':
                self.reset_button.pack(side="left", padx=(self.app.padding_large, 0)) # show
            else:
                self.reset_button.pack_forget() # hide
            self.tree.tag_configure('inherited', foreground="gray")
        else:
            self.add_button.config(state="disabled")
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.override_button.pack(side="left", padx=(self.app.padding_large, 0)) # show
            self.reset_button.pack_forget() # hide
            self.tree.tag_configure('inherited', foreground="gray")
            
    def create_override(self):
        """「この感情専用の設定を作成」ボタンの処理"""
        display_name = self.emotion_var.get()
        emotion_id = self.emotion_map.get(display_name)
        costume_id = self.editor.current_costume_id.get()
        if not emotion_id or emotion_id == 'normal': return
        
        # normalのデータをコピーして専用設定として保存
        normal_areas = self.character_data.get_touch_areas_for_costume(costume_id, 'normal')
        self.character_data.update_touch_areas_for_costume(costume_id, emotion_id, normal_areas)
        
        # UIを再読み込み
        self.on_emotion_select()

    def reset_to_normal(self):
        """「基本設定(normal)に戻す」ボタンの処理"""
        display_name = self.emotion_var.get()
        emotion_id = self.emotion_map.get(display_name)
        costume_id = self.editor.current_costume_id.get()
        if not emotion_id or emotion_id == 'normal': return

        if messagebox.askyesno("確認", f"感情 '{display_name}' 専用のタッチエリア設定をすべて削除し、\n基本設定(normal)を継承する状態に戻しますか？", parent=self):
            self.character_data.delete_touch_areas_for_emotion(costume_id, emotion_id)
            self.on_emotion_select()
    
    def collect_data(self):
        # 現在表示されている感情のデータのみを保存する
        display_name = self.emotion_var.get()
        if not display_name: return # 何も選択されていない場合は何もしない
        emotion_id = self.emotion_map.get(display_name)
        costume_id = self.editor.current_costume_id.get()
        
        specific_areas = self.character_data.get_specific_touch_areas_for_costume(costume_id, emotion_id)
        is_override_mode = specific_areas is not None
        
        # normalか、専用設定がある場合のみ保存処理を行う
        if emotion_id == 'normal' or is_override_mode:
            areas = []
            for parent_id in self.tree.get_children():
                current_areas = self.character_data.get_touch_areas_for_costume(costume_id, emotion_id)
                # Treeviewのインデックスとデータのインデックスは一致するはず
                tree_index = self.tree.index(parent_id)
                if tree_index < len(current_areas):
                    original_action = current_areas[tree_index]['action']
                    cursor = self.tree.item(parent_id, "values")[0].replace("カーソル: ", "")
                    rects = [eval(self.tree.item(child_id, "values")[0]) for child_id in self.tree.get_children(parent_id)]
                    if rects: areas.append({'action': original_action, 'cursor': cursor, 'rects': rects})
            
            self.character_data.update_touch_areas_for_costume(costume_id, emotion_id, areas)

    def add_area(self):
        self.editor.enter_rect_drawing_mode(self.on_area_drawn)

    def on_area_drawn(self, rect: tuple | None):
        if not rect: return
        dialog = TouchAreaDialog(self, title="アクション設定")
        if not dialog.result: return
        action_raw, cursor_raw = dialog.result
        # サニタイズ処理
        action = self.editor.sanitize_string(action_raw, max_length=50, allow_newlines=True)
        cursor = self.editor.sanitize_string(cursor_raw, max_length=50)

        # --- データ更新処理 ---
        costume_id = self.editor.current_costume_id.get()
        emotion_id = self.emotion_map.get(self.emotion_var.get())
        current_areas = self.character_data.get_touch_areas_for_costume(costume_id, emotion_id)

        # 既存のアクションかチェック
        target_area = None
        for area in current_areas:
            if area['action'] == action:
                target_area = area
                break
        
        if target_area:
            # 既存のアクションに矩形を追加
            target_area['rects'].append(list(rect))
            target_area['cursor'] = cursor # カーソル情報も更新する
        else:
            # 新しいアクションとして追加
            current_areas.append({
                'action': action,
                'cursor': cursor,
                'rects': [list(rect)]
            })
            
        # --- 保存とUIの再読み込み ---
        self.character_data.update_touch_areas_for_costume(costume_id, emotion_id, current_areas)
        self.on_emotion_select()

    def edit_area(self):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("警告", "編集する項目を選択してください。", parent=self); return
        if not self.tree.parent(selected_item):
            costume_id = self.editor.current_costume_id.get()
            emotion_id = self.emotion_map.get(self.emotion_var.get())
            current_areas = self.character_data.get_touch_areas_for_costume(costume_id, emotion_id)
            tree_index = self.tree.index(selected_item)
            
            if tree_index >= len(current_areas): return # 安全策
            
            original_action = current_areas[tree_index]['action']
            old_cursor = self.tree.item(selected_item, "values")[0].replace("カーソル: ", "")
            
            dialog = TouchAreaDialog(self, "アクションの編集", initial_action=original_action, initial_cursor=old_cursor)
            if dialog.result:
                new_action_raw, new_cursor_raw = dialog.result
                # サニタイズ処理
                new_action = self.editor.sanitize_string(new_action_raw, max_length=50, allow_newlines=True)
                new_cursor = self.editor.sanitize_string(new_cursor_raw, max_length=50)
                
                display_action = new_action.replace('\n', ' ')
                self.tree.item(selected_item, text=display_action, values=(f"カーソル: {new_cursor}",))
                # collect_dataを呼ぶ前に、データソースの対応する項目を直接更新する
                current_areas[tree_index]['action'] = new_action
                current_areas[tree_index]['cursor'] = new_cursor
                self.character_data.update_touch_areas_for_costume(costume_id, emotion_id, current_areas)
        else:
            messagebox.showinfo("情報", "矩形を編集するには、一度削除してから\n再度「エリアを追加」で描き直してください。", parent=self)
        
    def delete_area(self):
        selected_item = self.tree.focus()
        if not selected_item: messagebox.showwarning("警告", "削除する項目を選択してください。", parent=self); return
        
        # --- データ更新処理 ---
        costume_id = self.editor.current_costume_id.get()
        emotion_id = self.emotion_map.get(self.emotion_var.get())
        areas = self.character_data.get_touch_areas_for_costume(costume_id, emotion_id)
        
        parent_id = self.tree.parent(selected_item)
        if not parent_id:
            # アクション全体（親ノード）を削除
            index_to_delete = self.tree.index(selected_item)
            if 0 <= index_to_delete < len(areas):
                del areas[index_to_delete]
        else:
            # 特定の矩形（子ノード）を削除
            parent_index = self.tree.index(parent_id)
            children_of_parent = self.tree.get_children(parent_id)
            child_index = children_of_parent.index(selected_item)
            
            if 0 <= parent_index < len(areas) and 0 <= child_index < len(areas[parent_index]['rects']):
                del areas[parent_index]['rects'][child_index]
                # 矩形がすべて無くなったら、アクション自体も削除
                if not areas[parent_index]['rects']:
                    del areas[parent_index]

        # --- 保存とUIの再読み込み ---
        self.character_data.update_touch_areas_for_costume(costume_id, emotion_id, areas)
        self.on_emotion_select()
        self.editor.clear_highlights()

    def on_selection_change(self, event=None):
        self.update_highlight_from_selection()

    def update_highlight_from_selection(self):
        try: active_tab_widget = self.winfo_toplevel().nametowidget(self.editor.notebook.select())
        except (tk.TclError, KeyError): return
        if active_tab_widget != self:
            self.editor.clear_highlights(); return
        selected_item = self.tree.focus()
        if not selected_item: self.editor.clear_highlights(); return
        rects_to_highlight = []
        parent_id = self.tree.parent(selected_item)
        if not parent_id:
            for child_id in self.tree.get_children(selected_item):
                rect_str = self.tree.item(child_id, "values")[0]
                try: rects_to_highlight.append(eval(rect_str))
                except: pass
        else:
            rect_str = self.tree.item(selected_item, "values")[0]
            try: rects_to_highlight.append(eval(rect_str))
            except: pass
        self.editor.highlight_touch_areas(rects_to_highlight)
