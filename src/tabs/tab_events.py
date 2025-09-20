import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import uuid
import shutil
import os
from .tab_base import TabBase
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES
import datetime

class ConditionEditor(ttk.Frame):
    """条件リストを編集するためのUIウィジェット"""
    def __init__(self, parent, app, editor_instance, initial_conditions=None):
        super().__init__(parent)
        self.app = app
        self.editor = editor_instance # EditorWindowのインスタンスを保持
        self.conditions = initial_conditions or []

        # 条件タイプを拡張
        self.CONDITION_TYPES = {
            "好感度が...以上": "favorability_above",
            "好感度が...以下": "favorability_below",
            "フラグが...と等しい": "flag_equals",
            "フラグが...と等しくない": "flag_not_equals",
            "フラグが...より大きい": "flag_above",
            "フラグが...より小さい": "flag_below",
            "フラグが存在する": "flag_exists",
            "フラグが存在しない": "flag_not_exists",
            "イベント...が完了している": "event_completed",
            "イベント...完了から...以上経過": "event_completed_after",
            "日付が...と等しい": "date_equals", # ★追加
            "日付が...以降": "date_after",
            "日付が...以前": "date_before",
            "時刻が...と等しい": "time_equals", # ★追加
            "時刻が...以降": "time_after",
            "時刻が...以前": "time_before",
        }
        self.TYPE_VALUE_MAP = {v: k for k, v in self.CONDITION_TYPES.items()}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # Treeviewが伸縮するように設定
        
        tree_container = ttk.Frame(self)
        tree_container.grid(row=0, column=0, sticky="nsew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        tree_height = max(2, min(len(self.conditions), 5))
        
        # Treeviewの列構成を変更
        self.tree = ttk.Treeview(tree_container, columns=("details",), show="tree headings", height=tree_height)
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.heading("#0", text="条件")
        self.tree.heading("details", text="詳細")
        self.tree.column("#0", width=180, stretch=tk.NO)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="w", pady=(self.app.padding_small, 0))
        ttk.Button(btn_frame, text="+", command=self.add_condition, width=3).pack(side="left")
        ttk.Button(btn_frame, text="-", command=self.remove_condition, width=3).pack(side="left", padx=self.app.padding_small)
        ttk.Button(btn_frame, text="編集", command=self.edit_condition, width=5).pack(side="left")

        self._populate_tree()

    def _populate_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for cond in self.conditions:
            cond_type = cond.get("type", "")
            display_type = self.TYPE_VALUE_MAP.get(cond_type, "")
            details_str = ""
            
            # 条件タイプに応じて詳細表示を生成
            if cond_type in ("favorability_above", "favorability_below"):
                details_str = f"値: {cond.get('value', '')}"
            elif "flag" in cond_type:
                details_str = f"フラグ名: {cond.get('flag', '')}"
                if cond_type not in ("flag_exists", "flag_not_exists"):
                    details_str += f", 値: {cond.get('value', '')}"
            elif "event" in cond_type:
                details_str = f"イベントID: {cond.get('event_id', '')}"
                if cond_type == "event_completed_after":
                    details_str += f", 経過時間: {cond.get('duration', '')}"
            elif "date" in cond_type:
                details_str = f"日付: {cond.get('date', '')}"
            elif "time" in cond_type:
                details_str = f"時刻: {cond.get('time', '')}"
                
            self.tree.insert("", "end", text=display_type, values=(details_str,))

    def add_condition(self):
        event_ids = self.editor.character_data.get_event_ids()
        dialog = ConditionDialog(self, "条件の追加", 
                                 condition_types=list(self.CONDITION_TYPES.keys()),
                                 event_ids=event_ids)
        if dialog.result:
            self.conditions.append(dialog.result)
            self._populate_tree()
            self.tree.configure(height=max(2, min(len(self.conditions), 5)))

    def edit_condition(self):
        selected_item = self.tree.focus()
        if not selected_item: return
        
        index = self.tree.index(selected_item)
        initial_data = self.conditions[index].copy()
        initial_data['display_type'] = self.TYPE_VALUE_MAP.get(initial_data['type'])

        event_ids = self.editor.character_data.get_event_ids()
        dialog = ConditionDialog(self, "条件の編集", 
                                 condition_types=list(self.CONDITION_TYPES.keys()),
                                 event_ids=event_ids,
                                 initial_data=initial_data)
        if dialog.result:
            self.conditions[index] = dialog.result
            self._populate_tree()

    def remove_condition(self):
        selected_item = self.tree.focus()
        if not selected_item: return
        index = self.tree.index(selected_item)
        del self.conditions[index]
        self._populate_tree()
        self.tree.configure(height=max(2, min(len(self.conditions), 5)))

    def get_conditions(self):
        return self.conditions

class ConditionDialog(simpledialog.Dialog):
    """単一の条件を編集するためのダイアログ"""
    def __init__(self, parent, title, condition_types, event_ids, initial_data=None):
        self.app = parent.app
        self.initial_data = initial_data or {}
        self.type_var = tk.StringVar(value=self.initial_data.get("display_type", ""))
        self.condition_types = condition_types
        self.event_ids = event_ids
        self.param_widgets = {}
        super().__init__(parent, title)

    def body(self, master):
        master.columnconfigure(0, weight=1)
        ttk.Label(master, text="条件の種類:").grid(row=0, sticky="w")
        self.type_combo = ttk.Combobox(master, textvariable=self.type_var, values=self.condition_types, state="readonly")
        self.type_combo.grid(row=1, sticky="ew", pady=(0, self.app.padding_normal))
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        self.param_frame = ttk.Frame(master)
        self.param_frame.grid(row=2, sticky="ew")
        self.param_frame.columnconfigure(1, weight=1)

        self._on_type_change()
        return self.type_combo

    def _on_type_change(self, event=None):
        for widget in self.param_frame.winfo_children(): widget.destroy()
        self.param_widgets = {}
        
        selected_display_type = self.type_var.get()
        internal_type = self.master.CONDITION_TYPES.get(selected_display_type)
        
        if not internal_type: return

        if internal_type in ("favorability_above", "favorability_below"):
            self._add_param_entry("value", "値:", self.initial_data.get("value", "100"))
        elif "flag" in internal_type:
            self._add_param_entry("flag", "フラグ名:", self.initial_data.get("flag", ""))
            if internal_type not in ("flag_exists", "flag_not_exists"):
                self._add_param_entry("value", "値:", self.initial_data.get("value", "1"), row=1)
        elif "event" in internal_type:
            self._add_param_combobox("event_id", "イベントID:", self.initial_data.get("event_id", ""), self.event_ids)
            if internal_type == "event_completed_after":
                self._add_param_entry("duration", "経過時間 (例: 1h, 30m, 1d):", self.initial_data.get("duration", "24h"), row=1)
        elif "date" in internal_type:
            dt = datetime.datetime.today()
            self._add_param_entry("date", "日付 (YYYY/MM/DD):", self.initial_data.get("date", str(dt.year) + "/01/01"))
        elif "time" in internal_type:
            self._add_param_entry("time", "時刻 (HH:MM):", self.initial_data.get("time", "12:00"))

    def _add_param_entry(self, key, label, default_value, row=None):
        if row is None: row = len(self.param_widgets)
        ttk.Label(self.param_frame, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(self.param_frame)
        entry.insert(0, default_value)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.param_widgets[key] = entry
        
    def _add_param_combobox(self, key, label, default_value, values, row=None):
        if row is None: row = len(self.param_widgets)
        ttk.Label(self.param_frame, text=label).grid(row=row, column=0, sticky="w")
        combo = ttk.Combobox(self.param_frame, values=values, state="readonly")
        if default_value in values: combo.set(default_value)
        elif values: combo.set(values[0])
        combo.grid(row=row, column=1, sticky="ew", pady=2)
        self.param_widgets[key] = combo

    def apply(self):
        display_type = self.type_var.get()
        internal_type = self.master.CONDITION_TYPES.get(display_type)
        if not internal_type: return
        
        self.result = {"type": internal_type}
        for key, widget in self.param_widgets.items():
            self.result[key] = widget.get().strip()

# --- ダイアログ定義 ---
# イベントの基本設定（ID、名前、トリガー）を編集するダイアログ
class EventDialog(simpledialog.Dialog):
    def __init__(self, parent, title, editor_instance, event_id="", event_name="", triggers=None, repeatable=False, cooldown="24h", id_editable=True):
        self.app = parent.app
        self.editor = editor_instance  # editor_instanceをインスタンス変数として保持
        self.triggers = triggers or [] # 条件グループのリスト
        
        self.id_var = tk.StringVar(parent, value=event_id)
        self.name_var = tk.StringVar(parent, value=event_name)
        self.repeatable_var = tk.BooleanVar(parent, value=repeatable)
        self.cooldown_var = tk.StringVar(parent, value=cooldown)
        self.id_editable = id_editable
        self.condition_editors = [] # ConditionEditorのインスタンスを保持
        super().__init__(parent, title)

    def body(self, master):
        master.columnconfigure(0, weight=1)
        # --- 伸縮する行を triggers_frame (1) に設定 ---
        master.rowconfigure(1, weight=1)

        # --- 基本設定フレーム ---
        basic_frame = ttk.Frame(master)
        basic_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_large))
        basic_frame.columnconfigure(1, weight=1)
        
        ttk.Label(basic_frame, text="イベントID:").grid(row=0, column=0, sticky="w")
        self.id_entry = ttk.Entry(basic_frame, textvariable=self.id_var)
        self.id_entry.grid(row=0, column=1, sticky="ew")
        if not self.id_editable: self.id_entry.config(state="readonly")

        ttk.Label(basic_frame, text="イベント名:").grid(row=1, column=0, sticky="w", pady=(self.app.padding_small, 0))
        self.name_entry = ttk.Entry(basic_frame, textvariable=self.name_var)
        self.name_entry.grid(row=1, column=1, sticky="ew")

        # --- トリガー設定フレーム ---
        self.triggers_frame = ttk.LabelFrame(master, text="発生条件 (どれか1つのグループを満たせば発生)")
        self.triggers_frame.grid(row=1, column=0, sticky="nsew")
        self.triggers_frame.columnconfigure(0, weight=1)
        # --- 伸縮する行を triggers_canvas (0) に設定 ---
        self.triggers_frame.rowconfigure(0, weight=1)

        # CanvasとScrollbarを内包するフレームを追加
        canvas_container = ttk.Frame(self.triggers_frame)
        canvas_container.grid(row=0, column=0, sticky="nsew")
        canvas_container.rowconfigure(0, weight=1)
        canvas_container.columnconfigure(0, weight=1)
        
        self.triggers_canvas = tk.Canvas(canvas_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.triggers_canvas.yview)
        self.scrollable_triggers_frame = ttk.Frame(self.triggers_canvas)
        self.triggers_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.triggers_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.canvas_frame_id = self.triggers_canvas.create_window((0, 0), window=self.scrollable_triggers_frame, anchor="nw")
        
        def update_scroll_region(event):
            self.triggers_canvas.configure(scrollregion=self.triggers_canvas.bbox("all"))
            self.triggers_canvas.itemconfig(self.canvas_frame_id, width=event.width)

        self.scrollable_triggers_frame.bind("<Configure>", lambda e: self.triggers_canvas.configure(scrollregion=self.triggers_canvas.bbox("all")))
        self.triggers_canvas.bind("<Configure>", update_scroll_region)
        
        self.rebuild_trigger_editors()

        trigger_buttons = ttk.Frame(self.triggers_frame)
        trigger_buttons.grid(row=1, column=0, sticky="w", pady=(self.app.padding_small, 0))
        ttk.Button(trigger_buttons, text="条件グループを追加 (OR)", command=self.add_trigger_group).pack(side="left")

        # --- その他設定 ---
        other_frame = ttk.Frame(master)
        other_frame.grid(row=2, column=0, sticky="ew", pady=(self.app.padding_large, 0))
        self.repeat_check = ttk.Checkbutton(other_frame, text="繰り返し可能", variable=self.repeatable_var)
        self.repeat_check.pack(side="left")
        ttk.Label(other_frame, text="クールダウン:").pack(side="left", padx=(self.app.padding_large, self.app.padding_small))
        self.cooldown_entry = ttk.Entry(other_frame, textvariable=self.cooldown_var)
        self.cooldown_entry.pack(side="left")

        return self.id_entry

    def rebuild_trigger_editors(self):
        for widget in self.scrollable_triggers_frame.winfo_children(): widget.destroy()
        self.condition_editors = []

        if not self.triggers:
            ttk.Label(self.scrollable_triggers_frame, text="（条件はありません）").pack(pady=self.app.padding_normal)

        for i, group in enumerate(self.triggers):
            group_container = ttk.Frame(self.scrollable_triggers_frame)
            group_container.pack(fill="x", expand=True, padx=self.app.padding_small, pady=self.app.padding_small)
            group_container.columnconfigure(0, weight=1)
            
            group_frame = ttk.LabelFrame(group_container, text=f"グループ {i+1} (AND条件)")
            group_frame.grid(row=0, column=0, sticky="ew")
            
            remove_btn = ttk.Button(group_container, text="×", command=lambda idx=i: self.remove_trigger_group(idx), width=3)
            # LabelFrameの右横に配置する
            remove_btn.grid(row=0, column=1, sticky="ne", padx=(self.app.padding_small, 0), pady=self.app.padding_small)

            editor = ConditionEditor(group_frame, self.app, self.editor, group)
            editor.pack(fill="x", expand=True, padx=self.app.padding_small, pady=self.app.padding_small)
            self.condition_editors.append(editor)

    def add_trigger_group(self):
        self.triggers.append([])
        self.rebuild_trigger_editors()

    def remove_trigger_group(self, index_to_remove):
        """指定されたインデックスの条件グループを削除する"""
        if 0 <= index_to_remove < len(self.triggers):
            del self.triggers[index_to_remove]
            self.rebuild_trigger_editors()

    def validate(self):
        event_id = self.id_var.get().strip()
        if not event_id or not all(c.isalnum() or c == '_' for c in event_id):
            messagebox.showwarning("入力エラー", "イベントIDは必須で、半角英数字とアンダースコア(_)のみ使用できます。", parent=self)
            return 0
        return 1

    def apply(self):
        # 各ConditionEditorから最新の条件リストを収集
        final_triggers = [editor.get_conditions() for editor in self.condition_editors]
        
        self.result = {
            "id": self.id_var.get().strip(), "name": self.name_var.get().strip(),
            "triggers": final_triggers,
            "repeatable": self.repeatable_var.get(), "cooldown": self.cooldown_var.get()
        }

# シーケンス内のコマンドを編集するダイアログ
class CommandDialog(simpledialog.Dialog):
    # マッピング辞書をクラス属性として定義
    COMMAND_DISPLAY_MAP = {
        "dialogue": "セリフ",
        "monologue": "モノローグ",
        "choice": "選択肢",
        "screen_effect": "画面効果",
        "set_favorability": "好感度を操作",
        "add_long_term_memory": "長期記憶に追加",
        "change_costume": "衣装変更",
        "change_persona": "話し方を変更",
        "set_flag": "フラグを操作",
        "branch_on_flag": "フラグで分岐"
    }
    COMMAND_VALUE_MAP = {v: k for k, v in COMMAND_DISPLAY_MAP.items()}

    def __init__(self, parent, title, command_data=None, editor_instance=None, existing_labels=None):
        self.app = parent.app
        if not editor_instance:
            raise ValueError("CommandDialog requires an editor_instance.")
        self.editor = editor_instance
        self.command_type_var = tk.StringVar()
        self.param_widgets = {}
        initial_type = (command_data or {}).get("type", "dialogue")
        self.initial_data = command_data or {"type": initial_type, "params": {}}
        self.display_mode_var = tk.StringVar()
        self.option_widgets = []
        self.existing_labels = existing_labels or []
        self.is_permanent_memory_var = tk.BooleanVar()
        self.effect_type_var = tk.StringVar()
        self.method_var = tk.StringVar()
        self.wait_var = tk.BooleanVar()
        super().__init__(parent, title)

    def body(self, master):
        master.columnconfigure(0, weight=1)
        master.rowconfigure(3, weight=1)
        
        # --- 上部のUI（ラベル、ジャンプ先、コマンド種類）---
        top_frame = ttk.Frame(master)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(1, weight=1)
        
        ttk.Label(top_frame, text="ラベル (この地点の名前):", font=self.app.font_normal).grid(row=0, column=0, sticky="w")
        self.label_entry = ttk.Entry(top_frame, font=self.app.font_normal)
        self.label_entry.grid(row=0, column=1, sticky="ew", pady=(0, self.app.padding_small))
        if "label" in self.initial_data:
            self.label_entry.insert(0, self.initial_data["label"])

        ttk.Label(top_frame, text="次のジャンプ先:", font=self.app.font_normal).grid(row=1, column=0, sticky="w")
        jump_options = [""] + self.existing_labels
        self.jump_combo = ttk.Combobox(top_frame, values=jump_options, font=self.app.font_normal, state="readonly")
        self.jump_combo.grid(row=1, column=1, sticky="ew", pady=(0, self.app.padding_large))
        self.jump_combo.set(self.initial_data.get("jump_to", ""))

        ttk.Label(top_frame, text="コマンドの種類:", font=self.app.font_normal).grid(row=2, column=0, sticky="w")
        
        # Comboboxに渡す値を「表示名」のリストにする
        command_display_names = list(self.COMMAND_DISPLAY_MAP.values())
        self.type_combo = ttk.Combobox(top_frame, textvariable=self.command_type_var, values=command_display_names, state="readonly", font=self.app.font_normal)
        self.type_combo.grid(row=2, column=1, sticky="ew", pady=(0, self.app.padding_normal))
        self.type_combo.bind("<<ComboboxSelected>>", self.update_fields)
        
        # 初期値を設定 (内部名 -> 表示名 に変換してから設定)
        initial_display_name = self.COMMAND_DISPLAY_MAP.get(self.initial_data["type"], command_display_names[0])
        self.command_type_var.set(initial_display_name)
        
        # --- コマンドごとの可変フィールド ---
        self.fields_frame = ttk.Frame(master)
        self.fields_frame.grid(row=3, column=0, sticky="nsew")
        self.fields_frame.rowconfigure(0, weight=1)
        self.fields_frame.columnconfigure(0, weight=1)

        self.update_fields()
        return self.type_combo

    def update_fields(self, event=None):
        for widget in self.fields_frame.winfo_children(): widget.destroy()
        self.param_widgets = {}
        self.option_widgets = []

        # 表示名から内部名に変換
        selected_display_name = self.command_type_var.get()
        command_type = self.COMMAND_VALUE_MAP.get(selected_display_name)

        params = self.initial_data.get("params", {}) if self.initial_data.get("type") == command_type else {}

        if command_type == "dialogue" or command_type == "monologue":
            # dialogueとmonologueでUIを共通化
            self.fields_frame.columnconfigure(1, weight=1)

            # 表示タイプ選択用のラジオボタン
            mode_frame = ttk.Frame(self.fields_frame)
            mode_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, self.app.padding_small))
            ttk.Label(mode_frame, text="表示タイプ:", font=self.app.font_normal).pack(side="left")
            ttk.Radiobutton(mode_frame, text="表情ID", variable=self.display_mode_var, value="expression", command=self._update_display_fields).pack(side="left", padx=self.app.padding_small)
            ttk.Radiobutton(mode_frame, text="イベントスチル", variable=self.display_mode_var, value="still", command=self._update_display_fields).pack(side="left")

            self.display_content_frame = ttk.Frame(self.fields_frame)
            self.display_content_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
            self.display_content_frame.columnconfigure(1, weight=1)
            
            initial_mode = "still" if "still_image" in params else "expression"
            self.display_mode_var.set(initial_mode)
            self._update_display_fields()

            # コマンドタイプに応じてテキスト入力欄のラベルを切り替え
            text_label = "セリフ" if command_type == "dialogue" else "モノローグ文"
            self.add_param_field("text", text_label, params.get("text", ""), as_text=True, start_row=2)

        elif command_type == "choice":
            # fields_frameのグリッド設定
            self.fields_frame.rowconfigure(1, weight=1)
            self.fields_frame.columnconfigure(0, weight=1)

            # --- 上段: 問いかけ文と追加/削除ボタン ---
            top_choice_frame = ttk.Frame(self.fields_frame)
            top_choice_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_normal))
            top_choice_frame.columnconfigure(1, weight=1)
            
            self.add_param_field("prompt", "選択肢の問いかけ:", params.get("prompt", ""), as_text=True, parent_frame=top_choice_frame, start_row=0)
            
            button_frame = ttk.Frame(top_choice_frame)
            button_frame.grid(row=1, column=1, sticky="w", pady=self.app.padding_small)
            ttk.Button(button_frame, text="+ 選択肢を追加", command=self.add_option_field).pack(side="left")

            # --- 下段: スクロール可能な選択肢リスト ---
            canvas_container = ttk.Frame(self.fields_frame)
            canvas_container.grid(row=1, column=0, sticky="nsew")
            canvas_container.rowconfigure(0, weight=1)
            canvas_container.columnconfigure(0, weight=1)

            choice_canvas = tk.Canvas(canvas_container, highlightthickness=0)
            scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=choice_canvas.yview)
            self.options_container = ttk.Frame(choice_canvas) # 実際にウィジェットを置くフレーム
            choice_canvas.configure(yscrollcommand=scrollbar.set)
            
            choice_canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")
            canvas_frame_id = choice_canvas.create_window((0, 0), window=self.options_container, anchor="nw")

            def update_scroll_region(event):
                choice_canvas.configure(scrollregion=choice_canvas.bbox("all"))
                choice_canvas.itemconfig(canvas_frame_id, width=event.width)
            
            self.options_container.bind("<Configure>", lambda e: choice_canvas.configure(scrollregion=choice_canvas.bbox("all")))
            choice_canvas.bind("<Configure>", update_scroll_region)

            # 既存の選択肢を再構築
            initial_options = params.get("options", [])
            if not initial_options: 
                self.add_option_field()
            else:
                for i, option_data in enumerate(initial_options):
                    self.add_option_field(option_data, index=i)
        
        elif command_type == "screen_effect":
            self._create_screen_effect_ui(params)

        elif command_type == "set_favorability":
            print(params.get("change", "+10"))
            self.add_param_field("change", "好感度変化量 (例: +20, -10):", params.get("change", "+10"))

        elif command_type == "add_long_term_memory":
            self.fields_frame.columnconfigure(1, weight=1)
            # 要約 (summary) の入力欄 (複数行)
            self.add_param_field("summary", "記憶させる内容の要約:", params.get("summary", ""), as_text=True, start_row=0)
            
            # 永続化チェックボックス
            is_permanent = params.get("importance") == "100" or params.get("importance") == 100
            self.is_permanent_memory_var.set(is_permanent)
            permanent_check = ttk.Checkbutton(
                self.fields_frame,
                text="この記憶を永続化する (忘れないようにする)",
                variable=self.is_permanent_memory_var,
                command=self._toggle_importance_entry
            )
            permanent_check.grid(row=1, column=1, sticky="w", pady=self.app.padding_small)

            # 重要度 (importance) の入力欄
            self.add_param_field("importance", "重要度 (1-99):", params.get("importance", "50"), start_row=2)

            # チェックボックスの状態に応じて初期表示を更新
            self._toggle_importance_entry()

        elif command_type == "change_costume":
            self.fields_frame.columnconfigure(1, weight=1)
            
            # 利用可能な衣装リストを取得
            costumes = self.editor.character_data.get_costumes()
            costume_display_names = [f"{c['name']} ({c['id']})" for c in costumes]
            
            ttk.Label(self.fields_frame, text="変更先の衣装:", font=self.app.font_normal).grid(row=0, column=0, sticky="nw")
            
            costume_combo = ttk.Combobox(self.fields_frame, values=costume_display_names, state="readonly", font=self.app.font_normal)
            costume_combo.grid(row=0, column=1, sticky="ew")
            
            # 初期値が設定されていれば、それを選択状態にする
            initial_costume_id = params.get("costume_id")
            
            # costumesは辞書のリストなので、IDで検索する
            initial_costume_info = next((c for c in costumes if c['id'] == initial_costume_id), None)
            if initial_costume_info:
                initial_display_name = f"{initial_costume_info['name']} ({initial_costume_info['id']})"
                costume_combo.set(initial_display_name)
            elif costume_display_names:
                costume_combo.set(costume_display_names[0]) # 最初の衣装をデフォルトに
            
            self.param_widgets["costume_id"] = costume_combo
        
        elif command_type == "change_persona":
            self.fields_frame.columnconfigure(1, weight=1)
            # 現在のキャラクターの基本設定値を取得
            current_first_person = self.editor.character_data.get('INFO', 'FIRST_PERSON')
            current_user_ref = self.editor.character_data.get('INFO', 'USER_REFERENCE')
            current_third_person_ref = self.editor.character_data.get('INFO', 'THIRD_PERSON_REFERENCE')

            # 各入力欄を作成。placeholderとして現在の設定値を表示
            self.add_param_field("first_person", "一人称:", params.get("first_person", ""), placeholder=f"（現在: {current_first_person}）")
            self.add_param_field("user_reference", "ユーザーの呼び方:", params.get("user_reference", ""), start_row=1, placeholder=f"（現在: {current_user_ref}）")
            self.add_param_field("third_person_reference", "他キャラの呼び方:", params.get("third_person_reference", ""), start_row=2, placeholder=f"（現在: {current_third_person_ref}）")
            
            ttk.Label(self.fields_frame, text="※空欄の項目は変更されません。", font=self.app.font_small).grid(row=3, column=1, sticky="w", pady=(self.app.padding_small, 0))

        elif command_type == "set_flag":
            self.fields_frame.columnconfigure(1, weight=1)
            self.add_param_field("flag", "フラグ名:", params.get("flag", ""))
            op_combo = ttk.Combobox(self.fields_frame, values=["=", "+", "-"], state="readonly", width=5)
            op_combo.set(params.get("operator", "="))
            ttk.Label(self.fields_frame, text="操作:").grid(row=1, column=0, sticky="w")
            op_combo.grid(row=1, column=1, sticky="w")
            self.param_widgets["operator"] = op_combo
            self.add_param_field("value", "値:", params.get("value", "1"), start_row=2)

        elif command_type == "branch_on_flag":
            self.fields_frame.columnconfigure(1, weight=1)
            ttk.Label(self.fields_frame, text="条件 (ANDで評価):").grid(row=0, column=0, columnspan=2, sticky="w")
            conditions = params.get("conditions", [])
            cond_editor = ConditionEditor(self.fields_frame, self.app, self.editor, conditions)
            cond_editor.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, self.app.padding_normal))
            self.param_widgets["conditions"] = cond_editor # インスタンスを直接保存
            
            ttk.Label(self.fields_frame, text="条件を満たした場合のジャンプ先:").grid(row=2, column=0, sticky="w")
            true_jump_combo = ttk.Combobox(self.fields_frame, values=[""] + self.existing_labels, state="readonly")
            true_jump_combo.set(params.get("jump_if_true", ""))
            true_jump_combo.grid(row=2, column=1, sticky="ew")
            self.param_widgets["jump_if_true"] = true_jump_combo

            ttk.Label(self.fields_frame, text="満たさなかった場合のジャンプ先 (任意):").grid(row=3, column=0, sticky="w")
            false_jump_combo = ttk.Combobox(self.fields_frame, values=[""] + self.existing_labels, state="readonly")
            false_jump_combo.set(params.get("jump_if_false", ""))
            false_jump_combo.grid(row=3, column=1, sticky="ew")
            self.param_widgets["jump_if_false"] = false_jump_combo

        # 最後に、コマンドの種類に応じて一番上のジャンプ先フィールドの状態を制御する
        if command_type in ('choice', 'screen_effect', 'add_long_term_memory', 'change_costume', 'set_flag', 'branch_on_flag', 'change_persona'):
            self.jump_combo.config(state='disabled')
            message = ""
            if command_type == 'choice':
                message = "(選択肢で分岐します)"
            self.jump_combo.set(message)
        else:
            # stateを'normal'ではなく'readonly'に設定
            self.jump_combo.config(state='readonly')
            # プレースホルダーテキストを削除し、純粋に値だけを設定する
            self.jump_combo.set(self.initial_data.get("jump_to", ""))

    def add_option_field(self, option_data=None, index=None):
        """選択肢の入力UIブロックを一つ追加する"""
        if len(self.option_widgets) >= 5: return
        if option_data is None: option_data = {}
        
        row_index = index if index is not None else len(self.option_widgets)
        
        # LabelFrameで各選択肢を囲む
        option_frame = ttk.LabelFrame(self.options_container, text=f"選択肢 {row_index + 1}")
        option_frame.pack(fill="x", expand=True, padx=self.app.padding_small, pady=self.app.padding_small)
        # --- グリッド設定 ---
        option_frame.columnconfigure(1, weight=1)

        # 削除ボタンをLabelFrameの右上に配置 (place() から grid() に変更)
        remove_btn = ttk.Button(option_frame, text="×", command=lambda idx=row_index: self.remove_option_field(idx), width=3)
        remove_btn.grid(row=0, column=2, sticky="ne", padx=(self.app.padding_small, 0), pady=self.app.padding_small)

        # 上段: テキストとジャンプ先
        top_row = ttk.Frame(option_frame)
        top_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=self.app.padding_small, pady=self.app.padding_small)
        top_row.columnconfigure(1, weight=1)
        top_row.columnconfigure(3, weight=1)
        
        ttk.Label(top_row, text="テキスト:", font=self.app.font_normal).grid(row=0, column=0, sticky="w")
        text_entry = ttk.Entry(top_row, font=self.app.font_normal)
        text_entry.insert(0, option_data.get("text", ""))
        text_entry.grid(row=0, column=1, sticky="ew", padx=(self.app.padding_small, self.app.padding_large))
        
        ttk.Label(top_row, text="ジャンプ先:", font=self.app.font_normal).grid(row=0, column=2, sticky="w")
        jump_options = [""] + self.existing_labels
        jump_combo = ttk.Combobox(top_row, values=jump_options, font=self.app.font_normal, state="readonly")
        jump_combo.set(option_data.get("jump_to", ""))
        jump_combo.grid(row=0, column=3, sticky="ew", padx=self.app.padding_small)

        # 下段: 表示条件
        cond_editor = ConditionEditor(option_frame, self.app, self.editor, option_data.get("conditions", []))
        cond_editor.grid(row=1, column=0, columnspan=3, sticky="ew", padx=self.app.padding_small, pady=(0, self.app.padding_small))

        # ウィジェットを辞書に保存
        widget_set = {'frame': option_frame, 'text': text_entry, 'jump_to': jump_combo, 'conditions': cond_editor, 'remove_button': remove_btn}
        
        if index is not None:
             self.option_widgets.insert(index, widget_set)
        else:
            self.option_widgets.append(widget_set)
        
        self._relabel_option_frames()

    def remove_option_field(self, index_to_remove):
        """指定されたインデックスの選択肢UIブロックを削除する"""
        if len(self.option_widgets) <= 1: return
        
        if 0 <= index_to_remove < len(self.option_widgets):
            widget_set = self.option_widgets.pop(index_to_remove)
            widget_set['frame'].destroy()
            self._relabel_option_frames()

    def _relabel_option_frames(self):
        """選択肢の番号を再採番する"""
        for i, widget_set in enumerate(self.option_widgets):
            widget_set['frame'].config(text=f"選択肢 {i + 1}")
            widget_set['remove_button'].config(command=lambda idx=i: self.remove_option_field(idx))

    def _update_display_fields(self):
        """表示タイプに応じて、表情IDセレクタかスチル画像セレクタを表示する"""
        for widget in self.display_content_frame.winfo_children(): widget.destroy()

        mode = self.display_mode_var.get()
        params = self.initial_data.get("params", {})

        if mode == "expression":
            ttk.Label(self.display_content_frame, text="表情ID:", font=self.app.font_normal).grid(row=0, column=0, sticky="nw")
            costume_id = self.editor.current_costume_id.get()
            expressions = self.editor.character_data.get_expressions_for_costume(costume_id)
            expression_ids = [expr['id'] for expr in expressions]
            emotion_combo = ttk.Combobox(self.display_content_frame, values=expression_ids, state="readonly", font=self.app.font_normal)
            current_emotion = params.get("emotion", "normal")
            if current_emotion in expression_ids: emotion_combo.set(current_emotion)
            elif expression_ids: emotion_combo.set(expression_ids[0])
            emotion_combo.grid(row=0, column=1, sticky="ew")
            self.param_widgets["emotion"] = emotion_combo
        
        elif mode == "still":
            # --- スチル編集用のUIを再構築 ---
            # グリッド設定
            self.display_content_frame.columnconfigure(0, weight=2) # 設定エリア
            self.display_content_frame.columnconfigure(1, weight=3) # プレビューエリア
            self.display_content_frame.rowconfigure(0, weight=1)

            # --- 左側: 設定エリア ---
            settings_area = ttk.Frame(self.display_content_frame)
            settings_area.grid(row=0, column=0, sticky="nsew", padx=(0, self.app.padding_large))
            settings_area.columnconfigure(1, weight=1)

            # 1. スチル画像ファイル
            ttk.Label(settings_area, text="スチル画像 (D&D可):", font=self.app.font_normal).grid(row=0, column=0, sticky="w")
            still_entry_frame = ttk.Frame(settings_area)
            still_entry_frame.grid(row=0, column=1, sticky="ew", pady=(0, self.app.padding_normal))
            still_entry_frame.columnconfigure(0, weight=1)

            still_entry = ttk.Entry(still_entry_frame, font=self.app.font_normal)
            still_entry.insert(0, params.get("still_image", ""))
            still_entry.config(state="readonly") 

            still_entry.grid(row=0, column=0, sticky="ew", padx=(0, self.app.padding_small))

            # D&Dの受付設定
            still_entry.drop_target_register(DND_FILES)
            still_entry.dnd_bind('<<Drop>>', self._on_still_image_drop)

            browse_button = ttk.Button(still_entry_frame, text="参照...", command=self._browse_for_still)
            browse_button.grid(row=0, column=1, sticky="w")
            self.param_widgets["still_image"] = still_entry

            # 2. 透過色
            ttk.Label(settings_area, text="透過色:", font=self.app.font_normal).grid(row=1, column=0, sticky="w", pady=(0, self.app.padding_small))
            trans_color_frame = ttk.Frame(settings_area)
            trans_color_frame.grid(row=1, column=1, sticky="w", pady=(0, self.app.padding_small))
            
            trans_color_preview = tk.Label(trans_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
            trans_color_preview.config(background=params.get("transparent_color", self.editor.character_data.get('INFO', 'TRANSPARENT_COLOR', '#ff00ff')))
            trans_color_preview.pack(side="left", padx=(0, self.app.padding_small))
            ttk.Button(trans_color_frame, text="選択", command=lambda p=trans_color_preview: self.editor.pick_color(p)).pack(side="left")
            ttk.Button(trans_color_frame, text="取得", command=lambda p=trans_color_preview: self._enter_eyedropper_for_still(p)).pack(side="left", padx=self.app.padding_small)
            self.param_widgets["transparent_color"] = trans_color_preview

            # 3. 縁色
            ttk.Label(settings_area, text="縁色:", font=self.app.font_normal).grid(row=2, column=0, sticky="w")
            edge_color_frame = ttk.Frame(settings_area)
            edge_color_frame.grid(row=2, column=1, sticky="w")

            edge_color_preview = tk.Label(edge_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
            edge_color_preview.config(background=params.get("edge_color", self.editor.character_data.get('INFO', 'EDGE_COLOR', '#838383')))
            edge_color_preview.pack(side="left", padx=(0, self.app.padding_small))
            ttk.Button(edge_color_frame, text="選択", command=lambda p=edge_color_preview: self.editor.pick_color(p)).pack(side="left")
            ttk.Button(edge_color_frame, text="取得", command=lambda p=edge_color_preview: self._enter_eyedropper_for_still(p)).pack(side="left", padx=self.app.padding_small)
            self.param_widgets["edge_color"] = edge_color_preview

            # --- 右側: プレビューエリア ---
            preview_area = ttk.Frame(self.display_content_frame, relief="solid", borderwidth=1)
            preview_area.grid(row=0, column=1, rowspan=3, sticky="nsew")
            preview_area.rowconfigure(0, weight=1)
            preview_area.columnconfigure(0, weight=1)

            self.still_preview_canvas = tk.Canvas(preview_area, bg="white", highlightthickness=0)
            self.still_preview_canvas.grid(row=0, column=0, sticky="nsew")
            
            # D&Dの受付設定をCanvasにも追加
            self.still_preview_canvas.drop_target_register(DND_FILES)
            self.still_preview_canvas.dnd_bind('<<Drop>>', self._on_still_image_drop)

            # 初期プレビュー画像の読み込みと表示
            self._update_still_preview()

    def _on_still_image_drop(self, event):
        """スチル画像Entryにファイルがドロップされたときの処理"""
        # ドロップされたファイルパスの生データを取得し、波括弧などを除去
        filepath = self.tk.splitlist(event.data)[0]
        
        # ファイル形式をチェック
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            messagebox.showwarning("ファイル形式エラー", "PNG, JPG, BMP形式の画像ファイルをドロップしてください。", parent=self)
            return
            
        # _browse_for_still と同様のロジックで画像を処理・設定する
        filename = os.path.basename(filepath)
        stills_dir = os.path.join(self.editor.character_data.base_path, "stills")
        destination_path = os.path.join(stills_dir, filename)

        try:
            if not os.path.exists(destination_path):
                shutil.copy2(filepath, destination_path)
                print(f"スチル画像をプロジェクトにコピーしました: {destination_path}")
            
            if "still_image" in self.param_widgets:
                entry = self.param_widgets["still_image"]
                entry.config(state="normal")
                entry.delete(0, tk.END)
                entry.insert(0, filename)
                entry.config(state="readonly")
                self._update_still_preview() # プレビューを更新

        except Exception as e:
            messagebox.showerror("エラー", f"画像のコピーまたは設定に失敗しました:\n{e}", parent=self)

    def _browse_for_still(self):
        """イベントスチル用の画像ファイルを選択するダイアログを開く"""
        filepath = filedialog.askopenfilename(
            title="イベントスチル画像を選択",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
            parent=self
        )
        if not filepath: return

        filename = os.path.basename(filepath)
        stills_dir = os.path.join(self.editor.character_data.base_path, "stills")
        destination_path = os.path.join(stills_dir, filename)

        try:
            # まだstillsフォルダにコピーされていなければコピーする
            if not os.path.exists(destination_path):
                shutil.copy2(filepath, destination_path)
                print(f"スチル画像をプロジェクトにコピーしました: {destination_path}")
            
            # Entryウィジェットにファイル名を設定
            if "still_image" in self.param_widgets:
                entry = self.param_widgets["still_image"]
                entry.config(state="normal")
                entry.delete(0, tk.END)
                entry.insert(0, filename)
                entry.config(state="readonly")
                self._update_still_preview()
        except Exception as e:
            messagebox.showerror("エラー", f"画像のコピーに失敗しました:\n{e}", parent=self)

    def _update_still_preview(self):
        """スチル画像のプレビューを更新するヘルパーメソッド"""
        if "still_image" not in self.param_widgets: return
        
        filename = self.param_widgets["still_image"].get()
        if not filename:
            self.still_preview_canvas.delete("all")
            return
            
        filepath = os.path.join(self.editor.character_data.stills_dir, filename)
        if not os.path.exists(filepath):
            self.still_preview_canvas.delete("all")
            return
        
        # EditorWindowの画像表示ロジックを借用
        try:
            self.original_still_pil_image = Image.open(filepath).convert("RGBA")
            
            # Canvasのサイズに合わせてリサイズ
            canvas_w = self.still_preview_canvas.winfo_width()
            canvas_h = self.still_preview_canvas.winfo_height()
            if canvas_w < 10 or canvas_h < 10: # UI描画前は待機
                self.after(50, self._update_still_preview)
                return

            img_copy = self.original_still_pil_image.copy()
            img_copy.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            
            # PhotoImageに変換して保持 (ガベージコレクション対策)
            self.still_preview_tk_image = ImageTk.PhotoImage(img_copy)
            
            self.still_preview_canvas.delete("all")
            x_pos = (canvas_w - self.still_preview_tk_image.width()) / 2
            y_pos = (canvas_h - self.still_preview_tk_image.height()) / 2
            self.still_preview_canvas.create_image(x_pos, y_pos, image=self.still_preview_tk_image, anchor="nw")
            
        except Exception as e:
            print(f"スチルプレビューの更新エラー: {e}")
            self.still_preview_canvas.delete("all")
            self.original_still_pil_image = None

    def _enter_eyedropper_for_still(self, target_label):
        """スチルプレビューに対してスポイトモードを開始する"""
        if "still_image" not in self.param_widgets or not self.param_widgets["still_image"].get():
            messagebox.showwarning("エラー", "色を取得するためのスチル画像が設定されていません。", parent=self)
            return
            
        # EditorWindowのスポイト機能を呼び出す
        # どのCanvasとどの画像を使うかを明確に指定する
        self.editor.enter_eyedropper_mode(
            target_label=target_label,
            target_canvas=self.still_preview_canvas,
            pil_image=getattr(self, 'original_still_pil_image', None),
            tk_image=getattr(self, 'still_preview_tk_image', None) # tk_imageを渡す
        )

    def _toggle_importance_entry(self):
        """永続化チェックボックスに応じて重要度入力欄の状態を切り替える。"""
        if "importance" in self.param_widgets:
            entry = self.param_widgets["importance"]
            if self.is_permanent_memory_var.get():
                entry.delete(0, tk.END)
                entry.insert(0, "100")
                entry.config(state="readonly")
            else:
                entry.config(state="normal")
                # 永続化を解除した場合、デフォルト値に戻すか、前の値を復元するかは設計による
                # ここではシンプルに50に戻す
                if entry.get() == "100":
                    entry.delete(0, tk.END)
                    entry.insert(0, "50")

    def _create_screen_effect_ui(self, params):
        container = self.fields_frame
        container.columnconfigure(1, weight=1)

        self.effect_type_var.set(params.get("effect", "fade_out"))
        self.method_var.set(params.get("method", "fade"))
        self.wait_var.set(params.get("wait_for_completion", True))
        
        effect_frame = ttk.Frame(container)
        effect_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, self.app.padding_normal))
        ttk.Label(effect_frame, text="効果:", font=self.app.font_normal).pack(side="left")
        ttk.Radiobutton(effect_frame, text="画面を覆う (フェードアウト)", variable=self.effect_type_var, value="fade_out", command=self._update_screen_effect_ui_state).pack(side="left", padx=self.app.padding_small)
        ttk.Radiobutton(effect_frame, text="覆いを解除 (フェードイン)", variable=self.effect_type_var, value="fade_in", command=self._update_screen_effect_ui_state).pack(side="left")

        self.color_label = ttk.Label(container, text="色:", font=self.app.font_normal)
        self.color_label.grid(row=1, column=0, sticky="w")
        color_frame = ttk.Frame(container)
        color_frame.grid(row=1, column=1, sticky="w", pady=(0, self.app.padding_normal))
        
        color_preview = tk.Label(color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
        color_preview.config(background=params.get("color", "#000000"))
        color_preview.pack(side="left")
        self.param_widgets["color"] = color_preview

        self.color_button = ttk.Button(color_frame, text="選択...", command=lambda p=color_preview: self.editor.pick_color(p))
        self.color_button.pack(side="left", padx=self.app.padding_small)

        method_frame = ttk.Frame(container)
        method_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, self.app.padding_normal))
        ttk.Label(method_frame, text="方法:", font=self.app.font_normal).pack(side="left")
        ttk.Radiobutton(method_frame, text="フェード", variable=self.method_var, value="fade", command=self._update_screen_effect_ui_state).pack(side="left", padx=self.app.padding_small)
        ttk.Radiobutton(method_frame, text="一瞬", variable=self.method_var, value="instant", command=self._update_screen_effect_ui_state).pack(side="left")

        self.duration_label = ttk.Label(container, text="時間 (秒):", font=self.app.font_normal)
        self.duration_label.grid(row=3, column=0, sticky="w")
        duration_entry = ttk.Entry(container, width=10)
        duration_entry.insert(0, str(params.get("duration", 1.0)))
        duration_entry.grid(row=3, column=1, sticky="w", pady=(0, self.app.padding_normal))
        self.param_widgets["duration"] = duration_entry

        wait_check = ttk.Checkbutton(container, text="完了を待つ (次のコマンドへ進むのを待機する)", variable=self.wait_var)
        wait_check.grid(row=4, column=0, columnspan=2, sticky="w")
        self.param_widgets["wait_for_completion"] = self.wait_var
        
        self._update_screen_effect_ui_state()

    def _update_screen_effect_ui_state(self):
        is_fade_out = self.effect_type_var.get() == "fade_out"
        is_fade_method = self.method_var.get() == "fade"

        color_state = "normal" if is_fade_out else "disabled"
        self.color_label.config(state=color_state)
        if "color" in self.param_widgets:
            self.color_button.config(state=color_state)
        
        duration_state = "normal" if is_fade_method else "disabled"
        self.duration_label.config(state=duration_state)
        if "duration" in self.param_widgets:
            self.param_widgets["duration"].config(state=duration_state)

    def add_param_field(self, key, label, default_value, as_text=False, start_row=None, parent_frame=None, placeholder=None):
        parent = parent_frame if parent_frame is not None else self.fields_frame
        
        row = start_row if start_row is not None else len(self.param_widgets)
        ttk.Label(parent, text=label, font=self.app.font_normal).grid(row=row, column=0, sticky="w")
        
        if as_text:
            widget = tk.Text(parent, height=3, font=self.app.font_normal)
            widget.insert("1.0", default_value)
            
            # Textウィジェットにフォーカスが当たった時の処理
            def on_focus_in(event):
                # self.bind('<Return>', ...) で設定されたダイアログのデフォルト動作を一時的に解除
                self.unbind('<Return>')
            
            # Textウィジェットからフォーカスが外れた時の処理
            def on_focus_out(event):
                # 解除していたデフォルト動作を元に戻す
                # self.ok は simpledialog.Dialog が持つメソッド
                self.bind('<Return>', lambda e: self.ok())

            widget.bind("<FocusIn>", on_focus_in)
            widget.bind("<FocusOut>", on_focus_out)
            
        else:
            widget = ttk.Entry(parent, font=self.app.font_normal)
            widget.insert(0, default_value) # Entry作成後に値を挿入
        
        widget.grid(row=row, column=1, sticky="ew")
        self.param_widgets[key] = widget

        if placeholder:
            ttk.Label(parent, text=placeholder, font=self.app.font_small, foreground="gray").grid(row=row, column=2, sticky="w", padx=self.app.padding_small)
    
    def apply(self):
        # 表示名から内部名に変換
        selected_display_name = self.command_type_var.get()
        command_type = self.COMMAND_VALUE_MAP.get(selected_display_name)
        if not command_type:
            # 万が一変換に失敗した場合は何もしない
            self.result = None
            return
        params = {}
        if command_type in ("dialogue", "monologue"):
            if 'text' in self.param_widgets:
                params['text'] = self.param_widgets['text'].get("1.0", "end-1c")
            
            if self.display_mode_var.get() == "expression":
                if 'emotion' in self.param_widgets:
                    params['emotion'] = self.param_widgets['emotion'].get()

            elif self.display_mode_var.get() == "still":
                if 'still_image' in self.param_widgets:
                    params['still_image'] = self.param_widgets['still_image'].get()

                # 色情報を収集
                char_default_trans = self.editor.character_data.get('INFO', 'TRANSPARENT_COLOR', '#ff00ff')
                char_default_edge = self.editor.character_data.get('INFO', 'EDGE_COLOR', '#838383')
                
                if 'transparent_color' in self.param_widgets:
                    trans_color = self.param_widgets['transparent_color'].cget("background")
                    # キャラクターのデフォルト色と異なる場合のみ保存する
                    if trans_color.lower() != char_default_trans.lower():
                        params['transparent_color'] = trans_color

                if 'edge_color' in self.param_widgets:
                    edge_color = self.param_widgets['edge_color'].cget("background")
                    # キャラクターのデフォルト色と異なる場合のみ保存する
                    if edge_color.lower() != char_default_edge.lower():
                        params['edge_color'] = edge_color

        elif command_type == "choice":
            final_params = {"prompt": self.param_widgets.get("prompt", tk.Text()).get("1.0", "end-1c"), "options": []}
            for option_set in self.option_widgets:
                text = option_set['text'].get().strip()
                jump_to = option_set['jump_to'].get().strip()
                conditions = option_set['conditions'].get_conditions()
                if text: 
                    option_data = {"text": text, "jump_to": jump_to}
                    if conditions: option_data["conditions"] = conditions
                    final_params["options"].append(option_data)
            params = final_params
        
        elif command_type == "screen_effect":
            params = {
                "effect": self.effect_type_var.get(),
                "method": self.method_var.get(),
                "wait_for_completion": self.wait_var.get()
            }
            if params["effect"] == "fade_out":
                params["color"] = self.param_widgets["color"].cget("background")
            if params["method"] == "fade":
                try:
                    params["duration"] = float(self.param_widgets["duration"].get())
                except (ValueError, KeyError):
                    params["duration"] = 1.0

        elif command_type == "add_long_term_memory":
            params['summary'] = self.param_widgets.get('summary', tk.Text()).get("1.0", "end-1c").strip()
            if self.is_permanent_memory_var.get():
                params['importance'] = "100"
            else:
                importance_val = self.param_widgets.get('importance', tk.Entry()).get().strip()
                if importance_val.isdigit() and 1 <= int(importance_val) <= 99:
                    params['importance'] = importance_val
                else:
                    params['importance'] = "50"
        
        elif command_type == "change_costume":
            selected_display_name = self.param_widgets.get('costume_id', ttk.Combobox()).get()
            # "衣装名 (衣装ID)" の形式から正規表現でID部分を抽出
            import re
            match = re.search(r'\((\w+)\)$', selected_display_name)
            if match:
                params['costume_id'] = match.group(1)
        
        elif command_type == "change_persona":
            # 空でない項目のみを辞書に追加する
            persona_params = {
                "first_person": self.param_widgets["first_person"].get().strip(),
                "user_reference": self.param_widgets["user_reference"].get().strip(),
                "third_person_reference": self.param_widgets["third_person_reference"].get().strip()
            }
            params = {k: v for k, v in persona_params.items() if v}

        elif command_type == "branch_on_flag":
            params["conditions"] = self.param_widgets["conditions"].get_conditions()
            params["jump_if_true"] = self.param_widgets["jump_if_true"].get()
            params["jump_if_false"] = self.param_widgets["jump_if_false"].get()
        
        else: # set_favorability, set_flag などのシンプルなコマンド
            for key, widget in self.param_widgets.items():
                if hasattr(widget, 'get'):
                    params[key] = widget.get()

        self.result = {"type": command_type, "params": params}
        
        label_text = self.label_entry.get().strip()
        if label_text: self.result["label"] = label_text

        jump_text = self.jump_combo.get().strip()
        # ジャンプ先が無効化されていない場合のみ値を保存
        if self.jump_combo.cget("state") != "disabled" and jump_text:
            self.result["jump_to"] = jump_text

# --- メインのタブクラス ---
class TabEvents(TabBase):
    def __init__(self, parent, editor_instance):
        # ダイアログが開いているかを管理するフラグ
        self.is_dialog_open = False
        super().__init__(parent, editor_instance)

    def create_widgets(self):
        parent = self.scrollable_frame
        self.paned_window = ttk.PanedWindow(parent, orient='horizontal')
        self.paned_window.pack(expand=True, fill='both')

        # 左ペイン: イベントリスト
        left_pane = ttk.Frame(self.paned_window, padding=self.app.padding_normal)
        self.paned_window.add(left_pane, weight=1)
        left_pane.rowconfigure(1, weight=1); left_pane.columnconfigure(0, weight=1)
        
        event_buttons = ttk.Frame(left_pane)
        event_buttons.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        ttk.Button(event_buttons, text="イベント追加", command=self.add_event).pack(side="left")
        ttk.Button(event_buttons, text="編集", command=self.edit_event).pack(side="left", padx=self.app.padding_small)
        ttk.Button(event_buttons, text="削除", command=self.delete_event).pack(side="left")

        self.event_listbox = tk.Listbox(left_pane, font=self.app.font_normal)
        self.event_listbox.grid(row=1, column=0, sticky="nsew")
        self.event_listbox.bind("<<ListboxSelect>>", self.on_event_select)

        # 右ペイン: イベントエディタ
        right_pane = ttk.Frame(self.paned_window, padding=self.app.padding_normal)
        self.paned_window.add(right_pane, weight=3)
        right_pane.rowconfigure(1, weight=1); right_pane.columnconfigure(0, weight=1)
        
        # イベントプロパティフレーム
        self.properties_frame = ttk.LabelFrame(right_pane, text="イベントプロパティ", padding=self.app.padding_normal)
        self.properties_frame.grid(row=0, column=0, sticky="ew")
        self.event_prop_labels = {}
        # ラベル名を修正
        for i, (key, text) in enumerate([("id", "ID:"), ("name", "名前:"), ("triggers", "発生条件:"), ("repeat", "繰り返し:")]):
            ttk.Label(self.properties_frame, text=text, font=self.app.font_normal).grid(row=i, column=0, sticky="w")
            label = ttk.Label(self.properties_frame, text="-", font=self.app.font_normal, wraplength=400, justify="left")
            label.grid(row=i, column=1, sticky="w")
            self.event_prop_labels[key] = label

        # シーケンスフレーム
        sequence_frame = ttk.LabelFrame(right_pane, text="イベントシーケンス", padding=self.app.padding_normal)
        sequence_frame.grid(row=1, column=0, sticky="nsew", pady=(self.app.padding_normal, 0))
        sequence_frame.rowconfigure(1, weight=1); sequence_frame.columnconfigure(0, weight=1)

        command_buttons = ttk.Frame(sequence_frame)
        command_buttons.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        ttk.Button(command_buttons, text="コマンド追加", command=self.add_command).pack(side="left")
        ttk.Button(command_buttons, text="編集", command=self.edit_command).pack(side="left", padx=self.app.padding_small)
        ttk.Button(command_buttons, text="削除", command=self.delete_command).pack(side="left")
        ttk.Button(command_buttons, text="↑ 上へ", command=lambda: self._move_command(-1)).pack(side="left", padx=(self.app.padding_large, self.app.padding_small))
        ttk.Button(command_buttons, text="↓ 下へ", command=lambda: self._move_command(1)).pack(side="left")

        self.sequence_tree = ttk.Treeview(sequence_frame, columns=("type", "params", "label", "jump_to"), show="headings tree")
        self.sequence_tree.heading("#0", text="順序/選択肢")
        self.sequence_tree.heading("type", text="種類")
        self.sequence_tree.heading("params", text="パラメータ")
        self.sequence_tree.heading("label", text="ラベル")
        self.sequence_tree.heading("jump_to", text="ジャンプ先")
        self.sequence_tree.column("#0", width=120)
        self.sequence_tree.column("type", width=100)
        self.sequence_tree.column("params", width=250)
        self.sequence_tree.column("label", width=100)
        self.sequence_tree.column("jump_to", width=100)
        self.sequence_tree.grid(row=1, column=0, sticky="nsew")

    def load_data(self):
        self.event_listbox.delete(0, tk.END)
        for event_id in self.character_data.get_event_ids():
            self.event_listbox.insert(tk.END, event_id)
        self.clear_editor()

    def on_event_select(self, event=None):
        if self.is_dialog_open:
            return
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        event_id = self.event_listbox.get(selected_indices[0])
        event_data = self.character_data.load_event(event_id)
        if not event_data:
            messagebox.showerror("エラー", f"イベント '{event_id}' の読み込みに失敗しました。", parent=self)
            return

        # プロパティ表示を更新
        self.event_prop_labels["id"].config(text=event_data.get("id", "-"))
        self.event_prop_labels["name"].config(text=event_data.get("name", "-"))
        
        # 新しいtriggers形式の表示ロジック
        triggers = event_data.get("triggers", [])
        if not triggers or not any(triggers):
            trigger_text = "なし"
        else:
            group_texts = []
            for group in triggers:
                cond_texts = [self._format_condition(c) for c in group]
                group_texts.append("(" + " かつ ".join(cond_texts) + ")")
            trigger_text = " または ".join(group_texts)

        self.event_prop_labels["triggers"].config(text=trigger_text)
        
        repeat_text = f"{event_data.get('repeatable', False)} (クールダウン: {event_data.get('cooldown', '-')})"
        self.event_prop_labels["repeat"].config(text=repeat_text)

        # シーケンス表示を更新
        self.sequence_tree.delete(*self.sequence_tree.get_children())
        COMMAND_DISPLAY_MAP = CommandDialog.COMMAND_DISPLAY_MAP
        
        for i, command in enumerate(event_data.get("sequence", [])):
            params = command.get("params", {})
            params_str = ""
            
            # command.get("type")から表示名を取得
            command_type_internal = command.get("type")
            command_type_display = COMMAND_DISPLAY_MAP.get(command_type_internal, command_type_internal)

            # パラメータの要約表示ロジック (少し調整)
            if command_type_internal in ("dialogue", "monologue"):
                text = params.get("text", "")
                if len(text) > 50: text = text[:47] + "..."
                if "still_image" in params:
                    params_str = f"スチル: {params['still_image']}, 「{text}」"
                else:
                    params_str = f"表情: {params.get('emotion', 'normal')}, 「{text}」"
            elif command_type_internal == "screen_effect":
                effect = "覆う" if params.get("effect") == "fade_out" else "解除"
                color = params.get("color", "")
                method = "フェード" if params.get("method") == "fade" else "一瞬"
                duration = f"{params.get('duration', 0)}s" if method == "フェード" else ""
                wait = "待つ" if params.get("wait_for_completion", False) else "待たない"
                parts = [effect]
                if color: parts.append(color)
                parts.append(method)
                if duration: parts.append(duration)
                parts.append(f"完了を{wait}")
                params_str = ", ".join(parts)
            elif command_type_internal == "change_persona":
                parts = []
                if "first_person" in params: parts.append(f"一人称→'{params['first_person']}'")
                if "user_reference" in params: parts.append(f"ユーザー→'{params['user_reference']}'")
                if "third_person_reference" in params: parts.append(f"他キャラ→'{params['third_person_reference']}'")
                params_str = ", ".join(parts)
            else:
                params_str = str(params)
                if len(params_str) > 100: params_str = params_str[:97] + "..."
            
            label = command.get("label", "")
            jump_to = command.get("jump_to", "")

            node = self.sequence_tree.insert("", "end", text=f"Step {i+1}", values=(command_type_display, params_str, label, jump_to))
            
            if command_type_internal == "choice":
                for j, option in enumerate(params.get("options", [])):
                    option_jump = option.get('jump_to','')
                    self.sequence_tree.insert(node, "end", text=f"  └ 選択肢 {j+1}", values=("option", f"「{option.get('text','')}」", "", f"-> {option_jump}"))

    def _format_condition(self, cond):
        """条件辞書を人間が読める文字列にフォーマットするヘルパー"""
        cond_type = cond.get("type")
        if cond_type == "favorability_above": return f"好感度≧{cond.get('value')}"
        if cond_type == "favorability_below": return f"好感度≦{cond.get('value')}"
        if cond_type == "flag_equals": return f"フラグ'{cond.get('flag')}' == {cond.get('value')}"
        if cond_type == "flag_not_equals": return f"フラグ'{cond.get('flag')}' != {cond.get('value')}"
        if cond_type == "flag_above": return f"フラグ'{cond.get('flag')}' > {cond.get('value')}"
        if cond_type == "flag_below": return f"フラグ'{cond.get('flag')}' < {cond.get('value')}"
        if cond_type == "flag_exists": return f"フラグ'{cond.get('flag')}'が存在"
        if cond_type == "flag_not_exists": return f"フラグ'{cond.get('flag')}'が不在"
        if cond_type == "event_completed": return f"イベント'{cond.get('event_id')}'完了済"
        if cond_type == "event_completed_after": return f"イベント'{cond.get('event_id')}'完了から{cond.get('duration')}経過"
        if cond_type == "date_equals": return f"日付=={cond.get('date')}"
        if cond_type == "date_after": return f"日付≧{cond.get('date')}"
        if cond_type == "date_before": return f"日付≦{cond.get('date')}"
        if cond_type == "time_equals": return f"時刻=={cond.get('time')}"
        if cond_type == "time_after": return f"時刻≧{cond.get('time')}"
        if cond_type == "time_before": return f"時刻≦{cond.get('time')}"
        return "不明な条件"

    def clear_editor(self):
        for label in self.event_prop_labels.values(): label.config(text="-")
        self.sequence_tree.delete(*self.sequence_tree.get_children())
        
    def add_event(self):
        self.is_dialog_open = True
        # EventDialogにeditor_instanceを渡す
        dialog = EventDialog(self, "新規イベント作成", editor_instance=self.editor)
        self.is_dialog_open = False
        if dialog.result:
            event_id = dialog.result["id"]
            if event_id in self.character_data.get_event_ids():
                messagebox.showerror("エラー", f"イベントID '{event_id}' は既に使用されています。", parent=self)
                return
            
            event_data = {**dialog.result, "sequence": []}
            self.character_data.save_event(event_id, event_data)
            self.load_data()
    
    def edit_event(self):
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        old_event_id = self.event_listbox.get(selected_indices[0])
        event_data = self.character_data.load_event(old_event_id)
        if not event_data: return

        self.is_dialog_open = True
        
        if "trigger" in event_data and "triggers" not in event_data:
            print("古いtrigger形式を検出。新しいtriggers形式に変換します。")
            trigger_data = event_data.get("trigger", {})
            # 単一の条件を、単一の条件グループにラップしてリストにする
            # 例: {"type": "favorability_above", "value": "100"} -> [[{"type": "favorability_above", "value": "100"}]]
            event_data["triggers"] = [[trigger_data]] if trigger_data.get("type") != "none" else []

        dialog = EventDialog(self, "イベントの編集",
            editor_instance=self.editor,
            event_id=event_data.get("id", ""), 
            event_name=event_data.get("name", ""),
            triggers=event_data.get("triggers", []),
            repeatable=event_data.get("repeatable", False),
            cooldown=event_data.get("cooldown", "24h"),
            id_editable=True
        )
        self.is_dialog_open = False
        if dialog.result:
            new_event_id = dialog.result["id"]
            # IDが変更されたかチェック
            if old_event_id != new_event_id:
                if new_event_id in self.character_data.get_event_ids():
                    messagebox.showerror("エラー", f"イベントID '{new_event_id}' は既に使用されています。", parent=self); return
                self.character_data.rename_event(old_event_id, new_event_id)
            
            # 既存のシーケンスを保持して保存
            updated_data = {**dialog.result, "sequence": event_data.get("sequence", [])}
            self.character_data.save_event(new_event_id, updated_data)
            self.load_data()

    def delete_event(self):
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        event_id = self.event_listbox.get(selected_indices[0])
        if messagebox.askyesno("確認", f"本当にイベント '{event_id}' を削除しますか？", parent=self):
            self.character_data.delete_event(event_id)
            self.load_data()

    def add_command(self):
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        
        selected_index = selected_indices[0]
        event_id = self.event_listbox.get(selected_index)
        event_data = self.character_data.load_event(event_id)
        if not event_data: return
        
        # ダイアログに渡すための既存ラベルリストを作成
        existing_labels = [cmd.get("label") for cmd in event_data.get("sequence", []) if cmd.get("label")]

        self.is_dialog_open = True
        dialog = CommandDialog(self, "コマンド追加", editor_instance=self.editor, existing_labels=existing_labels)
        self.is_dialog_open = False

        if dialog.result:
            event_data.setdefault("sequence", []).append(dialog.result)
            self.character_data.save_event(event_id, event_data)
            self.after(20, lambda: self._restore_selection_and_refresh(selected_index))

    def edit_command(self):
        selected_item = self.sequence_tree.focus()
        if not selected_item or self.sequence_tree.parent(selected_item):
            messagebox.showwarning("警告", "編集するコマンド（Step）を選択してください。", parent=self); return
        
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return

        selected_index = selected_indices[0]
        event_id = self.event_listbox.get(selected_index)
        event_data = self.character_data.load_event(event_id)
        if not event_data: return
        
        command_index = self.sequence_tree.index(selected_item)
        command_to_edit = event_data.get("sequence", [])[command_index]

        # 編集対象自身のラベルはジャンプ先候補から除外する
        existing_labels = [
            cmd.get("label") for i, cmd in enumerate(event_data.get("sequence", []))
            if cmd.get("label") and i != command_index
        ]
        
        self.is_dialog_open = True
        dialog = CommandDialog(self, "コマンド編集", command_data=command_to_edit, editor_instance=self.editor, existing_labels=existing_labels)
        self.is_dialog_open = False

        if dialog.result:
            event_data["sequence"][command_index] = dialog.result
            self.character_data.save_event(event_id, event_data)
            self.after(20, lambda: self._restore_selection_and_refresh(selected_index))

    def delete_command(self):
        selected_item = self.sequence_tree.focus()
        if not selected_item or self.sequence_tree.parent(selected_item):
            messagebox.showwarning("警告", "削除するコマンド（Step）を選択してください。", parent=self); return

        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        event_id = self.event_listbox.get(selected_indices[0])
        event_data = self.character_data.load_event(event_id)
        if not event_data: return

        command_index = self.sequence_tree.index(selected_item)
        del event_data["sequence"][command_index]
        self.character_data.save_event(event_id, event_data)
        self.on_event_select()

    def _move_command(self, direction: int):
        """選択したコマンドを上または下に移動させる"""
        selected_item = self.sequence_tree.focus()
        # Step以外の項目（選択肢など）は移動させない
        if not selected_item or self.sequence_tree.parent(selected_item):
            messagebox.showwarning("警告", "移動するコマンド（Step）を選択してください。", parent=self)
            return

        # イベントデータを取得
        selected_indices = self.event_listbox.curselection()
        if not selected_indices: return
        event_id = self.event_listbox.get(selected_indices[0])
        event_data = self.character_data.load_event(event_id)
        if not event_data: return
        
        sequence = event_data.get("sequence", [])
        current_index = self.sequence_tree.index(selected_item)
        
        # 移動先インデックスを計算
        new_index = current_index + direction

        # 境界チェック (リストの範囲外に移動しようとしていないか)
        if not (0 <= new_index < len(sequence)):
            return

        # 1. データ（リスト）の要素を入れ替え
        sequence[current_index], sequence[new_index] = sequence[new_index], sequence[current_index]
        
        # 2. 変更したデータをファイルに保存
        self.character_data.save_event(event_id, event_data)

        # 3. Treeviewの表示を更新
        self.on_event_select()

        # 4. 移動後の項目が選択された状態を維持する
        #    UIの更新を確実にするため、afterで少し遅延させる
        def reselect_item():
            # on_event_selectでTreeviewが再構築された後、新しいIDを取得する
            all_items = self.sequence_tree.get_children("")
            if 0 <= new_index < len(all_items):
                item_to_select = all_items[new_index]
                self.sequence_tree.selection_set(item_to_select)
                self.sequence_tree.focus(item_to_select)
        
        self.after(20, reselect_item)

    def _restore_selection_and_refresh(self, index_to_select):
        """
        指定されたインデックスを選択状態にしてから、UIの更新をトリガーするヘルパーメソッド。
        """
        # 現在の選択をクリア
        self.event_listbox.selection_clear(0, tk.END)
        # 記憶しておいたインデックスを再度選択
        self.event_listbox.selection_set(index_to_select)
        # 選択状態をUIに反映させるためにイベントを発生させる
        self.event_listbox.event_generate("<<ListboxSelect>>")

    def collect_data(self):
        # このタブはリストやツリーの操作時に直接ファイルに保存するため、
        # メインの保存ボタンでの一括処理は不要
        pass
