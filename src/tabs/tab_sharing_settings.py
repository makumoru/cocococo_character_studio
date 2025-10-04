# src/tabs/tab_sharing_settings.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from .tab_base import TabBase
from ..ui_components import CharacterCountLabel

class ResetConfirmationDialog(simpledialog.Dialog):
    """共有情報リセットの意思確認と警告表示を行うカスタムダイアログ"""
    def __init__(self, parent, title):
        self.app = parent.app
        self.check_var = tk.BooleanVar(value=False)
        self.ok_button = None
        super().__init__(parent, title)

    def body(self, master):
        # メインメッセージ
        main_text = (
            "キャラクターに紐付けられている既存のGitHub共有情報（Issue番号/URL）を削除します。\n\n"
            "この操作を行うと、次回「GitHubに共有」を実行した際に、新しいIssueとして投稿されることになります。"
        )
        ttk.Label(master, text=main_text, wraplength=450).pack(pady=self.app.padding_normal)

        # 用途説明フレーム
        case_frame = ttk.LabelFrame(master, text="想定される利用ケース", padding=self.app.padding_normal)
        case_frame.pack(fill="x", expand=True, pady=self.app.padding_small)
        case_a_text = "・ケースA: 既存のキャラクターを改変し、別のキャラクターとして新規に共有したい場合"
        case_b_text = "・ケースB: 共有済みのIssueが削除されたなどの理由で、同じキャラクターを再投稿したい場合"
        ttk.Label(case_frame, text=case_a_text).pack(anchor="w")
        ttk.Label(case_frame, text=case_b_text).pack(anchor="w")

        # 警告フレーム
        warning_frame = ttk.Frame(master, padding=(self.app.padding_normal, self.app.padding_large))
        warning_frame.pack(fill="x", expand=True)
        warning_icon_label = ttk.Label(warning_frame, text="⚠️", font=("Segoe UI Emoji", 16)) # 絵文字フォントを指定
        warning_icon_label.pack(side="left", padx=(0, self.app.padding_small), anchor="n")
        
        warning_text = "他者が作成したキャラクターを、作者に無断でご自身の作品として再共有することは、利用規約で禁止されています。"
        warning_text_label = ttk.Label(warning_frame, text=warning_text, foreground="red", wraplength=400)
        warning_text_label.pack(side="left", fill="x", expand=True)

        # 確認チェックボックス
        check_button = ttk.Checkbutton(
            master,
            text="上記の注意点を理解しました。",
            variable=self.check_var,
            command=self.validate_ok_button
        )
        check_button.pack(pady=self.app.padding_normal)

        return check_button # 初期フォーカス

    def buttonbox(self):
        box = ttk.Frame(self)
        self.ok_button = ttk.Button(box, text="共有情報をリセットする", width=20, command=self.ok, state="disabled")
        self.ok_button.pack(side="left", padx=5, pady=5)
        cancel_button = ttk.Button(box, text="キャンセル", width=10, command=self.cancel)
        cancel_button.pack(side="left", padx=5, pady=5)

        self.bind("<Return>", lambda e: "break") # Enterでの実行を無効化
        self.bind("<Escape>", self.cancel)
        box.pack()

    def validate_ok_button(self):
        """チェックボックスの状態に応じてOKボタンを有効/無効化する"""
        if self.check_var.get():
            self.ok_button.config(state="normal")
        else:
            self.ok_button.config(state="disabled")

    def apply(self):
        # OKが押されたら結果をTrueにする
        self.result = True

class TabSharingSettings(TabBase):
    """
    「共有設定」タブ。キャラクターの説明文(readme.txt)を編集する。
    """
    def create_widgets(self):
        parent = self.scrollable_frame
        # メインフレームをPanedWindowで左右に分割
        paned_window = ttk.PanedWindow(parent, orient='horizontal')
        paned_window.pack(expand=True, fill='both')

        # --- 左ペイン：説明文と属性 ---
        left_pane = ttk.Frame(paned_window, padding=self.app.padding_normal)
        paned_window.add(left_pane, weight=2)
        left_pane.columnconfigure(0, weight=1)
        left_pane.rowconfigure(2, weight=1)

        # --- 右ペイン：サムネイルの黒塗り設定 ---
        right_pane = ttk.Frame(paned_window, padding=self.app.padding_normal)
        paned_window.add(right_pane, weight=1)
        right_pane.columnconfigure(0, weight=1)
        right_pane.rowconfigure(1, weight=1)


        # --- 左ペインのウィジェット ---
        self.is_derivative_var = tk.BooleanVar()
        self.is_nsfw_var = tk.BooleanVar()

        attributes_frame = ttk.LabelFrame(left_pane, text="キャラクターの属性", padding=self.app.padding_normal)
        attributes_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_large))
        
        ttk.Checkbutton(attributes_frame, text="二次創作", variable=self.is_derivative_var).pack(side="left", padx=self.app.padding_small)
        ttk.Checkbutton(attributes_frame, text="NSFW", variable=self.is_nsfw_var).pack(side="left", padx=self.app.padding_small)

        button_frame = ttk.Frame(left_pane)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.app.padding_small))
        ttk.Button(button_frame, text="基本設定からテンプレートを生成", command=self.populate_from_template).pack(side="left")
        
        self.reset_button = ttk.Button(button_frame, text="共有情報をリセット...", command=self.reset_sharing_info)
        self.reset_button.pack(side="left", padx=self.app.padding_normal)

        text_frame = ttk.Frame(left_pane)
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        
        self.readme_text = tk.Text(text_frame, height=15, wrap="word", font=self.app.font_normal, relief="solid", bd=self.app.border_width_normal)
        self.readme_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.readme_text.yview)
        self.readme_text.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")
        CharacterCountLabel(left_pane, self.readme_text, max_length=10000, font=self.app.font_small).grid(row=3, column=0, sticky="e")


        # --- 右ペインのウィジェット ---
        censor_frame = ttk.LabelFrame(right_pane, text="サムネイルの黒塗り修正", padding=self.app.padding_normal)
        censor_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_large))

        censor_button_frame = ttk.Frame(censor_frame)
        censor_button_frame.pack(fill="x", pady=(0, self.app.padding_small))
        ttk.Button(censor_button_frame, text="黒塗りエリアを追加", command=self.add_censor_area).pack(side="left", padx=(0, self.app.padding_small))
        ttk.Button(censor_button_frame, text="選択したエリアを削除", command=self.delete_censor_area).pack(side="left")

        censor_list_frame = ttk.Frame(right_pane)
        censor_list_frame.grid(row=1, column=0, sticky="nsew")
        censor_list_frame.columnconfigure(0, weight=1)
        censor_list_frame.rowconfigure(0, weight=1)

        self.censor_tree = ttk.Treeview(censor_list_frame, columns=("rect"), show="headings")
        self.censor_tree.heading("rect", text="黒塗りエリア座標")
        self.censor_tree.grid(row=0, column=0, sticky="nsew")
        self.censor_tree.bind("<<TreeviewSelect>>", self.on_censor_selection_change)

        self.widgets = {
            'readme_text': self.readme_text,
            'is_derivative': self.is_derivative_var,
            'is_nsfw': self.is_nsfw_var,
            'censor_tree': self.censor_tree,
            'reset_sharing_info_button': self.reset_button
        }

    def load_data(self):
        """タブが表示されたときにreadme.txtの内容とチェックボックスの状態を読み込む"""
        is_derivative = self.character_data.config.getboolean('INFO', 'IS_DERIVATIVE', fallback=False)
        is_nsfw = self.character_data.config.getboolean('INFO', 'IS_NSFW', fallback=False)
        self.is_derivative_var.set(is_derivative)
        self.is_nsfw_var.set(is_nsfw)
        
        content = self.character_data.get_readme_content()
        self.readme_text.delete("1.0", tk.END)
        if content:
            self.readme_text.insert("1.0", content)
        else:
            self.populate_from_template(confirm=False)

        # 黒塗りエリアの読み込み
        for item in self.censor_tree.get_children(): self.censor_tree.delete(item)
        rects = self.character_data.get_thumbnail_censor_rects()
        for rect in rects:
            self.censor_tree.insert("", "end", values=(str(rect),))

        # 共有情報の有無に応じてリセットボタンの有効/無効を切り替え
        issue_number, issue_url = self.character_data.get_issue_reference()
        if issue_number or issue_url:
            self.widgets['reset_sharing_info_button'].config(state="normal")
        else:
            self.widgets['reset_sharing_info_button'].config(state="disabled")

    def reset_sharing_info(self):
        """共有情報のリセット処理を開始する"""
        dialog = ResetConfirmationDialog(self, title="共有情報の削除確認")
        # dialog.result が True の場合のみ処理を続行 (OKボタンが押された場合)
        if dialog.result:
            try:
                # CharacterDataオブジェクトの情報をクリア
                self.character_data.set_issue_reference(issue_number="", issue_url="")
                # iniファイルに即時保存
                self.character_data.save()
                
                # UIを更新
                self.widgets['reset_sharing_info_button'].config(state="disabled")
                messagebox.showinfo("成功", "キャラクターの共有情報をリセットしました。", parent=self)
            except Exception as e:
                messagebox.showerror("エラー", f"リセット処理中にエラーが発生しました:\n{e}", parent=self)

    def collect_data(self):
        """保存時にテキストエリアの内容とチェックボックスの状態をiniに書き出す"""
        self.character_data.set('INFO', 'IS_DERIVATIVE', str(self.is_derivative_var.get()).lower())
        self.character_data.set('INFO', 'IS_NSFW', str(self.is_nsfw_var.get()).lower())
        content_raw = self.readme_text.get("1.0", "end-1c")
        content = self.editor.sanitize_string(content_raw, max_length=2000, allow_newlines=True)
        self.character_data.save_readme_content(content)

        # 黒塗りエリアの保存
        rects = []
        for item_id in self.censor_tree.get_children():
            rect_str = self.censor_tree.item(item_id, 'values')[0]
            try:
                rects.append(eval(rect_str))
            except:
                pass
        self.character_data.update_thumbnail_censor_rects(rects)

    def populate_from_template(self, confirm=True):
        """テンプレート生成ボタンが押されたときの処理"""
        should_proceed = False
        if confirm:
            if messagebox.askyesno("確認", "現在の説明文を上書きしてテンプレートを生成しますか？", parent=self):
                should_proceed = True
        else:
            should_proceed = True

        if should_proceed:
            template = self.character_data.generate_readme_template()
            self.readme_text.delete("1.0", tk.END)
            self.readme_text.insert("1.0", template)

    def add_censor_area(self):
        """「黒塗りエリアを追加」ボタンの処理"""
        # 描画モードに入る直前に、プレビューがサムネイルであることを確実にする
        self.editor.set_preview_to_thumbnail()
        # 描画モードを開始
        self.editor.enter_rect_drawing_mode(self.on_censor_area_drawn)

    def on_censor_area_drawn(self, rect: tuple | None):
        """描画モードのコールバック"""
        if rect:
            self.censor_tree.insert("", "end", values=(str(list(rect)),))
            # 追加後、すぐにプレビューに反映 (afterで遅延実行)
            self.editor.after(10, self.editor.redraw_image_preview)
            
    def delete_censor_area(self):
        """選択した黒塗りエリアを削除する処理"""
        selected_items = self.censor_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "削除するエリアをリストから選択してください。", parent=self)
            return
        for item in selected_items:
            self.censor_tree.delete(item)
        # 削除後、すぐにプレビューに反映
        self.on_censor_selection_change() # 選択が変更されるので、ハイライトも更新

    def on_censor_selection_change(self, event=None):
        """リストの選択が変更されたときにハイライトを更新する"""
        selected_rects = []
        for item_id in self.censor_tree.selection():
            rect_str = self.censor_tree.item(item_id, 'values')[0]
            try:
                selected_rects.append(eval(rect_str))
            except:
                pass
        
        self.editor.highlight_censor_rects(selected_rects)
        self.editor.redraw_image_preview()