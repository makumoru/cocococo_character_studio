# src/tabs/tab_costume.py

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .tab_base import TabBase
import os

class CostumeDialog(simpledialog.Dialog):
    """衣装のIDと名前をまとめて入力するためのカスタムダイアログ"""
    def __init__(self, parent, title, initial_id="", initial_name="", id_editable=True):
        self.app = parent.app # TabCostumesからappインスタンスを受け取る
        self.id_var = tk.StringVar(parent, value=initial_id)
        self.name_var = tk.StringVar(parent, value=initial_name)
        self.id_editable = id_editable
        super().__init__(parent, title)

    def body(self, master):
        style = ttk.Style(self)
        style.configure("Dialog.TLabel", font=self.app.font_normal)
        style.configure("Dialog.TEntry", font=self.app.font_normal)

        ttk.Label(master, text="衣装ID (半角英数字):", style="Dialog.TLabel").grid(row=0, sticky="w")
        self.id_entry = ttk.Entry(master, textvariable=self.id_var, font=self.app.font_normal)
        self.id_entry.grid(row=1, sticky="ew", pady=(0, self.app.padding_normal))
        if not self.id_editable: self.id_entry.config(state="readonly")

        ttk.Label(master, text="衣装の表示名:", style="Dialog.TLabel").grid(row=2, sticky="w")
        self.name_entry = ttk.Entry(master, textvariable=self.name_var, font=self.app.font_normal)
        self.name_entry.grid(row=3, sticky="ew")

        return self.id_entry

    def apply(self):
        self.result = (self.id_var.get().strip(), self.name_var.get().strip())

    def validate(self):
        costume_id = self.id_var.get().strip()
        costume_name = self.name_var.get().strip()
        if not costume_id or not costume_name:
            messagebox.showwarning("入力エラー", "IDと表示名の両方を入力してください。", parent=self)
            return 0
        if not costume_id.isalnum():
            messagebox.showwarning("入力エラー", "IDは半角英数字で入力してください。", parent=self)
            return 0
        return 1

class TabCostumes(TabBase):
    """
    「衣装」タブのUIとロジックを管理するクラス。
    """
    def create_widgets(self):
        parent = self.scrollable_frame
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        style = ttk.Style(self)
        style.configure("Tab.TButton", font=self.app.font_normal, padding=self.app.padding_small)

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_normal))
        
        ttk.Button(button_frame, text="衣装を追加", command=self.add_costume, style="Tab.TButton").pack(side="left", padx=(0, self.app.padding_small))
        ttk.Button(button_frame, text="衣装を編集/リネーム", command=self.edit_costume, style="Tab.TButton").pack(side="left", padx=self.app.padding_small)
        ttk.Button(button_frame, text="衣装を削除", command=self.delete_costume, style="Tab.TButton").pack(side="left", padx=self.app.padding_small)

        list_frame = ttk.Frame(parent)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.costume_listbox = tk.Listbox(list_frame, font=self.app.font_list)
        self.costume_listbox.grid(row=0, column=0, sticky="nsew")
        self.costume_listbox.bind("<<ListboxSelect>>", self.on_costume_select)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.costume_listbox.yview)
        self.costume_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.widgets = {'costume_listbox': self.costume_listbox}

    def load_data(self):
        self.costume_listbox.delete(0, tk.END)
        costumes = self.character_data.get_costumes()
        for costume in costumes:
            self.costume_listbox.insert(tk.END, f"{costume['name']} (ID: {costume['id']})")
        self.editor.update_costume_selector()
        if not self.editor.current_costume_id.get():
             self.editor.current_costume_id.set('default')
        self.select_costume_by_id(self.editor.current_costume_id.get(), fallback_to_first=True)

    def collect_data(self):
        pass
        
    def add_costume(self):
        dialog = CostumeDialog(self, title="衣装の追加")
        if not dialog.result: return
        costume_id, costume_name_raw = dialog.result
        # サニタイズ処理
        costume_name = self.editor.sanitize_string(costume_name_raw, max_length=50)
        try:
            self.character_data.add_costume(costume_id, costume_name)
            self.load_data()
            self.costume_listbox.selection_clear(0, tk.END)
            for i in range(self.costume_listbox.size()):
                if f"(ID: {costume_id})" in self.costume_listbox.get(i):
                    self.costume_listbox.select_set(i)
                    self.costume_listbox.event_generate("<<ListboxSelect>>")
                    break
        except ValueError as e:
            messagebox.showerror("エラー", str(e), parent=self)
            
    def edit_costume(self):
        selected_indices = self.costume_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "編集する衣装を選択してください。", parent=self)
            return
        selected_index = selected_indices[0]
        old_costume = self.character_data.get_costumes()[selected_index]
        old_id = old_costume['id']
        is_default = (old_id == 'default')
        dialog = CostumeDialog(self, title="衣装の編集", initial_id=old_id, initial_name=old_costume['name'], id_editable=not is_default)
        if not dialog.result: return
        new_id, new_name_raw = dialog.result
        # サニタイズ処理
        new_name = self.editor.sanitize_string(new_name_raw, max_length=50)

        try:
            self.character_data.rename_costume(old_id, new_id, new_name)
            self.load_data()
            for i in range(self.costume_listbox.size()):
                if f"(ID: {new_id})" in self.costume_listbox.get(i):
                    self.costume_listbox.select_set(i)
                    self.costume_listbox.event_generate("<<ListboxSelect>>")
                    break
        except ValueError as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def delete_costume(self):
        selected_indices = self.costume_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "削除する衣装を選択してください。", parent=self)
            return
        selected_index = selected_indices[0]
        costume_to_delete = self.character_data.get_costumes()[selected_index]
        costume_id = costume_to_delete['id']
        if costume_id == 'default':
            messagebox.showerror("エラー", "'default'衣装は削除できません。", parent=self)
            return
        if messagebox.askyesno("確認", f"本当に衣装 '{costume_to_delete['name']}' を削除しますか？\n関連する画像フォルダもすべて削除されます。", parent=self):
            self.character_data.delete_costume(costume_id)
            self.load_data()

    def on_costume_select(self, event):
        selected_indices = self.costume_listbox.curselection()
        if not selected_indices: return
        selected_index = selected_indices[0]
        costume = self.character_data.get_costumes()[selected_index]
        if self.editor.current_costume_id.get() != costume['id']:
            self.editor.current_costume_id.set(costume['id'])

    def select_costume_by_id(self, costume_id: str, fallback_to_first: bool = False):
        costumes = self.character_data.get_costumes()
        target_index = -1
        for i, costume in enumerate(costumes):
            if costume['id'] == costume_id:
                target_index = i; break
        if target_index != -1:
            self.costume_listbox.selection_clear(0, tk.END)
            self.costume_listbox.select_set(target_index)
            self.costume_listbox.activate(target_index)
        elif fallback_to_first and self.costume_listbox.size() > 0:
            self.costume_listbox.selection_clear(0, tk.END)
            self.costume_listbox.select_set(0)
            self.costume_listbox.activate(0)
            self.on_costume_select(None)