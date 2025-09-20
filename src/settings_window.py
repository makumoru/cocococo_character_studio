# src/settings_window.py

import tkinter as tk
from tkinter import ttk, messagebox, font
import configparser
import webbrowser

class SettingsWindow(tk.Toplevel):
    """
    GitHub Personal Access Tokenを設定するためのウィンドウ。
    """
    def __init__(self, parent, config_path: str):
        super().__init__(parent)
        self.app = parent
        self.config_path = config_path

        self.title("GitHub連携 設定")
        self.transient(parent)
        self.grab_set()

        # ウィンドウサイズと配置を調整
        # 親ウィンドウの幅を基準にしつつ、最小幅を確保
        base_width = self.app.winfo_width()
        win_width = max(500, int(base_width * 0.9))
        # 高さを少し余裕を持たせる
        win_height = max(400, int(self.app.winfo_height() * 0.8))
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(450, 380) # 最小サイズを設定

        self.token_var = tk.StringVar()
        
        # wraplengthをウィンドウ幅から計算
        self.wrap_length = win_width - self.app.padding_large * 4

        self.create_widgets()
        self.load_settings()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.wait_window(self)

    def create_widgets(self):
        # メインフレームのrowconfigureを調整
        main_frame = ttk.Frame(self, padding=self.app.padding_large)
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        # 説明文(0)と入力欄(1)がスペースを分け合うように weight を設定
        main_frame.rowconfigure(0, weight=3)
        main_frame.rowconfigure(1, weight=1)

        # --- 説明フレーム ---
        info_frame = ttk.LabelFrame(main_frame, text="設定方法", padding=self.app.padding_normal)
        info_frame.grid(row=0, column=0, sticky="nsew", pady=(0, self.app.padding_large))
        
        info_text = (
            "キャラクターの共有機能を利用するには、GitHubのPersonal Access Tokenが必要です。\n\n"
            "1. 下のリンクからトークン作成ページを開きます。\n"
            "2. Noteに「cocococo-uploader」など分かりやすい名前を付けます。\n"
            "3. Expiration（有効期限）は「No expiration」を推奨します。\n"
            "4. Scopes（権限）で「repo」と「read:user」にチェックを入れます。\n"
            "5. 「Generate token」ボタンを押し、表示されたトークンをコピーして下に貼り付けてください。"
        )
        # Labelのpackをgridに変更し、伸縮性を制御
        info_label = ttk.Label(info_frame, text=info_text, font=self.app.font_normal, wraplength=self.wrap_length)
        info_label.grid(row=0, column=0, sticky="nw")

        # ハイパーリンク
        link_font = font.Font(font=self.app.font_normal)
        link_font.configure(underline=True)
        link_label = ttk.Label(info_frame, text="▶ トークン作成ページを開く (github.com)", 
                               font=link_font, foreground="blue", cursor="hand2")
        link_label.grid(row=1, column=0, sticky="nw", pady=self.app.padding_small)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/settings/tokens/new"))
        
        info_frame.rowconfigure(0, weight=1) # ラベルがスペースを使うように
        info_frame.columnconfigure(0, weight=1)

        # --- 入力フレーム ---
        input_frame = ttk.LabelFrame(main_frame, text="Personal Access Token", padding=self.app.padding_normal)
        input_frame.grid(row=1, column=0, sticky="nsew")
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1) # Entryが中央に来るように

        token_entry = ttk.Entry(input_frame, textvariable=self.token_var, font=self.app.font_normal)
        token_entry.pack(fill="x", expand=False) # expand=Falseで中央配置

        # --- ボタンフレーム ---
        # main_frameの子にする
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky="se", pady=(self.app.padding_normal, 0))
        
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side="left", padx=self.app.padding_normal)
        ttk.Button(button_frame, text="キャンセル", command=self.on_close).pack(side="left")

    def load_settings(self):
        """config.iniからトークンを読み込んで表示する"""
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        token = config.get('GITHUB', 'personal_access_token', fallback="")
        self.token_var.set(token)

    def save_settings(self):
        """コメントを保持したままトークンを保存する"""
        new_token = self.token_var.get().strip()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            in_github_section = False
            updated = False
            with open(self.config_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line.lower() == '[github]':
                        in_github_section = True
                    elif stripped_line.startswith('['):
                        in_github_section = False

                    if in_github_section and stripped_line.lower().startswith('personal_access_token'):
                        f.write(f'personal_access_token = {new_token}\n')
                        updated = True
                    else:
                        f.write(line)
            
            if not updated:
                 raise ValueError("[GITHUB]セクションまたはpersonal_access_tokenキーが見つかりません。")

            messagebox.showinfo("成功", "設定を保存しました。", parent=self)
            self.destroy()

        except Exception as e:
            messagebox.showerror("保存エラー", f"設定の保存中にエラーが発生しました:\n{e}", parent=self)

    def on_close(self):
        self.destroy()