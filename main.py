# main.py

import os
import sys
import tkinter as tk
from tkinter import messagebox
import configparser

from src.app import CharacterMakerApp
from src.engine_manager import EngineManager

def ensure_github_config(config_path):
    """
    config.iniを読み込み、[GITHUB]セクションがなければコメントを保持したまま追記する。
    """
    config = configparser.ConfigParser()
    # 既存のファイルを読み込む
    config.read(config_path, encoding='utf-8')
    
    # [GITHUB]セクションが存在しない場合のみ、追記処理を行う
    if not config.has_section('GITHUB'):
        print(f"'{config_path}' に [GITHUB] セクションが見つからないため、追記します。")
        try:
            # 読み書き両用モード ('r+') でファイルを開く
            with open(config_path, 'r+', encoding='utf-8') as configfile:
                # ファイルの末尾に移動
                configfile.seek(0, os.SEEK_END)
                
                # ファイルが空でない場合のみ、最後の文字を確認
                if configfile.tell() > 0:
                    # 末尾から1文字前に移動して読み込む
                    configfile.seek(configfile.tell() - 1, os.SEEK_SET)
                    if configfile.read(1) != '\n':
                        # 最後の文字が改行でなければ、改行を追加
                        configfile.write('\n')
                
                # 新しいセクションを末尾に書き込む
                configfile.write('\n; ======================================================================\n')
                configfile.write('; ■■■ GitHub 連携設定 ■■■\n')
                configfile.write('; ======================================================================\n')
                configfile.write('[GITHUB]\n')
                configfile.write('; キャラクター共有機能で使用するGitHubのPersonal Access Tokenを設定します。\n')
                configfile.write('; repoスコープとread:userスコープの権限が必要です。\n')
                configfile.write('personal_access_token = \n')
            print("GITHUBセクションを追記しました。使用前に personal_access_token の設定が必要です。")
        except Exception as e:
            print(f"config.iniへの書き込み中にエラーが発生しました: {e}")


# PyInstallerでEXE化した場合に、EXEが置かれたディレクトリを基準にするための処理
if getattr(sys, 'frozen', False):
    # EXEとして実行されている場合
    application_path = os.path.dirname(sys.executable)
else:
    # スクリプトとして実行されている場合 (python main.py)
    application_path = os.path.dirname(os.path.abspath(__file__))

# スクリプトがあるディレクトリを作業ディレクトリに設定
# これにより、常に 'characters' フォルダが正しく参照されます。
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    engine_manager = None
    config_file = os.path.join(application_path, 'config.ini')

    # 親アプリのconfig.iniが存在する場合のみエンジン管理を行う
    if os.path.exists(config_file):
        print(f"'{config_file}' を検出しました。エンジン管理機能を有効にします。")
        
        # GitHub設定の確認と初期化（コメント保持版）
        ensure_github_config(config_file)
        
        try:
            # 依存ライブラリのチェック
            import psutil
            engine_manager = EngineManager(config_path=config_file, base_path=application_path)
            engine_manager.start_all_engines_if_needed()

        except ImportError:
            print("\n" + "="*50)
            print("警告: ライブラリ 'psutil' が見つかりません。")
            print("エンジン管理機能（自動起動・終了）は無効になります。")
            print("コマンドプロンプトで pip install psutil を実行してインストールしてください。")
            print("="*50 + "\n")
        except FileNotFoundError as e:
            print(f"エラー: {e}")
        except Exception as e:
            print(f"エンジン管理モジュールの初期化中に予期せぬエラーが発生しました: {e}")
    else:
        print(f"'{config_file}' が見つからないため、エンジン管理機能は無効です。")
    
    app = CharacterMakerApp(base_path=application_path)

    # ウィンドウが閉じられるときの処理を定義
    def on_closing():
        try:
            if engine_manager:
                engine_manager.stop_managed_engines_conditionally()
        finally:
            # tryブロックで何が起きても、最終的にウィンドウを破棄する
            app.destroy()

    # ウィンドウの「閉じる」ボタンが押されたときに on_closing 関数を呼び出すように設定
    app.protocol("WM_DELETE_WINDOW", on_closing)

    app.mainloop()