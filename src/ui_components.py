# src/ui_components.py

import tkinter as tk
from tkinter import ttk

class CharacterCountLabel(ttk.Label):
    """
    Textウィジェットの文字数をリアルタイムで表示し、上限に応じて色を変えるラベル。
    """
    def __init__(self, parent, text_widget: tk.Text, max_length: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget
        self.max_length = max_length

        # スタイルを設定
        self.style = ttk.Style()
        self.style.configure("CharCount.Normal.TLabel", foreground="black")
        self.style.configure("CharCount.Warning.TLabel", foreground="orange")
        self.style.configure("CharCount.Error.TLabel", foreground="red")

        self.update_count()

        # Textウィジェットの変更を監視
        self.text_widget.bind("<<Modified>>", self.on_text_modified)

    def on_text_modified(self, event=None):
        self.update_count()
        # Modifiedイベントは一度しか発生しないため、再度フラグを立てる
        self.text_widget.edit_modified(False)

    def update_count(self):
        # 現在の文字数を取得 (末尾の改行は除く)
        current_length = len(self.text_widget.get("1.0", "end-1c"))
        
        # スタイルを決定
        if current_length > self.max_length:
            style_name = "CharCount.Error.TLabel"
        elif current_length > self.max_length * 0.9:
            style_name = "CharCount.Warning.TLabel"
        else:
            style_name = "CharCount.Normal.TLabel"

        self.config(text=f"{current_length} / {self.max_length}", style=style_name)

    def update_count(self):
        # 現在の文字数を取得 (末尾の改行は除く)
        current_length = len(self.text_widget.get("1.0", "end-1c"))
        
        # スタイルを決定
        if current_length > self.max_length:
            style_name = "CharCount.Error.TLabel"
        elif current_length > self.max_length * 0.9:
            style_name = "CharCount.Warning.TLabel"
        else:
            style_name = "CharCount.Normal.TLabel"

        self.config(text=f"{current_length} / {self.max_length}", style=style_name)