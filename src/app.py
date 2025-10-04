# src/app.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Listbox, Scrollbar, font
import os
import subprocess
import platform
from tkinterdnd2 import TkinterDnD, DND_FILES
import webbrowser
import re

from .project_manager import ProjectManager
from .editor_window import EditorWindow
from .settings_window import SettingsWindow
from .character_installer import CharacterInstaller

class CharacterMakerApp(TkinterDnD.Tk):
    """
    キャラクター作成支援ツールのメインアプリケーションウィンドウ。
    """
    def __init__(self, base_path: str):
        super().__init__()
        self.title("ここここ キャラクタースタジオ")
        self.base_path = base_path
        self.config_file = os.path.join(self.base_path, 'config.ini')
        self.character_repo_url = "https://github.com/YobiYobiMoru/cocococo_character_uploader/issues"

        # --- UI基準単位の計算 ---
        screen_height = self.winfo_screenheight()
        screen_width = self.winfo_screenwidth()
        
        self.base_font_size = max(8, int(screen_height * 0.012))
        self.font_title = ("Yu Gothic UI", self.base_font_size + 4, "bold")
        self.font_normal = ("Yu Gothic UI", self.base_font_size)
        self.font_list = ("Yu Gothic UI", self.base_font_size + 2)
        self.font_small = ("Yu Gothic UI", self.base_font_size - 2)

        self.padding_large = self.base_font_size
        self.padding_normal = int(self.base_font_size * 0.5)
        self.padding_small = int(self.base_font_size * 0.25)
        
        self.border_width_normal = max(1, int(self.base_font_size * 0.1))

        # ウィンドウサイズも画面比率で設定
        win_width = int(screen_width * 0.3)
        win_height = int(screen_height * 0.4)
        self.geometry(f"{win_width}x{win_height}")
        # ウィンドウの最小高さを設定してボタンが見切れないようにする
        self.minsize(int(win_width * 0.8), int(win_height * 0.7))


        self.project_manager = ProjectManager(base_dir=self.base_path)
        
        # --- インストーラーを初期化 ---
        self.installer = CharacterInstaller(parent=self, characters_dir=self.project_manager.characters_dir)

        self.create_start_widgets()

    def create_menu(self):
        """アプリケーションのメニューバーを作成する"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 設定メニュー
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="GitHub連携 設定...", command=self.open_settings_window)

    def open_settings_window(self):
        """設定ウィンドウを開く"""
        if not os.path.exists(self.config_file):
            messagebox.showerror("エラー", f"設定ファイルが見つかりません。\n({self.config_file})\n\n親アプリの起動が完了しているか確認してください。")
            return
        # SettingsWindowを呼び出す
        SettingsWindow(self, self.config_file)

    def create_start_widgets(self):
        """起動時のプロジェクト選択画面を生成します。"""
        for widget in self.winfo_children():
            widget.destroy()

        # ウィジェットを再生成する際に、メニューも必ず再生成する
        self.create_menu()

        # --- ボタンフレーム (ウィンドウ下部に固定) ---
        # 先に button_frame を作成し、ウィンドウ下部に配置します。
        # packの順序が重要です。
        button_frame = ttk.Frame(self, padding=(self.padding_large, self.padding_small, self.padding_large, self.padding_large))
        button_frame.pack(side="bottom", fill="x")

        # --- メインフレーム (残りの領域全体を占める) ---
        # 次に main_frame を作成し、残りの領域を埋めるように配置します。
        main_frame = ttk.Frame(self, padding=(self.padding_large, self.padding_large, self.padding_large, 0))
        main_frame.pack(expand=True, fill="both")
        
        # --- メインフレーム内のウィジェット ---
        info_text = "キャラクターを選択または新規作成してください\n(リストにキャラクターZIPをD&Dで追加できます)"
        ttk.Label(main_frame, text=info_text, font=self.font_title, justify="center").pack(pady=(0, self.padding_large))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(expand=True, fill="both", pady=self.padding_normal)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.project_listbox = Listbox(list_frame, font=self.font_list)
        self.project_listbox.grid(row=0, column=0, sticky="nsew")
        self.project_listbox.bind("<Double-Button-1>", lambda e: self.edit_project())

        # --- D&Dの受付設定を追加 ---
        self.project_listbox.drop_target_register(DND_FILES)
        self.project_listbox.dnd_bind('<<Drop>>', self.on_character_drop)

        scrollbar = Scrollbar(list_frame, orient="vertical", command=self.project_listbox.yview)
        self.project_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.refresh_project_list()

        button_style = ttk.Style()
        button_style.configure("App.TButton", font=self.font_normal, padding=self.padding_small)
        
        # ボタンフレームを2段にする
        top_button_frame = ttk.Frame(button_frame)
        top_button_frame.pack(fill="x", expand=True)
        bottom_button_frame = ttk.Frame(button_frame)
        bottom_button_frame.pack(fill="x", expand=True, pady=(self.padding_small, 0))

        ttk.Button(top_button_frame, text="新規作成...", command=self.new_project, style="App.TButton").pack(side="left", expand=True, fill="x", padx=(0, self.padding_small))
        ttk.Button(top_button_frame, text="選択したキャラクターを編集", command=self.edit_project, style="App.TButton").pack(side="left", expand=True, fill="x")

        ttk.Button(bottom_button_frame, text="キャラクターを探す(Web)", command=self.open_character_repo, style="App.TButton").pack(side="left", expand=True, fill="x", padx=(0, self.padding_small))
        ttk.Button(bottom_button_frame, text="キャラクターフォルダを開く", command=self.open_characters_folder, style="App.TButton").pack(side="left", expand=True, fill="x", padx=(0, self.padding_small))
        ttk.Button(bottom_button_frame, text="更新", command=self.refresh_project_list, style="App.TButton").pack(side="left", expand=True, fill="x")

    def on_character_drop(self, event):
        """キャラクターリストにファイルがドロップされたときの処理"""

        # ドロップされたファイルパスの生データを取得
        file_data = event.data
        
        # 正規表現を使い、{...}で囲まれたパスか、スペースを含まないパスをリストとして抽出
        # これにより、スペースを含む単一のファイルパスが分割されるのを防ぐ
        paths = re.findall(r'\{[^{}]+\}|\S+', file_data)
        
        if not paths:
            messagebox.showwarning("エラー", "ドロップされたファイルパスを取得できませんでした。", parent=self)
            return

        # 複数ドロップされた場合も、最初のファイルパスのみを処理対象とする
        # パスを囲む波括弧が残っている場合は取り除く
        filepath = paths[0].strip('{}')
        
        if not filepath.lower().endswith('.zip'):
            messagebox.showwarning("ファイル形式エラー", "キャラクターのZIPファイルをドロップしてください。", parent=self)
            return
        
        print(f"ドロップされたZIPファイル: {filepath}")
        
        # インストーラーに処理を委譲
        self.installer.install_from_zip(filepath)
        
        # インストールが完了したらリストを更新
        self.refresh_project_list()

    def open_characters_folder(self):
        """
        キャラクタープロジェクトが格納されているフォルダをOSのファイルマネージャーで開きます。
        """
        folder_path = self.project_manager.characters_dir
        if not os.path.isdir(folder_path):
            messagebox.showerror("エラー", f"キャラクターフォルダが見つかりません:\n{folder_path}", parent=self)
            return
        
        try:
            current_os = platform.system()
            if current_os == "Windows":
                subprocess.run(['explorer', os.path.normpath(folder_path)])
            elif current_os == "Darwin": # macOS
                subprocess.run(['open', folder_path])
            else: # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{e}", parent=self)

    def open_character_repo(self):
        """キャラクター配布リポジトリのIssueページをブラウザで開く"""
        webbrowser.open(self.character_repo_url)

    def refresh_project_list(self):
        """キャラクターリストを最新の状態に更新します。"""
        self.project_listbox.delete(0, tk.END)
        projects = self.project_manager.list_projects()
        for project_name in projects:
            self.project_listbox.insert(tk.END, project_name)

    def new_project(self):
        """新規キャラクター作成のプロセスを開始します。"""
        project_id = simpledialog.askstring("新規作成", "新しいキャラクターのIDを入力してください:", parent=self)
        if not project_id:
            return

        try:
            self.project_manager.create_new_project(project_id)
            self.refresh_project_list()
            messagebox.showinfo("成功", f"キャラクター '{project_id}' のプロジェクトを作成しました。\n続けて編集画面を開きます。", parent=self)
            self.open_editor_and_wait(project_id)
        except ValueError as e:
            messagebox.showerror("エラー", str(e), parent=self)

    def edit_project(self):
        """選択した既存キャラクターの編集画面を開きます。"""
        selected_indices = self.project_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "編集するキャラクターをリストから選択してください。", parent=self)
            return
        
        project_id = self.project_listbox.get(selected_indices[0])
        self.open_editor_and_wait(project_id)

    def open_editor_and_wait(self, project_id):
        """エディタウィンドウを開き、それが閉じられるまでメインウィンドウを無効化する"""
        editor = EditorWindow(self, project_id)
        self.attributes("-disabled", True)
        self.wait_window(editor)
        self.attributes("-disabled", False)
        self.deiconify()
        self.lift()
        self.focus_force()
