import configparser
import os
import subprocess
import psutil

class EngineManager:
    """
    音声合成エンジン（VOICEVOX, AivisSpeech）のプロセスを管理するクラス。
    アプリケーション起動時にエンジンが動いていなければ起動し、
    終了時に他の依存アプリが動いていなければエンジンを終了させる。
    """
    def __init__(self, config_path='config.ini', base_path='.'):
        self.config = configparser.ConfigParser()
        self.base_path = base_path
        # config.iniが存在するか確認
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        self.config.read(config_path, encoding='utf-8')
        
        # このエディタが起動したプロセスを記録するリスト
        self.managed_processes = []
        
        # --- 依存アプリケーションのプロセス名リスト ---
        # ここに記載されたアプリが一つでも実行中の場合、エディタ終了時にエンジンを閉じません。
        # 親となるデスクトップマスコットアプリの実行ファイル名などに合わせて適宜変更してください。
        self.dependent_apps = [
            "kokokoko.exe",      # TODO: 親アプリの実行ファイル名に要変更
            "VOICEVOX.exe",      # VOICEVOXのGUIアプリ本体
            "AivisSpeech.exe",   # AivisSpeechのGUIアプリ本体
        ]

    def _is_process_running(self, exe_path: str) -> bool:
        """指定されたフルパスのプロセスが実行中か正確に確認する"""
        if not exe_path:
            return False
            
        # 比較のためにパスを正規化し、小文字に変換する
        normalized_path = os.path.normpath(exe_path).lower()
        for proc in psutil.process_iter(['exe']):
            try:
                # 取得したパスも同様に正規化・小文字化して比較
                if proc.info['exe'] and os.path.normpath(proc.info['exe']).lower() == normalized_path:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def _start_engine(self, section: str):
        """設定ファイルからパスを読み取り、エンジンが未起動の場合のみ起動する"""
        try:
            exe_path_from_config = self.config.get(section, 'exe_path', fallback=None)
            if not exe_path_from_config:
                print(f"[{section}] の exe_path が config.ini に見つかりません。")
                return
            
            # exe_pathが絶対パスでなければ、base_pathと結合して絶対パスに変換
            if not os.path.isabs(exe_path_from_config):
                exe_path = os.path.join(self.base_path, exe_path_from_config)
            else:
                exe_path = exe_path_from_config # 元々絶対パスならそのまま使う

            if not os.path.exists(exe_path):
                print(f"[{section}] の exe_path が見つからないか、無効です: {exe_path}")
                return

            # プロセスが実行中でないことを確認してから起動
            if not self._is_process_running(exe_path):
                print(f"[{section}] エンジンが見つからないため、起動します: {exe_path}")
                # エンジンの実行ファイルがあるディレクトリを取得
                engine_dir = os.path.dirname(exe_path)
                
                # cwdを指定してプロセスを起動する
                process = subprocess.Popen(
                    [exe_path], 
                    cwd=engine_dir,  # 作業ディレクトリをエンジンのディレクトリに設定
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                )
                self.managed_processes.append(process)
            else:
                print(f"[{section}] エンジンは既に実行中です。")

        except Exception as e:
            print(f"[{section}] エンジンの起動に失敗しました: {e}")

    def start_all_engines_if_needed(self):
        """VOICEVOXとAivisSpeechのエンジンを必要に応じて起動する"""
        print("音声エンジンの状態を確認しています...")
        self._start_engine('VOICEVOX')
        self._start_engine('AIVIS_SPEECH')

    def stop_managed_engines_conditionally(self):
        """依存アプリが動いていなければ、このエディタが起動したエンジンを停止する"""
        print("アプリケーション終了処理を確認しています...")
        
        # 依存アプリケーションが実行中か確認
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] in self.dependent_apps:
                print(f"依存アプリケーション '{proc.info['name']}' が実行中のため、エンジンは終了しません。")
                return # 依存アプリが動いていたら、何もせず処理を終了

        # 依存アプリがなければ、管理下のプロセスを終了させる
        if not self.managed_processes:
            print("このエディタが起動したエンジンはありませんでした。")
            return
            
        print("依存アプリケーションが見つからないため、このエディタが起動したエンジンを終了します...")
        for process in self.managed_processes:
            try:
                if process.poll() is None: # プロセスがまだ実行中か確認
                    print(f"プロセス {process.pid} を終了します。")
                    process.terminate() # プロセスに終了シグナルを送信
                    process.wait(timeout=5) # 5秒間、プロセスの終了を待つ
            except psutil.NoSuchProcess:
                pass # すでにプロセスが存在しない場合は何もしない
            except subprocess.TimeoutExpired:
                print(f"プロセス {process.pid} の終了がタイムアウトしたため、強制終了します。")
                process.kill() # 強制終了
            except Exception as e:
                print(f"プロセスの終了中にエラーが発生しました: {e}")