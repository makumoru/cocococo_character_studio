# src/tabs/tab_basic_settings.py

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .tab_base import TabBase
from ..ui_components import CharacterCountLabel

class TopicDialog(simpledialog.Dialog):
    """専用話題を追加・編集するためのダイアログ"""
    def __init__(self, parent, title, initial_value=""):
        self.app = parent.app
        self.initial_value = initial_value
        super().__init__(parent, title)

    def body(self, master):
        self.topic_text = tk.Text(master, font=self.app.font_normal, height=3, width=50, relief="solid", bd=1, wrap="word")
        self.topic_text.pack(padx=self.app.padding_normal, pady=self.app.padding_normal)
        self.topic_text.insert("1.0", self.initial_value)
        
        # 文字数カウンターを追加
        CharacterCountLabel(master, self.topic_text, max_length=100, font=self.app.font_small).pack(anchor="e", padx=self.app.padding_normal)
        
        return self.topic_text

    def apply(self):
        # 末尾の改行を除去
        self.result = self.topic_text.get("1.0", "end-1c").strip()

    def validate(self):
        content = self.topic_text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("入力エラー", "話題を入力してください。", parent=self)
            return 0
        if len(content) > 100:
            messagebox.showwarning("入力エラー", "話題は100文字以内で入力してください。", parent=self)
            return 0
        return 1

class TabBasicSettings(TabBase):
    """
    「基本設定」タブのUIとロジックを管理するクラス。
    """
    def create_widgets(self):
        # 親フレームを scrollable_frame に設定
        parent = self.scrollable_frame
        parent.columnconfigure(1, weight=1)

        # 行の伸縮設定を更新
        parent.rowconfigure(5, weight=1) # 性格設定
        parent.rowconfigure(12, weight=1) # 専用話題
        parent.rowconfigure(14, weight=1) # システムメッセージ設定

        style = ttk.Style(self)
        style.configure("Tab.TLabel", font=self.app.font_normal)
        style.configure("Tab.TButton", font=self.app.font_normal, padding=self.app.padding_small)
        style.configure("TLabelFrame.Label", font=self.app.font_normal)
        style.configure("Fav.Treeview", rowheight=int(self.app.base_font_size * 1.8))

        # ウィジェット間のパディング
        pady = self.app.padding_small
        padx = self.app.padding_small

        # 基本情報
        ttk.Label(parent, text="キャラクター名:", style="Tab.TLabel").grid(row=0, column=0, sticky="w", pady=pady)
        name_entry = ttk.Entry(parent, font=self.app.font_normal)
        name_entry.grid(row=0, column=1, sticky="ew", pady=pady)

        ttk.Label(parent, text="システム名:", style="Tab.TLabel").grid(row=1, column=0, sticky="w", pady=pady)
        system_name_entry = ttk.Entry(parent, font=self.app.font_normal)
        system_name_entry.grid(row=1, column=1, sticky="ew", pady=pady)

        # 話し方設定
        ttk.Label(parent, text="一人称:", style="Tab.TLabel").grid(row=2, column=0, sticky="w", pady=pady)
        first_person_entry = ttk.Entry(parent, font=self.app.font_normal)
        first_person_entry.grid(row=2, column=1, sticky="ew", pady=pady)

        ttk.Label(parent, text="ユーザーの呼び方:", style="Tab.TLabel").grid(row=3, column=0, sticky="w", pady=pady)
        user_ref_entry = ttk.Entry(parent, font=self.app.font_normal)
        user_ref_entry.grid(row=3, column=1, sticky="ew", pady=pady)

        ttk.Label(parent, text="他キャラの呼び方(汎用):", style="Tab.TLabel").grid(row=4, column=0, sticky="w", pady=pady)
        third_person_ref_entry = ttk.Entry(parent, font=self.app.font_normal)
        third_person_ref_entry.grid(row=4, column=1, sticky="ew", pady=pady)

        # 性格設定
        ttk.Label(parent, text="性格設定:", style="Tab.TLabel").grid(row=5, column=0, sticky="nw", pady=pady)
        personality_text = tk.Text(parent, height=10, font=self.app.font_normal, relief="solid", bd=self.app.border_width_normal)
        personality_text.grid(row=5, column=1, sticky="nsew", pady=pady)
        CharacterCountLabel(parent, personality_text, max_length=2000, font=self.app.font_small).grid(row=6, column=1, sticky="e")

        # 自動発話の頻度
        freq_frame = ttk.Frame(parent)
        freq_frame.grid(row=8, column=1, sticky="ew", pady=pady)
        freq_frame.columnconfigure(0, weight=1)
        freq_value_label = ttk.Label(freq_frame, text="50", font=self.app.font_normal)
        freq_value_label.grid(row=0, column=1, padx=(padx,0))
        def update_freq_label(value): freq_value_label.config(text=f"{int(float(value))}")
        freq_scale = ttk.Scale(freq_frame, from_=0, to=100, orient="horizontal", command=update_freq_label)
        freq_scale.grid(row=0, column=0, sticky="ew")
        ttk.Label(parent, text="自動発話の頻度:", style="Tab.TLabel").grid(row=8, column=0, sticky="w", pady=pady)

        # --- ウィンドウ透過設定 ---
        transparency_frame = ttk.LabelFrame(parent, text="ウィンドウ透過設定", padding=self.app.padding_normal)
        transparency_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=pady)
        transparency_frame.columnconfigure(1, weight=1)

        self.transparency_mode_var = tk.StringVar(value="color_key")
        
        mode_frame = ttk.Frame(transparency_frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, pady))
        ttk.Label(mode_frame, text="透過方式:", style="Tab.TLabel").pack(side="left")
        ttk.Radiobutton(mode_frame, text="透明度維持", variable=self.transparency_mode_var, value="alpha", command=self._toggle_color_settings).pack(side="left", padx=padx)
        ttk.Radiobutton(mode_frame, text="色指定", variable=self.transparency_mode_var, value="color_key", command=self._toggle_color_settings).pack(side="left")
        
        self.color_settings_frame = ttk.Frame(transparency_frame)
        self.color_settings_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.color_settings_frame.columnconfigure(1, weight=1)

        # 透過色
        ttk.Label(self.color_settings_frame, text="ウィンドウ透過色:", style="Tab.TLabel").grid(row=0, column=0, sticky="w", pady=(0, pady))
        trans_color_frame = ttk.Frame(self.color_settings_frame)
        trans_color_frame.grid(row=0, column=1, sticky="ew", pady=(0, pady))

        trans_color_preview = tk.Label(trans_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
        trans_color_preview.grid(row=0, column=0, padx=(0, padx))

        trans_color_btn = ttk.Button(trans_color_frame, text="色の選択", style="Tab.TButton",
                   command=lambda: self.editor.pick_color(trans_color_preview))
        trans_color_btn.grid(row=0, column=1, sticky="w")
        trans_color_eyedropper = ttk.Button(trans_color_frame, text="画像から色を取得", style="Tab.TButton",
                   command=lambda: self.editor.enter_eyedropper_mode(trans_color_preview))
        trans_color_eyedropper.grid(row=0, column=2, padx=padx)

        # 縁色
        ttk.Label(self.color_settings_frame, text="ウィンドウ縁色:", style="Tab.TLabel").grid(row=1, column=0, sticky="w")
        edge_color_frame = ttk.Frame(self.color_settings_frame)
        edge_color_frame.grid(row=1, column=1, sticky="ew")

        edge_color_preview = tk.Label(edge_color_frame, text="      ", relief="solid", bd=self.app.border_width_normal)
        edge_color_preview.grid(row=0, column=0, padx=(0, padx))

        edge_color_btn = ttk.Button(edge_color_frame, text="色の選択", style="Tab.TButton",
                   command=lambda: self.editor.pick_color(edge_color_preview))
        edge_color_btn.grid(row=0, column=1, sticky="w")
        edge_color_eyedropper = ttk.Button(edge_color_frame, text="画像から色を取得", style="Tab.TButton",
                   command=lambda: self.editor.enter_eyedropper_mode(edge_color_preview))
        edge_color_eyedropper.grid(row=0, column=2, padx=padx)
        
        ttk.Separator(parent, orient="horizontal").grid(row=11, column=0, columnspan=2, sticky="ew", pady=self.app.padding_large)
        
        topics_frame = ttk.LabelFrame(parent, text="専用話題設定（自動発話で使われるキャラクター固有の話題）", padding=self.app.padding_normal)
        topics_frame.grid(row=12, column=0, columnspan=2, sticky="nsew")
        topics_frame.columnconfigure(0, weight=1)
        topics_frame.rowconfigure(1, weight=1)
        
        topics_button_frame = ttk.Frame(topics_frame)
        topics_button_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        ttk.Button(topics_button_frame, text="追加", command=self.add_topic, style="Tab.TButton").pack(side="left")
        ttk.Button(topics_button_frame, text="編集", command=self.edit_topic, style="Tab.TButton").pack(side="left", padx=padx)
        ttk.Button(topics_button_frame, text="削除", command=self.delete_topic, style="Tab.TButton").pack(side="left")

        topics_tree_frame = ttk.Frame(topics_frame)
        topics_tree_frame.grid(row=1, column=0, sticky="nsew")
        topics_tree_frame.columnconfigure(0, weight=1)
        topics_tree_frame.rowconfigure(0, weight=1)

        topics_tree = ttk.Treeview(topics_tree_frame, columns=("topic"), show="headings", style="Fav.Treeview")
        topics_tree.heading("topic", text="話題")
        topics_tree.grid(row=0, column=0, sticky="nsew")

        topics_scrollbar = ttk.Scrollbar(topics_tree_frame, orient="vertical", command=topics_tree.yview)
        topics_tree.config(yscrollcommand=topics_scrollbar.set)
        topics_scrollbar.grid(row=0, column=1, sticky="ns")

        self.widgets = {
            'CHARACTER_NAME': name_entry, 'SYSTEM_NAME': system_name_entry,
            'FIRST_PERSON': first_person_entry, 'USER_REFERENCE': user_ref_entry,
            'THIRD_PERSON_REFERENCE': third_person_ref_entry,
            'CHARACTER_PERSONALITY': personality_text, 'SPEECH_FREQUENCY': freq_scale,
            'SPEECH_FREQUENCY_LABEL': freq_value_label,
            'TRANSPARENCY_MODE': self.transparency_mode_var,
            'TRANSPARENT_COLOR': trans_color_preview, 'EDGE_COLOR': edge_color_preview,
            'trans_color_btn': trans_color_btn, 'trans_color_eyedropper': trans_color_eyedropper,
            'edge_color_btn': edge_color_btn, 'edge_color_eyedropper': edge_color_eyedropper,
            'SYSTEM_MESSAGES': {}, 'topics_tree': topics_tree
        }

        # システムメッセージ
        ttk.Separator(parent, orient="horizontal").grid(row=13, column=0, columnspan=2, sticky="ew", pady=self.app.padding_large)

        messages_frame = ttk.LabelFrame(parent, text="システムメッセージ設定", padding=self.app.padding_normal)
        messages_frame.grid(row=14, column=0, columnspan=2, sticky="nsew")
        messages_frame.columnconfigure(1, weight=1)

        system_messages = {
            "ON_EMPTY_RESPONSE": "AIの応答が空の場合:", "ON_API_TIMEOUT": "APIがタイムアウトした場合:",
            "ON_ALL_MODELS_FAILED": "全モデルが応答失敗した場合:", "ON_SPECIFIC_MODEL_FAILED": "特定モデルが失敗した場合:"
        }

        row_count = 0
        for key, label_text in system_messages.items():
            ttk.Label(messages_frame, text=label_text, style="Tab.TLabel").grid(row=row_count, column=0, sticky="nw", padx=(0, padx), pady=pady)
            msg_text = tk.Text(messages_frame, height=2, font=self.app.font_normal, relief="solid", bd=self.app.border_width_normal)
            msg_text.grid(row=row_count, column=1, sticky="ew", pady=pady)
            self.widgets['SYSTEM_MESSAGES'][key] = msg_text
            CharacterCountLabel(messages_frame, msg_text, max_length=500, font=self.app.font_small).grid(row=row_count + 1, column=1, sticky="e")

            if key == "ON_SPECIFIC_MODEL_FAILED":
                ttk.Label(messages_frame, text="({model_key}がモデル名に置換されます)", font=self.app.font_small).grid(row=row_count + 1, column=1, sticky="w")
                row_count += 1
            row_count += 2

    def _toggle_color_settings(self):
        """透過モードに応じて色指定UIの有効/無効を切り替える"""
        state = "disabled" if self.transparency_mode_var.get() == "alpha" else "normal"
        
        # 色設定UIのウィジェットにアクセスして状態を変更
        for key in ['trans_color_btn', 'trans_color_eyedropper', 'edge_color_btn', 'edge_color_eyedropper']:
            if key in self.widgets:
                self.widgets[key].config(state=state)

    def load_data(self):
        self.widgets['CHARACTER_NAME'].delete(0, tk.END)
        self.widgets['CHARACTER_NAME'].insert(0, self.character_data.get('INFO', 'CHARACTER_NAME'))
        self.widgets['SYSTEM_NAME'].delete(0, tk.END)
        self.widgets['SYSTEM_NAME'].insert(0, self.character_data.get('INFO', 'SYSTEM_NAME'))
        self.widgets['FIRST_PERSON'].delete(0, tk.END)
        self.widgets['FIRST_PERSON'].insert(0, self.character_data.get('INFO', 'FIRST_PERSON'))
        self.widgets['USER_REFERENCE'].delete(0, tk.END)
        self.widgets['USER_REFERENCE'].insert(0, self.character_data.get('INFO', 'USER_REFERENCE'))
        self.widgets['THIRD_PERSON_REFERENCE'].delete(0, tk.END)
        self.widgets['THIRD_PERSON_REFERENCE'].insert(0, self.character_data.get('INFO', 'THIRD_PERSON_REFERENCE'))

        self.widgets['CHARACTER_PERSONALITY'].delete("1.0", tk.END)
        personality_text_raw = self.character_data.get('INFO', 'CHARACTER_PERSONALITY')
        personality_text_unescaped = personality_text_raw.replace(r'\n', '\n')
        self.widgets['CHARACTER_PERSONALITY'].insert("1.0", personality_text_unescaped)
        freq_value = self.character_data.get('INFO', 'SPEECH_FREQUENCY', fallback='50')
        self.widgets['SPEECH_FREQUENCY'].set(float(freq_value))

        trans_mode = self.character_data.get('INFO', 'TRANSPARENCY_MODE', fallback='color_key')
        self.transparency_mode_var.set(trans_mode)
        self._toggle_color_settings() # UIの状態を更新

        trans_color = self.character_data.get('INFO', 'TRANSPARENT_COLOR', fallback='#ff00ff')
        edge_color = self.character_data.get('INFO', 'EDGE_COLOR', fallback='#838383')
        try:
            self.widgets['TRANSPARENT_COLOR'].config(background=trans_color)
            self.widgets['EDGE_COLOR'].config(background=edge_color)
        except tk.TclError:
            print(f"警告: 不正な色コードのため、プレビューに反映できませんでした (TRANSPARENT_COLOR: {trans_color}, EDGE_COLOR: {edge_color})")

        for key, widget in self.widgets['SYSTEM_MESSAGES'].items():
            widget.delete("1.0", "end")
            widget.insert("1.0", self.character_data.get('SYSTEM_MESSAGES', key))
            
        # 専用話題を読み込んで表示
        for item in self.widgets['topics_tree'].get_children():
            self.widgets['topics_tree'].delete(item)
        
        special_topics = self.character_data.get_special_topics()
        for topic in special_topics:
            self.widgets['topics_tree'].insert("", "end", values=(topic,))

    def collect_data(self):
        # キャラクター名 (50文字制限)
        char_name = self.editor.sanitize_string(self.widgets['CHARACTER_NAME'].get(), max_length=50)
        self.character_data.set('INFO', 'CHARACTER_NAME', char_name)

        # システム名 (50文字制限)
        sys_name = self.editor.sanitize_string(self.widgets['SYSTEM_NAME'].get(), max_length=50)
        self.character_data.set('INFO', 'SYSTEM_NAME', sys_name)

        # 追加項目
        first_person = self.editor.sanitize_string(self.widgets['FIRST_PERSON'].get(), max_length=20)
        self.character_data.set('INFO', 'FIRST_PERSON', first_person)
        user_ref = self.editor.sanitize_string(self.widgets['USER_REFERENCE'].get(), max_length=20)
        self.character_data.set('INFO', 'USER_REFERENCE', user_ref)
        third_person_ref = self.editor.sanitize_string(self.widgets['THIRD_PERSON_REFERENCE'].get(), max_length=20)
        self.character_data.set('INFO', 'THIRD_PERSON_REFERENCE', third_person_ref)

        personality_raw = self.widgets['CHARACTER_PERSONALITY'].get("1.0", "end-1c")
        personality = self.editor.sanitize_string(personality_raw, max_length=2000, allow_newlines=True) # 改行を許可
        self.character_data.set('INFO', 'CHARACTER_PERSONALITY', personality)

        freq = int(self.widgets['SPEECH_FREQUENCY'].get())
        self.character_data.set('INFO', 'SPEECH_FREQUENCY', freq)

        trans_mode = self.widgets['TRANSPARENCY_MODE'].get()
        self.character_data.set('INFO', 'TRANSPARENCY_MODE', trans_mode)
        
        trans_color = self.widgets['TRANSPARENT_COLOR'].cget("background")
        edge_color = self.widgets['EDGE_COLOR'].cget("background")
        self.character_data.set('INFO', 'TRANSPARENT_COLOR', trans_color)
        self.character_data.set('INFO', 'EDGE_COLOR', edge_color)

        # システムメッセージ (各500文字制限、改行は許可しない)
        for key, widget in self.widgets['SYSTEM_MESSAGES'].items():
            content_raw = widget.get("1.0", "end-1c")
            content = self.editor.sanitize_string(content_raw, max_length=500, allow_newlines=True) # 改行を許可
            self.character_data.set('SYSTEM_MESSAGES', key, content)
            
        # 専用話題を収集して保存
        topics_tree = self.widgets['topics_tree']
        special_topics = [topics_tree.item(item, "values")[0] for item in topics_tree.get_children()]
        self.character_data.update_special_topics(special_topics)

    def add_topic(self):
        """専用話題を追加するボタンのコールバック"""
        dialog = TopicDialog(self, "専用話題の追加")
        if dialog.result:
            # サニタイズ
            new_topic = self.editor.sanitize_string(dialog.result, max_length=100, allow_newlines=False)
            self.widgets['topics_tree'].insert("", "end", values=(new_topic,))

    def edit_topic(self):
        """専用話題を編集するボタンのコールバック"""
        selected_item = self.widgets['topics_tree'].focus()
        if not selected_item:
            messagebox.showwarning("警告", "編集する話題を選択してください。", parent=self)
            return
        
        old_topic = self.widgets['topics_tree'].item(selected_item, "values")[0]
        dialog = TopicDialog(self, "専用話題の編集", initial_value=old_topic)
        if dialog.result:
            # サニタイズ
            edited_topic = self.editor.sanitize_string(dialog.result, max_length=100, allow_newlines=False)
            self.widgets['topics_tree'].item(selected_item, values=(edited_topic,))

    def delete_topic(self):
        """専用話題を削除するボタンのコールバック"""
        selected_item = self.widgets['topics_tree'].focus()
        if not selected_item:
            messagebox.showwarning("警告", "削除する話題を選択してください。", parent=self)
            return
        self.widgets['topics_tree'].delete(selected_item)
