# src/github_uploader.py

import configparser
import os
import shutil
import tempfile
import requests
import sys
import hashlib
import json
from datetime import datetime, timezone
# PIL(Pillow)ライブラリをインポート
from PIL import Image, ImageOps, ImageDraw

from .character_data import CharacterData


class GithubUploader:
    """
    キャラクターデータをZIP化し、GitHubのIssueとして投稿する機能を提供するクラス。
    """
    REPO_OWNER = "YobiYobiMoru"
    REPO_NAME = "cocococo_character_uploader"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    
    # GitHubのZIPファイルサイズ上限（マージンを設ける）
    ZIP_SIZE_LIMIT_BYTES = 24 * 1024 * 1024 # 24MB

    def __init__(self, config_path: str):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        # 最初に一度読み込んでおく
        self.config.read(self.config_path, encoding='utf-8')

        # 署名ソルトをファイルから読み込む
        self.signature_salt = self._load_salt()
        
        # 認証済みユーザーのログイン名をキャッシュする変数
        self.current_user_login = None

        # --- ZIP保存用フォルダのパスを決定 ---
        if getattr(sys, 'frozen', False):
            # EXEとして実行されている場合
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
        
        self.zip_output_dir = os.path.join(self.base_path, "_temp_zips")
        # フォルダが存在しない場合は作成
        os.makedirs(self.zip_output_dir, exist_ok=True)

    def _load_salt(self) -> str:
        """
        salt.keyファイルから署名ソルトを読み込む。
        スクリプト実行時とPyInstaller実行時の両方に対応する。
        """
        try:
            # PyInstallerでバンドルされた実行可能ファイル内かチェック
            if getattr(sys, 'frozen', False):
                # EXE実行時: データは sys._MEIPASS に展開される
                base_path = sys._MEIPASS
            else:
                # スクリプト実行時: main.py があるプロジェクトルートを基準にする
                # このファイル(github_uploader.py)は src/ にあるので、2階層上がる
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            salt_file_path = os.path.join(base_path, 'salt.key')
            
            with open(salt_file_path, 'r', encoding='utf-8') as f:
                salt = f.read().strip()
            
            if not salt:
                raise ValueError("salt.keyファイルが空です。")
                
            return salt

        except FileNotFoundError:
            # ユーザーフレンドリーなエラーメッセージを表示
            raise FileNotFoundError(
                "署名用のソルトファイル 'salt.key' が見つかりません。\n"
                "プロジェクトのルートディレクトリに salt.key を作成し、\n"
                "配布されたソルト文字列を記述してください。"
            )
        except Exception as e:
            raise RuntimeError(f"ソルトファイルの読み込み中に予期せぬエラーが発生しました: {e}")

    def get_pat(self) -> str | None:
        """設定ファイルからPersonal Access Tokenを取得する。毎回ファイルを読み直す。"""
        # ファイルの最新の状態を反映するために、このメソッドが呼ばれるたびにconfigを読み直す
        self.config.read(self.config_path, encoding='utf-8')
        
        # strip()で前後の空白を除去し、空文字列の場合はNoneを返す
        token = self.config.get('GITHUB', 'personal_access_token', fallback="").strip()
        
        if token:
            return token
        return None
    
    def _get_current_user_login(self, pat: str) -> str:
        """PATを使って認証済みユーザーのログイン名を取得し、キャッシュする。"""
        if self.current_user_login:
            return self.current_user_login
        
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            self.current_user_login = res.json()["login"]
            return self.current_user_login
        else:
            raise ValueError("GitHubの認証に失敗しました。Personal Access Tokenが正しいか確認してください。")
            
    def _get_issue_details(self, issue_number: int, pat: str) -> dict:
        """指定されたIssueの詳細情報を取得する。"""
        url = f"{self.API_URL}/{issue_number}"
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        if res.status_code in [403,404,410]:
            raise requests.exceptions.RequestException(f"更新対象のIssueが見つかりません (#{issue_number})。\n削除されたか、番号が間違っている可能性があります。")
        res.raise_for_status() # その他のHTTPエラー
        return {} # Fallback

    def _calculate_sha256(self, file_path: str) -> str:
        """ファイルのSHA256ハッシュを計算するヘルパー関数"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256.update(byte_block)
        return sha256.hexdigest()

    def _calculate_dir_size(self, directory: str) -> int:
        """指定されたディレクトリ内の全ファイルサイズの合計を計算する"""
        total = 0
        for entry in os.scandir(directory):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += self._calculate_dir_size(entry.path)
        return total

    def _prepare_and_sign_zip(self, project_id: str, zip_base_name: str, source_dir: str, items_to_include: list[str], package_info: dict) -> str:
        """
        指定されたファイル/ディレクトリ群から署名とパッケージ情報付きのZIPを作成するヘルパー。
        source_dirからitems_to_includeで指定されたものだけをZIP化する。
        """
        package_dir = tempfile.mkdtemp()
        try:
            # 1. パッケージ情報JSONファイルを生成
            package_info_path = os.path.join(package_dir, 'package_info.json')
            with open(package_info_path, 'w', encoding='utf-8') as f:
                json.dump(package_info, f, indent=2, ensure_ascii=False)

            # 2. 指定されたアイテムをパッケージ用ディレクトリにコピー
            for item_name in items_to_include:
                src_path = os.path.join(source_dir, item_name)
                dest_path = os.path.join(package_dir, item_name)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dest_path)
                elif os.path.isfile(src_path):
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(src_path, dest_path)
            
            # 3. パッケージディレクトリ内の全ファイルからマニフェストを作成
            file_manifest = {}
            for dirpath, _, filenames in os.walk(package_dir):
                for filename in filenames:
                    # 署名ファイル自体はマニフェストに含めない
                    if filename == 'signature.json':
                        continue
                    full_path = os.path.join(dirpath, filename)
                    manifest_key = os.path.relpath(full_path, package_dir).replace("\\", "/")
                    file_manifest[manifest_key] = self._calculate_sha256(full_path)

            # 4. 署名ファイル生成
            signature_data = {
                "version": "1.0.0",
                "generated_by": "cocococo_character_maker",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "character_id": project_id,
                "file_manifest": file_manifest
            }

            # 署名データ本体をJSON文字列に変換（キーをソートして一貫性を確保）
            signature_content_str = json.dumps(signature_data, sort_keys=True, separators=(',', ':'))

            # 署名を計算（内容＋ソルトのハッシュ）
            signature_hash = hashlib.sha256((signature_content_str + self.signature_salt).encode('utf-8')).hexdigest()
            
            # 最終的なJSONデータに署を追加
            signature_data_with_signature = signature_data.copy()
            signature_data_with_signature["signature"] = signature_hash

            # 署名ファイルを一時フォルダに書き出す
            signature_file_path = os.path.join(package_dir, 'signature.json')
            with open(signature_file_path, 'w', encoding='utf-8') as f:
                json.dump(signature_data_with_signature, f, indent=2)

            # 5. ZIP化
            zip_path = shutil.make_archive(base_name=zip_base_name, format='zip', root_dir=package_dir)
            return zip_path
        finally:
            shutil.rmtree(package_dir)

    def create_character_zip(self, character_data: CharacterData, character_base_path: str, project_id: str, character_name: str) -> tuple[list[str], str | None]:
        """
        キャラクターフォルダをZIP圧縮する。サイズが25MBを超える場合は衣装ごとに分割する。
        各ZIPにはパッケージ情報(package_info.json)が含まれる。
        
        Returns:
            tuple[list[str], str | None]: (作成されたZIPファイルのフルパスのリスト, 黒塗り適用後サムネイルのパス or None)
        """
        ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
        ALLOWED_ROOT_FILES = {'character.ini', 'readme.txt', 'thumbnail.png', 'topics.txt'}

        # --- 1. ZIP出力先を準備 ---
        safe_character_name = "".join(c for c in character_name if c.isalnum() or c in " _-").rstrip()
        if not safe_character_name: safe_character_name = project_id
        character_zip_dir = os.path.join(self.zip_output_dir, safe_character_name)
        os.makedirs(character_zip_dir, exist_ok=True)

        # --- 2. 黒塗り適用サムネイルの生成 ---
        censored_thumbnail_path = None
        source_thumbnail_path = os.path.join(character_base_path, 'thumbnail.png')
        if os.path.exists(source_thumbnail_path):
            try:
                # 黒塗り適用サムネイルは別名で一時フォルダに保存
                censored_thumbnail_path = os.path.join(character_zip_dir, 'censored_thumbnail_for_issue.png')
                image = Image.open(source_thumbnail_path).convert("RGBA")
                
                # 黒塗り修正を適用
                censor_rects = character_data.get_thumbnail_censor_rects()
                if censor_rects:
                    draw = ImageDraw.Draw(image)
                    for rect in censor_rects: draw.rectangle(rect, fill="black")
                
                # リサイズして保存
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                image.save(censored_thumbnail_path, "PNG")
            except Exception as e:
                print(f"警告: 黒塗りサムネイル生成中にエラーが発生: {e}")
                censored_thumbnail_path = None


        # --- 3. ZIP対象の全ファイルを一時ステージングディレクトリに集める ---
        staging_dir = tempfile.mkdtemp()
        try:
            # ルートにある許可されたファイル（元の黒塗りなしthumbnail.pngを含む）をコピー
            for filename in os.listdir(character_base_path):
                if filename.lower() in ALLOWED_ROOT_FILES:
                    # 元のthumbnail.pngをそのままコピー
                    shutil.copy2(os.path.join(character_base_path, filename), os.path.join(staging_dir, filename))
            
            # 各ディレクトリを処理
            for dirname in os.listdir(character_base_path):
                src_dir_path = os.path.join(character_base_path, dirname)
                if os.path.isdir(src_dir_path):
                    dest_dir_path = os.path.join(staging_dir, dirname)
                    
                    if dirname in ['events', 'stills']:
                        shutil.copytree(src_dir_path, dest_dir_path)
                    else:
                        # それ以外のディレクトリ（衣装、heartsなど）は画像ファイルのみコピー
                        os.makedirs(dest_dir_path, exist_ok=True)
                        for filename in os.listdir(src_dir_path):
                            _, ext = os.path.splitext(filename)
                            if ext.lower() in ALLOWED_IMAGE_EXTENSIONS:
                                shutil.copy2(os.path.join(src_dir_path, filename), os.path.join(dest_dir_path, filename))

            # --- 4. 合計サイズを計算し、分割が必要か判断 ---
            total_size = self._calculate_dir_size(staging_dir)
            costumes = character_data.get_costumes()
            should_split = total_size > self.ZIP_SIZE_LIMIT_BYTES and len(costumes) > 1
            
            zip_paths = []
            
            # --- 5. package_info.json のための共通メタデータを作成 ---
            base_meta = {
                "format_version": "1.0",
                "character_id": project_id,
                "character_name": character_name,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "generated_by": "cocococo_character_maker"
            }

            if not should_split:
                print(f"合計サイズ ({total_size / 1024**2:.2f}MB) が制限内か単一衣装のため分割しません。")
                
                # 単独ZIP用のパッケージ情報を作成
                package_info = base_meta.copy()
                package_info.update({
                    "package_type": "complete",
                    "base_id": project_id
                })

                zip_base_name = os.path.join(character_zip_dir, project_id)
                # ステージングディレクトリ内の全ファイル(サムネイル含む)をZIP化
                all_items = os.listdir(staging_dir)
                zip_path = self._prepare_and_sign_zip(
                    project_id, zip_base_name, staging_dir, all_items, package_info=package_info
                )
                
                # 単一ZIPでもサイズチェック
                if os.path.getsize(zip_path) > self.ZIP_SIZE_LIMIT_BYTES:
                    raise ValueError(
                        f"ファイルサイズ超過エラー:\n\n"
                        f"ZIPファイル ({os.path.basename(zip_path)}) が25MBの上限を超えました。\n\n"
                        "衣装が1つしかないか、合計サイズが小さいためファイルは分割されませんでした。\n"
                        "キャラクター内の画像サイズを小さくするか、ファイル数を減らしてください。"
                    )
                zip_paths.append(zip_path)
            else:
                print(f"合計サイズ ({total_size / 1024**2:.2f}MB) が制限を超えているため、衣装ごとにZIPを分割します。")
                
                # 1. 親ZIPを作成する前に、どの子ZIP(衣装)が存在するかリストアップする
                child_part_names = []
                for costume in costumes:
                    costume_id = costume['id']
                    if costume_id != 'default' and os.path.isdir(os.path.join(staging_dir, costume_id)):
                        child_part_names.append(costume_id)

                # 2. 親となるベースZIPの作成
                base_items = [f for f in ALLOWED_ROOT_FILES if os.path.exists(os.path.join(staging_dir, f))]
                if os.path.isdir(os.path.join(staging_dir, 'default')): base_items.append('default')
                if os.path.isdir(os.path.join(staging_dir, 'hearts')): base_items.append('hearts')
                if os.path.isdir(os.path.join(staging_dir, 'events')): base_items.append('events')
                if os.path.isdir(os.path.join(staging_dir, 'stills')): base_items.append('stills')
                
                base_package_info = base_meta.copy()
                base_package_info.update({
                    "package_type": "split",
                    "base_id": project_id,
                    "part_name": "base",
                    "package_role": "parent",
                    "child_parts": child_part_names
                })

                base_zip_name = os.path.join(character_zip_dir, f"{project_id}_base")
                base_zip_path = self._prepare_and_sign_zip(
                    project_id, base_zip_name, staging_dir, base_items, package_info=base_package_info
                )

                # ベースZIPのサイズチェック
                if os.path.getsize(base_zip_path) > self.ZIP_SIZE_LIMIT_BYTES:
                    raise ValueError(
                        f"ファイルサイズ超過エラー:\n\n"
                        f"ベースファイル群 ({os.path.basename(base_zip_path)}) が25MBの上限を超えました。\n\n"
                        "default衣装やheartsフォルダ内の画像サイズを小さくするか、ファイル数を減らしてください。"
                    )
                zip_paths.append(base_zip_path)

                # 3. 子となる衣装ごとのZIP作成
                for costume_id in child_part_names:
                    costume_package_info = base_meta.copy()
                    costume_package_info.update({
                        "package_type": "split",
                        "base_id": project_id,
                        "part_name": costume_id,
                        "package_role": "child",
                        "parent_part": "base"
                    })

                    costume_zip_name = os.path.join(character_zip_dir, f"{project_id}_{costume_id}")
                    costume_zip_path = self._prepare_and_sign_zip(
                        project_id, costume_zip_name, staging_dir, [costume_id], package_info=costume_package_info
                    )

                    if os.path.getsize(costume_zip_path) > self.ZIP_SIZE_LIMIT_BYTES:
                        raise ValueError(
                            f"ファイルサイズ超過エラー:\n\n"
                            f"衣装 '{costume_id}' ({os.path.basename(costume_zip_path)}) が25MBの上限を超えました。\n\n"
                            "この衣装に含まれる画像サイズを小さくするか、表情の数を減らしてください。"
                        )
                    zip_paths.append(costume_zip_path)
            
            print(f"作成されたZIPファイル: {zip_paths}")
            # 戻り値をタプルに変更
            return zip_paths, censored_thumbnail_path
        finally:
            # --- 処理が終わったら、一時フォルダを必ず削除 ---
            shutil.rmtree(staging_dir)

    def create_issue(self, title: str, body: str, pat: str) -> dict:
        """
        GitHub APIを呼び出してIssueを作成する。(変更なし)
        """
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": title,
            "body": body
        }
        
        print("GitHub APIにIssue作成リクエストを送信します...")
        response = requests.post(self.API_URL, headers=headers, json=data, timeout=15)
        
        if response.status_code == 201:
            print("Issueの作成に成功しました。")
            return response.json()
        elif response.status_code == 401:
            raise ValueError("GitHubの認証に失敗しました。Personal Access Tokenが正しいか確認してください。")
        else:
            error_message = f"Issueの作成に失敗しました (HTTP {response.status_code}): {response.text}"
            print(error_message)
            raise requests.exceptions.RequestException(error_message)

    def set_issue_state(self, issue_number: int, pat: str, state: str) -> None:
        """
        Issue の状態を変更する（open/closed）。存在しない番号や権限不足は例外送出。
        """
        url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/issues/{issue_number}"
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        res = requests.patch(url, headers=headers, json={"state": state}, timeout=15)
        res.raise_for_status()

    def create_issue_initially_closed(self, title: str, body: str, pat: str, labels: list[str] | None = None) -> dict:
        """
        Issue を作成してから即クローズするユーティリティ。
        - 作成時点で 'pending' などのラベルを付与可能。
        - 戻り値は GitHub の Issue JSON（html_url, number 等を含む）。
        """
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels

        print("GitHub APIにIssue作成リクエストを送信します...(initially closed)")
        response = requests.post(self.API_URL, headers=headers, json=data, timeout=15)
        if response.status_code != 201:
            if response.status_code == 401:
                raise ValueError("GitHubの認証に失敗しました。Personal Access Tokenが正しいか確認してください。")
            raise requests.exceptions.RequestException(
                f"Issueの作成に失敗しました (HTTP {response.status_code}): {response.text}"
            )

        issue = response.json()
        number = issue.get("number")
        if not number:
            raise requests.exceptions.RequestException("Issue作成応答に number が含まれていません。")

        # 作成直後にクローズ
        try:
            self.set_issue_state(number, pat, "closed")
        except Exception as e:
            # 作成は成功しているので、ユーザーに URL を見せるため例外にせず通す
            print(f"[warn] Issueの初手クローズに失敗: {e}")

        return issue

    def update_issue_body(self, issue_number: int, body: str, pat: str, title: str | None = None, labels: list[str] | None = None) -> dict:
        """既存の Issue の本文（および任意でタイトル／ラベル）を更新する。"""
        # 1. 更新前にIssueの詳細情報を取得
        try:
            issue_details = self._get_issue_details(issue_number, pat)
            
            # 取得した情報がPull Requestのものでないか確認する
            if "pull_request" in issue_details and issue_details["pull_request"]:
                raise ValueError(
                    f"更新対象 #{issue_number} はプルリクエストです。\n\n"
                    "キャラクターの共有情報として、プルリクエストの番号は使用できません。"
                )

            issue_author = issue_details.get("user", {}).get("login")
            current_user = self._get_current_user_login(pat)

            if issue_author and current_user and issue_author.lower() != current_user.lower():
                raise ValueError(
                    f"作者不一致エラー:\n\n"
                    f"このIssueは他のユーザー ({issue_author}) によって作成されたため、更新できません。\n"
                    f"(あなたのアカウント: {current_user})\n\n"
                )
        except requests.exceptions.RequestException as e:
            # Issue取得失敗はそのまま上に投げる
            raise e

        # 2. 作者チェックをパスした場合のみ、更新処理を行う
        url = f"https://api.github.com/repos/{self.REPO_OWNER}/{self.REPO_NAME}/issues/{issue_number}"
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {"body": body}
        if title is not None and title.strip():
            payload["title"] = title
        if labels is not None:
            payload["labels"] = labels
        res = requests.patch(url, headers=headers, json=payload, timeout=15)
        
        if res.status_code in (200, 201):
            return res.json()
        if res.status_code == 401:
            raise ValueError("GitHubの認証に失敗しました。Personal Access Tokenが正しいか確認してください。")
        if res.status_code == 404:
            raise requests.exceptions.RequestException(f"Issueが見つかりません (#{issue_number})")
        raise requests.exceptions.RequestException(f"Issueの更新に失敗しました (HTTP {res.status_code}): {res.text}")
