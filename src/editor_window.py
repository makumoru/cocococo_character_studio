# src/editor_window.py

import tkinter as tk
from tkinter import ttk, messagebox, font
from tkinter import colorchooser
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import os
import threading
import requests
import platform
if platform.system() == "Windows":
    import winsound
import traceback
import webbrowser
import subprocess

from .character_data import CharacterData
from .github_uploader import GithubUploader
from .settings_window import SettingsWindow 
from .tabs.tab_basic_settings import TabBasicSettings
from .tabs.tab_sharing_settings import TabSharingSettings
from .tabs.tab_voice_settings import TabVoiceSettings
from .tabs.tab_costume import TabCostumes
from .tabs.tab_expressions import TabExpressions
from .tabs.tab_touch_areas import TabTouchAreas
from .tabs.tab_favorability import TabFavorability
from .tabs.tab_events import TabEvents

class EditorDNDWindow(tk.Toplevel, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class EditorWindow(EditorDNDWindow):
    def __init__(self, parent, project_id: str):
        try:
            super().__init__(parent)
            self.app = parent
            self.project_id = project_id
            
            self.title(f"キャラクターエディタ - [{self.project_id}]")
            
            self.grab_set()

            self.transient(parent)
            self.grab_set()

            self.character_data = CharacterData(self.project_id, base_path=self.app.base_path)
            
            self.image_preview_label = None
            self.original_pil_image = None
            self.display_tk_image = None
            self.current_preview_filepath = None # プレビュー中の画像のパスを保持
            
            self.speaker_data_cache = {} 
            self.selected_engine = tk.StringVar()
            self.selected_speaker = tk.StringVar()
            self.selected_style = tk.StringVar()
            
            self.tabs = {}

            self.current_costume_id = tk.StringVar()
            self.current_costume_id.trace_add("write", self.on_costume_id_change)

            self.drawing_mode = False
            self.draw_callback = None
            self.start_x = self.start_y = 0
            self.current_rect = None
            self.image_canvas = None
            self.notebook = None
            self.active_tab_before_draw = None
            self.highlighted_rects = [] 
            self.highlighted_censor_rects = [] # 黒塗りハイライト用

            self.eyedropper_mode = False
            self.eyedropper_target_label = None

            self.preview_mode_label = None
            self.placeholder_font = font.Font(font=self.app.font_normal)

            self.github_uploader = GithubUploader(os.path.join(self.app.base_path, 'config.ini'))

            self.create_widgets()
            
            # --- ウィンドウサイズの自動計算 ---
            self.update_idletasks() # UIウィジェットの要求サイズを計算させる
            
            # ディスプレイサイズを取得
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # ウィンドウの初期サイズをディスプレイの80%程度に設定
            initial_width = int(screen_width * 0.8)
            initial_height = int(screen_height * 0.8)
            
            # ウィンドウの最小サイズを設定
            self.minsize(int(screen_width * 0.5), int(screen_height * 0.5))

            # ウィンドウサイズを設定
            self.geometry(f"{initial_width}x{initial_height}")

            self.load_data_to_ui()

            self.bind("<Configure>", self.on_window_resize)
            self.protocol("WM_DELETE_WINDOW", self.on_close)

        except Exception as e:
            # エラーが発生した場合、その内容をメッセージボックスで表示
            error_info = f"エディタの初期化中に致命的なエラーが発生しました。\n\n"
            error_info += f"エラーの種類: {type(e).__name__}\n"
            error_info += f"エラーメッセージ: {e}\n\n"
            error_info += "--- トレースバック ---\n"
            error_info += traceback.format_exc()
            
            messagebox.showerror("初期化エラー", error_info)
            self.destroy() # エラーウィンドウを閉じる

    def create_widgets(self):
        style = ttk.Style(self)
        style.configure("TNotebook.Tab", font=self.app.font_normal, padding=[self.app.padding_small, self.app.padding_small])
        style.configure("TButton", font=self.app.font_normal, padding=self.app.padding_small)

        # --- ボタンフレーム (ウィンドウ下部に固定) ---
        self.button_frame = ttk.Frame(self, padding=(self.app.padding_normal, self.app.padding_small, self.app.padding_normal, self.app.padding_normal))
        self.button_frame.pack(side="bottom", fill="x")

        # --- メインフレーム (残りの領域全体を占める) ---
        self.main_frame = ttk.Frame(self, padding=(self.app.padding_small, self.app.padding_small, self.app.padding_small, 0))
        self.main_frame.pack(expand=True, fill="both")
        # 左パネル(0)と右パネル(1)の伸縮比率を設定 (例: 1:3)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=3)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # 左パネル (main_frameの子、固定エリア)
        left_panel = ttk.Frame(self.main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, self.app.padding_normal))
        left_panel.rowconfigure(3, weight=1)  # image_preview_frameが伸縮するように行を調整
        left_panel.columnconfigure(0, weight=1)

        # 衣装セレクタ (left_panelの子)
        costume_selector_frame = ttk.Frame(left_panel)
        costume_selector_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.app.padding_small))
        costume_selector_frame.columnconfigure(1, weight=1)
        ttk.Label(costume_selector_frame, text="編集中の衣装:", font=self.app.font_normal).grid(row=0, column=0, sticky="w")
        self.costume_selector = ttk.Combobox(costume_selector_frame, textvariable=self.current_costume_id, state="readonly", font=self.app.font_normal)
        self.costume_selector.grid(row=0, column=1, sticky="ew", padx=self.app.padding_small)
        self.costume_selector.bind("<<ComboboxSelected>>", self.sync_costume_tab_selection)

        # プレビューモードラベル (left_panelの子)
        self.preview_mode_label = ttk.Label(left_panel, text="プレビュー対象: なし", font=self.app.font_small)
        self.preview_mode_label.grid(row=1, column=0, sticky="w", pady=(self.app.padding_small, 0))

        # サムネイル説明ラベル (left_panelの子)
        self.thumbnail_info_label = ttk.Label(left_panel, text="", font=self.app.font_small, foreground="blue")
        self.thumbnail_info_label.grid(row=2, column=0, sticky="w", pady=(2, 2))

        # 画像プレビューフレーム (left_panelの子)
        image_preview_frame = ttk.Frame(left_panel, relief="solid", borderwidth=self.app.border_width_normal)
        image_preview_frame.grid(row=3, column=0, sticky="nsew")
        
        self.image_canvas = tk.Canvas(image_preview_frame, bg="white", highlightthickness=0)
        self.image_canvas.pack(expand=True, fill="both")
        
        self.image_canvas.drop_target_register(DND_FILES)
        self.image_canvas.dnd_bind('<<Drop>>', self.on_image_drop)
        self.image_canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.image_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.image_canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

        # 右パネル (Notebookを配置、タブの中がスクロール対象)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=1, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # タブの作成
        self.tabs['basic'] = TabBasicSettings(self.notebook, self)
        self.tabs['voice'] = TabVoiceSettings(self.notebook, self)
        self.tabs['costumes'] = TabCostumes(self.notebook, self)
        self.tabs['expressions'] = TabExpressions(self.notebook, self)
        self.tabs['touch'] = TabTouchAreas(self.notebook, self)
        self.tabs['favor'] = TabFavorability(self.notebook, self)
        self.tabs['events'] = TabEvents(self.notebook, self)
        self.tabs['sharing'] = TabSharingSettings(self.notebook, self)

        self.notebook.add(self.tabs['basic'], text="基本設定")
        self.notebook.add(self.tabs['voice'], text="音声設定")
        self.notebook.add(self.tabs['costumes'], text="衣装")
        self.notebook.add(self.tabs['expressions'], text="表情")
        self.notebook.add(self.tabs['touch'], text="タッチエリア")
        self.notebook.add(self.tabs['favor'], text="好感度設定")
        self.notebook.add(self.tabs['events'], text="イベント")
        self.notebook.add(self.tabs['sharing'], text="共有設定")
        
        # ボタンフレーム内のウィジェット (main_frame の後に定義)
        ttk.Button(self.button_frame, text="保存して閉じる", command=self.save_and_close).pack(side="right", padx=self.app.padding_small)
        ttk.Button(self.button_frame, text="保存", command=self.save_settings).pack(side="right", padx=self.app.padding_small)
        ttk.Button(self.button_frame, text="キャンセル", command=self.on_close).pack(side="right", padx=self.app.padding_small)
        # GitHub共有ボタンを左側に配置
        self.share_button = ttk.Button(self.button_frame, text="GitHubに共有...", command=self.share_on_github)
        self.share_button.pack(side="left", padx=self.app.padding_small)

    def load_data_to_ui(self):
        print("全タブのデータをUIに読み込んでいます...")
        for tab in self.tabs.values():
            tab.load_data()

    def collect_data_from_ui(self):
        print("全タブからデータを収集しています...")
        for tab in self.tabs.values():
            tab.collect_data()

    def save_settings(self):
        try:
            self.collect_data_from_ui()
            self.character_data.save()
            messagebox.showinfo("保存完了", f"キャラクター '{self.project_id}' の設定を保存しました。", parent=self)
            self.master.refresh_project_list()
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定の保存中にエラーが発生しました:\n{e}", parent=self)

    def save_and_close(self):
        try:
            self.collect_data_from_ui()
            self.character_data.save()
            messagebox.showinfo("成功", f"キャラクター '{self.project_id}' の設定を保存しました。", parent=self)
            self.master.refresh_project_list()
            self.destroy()
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定の保存中にエラーが発生しました:\n{e}", parent=self)

    def share_on_github(self):
        """「GitHubに共有」ボタンが押されたときの処理"""

        # --- NSFW検証 ---
        # 検証の前に、UIの最新の状態をデータオブジェクトに反映させる
        self.collect_data_from_ui()
        is_nsfw = self.character_data.config.getboolean('INFO', 'IS_NSFW', fallback=False)
        censor_rects = self.character_data.get_thumbnail_censor_rects()
        
        if is_nsfw and not censor_rects:
            messagebox.showerror(
                "検証エラー",
                "NSFW属性が有効になっていますが、サムネイルの黒塗り修正エリアが1つも設定されていません。\n\n"
                "「黒塗りエリアを追加」ボタンから、画像を修正してください。",
                parent=self
            )
            return  # 共有処理を中断

        # ダイアログメッセージを変更し、保存処理が含まれることを明記する
        if not messagebox.askyesno("GitHub共有の確認",
            "現在の編集内容をすべて保存し、キャラクターをGitHubで共有します。\n\n"
            "・「共有設定」タブの内容が readme.txt に保存されます。\n"
            "・character.ini と画像ファイルがZIP圧縮されます。\n\n"
            "続行しますか？", parent=self):
            return

        self.share_button.config(state="disabled", text="準備中...")
        self.update_idletasks()

        # ワーカースレッドで重い処理を実行
        threading.Thread(target=self._execute_share, daemon=True).start()

    def _execute_share(self):
        """保存、API通信、ZIP作成を連続して行うワーカースレッド"""
        try:
            # 1. ワーカースレッドの先頭で、UIからのデータ収集と最初の保存処理を行う
            self.collect_data_from_ui()
            self.character_data.save()

            # 2. PATやIssueの本文など、API通信に必要な情報を準備する
            pat = self.github_uploader.get_pat()
            if not pat:
                raise ValueError("TOKEN_NOT_SET")

            # SYSTEM_NAMEが空ならCHARACTER_NAME、それも空ならproject_idをフォールバックとして使用
            system_name = self.character_data.get('INFO', 'SYSTEM_NAME')
            character_name = self.character_data.get('INFO', 'CHARACTER_NAME', self.project_id)
            title = system_name or character_name

            body = self.character_data.get_readme_content()
            if not body.strip():
                raise ValueError("「共有設定」タブの説明文が空です。キャラクター紹介文を記述してください。")
            
            # --- 3. Issueの作成または更新を先に行う ---
            # 共有対象のIssue参照を確認
            saved_number, saved_url = self.character_data.get_issue_reference()
            issue_number = None
            if saved_number:
                issue_number = saved_number
            elif saved_url:
                import re
                mref = re.search(r'/issues/(\d+)', saved_url)
                if mref:
                    try:
                        issue_number = int(mref.group(1))
                    except ValueError:
                        issue_number = None
            
            # ラベル自動付与
            labels = ["pending"]
            if self.character_data.config.getboolean('INFO', 'IS_DERIVATIVE', fallback=False):
                labels.append("derivative-work")
            if self.character_data.config.getboolean('INFO', 'IS_NSFW', fallback=False):
                labels.append("nsfw")

            is_update = False
            if issue_number:
                # 既存Issueがある場合は本文を上書き更新
                response_json = self.github_uploader.update_issue_body(
                    issue_number=issue_number, body=body, pat=pat, title=title, labels=labels
                )
                issue_url = response_json.get("html_url") or saved_url or f"https://github.com/{self.github_uploader.REPO_OWNER}/{self.github_uploader.REPO_NAME}/issues/{issue_number}"
                is_update = True
            else:
                # 新規作成（初期状態は Closed）
                response_json = self.github_uploader.create_issue_initially_closed(
                    title, body, pat, labels=labels
                )
                issue_url = response_json.get("html_url")
                is_update = False

            # --- 4. Issue情報をcharacter.iniに保存する ---
            try:
                number = response_json.get("number")
                if number and issue_url:
                    self.character_data.set_issue_reference(issue_number=number, issue_url=issue_url)
                    self.character_data.save() # ★★★ ここで再度保存
                    print(f"Issue情報 (Number: {number}) を character.ini に保存しました。")
            except Exception as e:
                # 保存に失敗しても処理は続行するが、警告は出しておく
                print(f"[警告] Issue参照情報のiniファイルへの保存に失敗しました: {e}")

            # --- 5. 最新のiniファイルを含んだ状態でZIPを作成する ---
            zip_paths, censored_thumbnail_path = self.github_uploader.create_character_zip(
                self.character_data, self.character_data.base_path, self.project_id, character_name=character_name)

            # --- 6. 成功時のUIコールバックを呼び出す ---
            self.after(0, self._on_share_success, issue_url, zip_paths, is_update, censored_thumbnail_path)

        except ValueError as e:
            # 例外処理
            error_str = str(e)
            if "ファイルサイズ超過エラー" in error_str or "作者不一致エラー" in error_str:
                self.after(0, self._on_share_failure, error_str, False)
            elif error_str == "TOKEN_NOT_SET" or "認証に失敗" in error_str:
                self.after(0, self._on_share_failure, error_str, True)
            else:
                self.after(0, self._on_share_failure, f"共有に失敗しました。\n\n詳細: {error_str}", False)
        except Exception as e:
            # その他のAPIエラーなど
            error_message = f"共有に失敗しました。\n\n詳細: {e}"
            self.after(0, self._on_share_failure, error_message, False)

    def _on_share_success(self, issue_url, zip_paths, is_update, censored_thumbnail_path):
        """共有成功後のUI処理"""
        self.share_button.config(state="normal", text="GitHubに共有...")
        
        # ブラウザでIssueページを開く
        webbrowser.open(issue_url)
        
        # ZIPファイルと黒塗りサムネイルが保存された「フォルダ」を開く
        output_folder = None
        if zip_paths:
            output_folder = os.path.dirname(zip_paths[0])
        elif censored_thumbnail_path:
            output_folder = os.path.dirname(censored_thumbnail_path)

        if output_folder:
            if platform.system() == "Windows":
                subprocess.run(['explorer', os.path.normpath(output_folder)])
            elif platform.system() == "Darwin": # macOS
                 subprocess.run(['open', output_folder])
            else: # Linux
                 subprocess.run(['xdg-open', output_folder])

        # --- メッセージボックスだけを最前面に表示するための措置 ---
        # 1. 一時的なToplevelウィンドウを作成
        topmost_parent = tk.Toplevel(self)
        # 2. この一時ウィンドウを最前面に設定
        topmost_parent.attributes("-topmost", True)
        # 3. 画面に表示されないように隠す
        topmost_parent.withdraw()
        
        # --- メッセージの組み立てを「元の形式」に戻す ---
        # アップロードが必要なファイルのリストを作成
        files_to_upload = []
        if censored_thumbnail_path and os.path.exists(censored_thumbnail_path):
            files_to_upload.append(os.path.basename(censored_thumbnail_path))
        if zip_paths:
            files_to_upload.extend(os.path.basename(p) for p in zip_paths)

        # ファイルの数に応じて元のメッセージ形式を復元
        message_body = ""
        if len(files_to_upload) == 1:
            # 単一ファイルの場合の元のメッセージ
            message_body = (
                "開いたブラウザのコメント欄に、\n"
                f"今エクスプローラーで表示された '{files_to_upload[0]}' をドラッグ＆ドロップしてください。"
            )
        elif len(files_to_upload) > 1:
            # 複数ファイルの場合の元のメッセージ
            # 分割の理由は必ずしもサイズだけではないため、冒頭文は汎用的にする
            files_list_str = "\n".join([f"・ {f}" for f in files_to_upload])
            message_body = (
                "開いたブラウザのコメント欄に、\n"
                "今エクスプローラーで表示された、以下のファイルをすべてドラッグ＆ドロップしてください：\n\n"
                f"{files_list_str}"
            )
        else:
            # 念の為ファイルがない場合のフォールバック
            message_body = "Issueの作成が完了しました。"

        final_message = (
            "GitHubにIssue（初期状態: Closed）を作成しました。\n\n"
            f"{message_body}\n\n"
            "Actions が検証し、OKになったタイミングで Issue は自動的に Open になります。"
        )

        messagebox.showinfo(
            "Issue作成完了",
            final_message,
            parent=topmost_parent # 親を一時ウィンドウにする
        )
        
        # 4. メッセージボックスが閉じられた後、一時ウィンドウを破棄
        topmost_parent.destroy()

    def _on_share_failure(self, error_message, open_settings=False):
        """共有失敗後のUI処理。トークンエラーの場合は設定画面を開く"""
        self.share_button.config(state="normal", text="GitHubに共有...")

        if open_settings:
            # 失敗理由のメッセージボックスを表示
            messagebox.showwarning("設定エラー",
                "GitHub Personal Access Tokenが設定されていないか、無効です。\n\n"
                "設定画面を開きますので、トークンを設定してください。", parent=self)
            # 設定ウィンドウを開く
            SettingsWindow(self.app, self.app.config_file)
        else:
            # 通常のエラーメッセージを表示
            messagebox.showerror("エラー", error_message, parent=self)

    def on_image_drop(self, event):
        filepath = event.data.strip('{}')
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            messagebox.showwarning("ファイル形式エラー", "PNG, JPG, BMP, GIF形式の画像ファイルをドロップしてください。", parent=self)
            return

        try:
            # 現在のタブが共有設定タブかどうかで処理を分岐
            selected_tab_widget = self.nametowidget(self.notebook.select())
            
            if selected_tab_widget == self.tabs.get('sharing', None):
                # --- サムネイルを上書きする処理 ---
                dropped_image = Image.open(filepath).convert("RGBA")
                save_path = os.path.join(self.character_data.base_path, "thumbnail.png")
                dropped_image.save(save_path, "PNG")
                
                # 黒塗り矩形データをリセット
                self.character_data.update_thumbnail_censor_rects([])
                # UIのリストもクリア
                sharing_tab = self.tabs['sharing']
                for item in sharing_tab.censor_tree.get_children():
                    sharing_tab.censor_tree.delete(item)
                
                print(f"サムネイル画像を更新し、黒塗り設定をリセットしました: {save_path}")
                self.update_preview_image(save_path) # プレビューを即時更新
                messagebox.showinfo("成功", "サムネイル画像を更新し、関連する黒塗り設定をリセットしました。", parent=self)
            else:
                # --- 従来の基準画像を保存する処理 ---
                costume_id = self.current_costume_id.get()
                if not costume_id:
                    messagebox.showerror("エラー", "画像を登録する衣装が選択されていません。", parent=self)
                    return

                dropped_image = Image.open(filepath).convert("RGBA")
                save_dir = os.path.join(self.character_data.base_path, costume_id)
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, "normal_close.png")
                dropped_image.save(save_path, "PNG")
                self.original_pil_image = dropped_image
                self.current_preview_filepath = save_path
                print(f"基準画像を保存しました: {save_path}")
                self.redraw_image_preview()

        except Exception as e:
            messagebox.showerror("画像処理エラー", f"画像の処理中にエラーが発生しました:\n{e}", parent=self)
            self.original_pil_image = None
            self.current_preview_filepath = None

    def redraw_image_preview(self):
        self.image_canvas.delete("all")
        if self.original_pil_image is None:
            self.after(20, self._draw_placeholder_text)
            return

        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        if canvas_w < 20 or canvas_h < 20:
            self.after(50, self.redraw_image_preview)
            return

        img_copy = self.original_pil_image.copy()
        img_copy.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        self.display_tk_image = ImageTk.PhotoImage(img_copy)
        x_pos = (canvas_w - self.display_tk_image.width()) / 2
        y_pos = (canvas_h - self.display_tk_image.height()) / 2
        self.image_canvas.create_image(x_pos, y_pos, image=self.display_tk_image, anchor="nw")

        # --- 黒塗り矩形の描画 ---
        thumbnail_path = os.path.join(self.character_data.base_path, "thumbnail.png")
        if self.current_preview_filepath and os.path.normpath(self.current_preview_filepath) == os.path.normpath(thumbnail_path):
            # 共有タブのリストから直接データを取得して描画する
            censor_rects_str = [self.tabs['sharing'].censor_tree.item(item, 'values')[0] for item in self.tabs['sharing'].censor_tree.get_children()]
            censor_rects = [eval(s) for s in censor_rects_str if s]

            if censor_rects:
                img_w, img_h = self.display_tk_image.width(), self.display_tk_image.height()
                if img_w > 0 and img_h > 0:
                    scale_w = img_w / self.original_pil_image.width
                    scale_h = img_h / self.original_pil_image.height
                    offset_x = (canvas_w - img_w) / 2
                    offset_y = (canvas_h - img_h) / 2
                    for rect in censor_rects:
                        # ハイライト対象かどうかで色を決定
                        color = "blue" if rect in self.highlighted_censor_rects else "black"
                        
                        disp_x1 = int(rect[0] * scale_w + offset_x)
                        disp_y1 = int(rect[1] * scale_h + offset_y)
                        disp_x2 = int(rect[2] * scale_w + offset_x)
                        disp_y2 = int(rect[3] * scale_h + offset_y)
                        self.image_canvas.create_rectangle(disp_x1, disp_y1, disp_x2, disp_y2, fill=color, outline="")

        self.after(10, self.redraw_highlighted_rects)

    def _draw_placeholder_text(self):
        self.image_canvas.delete("all")
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        text = f"衣装 '{self.current_costume_id.get()}' の\n基準画像をD&D"
        self.image_canvas.create_text(canvas_w/2, canvas_h/2, text=text, justify="center", font=self.placeholder_font)

    def on_window_resize(self, event):
        self.after(50, self.redraw_image_preview)

    def update_costume_selector(self):
        costumes = self.character_data.get_costumes()
        self.costume_selector['values'] = [c['id'] for c in costumes]

    def on_costume_id_change(self, *args):
        # 描画モード中はプレビューの自動更新を抑制する
        if self.drawing_mode:
            return

        costume_id = self.current_costume_id.get()
        if not costume_id:
            return
            
        # プレビュー画像を更新
        try:
            # 現在のタブが共有設定タブでなければ、基準画像を更新する
            selected_tab_widget = self.nametowidget(self.notebook.select())
            if selected_tab_widget != self.tabs.get('sharing'):
                self.set_preview_to_character_base(costume_id)
        except (tk.TclError, KeyError):
            # UI初期化中などでエラーになる場合は、とりあえず更新を試みる
            self.set_preview_to_character_base(costume_id)

        # 衣装の変更を関連するタブに通知し、データを再読み込みさせる
        # .winfo_exists() は、タブが破棄されていないことを確認するための安全策です。
        
        # 表情タブを更新
        if 'expressions' in self.tabs and self.tabs['expressions'].winfo_exists():
            self.tabs['expressions'].load_data()
        
        # タッチエリアタブを更新
        if 'touch' in self.tabs and self.tabs['touch'].winfo_exists():
            self.tabs['touch'].load_data()

    def on_tab_changed(self, event):
        try:
            # <<NotebookTabChanged>> イベントが発生した時点での選択タブウィジェットを取得
            selected_tab_widget = self.nametowidget(self.notebook.select())
        except (tk.TclError, KeyError):
            return  # ウィンドウ破棄中などに発生する可能性のあるエラーを無視

        def _update_preview():
            # afterコールバック実行時にウィンドウが存在するか再確認
            if not self.winfo_exists(): return

            # 他のタブに移動したら、黒塗りハイライトをクリア
            if selected_tab_widget != self.tabs.get('sharing'):
                self.highlighted_censor_rects.clear()

            # 表情タブが表示された際に、プレビューエリアの再描画をトリガーする。
            if selected_tab_widget == self.tabs.get('expressions'):
                self.tabs['expressions'].update_dnd_previews()

            # サムネイル説明ラベルの表示/非表示を切り替え
            thumbnail_info_text = ""
            if selected_tab_widget == self.tabs.get('sharing'):
                thumbnail_info_text = "この画像は共有時のサムネイル画像です。\nドラッグアンドドロップで変更できます。"
            self.thumbnail_info_label.config(text=thumbnail_info_text)

            # プレビュー画像の切り替え
            if selected_tab_widget == self.tabs.get('sharing'):
                self.set_preview_to_thumbnail()
            elif selected_tab_widget == self.tabs.get('favor'):
                # 好感度タブに切り替えた際は、選択中のハート画像のプレビューを試みる
                self.tabs['favor'].on_heart_select()
            else:
                # それ以外のタブはキャラクターの基準画像を表示
                self.set_preview_to_character_base(self.current_costume_id.get())
        
        # UIの状態が確定するのを待ってからプレビューを更新
        self.after(20, _update_preview)

    def set_preview_to_character_base(self, costume_id):
        # 描画モード中は、この関数によるプレビューの変更を一切禁止する
        if self.drawing_mode:
            return
        if not costume_id: return
        self.preview_mode_label.config(text=f"プレビュー対象: キャラクター基準画像")
        filepath = os.path.join(self.character_data.base_path, costume_id, "normal_close.png")
        self.update_preview_image(filepath)
        if 'touch' in self.tabs and self.notebook.select() != self.tabs['touch'].winfo_parent():
             self.clear_highlights()
    
    def set_preview_to_thumbnail(self):
        """プレビュー画像をサムネイル(thumbnail.png)に設定する。"""
        self.preview_mode_label.config(text="プレビュー対象: サムネイル (thumbnail.png)")
        filepath = os.path.join(self.character_data.base_path, "thumbnail.png")
        
        if os.path.exists(filepath):
            self.update_preview_image(filepath)
        else:
            # サムネイルが存在しない場合は、代わりにキャラクターの基準画像を表示する
            self.set_preview_to_character_base(self.current_costume_id.get())

        # 共有タブではハイライトは不要なのでクリアする
        if 'touch' in self.tabs:
             self.clear_highlights()

    def set_preview_to_heart_image(self, filename, filepath):
        self.preview_mode_label.config(text=f"プレビュー対象: ハート画像 ({filename})")
        self.update_preview_image(filepath)

    def update_preview_image(self, filepath):
        self.current_preview_filepath = filepath
        if filepath and os.path.exists(filepath):
            try:
                self.original_pil_image = Image.open(filepath).convert("RGBA")
            except Exception as e:
                print(f"プレビュー画像読込エラー: {e}")
                self.original_pil_image = None
        else:
            self.original_pil_image = None
        self.redraw_image_preview()

    def sync_costume_tab_selection(self, event=None):
        if 'costumes' in self.tabs:
            self.tabs['costumes'].select_costume_by_id(self.current_costume_id.get())

    def enter_rect_drawing_mode(self, callback):
        if self.original_pil_image is None:
            messagebox.showwarning("エラー", "プレビューに描画対象の画像が表示されていません。", parent=self)
            return
        self.drawing_mode = True
        self.draw_callback = callback
        self.image_canvas.config(cursor="crosshair")
        self.active_tab_before_draw = self.notebook.select()
        for i in range(len(self.tabs)):
            self.notebook.tab(i, state="disabled")
        self.redraw_image_preview()
        self.image_canvas.focus_set()
        self.after(20, self._draw_drawing_mode_text)
        self.grab_set()
        self.bind_all("<Escape>", self.cancel_drawing_mode)

    def _draw_drawing_mode_text(self):
        if not self.drawing_mode: return
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        bg_height = self.app.font_normal[1] + self.app.padding_normal * 2
        self.image_canvas.create_rectangle(0, canvas_h - bg_height, canvas_w, canvas_h, fill="black", outline="", tags="draw_mode_text_bg")
        self.image_canvas.create_text(canvas_w / 2, canvas_h - (bg_height / 2), 
                                      text="プレビュー上でドラッグしてエリアを指定 (Escキーでキャンセル)", 
                                      fill="white", font=self.app.font_normal, tags="draw_mode_text")

    def exit_drawing_mode(self):
        if not self.drawing_mode: return
        self.drawing_mode = False
        self.draw_callback = None
        self.image_canvas.config(cursor="")
        if self.notebook.winfo_exists():
            for i in range(len(self.tabs)):
                self.notebook.tab(i, state="normal")
        if self.active_tab_before_draw:
            self.notebook.select(self.active_tab_before_draw)
            self.active_tab_before_draw = None
        self.image_canvas.delete("draw_mode_text_bg")
        self.image_canvas.delete("draw_mode_text")
        self.unbind_all("<Escape>")
        self.grab_release()

    def cancel_drawing_mode(self, event=None):
        if self.drawing_mode:
            if self.current_rect:
                self.image_canvas.delete(self.current_rect)
                self.current_rect = None
            self.exit_drawing_mode()

    def on_mouse_press(self, event):
        # --- MODIFIED: スポイト関連の処理を削除 ---
        if self.drawing_mode:
            self.start_x = event.x
            self.start_y = event.y
            if self.current_rect: self.image_canvas.delete(self.current_rect)
            self.current_rect = self.image_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2, dash=(4, 4))

    def on_mouse_drag(self, event):
        if not self.drawing_mode or not self.current_rect: return
        self.image_canvas.coords(self.current_rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_release(self, event):
        if not self.drawing_mode: return
        callback = self.draw_callback
        self.exit_drawing_mode()
        if callback is None: return
        if self.current_rect:
            self.image_canvas.delete(self.current_rect)
            self.current_rect = None
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        if abs(x1 - x2) < 5 or abs(y1 - y2) < 5:
            callback(None)
            return
        canvas_w, canvas_h = self.image_canvas.winfo_width(), self.image_canvas.winfo_height()
        if self.display_tk_image is None:
            callback(None); return
        img_w, img_h = self.display_tk_image.width(), self.display_tk_image.height()
        scale_w = self.original_pil_image.width / img_w
        scale_h = self.original_pil_image.height / img_h
        offset_x = (canvas_w - img_w) / 2
        offset_y = (canvas_h - img_h) / 2
        if x2 < offset_x or x1 > offset_x + img_w or y2 < offset_y or y1 > offset_y + img_h:
             callback(None); return
        orig_x1 = int((x1 - offset_x) * scale_w)
        orig_y1 = int((y1 - offset_y) * scale_h)
        orig_x2 = int((x2 - offset_x) * scale_w)
        orig_y2 = int((y2 - offset_y) * scale_h)
        orig_x1 = max(0, orig_x1)
        orig_y1 = max(0, orig_y1)
        orig_x2 = min(self.original_pil_image.width, orig_x2)
        orig_y2 = min(self.original_pil_image.height, orig_y2)
        callback((orig_x1, orig_y1, orig_x2, orig_y2))

    def highlight_touch_areas(self, rects: list):
        self.clear_highlights()
        if self.display_tk_image is None or self.original_pil_image is None: return
        canvas_w, canvas_h = self.image_canvas.winfo_width(), self.image_canvas.winfo_height()
        img_w, img_h = self.display_tk_image.width(), self.display_tk_image.height()
        if img_w == 0 or img_h == 0: return
        scale_w = img_w / self.original_pil_image.width
        scale_h = img_h / self.original_pil_image.height
        offset_x = (canvas_w - img_w) / 2
        offset_y = (canvas_h - img_h) / 2
        for rect in rects:
            orig_x1, orig_y1, orig_x2, orig_y2 = rect
            disp_x1 = int(orig_x1 * scale_w + offset_x)
            disp_y1 = int(orig_y1 * scale_h + offset_y)
            disp_x2 = int(orig_x2 * scale_w + offset_x)
            disp_y2 = int(orig_y2 * scale_h + offset_y)
            rect_id = self.image_canvas.create_rectangle(disp_x1, disp_y1, disp_x2, disp_y2, fill="cyan", stipple="gray50", outline="")
            self.highlighted_rects.append(rect_id)

    def clear_highlights(self):
        for rect_id in self.highlighted_rects:
            self.image_canvas.delete(rect_id)
        self.highlighted_rects = []
    
    def redraw_highlighted_rects(self):
        if 'touch' in self.tabs:
            self.tabs['touch'].update_highlight_from_selection()
    
    def highlight_censor_rects(self, rects: list):
        """共有タブから呼び出され、ハイライトする黒塗り矩形を設定する"""
        self.highlighted_censor_rects = rects

    def enter_eyedropper_mode(self, target_label, target_canvas=None, pil_image=None, tk_image=None):
        canvas_to_use = target_canvas if target_canvas is not None else self.image_canvas
        pil_image_to_use = pil_image if pil_image is not None else self.original_pil_image
        tk_image_to_use = tk_image if tk_image is not None else self.display_tk_image
        
        if pil_image_to_use is None or tk_image_to_use is None:
            messagebox.showwarning("エラー", "色を抽出するための画像が表示されていません。", parent=self)
            return

        self.eyedropper_mode = True
        self.eyedropper_target_label = target_label
        self.eyedropper_target_canvas = canvas_to_use
        self.eyedropper_pil_image = pil_image_to_use
        self.eyedropper_tk_image = tk_image_to_use

        canvas_to_use.config(cursor="tcross")
        
        # --- グラブとバインドのロジックを変更 ---
        # どのウィンドウがイベントを掴むかを明確にする
        grabber_window = canvas_to_use.winfo_toplevel()
        grabber_window.grab_set()
        
        # クリックイベントを一時的に乗っ取る
        self.temp_mouse_press_binding_id = grabber_window.bind("<ButtonPress-1>", self.on_mouse_press_for_eyedropper)
        grabber_window.bind_all("<Escape>", self.cancel_eyedropper_mode)

    def exit_eyedropper_mode(self):
        if not self.eyedropper_mode: return
        
        grabber_window = self.eyedropper_target_canvas.winfo_toplevel()
        
        # 設定した一時的なバインドを解除
        if hasattr(self, 'temp_mouse_press_binding_id'):
            grabber_window.unbind("<ButtonPress-1>", self.temp_mouse_press_binding_id)

        grabber_window.unbind_all("<Escape>")
        
        self.eyedropper_mode = False
        self.eyedropper_target_label = None
        if self.eyedropper_target_canvas and self.eyedropper_target_canvas.winfo_exists():
            self.eyedropper_target_canvas.config(cursor="")
        self.eyedropper_target_canvas = None
        self.eyedropper_pil_image = None
        self.eyedropper_tk_image = None
        
        # グラブを解放
        grabber_window.grab_release()
        
    def cancel_eyedropper_mode(self, event=None):
        if self.eyedropper_mode:
            self.exit_eyedropper_mode()
        return "break"

    def on_mouse_press_for_eyedropper(self, event):
        """スポイトモード専用のマウスプレスイベントハンドラ"""
        if self.eyedropper_mode and self.eyedropper_target_canvas == event.widget:
            self.pick_color_at(event.x, event.y)
        else:
            # 予期せぬ場所がクリックされた場合はモードを終了
            self.exit_eyedropper_mode()

    def pick_color_at(self, canvas_x, canvas_y):
        print("pick_color_at:start")
        canvas_to_use = self.eyedropper_target_canvas
        pil_image_to_use = self.eyedropper_pil_image
        display_image = self.eyedropper_tk_image # 記憶したPhotoImageを使用

        if pil_image_to_use is None or display_image is None:
            self.exit_eyedropper_mode(); return

        canvas_w = canvas_to_use.winfo_width()
        canvas_h = canvas_to_use.winfo_height()
        img_w = display_image.width()
        img_h = display_image.height()

        offset_x = (canvas_w - img_w) / 2
        offset_y = (canvas_h - img_h) / 2

        if not (offset_x <= canvas_x < offset_x + img_w and offset_y <= canvas_y < offset_y + img_h):
            self.exit_eyedropper_mode(); return

        scale_w = pil_image_to_use.width / img_w
        scale_h = pil_image_to_use.height / img_h

        orig_x = int((canvas_x - offset_x) * scale_w)
        orig_y = int((canvas_y - offset_y) * scale_h)

        pixel_color = pil_image_to_use.getpixel((orig_x, orig_y))

        hex_color = f"#{pixel_color[0]:02x}{pixel_color[1]:02x}{pixel_color[2]:02x}"
        if self.eyedropper_target_label:
            self.eyedropper_target_label.config(background=hex_color)
        print("pick_color_at:end")
        self.exit_eyedropper_mode()

    def pick_color(self, preview_label: tk.Label):
        initial_color = preview_label.cget("background")
        color_code = colorchooser.askcolor(title="色の選択", initialcolor=initial_color)
        if color_code[1]: preview_label.config(background=color_code[1])

    def on_close(self):
        self.grab_release()
        self.destroy()

    def trigger_test_speech(self, text: str, params_override: dict, on_finish_callback=None):
        if platform.system() != "Windows":
            messagebox.showinfo("情報", "音声再生はWindows環境でのみサポートされています。", parent=self)
            if on_finish_callback: on_finish_callback()
            return
        engine = self.selected_engine.get()
        speaker_name = self.selected_speaker.get()
        style_name = self.selected_style.get()
        if not all([engine, speaker_name, style_name, text]):
            messagebox.showwarning("設定不足", "音声設定タブでエンジン、話者名、スタイルをすべて選択し、テキストを入力してください。", parent=self)
            if on_finish_callback: on_finish_callback()
            return
        threading.Thread(target=self._generate_and_play, args=(text, engine, speaker_name, style_name, params_override, on_finish_callback), daemon=True).start()

    def _generate_and_play(self, text, engine, speaker_name, style_name, params_override, on_finish_callback):
        wav_data = None
        try:
            speaker_id = self._find_speaker_id(engine, speaker_name, style_name)
            if speaker_id is None: raise ValueError("指定された話者/スタイルが見つかりません。")
            urls = {'voicevox': 'http://127.0.0.1:50021', 'aivisspeech': 'http://127.0.0.1:10101'}
            base_url = urls.get(engine)
            if not base_url: raise ValueError(f"不明なエンジン: {engine}")
            query_res = requests.post(f"{base_url}/audio_query", params={'text': text, 'speaker': speaker_id}, timeout=5)
            query_res.raise_for_status()
            audio_query = query_res.json()
            for key, value in params_override.items():
                if key in audio_query: audio_query[key] = value
            synth_res = requests.post(f"{base_url}/synthesis", params={'speaker': speaker_id}, json=audio_query, timeout=10)
            synth_res.raise_for_status()
            wav_data = synth_res.content
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("APIエラー", f"音声の生成に失敗しました。\n詳細: {e}", parent=self))
        finally:
            if wav_data and platform.system() == "Windows":
                try: winsound.PlaySound(wav_data, winsound.SND_MEMORY)
                except Exception as e: print(f"音声の再生に失敗: {e}")
            if on_finish_callback: self.after(0, on_finish_callback)

    def _find_speaker_id(self, engine, speaker_name, style_name):
        speakers = self.speaker_data_cache.get(engine, [])
        for speaker in speakers:
            if speaker['name'] == speaker_name:
                for style in speaker['styles']:
                    if style['name'] == style_name: return style['id']
        return None
    
    def sanitize_string(self, text: str, max_length: int, allow_newlines: bool = False) -> str:
        """
        文字列をサニタイズ（無害化）する。
        - 印刷不可能な制御文字を除去する。
        - オプションに応じて改行を許可または削除する。
        - 指定された最大長に切り詰める。
        """
        if not isinstance(text, str):
            return ""

        # 印刷不可能な文字を除去（改行はオプションで保持）
        if allow_newlines:
            clean_chars = [c for c in text if c.isprintable() or c in '\n\r']
        else:
            # .isprintable() は改行をFalseと判定するので、これで改行も除去される
            clean_chars = [c for c in text if c.isprintable()]
        
        sanitized_text = "".join(clean_chars)

        # 最大長を超えている場合は切り詰める
        return sanitized_text[:max_length]

    def get_available_tab_height(self) -> int:
        """
        ノートブック（タブ表示エリア）が使用できる高さを計算して返す。
        """
        self.update_idletasks()
        
        # ウィンドウ全体の高さを取得
        window_height = self.winfo_height()
        
        # 下部ボタンフレームの高さを取得
        button_frame_height = self.button_frame.winfo_height()
        
        # 上部のノートブックタブ部分の高さを取得 (y座標の差分で計算)
        # notebookウィジェットそのものではなく、その中の最初のタブのy座標を見る
        try:
            # 最初のタブウィジェットを取得
            first_tab_widget = self.nametowidget(self.notebook.tabs()[0])
            # ノートブックの上辺からタブの上辺までの距離がタブ部分の高さ
            notebook_tab_height = first_tab_widget.winfo_y()
        except (IndexError, tk.TclError):
            # タブが存在しないか、ウィジェットがまだない場合
            notebook_tab_height = 20 # フォールバック値

        # 利用可能な高さを計算
        # ウィンドウ高さ - (タブ部分 + ボタン部分 + 上下マージン)
        available_height = window_height - notebook_tab_height - button_frame_height - (self.app.padding_large * 3)

        return max(50, available_height) # 最小でも50pxは確保する
