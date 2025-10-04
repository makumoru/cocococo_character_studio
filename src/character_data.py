# src/character_data.py

import configparser
import os
import shutil
import ast
import re
import json

class CharacterData:
    """
    character.iniの内容をオブジェクトとして管理し、読み書きを行うクラス。
    """
    class SafeFormatDict(dict):
        """
        format_mapで使用する辞書。
        キーが見つからない場合、空文字返す。
        """
        def __missing__(self, key):
            return ''

    DEFAULT_INI_CONTENT = """
; ======================================================================
; ■■■ キャラクター設定 ■■■
; ======================================================================
; キャラクターの名前、性格、画像、音声などを設定します。

; --- キャラクターの基本設定 ---
[INFO]
; キャラクター名
CHARACTER_NAME = {CHARACTER_NAME}
; システムメニューなどで使われる名前
SYSTEM_NAME = {SYSTEM_NAME}

; --- キャラクターの話し方 ---
; 一人称 (例: 私, 俺, 僕)
FIRST_PERSON = {FIRST_PERSON}
; ユーザー(プレイヤー)の呼び方 (例: あなた, 君, 〇〇さん)
USER_REFERENCE = {USER_REFERENCE}
; 他のキャラクターや第三者を指すときの汎用的な呼び方 (例: あの人, 彼, 彼女)
THIRD_PERSON_REFERENCE = {THIRD_PERSON_REFERENCE}

; --- キャラクターの性格や振る舞い ---
; キャラクターロールプレイ用の指示文
CHARACTER_PERSONALITY = {CHARACTER_PERSONALITY}
; 自動発話の頻度（おしゃべり度）。0(寡黙)～100(おしゃべり)の範囲で設定します。
; 2人モードの場合、この数値の比率でどちらが話すかが決まります。
SPEECH_FREQUENCY = {SPEECH_FREQUENCY}

; --- キャラクターの表示設定 ---
; ウィンドウの透過方式 (alpha: アルファチャンネル / color_key: 透過色指定)
TRANSPARENCY_MODE = {TRANSPARENCY_MODE}
; ウィンドウの透過色や境界線の色を個別に設定したい場合は、ここに記述します。
TRANSPARENT_COLOR = {TRANSPARENT_COLOR}
EDGE_COLOR = {EDGE_COLOR}

; --- キャラクターの属性 ---
; このキャラクターが版権作品の二次創作であるか (true/false)
IS_DERIVATIVE = {IS_DERIVATIVE}
; このキャラクターがNSFW(職場での閲覧に不適切)な要素を含むか (true/false)
IS_NSFW = {IS_NSFW}


; ======================================================================
; ■■■ 音声設定 ■■■
; ======================================================================
[VOICE]
; 使用する音声エンジンを指定します (例: voicevox)
; 対応するエンジン名は src/voice_manager.py の ENGINE_MAP を参照してください。
engine = {engine}

; --- VOICEVOXを使用する場合の設定(他エンジンを使用する設定の場合はここに書いても読み込まれません) ---
[VOICE_VOX]
# ここで話者の名前とスタイルを指定します。VOICEVOXアプリの表示と完全に一致させてください。
speaker_name = {vv_speaker_name}
speaker_style = {vv_speaker_style}

; --- AivisSpeechを使用する場合の設定(他エンジンを使用する設定の場合はここに書いても読み込まれません) ---
[AIVIS_SPEECH]
# ここで話者の名前とスタイルを指定します。AivisSpeechアプリの表示と完全に一致させてください。
speaker_name = {aivis_speaker_name}
speaker_style = {aivis_speaker_style}


; ======================================================================
; ■■■ システムメッセージ設定 ■■■
; ======================================================================
; AIの応答失敗時やタイムアウト時などにキャラクターが発するセリフを個別に設定できます。
; 設定しない場合は、デフォルトのセリフが使用されます。
[SYSTEM_MESSAGES]
; Geminiが何も返事せず「虚無を返信」してきた際のエラーメッセージです。だいたいGemini側のフィルターに引っかかってます。
ON_EMPTY_RESPONSE = {ON_EMPTY_RESPONSE}
; Geminiからの返事が返って来ずタイムアウトした際のエラーメッセージです。APIキーが間違ってるか通信の問題が多いです。
ON_API_TIMEOUT = {ON_API_TIMEOUT}
; 試せるAPI全部に通信してもエラーが返ってきた際のエラーメッセージです。滅多にありませんが無料枠のレート範囲を超えてるとかです。
ON_ALL_MODELS_FAILED = {ON_ALL_MODELS_FAILED}
; 特定モデルとの通信で予期せぬエラーが発生した際のメッセージです。
; {model_key} は、エラーが発生したモデル名に自動で置き換えられます。
{ON_SPECIFIC_MODEL_FAILED_LINE}


; ======================================================================
; ■■■ コスチュームの登録 ■■■ (「衣装ID = 衣装名」で記載してください)
; ======================================================================
[COSTUMES]
{COSTUMES_SECTION}


; ======================================================================
; ■■■ 各コスチュームの設定 ■■■ (「COSTUME_DETAIL_衣装ID」でセクション名を登録してください)
; ======================================================================
{COSTUME_DETAIL_SECTIONS}

; ======================================================================
; ■■■ タッチエリア設定の詳細説明 ■■■
; ======================================================================
; キャラクターセクションまたは衣装セクション内に、以下の書式で記述します。
;
; 書式: touch_area_N = [[x1, y1, x2, y2]], アクション名, カーソル名
;
; ・ N             : 「_」に続く数字は1から始まる連番です。(例: touch_area_1, touch_area_2)
; ・ [x1, y1, x2, y2] : 元画像(例: normal_close.png)におけるタッチ判定矩形の
;                      左上(x1, y1)と右下(x2, y2)の座標を指定します。
;                      複数の矩形を同じアクションに割り当てることも可能です。
;                      (例: [[10,10,50,50], [60,60,100,100]])
; ・ アクション名  : AIに伝わるアクションの名前です。(例: 頭を撫でる)
; ・ カーソル名    : images/cursors/ フォルダ内のカーソルファイル名です(拡張子は不要)。
;                      (例: hand, poke)
; ======================================================================

; ======================================================================
; ■■■ 音声パラメータ設定 ■■■
; ======================================================================
; このキャラクターが利用する感情ごとの音声パラメータを設定します。
; キー名はAVAILABLE_EMOTIONSで定義した英語名と一致させてください。
[VOICE_PARAMS]
{VOICE_PARAMS_SECTION}


; ===================================
; 好感度の段階設定
; ===================================
; 閾値 = "その閾値以上になった時のユーザーへの認識名" の形式で記述します。
; 閾値は大きい順でなくても構いません（プログラム側で自動的に並べ替えます）。
[FAVORABILITY_STAGES]
{FAVORABILITY_STAGES_SECTION}


; ---------------------------------------------------
; ハート専用のUI設定（任意）
; ---------------------------------------------------
; このセクションが存在する場合、ハート画像にここでの設定が適用されます。
; 設定がない項目は、キャラクター本体の[INFO]セクションの設定にフォールバックします。
[FAVORABILITY_HEARTS]
{FAVORABILITY_HEARTS_SECTION}

[HEART_UI]
; ウィンドウの透過方式 (alpha: アルファチャンネル / color_key: 透過色指定)
TRANSPARENCY_MODE = {HEART_TRANSPARENCY_MODE}
TRANSPARENT_COLOR = {HEART_TRANSPARENT_COLOR}
EDGE_COLOR = {HEART_EDGE_COLOR}


; ======================================================================
; ■■■ 共有情報（GitHub） ■■■
; ======================================================================
[GITHUB]
; 共有先IssueのURL（または番号）。空なら新規作成されます。
ISSUE_URL = {GITHUB_ISSUE_URL}
ISSUE_NUMBER = {GITHUB_ISSUE_NUMBER}


; ======================================================================
; ■■■ サムネイル設定 ■■■
; ======================================================================
; 共有時のサムネイル(thumbnail.png)に重ねて表示する黒塗り修正エリアを設定します。
[THUMBNAIL]
; censor_rects = [[x1, y1, x2, y2], [x3, y3, x4, y4]] のように矩形のリストを記述します。
censor_rects = {censor_rects}
"""

    def __init__(self, project_id: str, base_path: str):
        self.project_id = project_id
        # 1. EXEのある場所から "characters" フォルダへの絶対パスを作成
        characters_dir_path = os.path.join(base_path, 'characters')
        
        # 2. このキャラクター専用のフォルダ（プロジェクトフォルダ）への絶対パスを作成
        self.base_path = os.path.join(characters_dir_path, self.project_id)
        
        # 3. character.ini ファイルへの最終的な絶対パスを作成
        self.ini_path = os.path.join(self.base_path, "character.ini")
        
        # 4.イベントファイルが格納されるディレクトリのパス
        self.events_dir = os.path.join(self.base_path, "events")
        # events ディレクトリが存在しない場合は作成
        os.makedirs(self.events_dir, exist_ok=True)
        # イベントスチルが格納されるディレクトリのパス
        self.stills_dir = os.path.join(self.base_path, "stills")
        # stills ディレクトリが存在しない場合は作成
        os.makedirs(self.stills_dir, exist_ok=True)

        # 5. readme.txt ファイルへのパスを作成
        self.readme_path = os.path.join(self.base_path, "readme.txt")

        # 6.専用話題ファイルのパスを作成
        self.topics_character_path = os.path.join(self.base_path, "topics.txt")

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.optionxform = str
        self.load()

        # 6.サムネイルが存在しなければ生成を試みる
        self._ensure_thumbnail_exists()

    def _ensure_thumbnail_exists(self):
        """
        キャラクターフォルダ直下にthumbnail.pngがなければ生成を試みる。
        """
        thumbnail_path = os.path.join(self.base_path, "thumbnail.png")
        source_image_path = os.path.join(self.base_path, "default", "normal_close.png")

        # サムネイルが存在しない、かつ、コピー元の基準画像が存在する場合のみ処理
        if not os.path.exists(thumbnail_path) and os.path.exists(source_image_path):
            try:
                print(f"サムネイルが存在しないため、'{source_image_path}' からコピーします。")
                shutil.copy2(source_image_path, thumbnail_path)
                print(f"'{thumbnail_path}' を作成しました。")
            except Exception as e:
                print(f"サムネイルのコピー中にエラーが発生しました: {e}")

    def load(self):
        """iniファイルを読み込む。存在しない場合は雛形から生成。"""
        if os.path.exists(self.ini_path):
            self.config.read(self.ini_path, encoding='utf-8')
            print(f"既存のiniファイルを読み込みました: {self.ini_path}")
        else:
            self._load_from_template()

    def _load_from_template(self):
        """
        新規キャラクター作成時に、メモリ上のconfigオブジェクトを
        DEFAULT_INI_CONTENTの構造とデフォルト値に基づいて初期化する。
        """
        print(f"新規キャラクター '{self.project_id}' のため、雛形からデフォルト設定を読み込みます。")
        
        # プレースホルダーに渡すための基本的なデフォルト値
        default_values = {
            'CHARACTER_NAME': self.project_id,
            'SYSTEM_NAME': self.project_id,
            'FIRST_PERSON': '私',
            'USER_REFERENCE': 'あなた',
            'THIRD_PERSON_REFERENCE': '(キャラクター名)ちゃん',
            'CHARACTER_PERSONALITY': '（ここにキャラクターの性格や設定を記述してください）',
            'SPEECH_FREQUENCY': '50',
            'TRANSPARENCY_MODE': 'color_key',
            'TRANSPARENT_COLOR': '#ff00ff',
            'EDGE_COLOR': '#838383',
            'IS_DERIVATIVE': 'false',
            'IS_NSFW': 'false',
            'engine': 'voicevox',
            'vv_speaker_name': '',
            'vv_speaker_style': '',
            'aivis_speaker_name': '',
            'aivis_speaker_style': '',
            'ON_EMPTY_RESPONSE': 'うーん、うまく言葉が出てきません。質問の内容がAIのルールに触れてしまったのかもしれません。表現を少し変えて、もう一度試していただけますか？',
            'ON_API_TIMEOUT': '考えるのに時間がかかりすぎているみたいです…。ネットワークやAPIキーの設定を確認してみてください。',
            'ON_ALL_MODELS_FAILED': 'すべてのAIモデルが今、使えないみたいです。少し待ってからもう一度試してみてください。',
            'ON_SPECIFIC_MODEL_FAILED_LINE': "ON_SPECIFIC_MODEL_FAILED = モデル'{model_key}'との通信でエラーが起きました。",
            'HEART_TRANSPARENCY_MODE': 'color_key',
            'HEART_TRANSPARENT_COLOR': '#FF00FF',
            'HEART_EDGE_COLOR': '#000000',
            'censor_rects': '',
            # --- 動的セクションの初期値 ---
            'COSTUMES_SECTION': 'default = デフォルト',
            'VOICE_PARAMS_SECTION': "normal = {'speedScale': 1.0, 'pitchScale': 0.0, 'intonationScale': 1.0, 'volumeScale': 1.0}",
            'FAVORABILITY_STAGES_SECTION': "450 = 唯一無二の存在\n300 = 親友\n150 = 信頼する相手\n100 = 友人\n50 = 顔なじみ\n5 = 知り合い\n0 = 初めまして\n-5 = 気まずい相手\n-50 = ちょっと苦手な相手\n-100 = 警戒している相手\n-150 = 嫌悪している相手\n-300 = 憎悪している相手\n-450 = 宿敵\n-500 = 不俱戴天の敵",
            'FAVORABILITY_HEARTS_SECTION': '450 = heart_6.png\n300 = heart_5.png\n150 = heart_4.png\n100 = heart_3.png\n50 = heart_2.png\n5 = heart_1.png\n0 = heart_0.png\n-5 = heart_-1.png\n-50 = heart_-2.png\n-100 = heart_-3.png\n-150 = heart_-4.png\n-300 = heart_-5.png\n-450 = heart_-6.png\n-500 = heart_-7.png',
        }
        
        # COSTUME_DETAILセクションの雛形もここで定義
        costume_detail_default = (
            "[COSTUME_DETAIL_default]\n"
            "IMAGE_PATH = default\n"
            "AVAILABLE_EMOTIONS = normal:通常\n"
        )
        default_values['COSTUME_DETAIL_SECTIONS'] = costume_detail_default

        # SafeFormatDictを使ってテンプレートを安全にフォーマット
        safe_args = self.SafeFormatDict(default_values)
        ini_string = self.DEFAULT_INI_CONTENT.format_map(safe_args)
        
        # フォーマットした文字列をConfigParserで直接読み込む
        self.config.read_string(ini_string)

    def save(self):
        """現在の設定内容を、コメントと構造を保持した形でiniファイルに書き出します。"""

        def _normalize_placeholder(v: str) -> str:
            s = (v or '').strip()
            # {SOMETHING} だけが入っているなら空扱いにする
            return '' if (len(s) >= 2 and s[0] == '{' and s[-1] == '}') else v

        os.makedirs(os.path.dirname(self.ini_path), exist_ok=True)
        
        # --- 1. 固定セクションの値を辞書にまとめる ---
        format_args = {
            # [INFO]
            'CHARACTER_NAME': self.get('INFO', 'CHARACTER_NAME', '新しいキャラクター'),
            'SYSTEM_NAME': self.get('INFO', 'SYSTEM_NAME', ''),
            'FIRST_PERSON': self.get('INFO', 'FIRST_PERSON', ''),
            'USER_REFERENCE': self.get('INFO', 'USER_REFERENCE', ''),
            'THIRD_PERSON_REFERENCE': self.get('INFO', 'THIRD_PERSON_REFERENCE', ''),
            'CHARACTER_PERSONALITY': self.get('INFO', 'CHARACTER_PERSONALITY', '').replace('\n', r'\n'),
            'SPEECH_FREQUENCY': self.get('INFO', 'SPEECH_FREQUENCY', '50'),
            'TRANSPARENCY_MODE': self.get('INFO', 'TRANSPARENCY_MODE', 'color_key'),
            'TRANSPARENT_COLOR': self.get('INFO', 'TRANSPARENT_COLOR', '#ff00ff'),
            'EDGE_COLOR': self.get('INFO', 'EDGE_COLOR', '#838383'),
            'IS_DERIVATIVE': self.get('INFO', 'IS_DERIVATIVE', 'false'),
            'IS_NSFW': self.get('INFO', 'IS_NSFW', 'false'),
            # [VOICE] & [VOICE_*]
            'engine': self.get('VOICE', 'engine', 'voicevox'),
            'vv_speaker_name': self.get('VOICE_VOX', 'speaker_name', ''),
            'vv_speaker_style': self.get('VOICE_VOX', 'speaker_style', ''),
            'aivis_speaker_name': self.get('AIVIS_SPEECH', 'speaker_name', ''),
            'aivis_speaker_style': self.get('AIVIS_SPEECH', 'speaker_style', ''),
            # [SYSTEM_MESSAGES] (安全なものだけ)
            'ON_EMPTY_RESPONSE': self.get('SYSTEM_MESSAGES', 'ON_EMPTY_RESPONSE', ''),
            'ON_API_TIMEOUT': self.get('SYSTEM_MESSAGES', 'ON_API_TIMEOUT', ''),
            'ON_ALL_MODELS_FAILED': self.get('SYSTEM_MESSAGES', 'ON_ALL_MODELS_FAILED', ''),
            # [HEART_UI]
            'HEART_TRANSPARENCY_MODE': self.get('HEART_UI', 'TRANSPARENCY_MODE', 'color_key'),
            'HEART_TRANSPARENT_COLOR': self.get('HEART_UI', 'TRANSPARENT_COLOR', '#FF00FF'),
            'HEART_EDGE_COLOR': self.get('HEART_UI', 'EDGE_COLOR', '#000000'),
            # [GITHUB]（ここだけ _normalize_placeholder を噛ませる）
            'GITHUB_ISSUE_URL': _normalize_placeholder(self.get('GITHUB', 'ISSUE_URL', '')),
            'GITHUB_ISSUE_NUMBER': _normalize_placeholder(self.get('GITHUB', 'ISSUE_NUMBER', '')),
            # [THUMBNAIL]
            'censor_rects': self.get('THUMBNAIL', 'censor_rects', ''),
        }

        # --- 2. 特別な扱いが必要な行や、動的セクションの文字列を生成する ---

        # ON_SPECIFIC_MODEL_FAILED の行全体を文字列として生成する
        specific_fail_value = self.get('SYSTEM_MESSAGES', 'ON_SPECIFIC_MODEL_FAILED', fallback='', raw=True)
        format_args['ON_SPECIFIC_MODEL_FAILED_LINE'] = f"ON_SPECIFIC_MODEL_FAILED = {specific_fail_value}"

        def build_section_string(section_name):
            """指定されたセクションの内容を 'key = value' の文字列リストに変換する"""
            lines = []
            if self.config.has_section(section_name):
                for key, value in self.config.items(section_name):
                    lines.append(f"{key} = {value}")
            return "\n".join(lines)

        format_args['COSTUMES_SECTION'] = build_section_string('COSTUMES')
        format_args['VOICE_PARAMS_SECTION'] = build_section_string('VOICE_PARAMS')
        format_args['FAVORABILITY_STAGES_SECTION'] = build_section_string('FAVORABILITY_STAGES')
        format_args['FAVORABILITY_HEARTS_SECTION'] = build_section_string('FAVORABILITY_HEARTS')

        # [COSTUME_DETAIL_*] セクション
        costume_detail_lines = []
        costumes = self.get_costumes()
        for costume in costumes:
            section_name = f'COSTUME_DETAIL_{costume["id"]}'
            if self.config.has_section(section_name):
                costume_detail_lines.append(f"[{section_name}]")
                for key, value in self.config.items(section_name):
                    costume_detail_lines.append(f"{key} = {value}")
                costume_detail_lines.append("") 
        format_args['COSTUME_DETAIL_SECTIONS'] = "\n".join(costume_detail_lines)

        # --- 3.安全な辞書を使ってテンプレートをフォーマット  ---
        # `format_map` は、`SafeFormatDict` の `__missing__` を利用してエラーを回避する
        safe_args = self.SafeFormatDict(format_args)
        output_content = self.DEFAULT_INI_CONTENT.format_map(safe_args)
        
        with open(self.ini_path, 'w', encoding='utf-8') as configfile:
            configfile.write(output_content.strip())
            
        print(f"設定をコメントを保持した形式でファイルに保存しました: {self.ini_path}")

    def get(self, section: str, option: str, fallback: str = '', raw: bool = False) -> str:
        """
        設定値を取得します。raw=Trueで補間を無効化できます。
        
        Args:
            section (str): セクション名.
            option (str): オプション名.
            fallback (str): 値が存在しない場合に返すデフォルト値.
            raw (bool): Trueの場合、値の補間を行わず生の文字列を返します。
        
        Returns:
            str: 取得した設定値.
        """
        # self.config.get に raw と fallback を渡す
        return self.config.get(section, option, fallback=fallback, raw=raw)

    def set(self, section: str, option: str, value):
        """
        設定値をセットします。
        
        Args:
            section (str): セクション名.
            option (str): オプション名.
            value: セットする値 (自動的に文字列に変換されます).
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))

    def get_issue_reference(self):
        """character.ini 内の [GITHUB] から Issue 参照を取得する。
        Returns:
            tuple[int|None, str|None]: (issue_number, issue_url)
        """
        num_raw = self.get('GITHUB', 'ISSUE_NUMBER', '').strip()
        url = self.get('GITHUB', 'ISSUE_URL', '').strip()
        number = None
        # 優先: 数値があればそれを使う
        if num_raw.isdigit():
            number = int(num_raw)
        # URL からも抽出を試みる
        if number is None and url:
            import re
            m = re.search(r'/issues/(\d+)', url)
            if m:
                try:
                    number = int(m.group(1))
                except ValueError:
                    number = None
        return number, (url or None)

    def set_issue_reference(self, issue_number: int | None = None, issue_url: str | None = None):
        """[GITHUB] セクションに Issue 情報を保存する（セクションが無ければ作成）。
        このメソッドはメモリ上の値を更新するだけ。ディスクに反映するには save() を呼ぶ。
        """
        if issue_number is not None:
            self.set('GITHUB', 'ISSUE_NUMBER', str(issue_number))
        if issue_url is not None:
            self.set('GITHUB', 'ISSUE_URL', issue_url)

    def get_costumes(self) -> list:
        """
        [COSTUMES]セクションから衣装のリストを取得します。
        Returns:
            list: [{'id': str, 'name': str}, ...] の形式のリスト。
        """
        if not self.config.has_section('COSTUMES'):
            return []
        
        costumes = []
        for costume_id, costume_name in self.config.items('COSTUMES'):
            costumes.append({'id': costume_id, 'name': costume_name})
        return costumes

    def add_costume(self, costume_id: str, costume_name: str):
        """
        新しい衣装をiniファイルとファイルシステムに追加します。
        """
        if self.config.has_option('COSTUMES', costume_id):
            raise ValueError(f"衣装ID '{costume_id}' は既に使用されています。")

        # 1. [COSTUMES]セクションに追記
        self.set('COSTUMES', costume_id, costume_name)

        # 2. 対応する[COSTUME_DETAIL_...]セクションを雛形から作成
        section_name = f'COSTUME_DETAIL_{costume_id}'
        self.config.add_section(section_name)
        self.set(section_name, 'IMAGE_PATH', costume_id) # IMAGE_PATHはIDと同じにするのが規約
        self.set(section_name, 'AVAILABLE_EMOTIONS', 'normal:通常')

        # 3. 対応する画像フォルダを作成
        costume_image_path = os.path.join(self.base_path, costume_id)
        os.makedirs(costume_image_path, exist_ok=True)

    def rename_costume(self, old_id: str, new_id: str, new_name: str):
        """
        衣装のIDと名前を変更します。
        """
        if old_id == 'default':
            # default衣装は名前のみ変更可能
            self.set('COSTUMES', old_id, new_name)
            return

        # [COSTUMES]セクションのキーと値を更新
        self.config.remove_option('COSTUMES', old_id)
        self.set('COSTUMES', new_id, new_name)

        # [COSTUME_DETAIL_...]セクションをリネーム
        old_section = f'COSTUME_DETAIL_{old_id}'
        new_section = f'COSTUME_DETAIL_{new_id}'
        if self.config.has_section(old_section):
            items = self.config.items(old_section)
            self.config.remove_section(old_section)
            self.config.add_section(new_section)
            for key, value in items:
                # IMAGE_PATHも新しいIDに更新
                if key.lower() == 'image_path':
                    self.set(new_section, key, new_id)
                else:
                    self.set(new_section, key, value)
        
        # 画像フォルダをリネーム
        old_folder = os.path.join(self.base_path, old_id)
        new_folder = os.path.join(self.base_path, new_id)
        if os.path.isdir(old_folder):
            os.rename(old_folder, new_folder)

    def delete_costume(self, costume_id: str):
        """
        指定された衣装をiniファイルとファイルシステムから削除します。
        """
        if costume_id == 'default':
            raise ValueError("'default'衣装は削除できません。")

        # 1. [COSTUMES]セクションから削除
        self.config.remove_option('COSTUMES', costume_id)

        # 2. [COSTUME_DETAIL_...]セクションを削除
        section_name = f'COSTUME_DETAIL_{costume_id}'
        if self.config.has_section(section_name):
            self.config.remove_section(section_name)

        # 3. 画像フォルダを再帰的に削除
        costume_image_path = os.path.join(self.base_path, costume_id)
        if os.path.isdir(costume_image_path):
            shutil.rmtree(costume_image_path)

    def get_expressions_for_costume(self, costume_id: str) -> list:
        """
        指定された衣装の表情リストを取得します。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        emotions_str = self.get(section, 'AVAILABLE_EMOTIONS')
        if not emotions_str:
            return []
            
        expressions = []
        try:
            for pair in emotions_str.split(','):
                if ':' in pair:
                    eng_id, jp_name = pair.split(':', 1)
                    expressions.append({'id': eng_id.strip(), 'name': jp_name.strip()})
        except Exception as e:
            print(f"表情データの解析エラー: {e}")
        return expressions

    def update_expressions_for_costume(self, costume_id: str, expressions: list):
        """
        指定された衣装の表情リストをiniファイルに保存します。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        # リストを "id:name,id2:name2" 形式の文字列に変換
        emotions_str = ",".join([f"{expr['id']}:{expr['name']}" for expr in expressions])
        self.set(section, 'AVAILABLE_EMOTIONS', emotions_str)

    def get_touch_areas_for_costume(self, costume_id: str, emotion_id: str) -> list:
        """
        指定された衣装と感情のタッチエリア設定を解析してリストで返します。
        指定された感情に設定がなければ、normal(基本)の設定を返します。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        if not self.config.has_section(section):
            return []

        # --- 1. 指定された感情専用のキーパターンを定義 ---
        # 例: emotion_idが"fun"なら、"touch_area_fun_..."にマッチ
        emotion_specific_pattern = re.compile(f'^touch_area_{re.escape(emotion_id)}_(\\d+)$')
        
        # --- 2. 基本となるnormal用のキーパターンを定義 ---
        # "touch_area_数字" にのみマッチし、"touch_area_fun_数字" などは除外
        normal_pattern = re.compile(r'^touch_area_(\d+)$')

        def _parse_areas_from_pattern(pattern):
            areas = []
            for key, value in self.config.items(section):
                match = pattern.match(key)
                if match:
                    try:
                        parts = value.rsplit(',', 2)
                        if len(parts) != 3: continue

                        coords_def_str, action_name_raw, cursor_name = [p.strip() for p in parts]
                        # エスケープされた改行文字(\\n)を実際の改行(\n)に戻す
                        action_name = action_name_raw.replace('\\n', '\n')
                        rect_list = ast.literal_eval(coords_def_str)
                        
                        areas.append({
                            'key': key,
                            'rects': rect_list,
                            'action': action_name,
                            'cursor': cursor_name
                        })
                    except (ValueError, SyntaxError, IndexError) as e:
                        print(f"タッチエリアの解析エラー ({key}): {e}")
            # キーの連番でソートして返す
            return sorted(areas, key=lambda x: int(pattern.match(x['key']).group(1)))

        # --- 3. 指定された感情のエリアを探し、なければnormalを探す ---
        emotion_areas = _parse_areas_from_pattern(emotion_specific_pattern)
        if emotion_areas:
            # 専用設定が見つかった場合はそれを返す
            return emotion_areas
        
        # normal自身を要求されているか、フォールバックとしてnormalを返す
        return _parse_areas_from_pattern(normal_pattern)

    def get_specific_touch_areas_for_costume(self, costume_id: str, emotion_id: str) -> list | None:
        """
        指定された感情専用のタッチエリア設定"のみ"を取得します。
        存在しない場合はNoneを返します。UIでの継承状態の判定に使用します。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        if not self.config.has_section(section):
            return None
        
        emotion_specific_pattern = re.compile(f'^touch_area_{re.escape(emotion_id)}_(\\d+)$')
        has_specific_setting = any(emotion_specific_pattern.match(key) for key in self.config.options(section))

        if has_specific_setting:
            return self.get_touch_areas_for_costume(costume_id, emotion_id)
        else:
            return None

    def update_touch_areas_for_costume(self, costume_id: str, emotion_id: str, areas: list):
        """
        指定された感情のタッチエリアリストからiniファイルの設定を更新します。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        if not self.config.has_section(section):
            return

        # --- 1. 更新対象の感情に対応する既存のtouch_areaをすべて削除 ---
        key_prefix = f'touch_area_{emotion_id}_' if emotion_id != 'normal' else 'touch_area_'
        pattern = re.compile(f'^{re.escape(key_prefix)}(\\d+)$')
        
        for key in list(self.config.options(section)):
            if pattern.match(key):
                self.config.remove_option(section, key)
        
        # --- 2. 新しいリストから設定を再構築 ---
        for i, area in enumerate(areas):
            new_key = f'{key_prefix}{i+1}'
            rects_str = str(area['rects'])
            # 実際の改行(\n)をエスケープされた文字列(\\n)に置換する
            action_name_escaped = area['action'].replace('\n', '\\n')
            value = f"{rects_str}, {action_name_escaped}, {area['cursor']}"
            self.set(section, new_key, value)
            
    def delete_touch_areas_for_emotion(self, costume_id: str, emotion_id: str):
        """
        指定された感情専用のタッチエリア設定をすべて削除し、normalへの継承状態に戻す。
        """
        section = f'COSTUME_DETAIL_{costume_id}'
        if not self.config.has_section(section) or emotion_id == 'normal':
            return
            
        key_prefix = f'touch_area_{emotion_id}_'
        pattern = re.compile(f'^{re.escape(key_prefix)}(\\d+)$')
        
        for key in list(self.config.options(section)):
            if pattern.match(key):
                self.config.remove_option(section, key)

    def get_favorability_stages(self) -> list:
        """
        [FAVORABILITY_STAGES]セクションから好感度段階のリストを取得します。
        閾値の降順でソートして返します。
        """
        if not self.config.has_section('FAVORABILITY_STAGES'):
            return []
            
        stages = []
        for threshold_str, name in self.config.items('FAVORABILITY_STAGES'):
            try:
                stages.append({'threshold': int(threshold_str), 'name': name})
            except ValueError:
                print(f"警告: 不正な閾値'{threshold_str}'は無視されました。")
        
        # 閾値の降順（大きいものから）でソート
        stages.sort(key=lambda x: x['threshold'], reverse=True)
        return stages

    def update_favorability_stages(self, stages: list):
        """
        好感度段階のリストからiniファイルの設定を更新します。
        """
        # 既存のセクションをクリア
        if self.config.has_section('FAVORABILITY_STAGES'):
            self.config.remove_section('FAVORABILITY_STAGES')
        self.config.add_section('FAVORABILITY_STAGES')
        
        # 新しいリストから設定を再構築
        for stage in stages:
            self.set('FAVORABILITY_STAGES', str(stage['threshold']), stage['name'])

    def get_favorability_hearts(self) -> list:
        """
        [FAVORABILITY_HEARTS]セクションからハート設定のリストを取得します。
        閾値の降順でソートして返します。
        """
        if not self.config.has_section('FAVORABILITY_HEARTS'):
            return []
            
        hearts = []
        for threshold_str, filename in self.config.items('FAVORABILITY_HEARTS'):
            try:
                hearts.append({'threshold': int(threshold_str), 'filename': filename})
            except ValueError:
                print(f"警告: 不正な閾値'{threshold_str}'は無視されました。")
        
        hearts.sort(key=lambda x: x['threshold'], reverse=True)
        return hearts

    def update_favorability_hearts(self, hearts: list):
        """
        ハート設定のリストからiniファイルの設定を更新します。
        """
        if self.config.has_section('FAVORABILITY_HEARTS'):
            self.config.remove_section('FAVORABILITY_HEARTS')
        self.config.add_section('FAVORABILITY_HEARTS')
        
        for heart in hearts:
            self.set('FAVORABILITY_HEARTS', str(heart['threshold']), heart['filename'])

    def get_heart_ui_colors(self) -> dict:
        """
        [HEART_UI]セクションから色設定と透過モードを取得します。
        """
        if not self.config.has_section('HEART_UI'):
            return {'TRANSPARENCY_MODE': 'color_key', 'TRANSPARENT_COLOR': '', 'EDGE_COLOR': ''}
        
        return {
            'TRANSPARENCY_MODE': self.get('HEART_UI', 'TRANSPARENCY_MODE', fallback='color_key'),
            'TRANSPARENT_COLOR': self.get('HEART_UI', 'TRANSPARENT_COLOR', fallback=''),
            'EDGE_COLOR': self.get('HEART_UI', 'EDGE_COLOR', fallback='')
        }

    def update_heart_ui_colors(self, mode: str, trans_color: str, edge_color: str):
        """
        [HEART_UI]セクションの色設定と透過モードを更新します。
        """
        if not self.config.has_section('HEART_UI'):
            self.config.add_section('HEART_UI')
            
        self.set('HEART_UI', 'TRANSPARENCY_MODE', mode)
        self.set('HEART_UI', 'TRANSPARENT_COLOR', trans_color)
        self.set('HEART_UI', 'EDGE_COLOR', edge_color)

    def remove_voice_param(self, expression_id: str):
        """指定された表情IDの音声パラメータをiniから削除します。"""
        if self.config.has_option('VOICE_PARAMS', expression_id):
            self.config.remove_option('VOICE_PARAMS', expression_id)
            print(f"音声パラメータ '{expression_id}' を削除しました。")

    def get_voice_param(self, expression_id: str, fallback: dict = None) -> dict:
        """
        指定された表情IDの音声パラメータを辞書として取得します。
        """
        params_str = self.get('VOICE_PARAMS', expression_id)
        if params_str:
            try:
                return ast.literal_eval(params_str)
            except (ValueError, SyntaxError):
                print(f"音声パラメータ '{expression_id}' の解析に失敗しました。")
        
        if fallback is not None:
            return fallback

        return {'speedScale': 1.0, 'pitchScale': 0.0, 'intonationScale': 1.0, 'volumeScale': 1.0}

    def get_readme_content(self) -> str:
        """readme.txtの内容を読み込む。存在しない場合は空文字列を返す。"""
        try:
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def save_readme_content(self, content: str):
        """readme.txtに内容を書き込む。"""
        with open(self.readme_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def generate_readme_template(self) -> str:
        """設定情報からreadmeのテンプレート文字列を生成する。"""
        character_name = self.get('INFO', 'CHARACTER_NAME', '未設定')
        # 複数行の可能性があるため、最初の行のみを取得するか、適切に処理する
        personality_raw = self.get('INFO', 'CHARACTER_PERSONALITY', '（ここにキャラクター紹介文を記述してください）')
        personality = personality_raw.replace(r'\n', '\n').split('\n')[0]
        engine = self.get('VOICE', 'engine', '未設定')
        
        speaker_section = 'VOICE_VOX' if engine == 'voicevox' else 'AIVIS_SPEECH'
        speaker_name = self.get(speaker_section, 'speaker_name', '未設定')
        speaker_style = self.get(speaker_section, 'speaker_style', '未設定')

        template = (
            f"# キャラクター配布: {character_name}\n\n"
            f"## キャラクター紹介\n"
            f"> {personality}\n\n"
            f"---\n\n"
            f"**音声エンジン:** {engine}\n"
            f"**話者:** {speaker_name} / {speaker_style}\n\n"
            f"---\n\n"
            f"このキャラクターを使用するには、添付のZIPファイルをダウンロードし、「キャラクタースタジオ」の`characters`フォルダ内に解凍してください。\n"
        )
        return template

    def get_thumbnail_censor_rects(self) -> list:
        """
        [THUMBNAIL]セクションから黒塗り矩形のリストを取得します。
        """
        rects_str = self.get('THUMBNAIL', 'censor_rects', '[]')
        try:
            rects = ast.literal_eval(rects_str)
            if isinstance(rects, list):
                return rects
        except (ValueError, SyntaxError):
            print(f"警告: 不正な黒塗り矩形データです: {rects_str}")
        return []

    def update_thumbnail_censor_rects(self, rects: list):
        """
        黒塗り矩形のリストをiniファイルに保存します。
        """
        self.set('THUMBNAIL', 'censor_rects', str(rects))

    def get_event_ids(self) -> list[str]:
        """
        eventsフォルダ内のすべてのイベントID（ファイル名から拡張子を除いたもの）のリストを返す。
        """
        if not os.path.isdir(self.events_dir):
            return []
        return sorted([
            os.path.splitext(f)[0] for f in os.listdir(self.events_dir)
            if f.endswith('.json')
        ])

    def load_event(self, event_id: str) -> dict | None:
        """
        指定されたイベントIDのJSONファイルを読み込み、辞書として返す。
        """
        event_path = os.path.join(self.events_dir, f"{event_id}.json")
        if not os.path.exists(event_path):
            return None
        try:
            with open(event_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"イベントファイル '{event_path}' の読み込みに失敗しました: {e}")
            return None

    def save_event(self, event_id: str, event_data: dict):
        """
        イベントデータを指定されたIDのJSONファイルとして保存する。
        """
        event_path = os.path.join(self.events_dir, f"{event_id}.json")
        try:
            with open(event_path, 'w', encoding='utf-8') as f:
                json.dump(event_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"イベントファイル '{event_path}' の保存に失敗しました: {e}")
            raise # エラーを呼び出し元に伝える

    def delete_event(self, event_id: str):
        """
        指定されたイベントIDのJSONファイルを削除する。
        """
        event_path = os.path.join(self.events_dir, f"{event_id}.json")
        if os.path.exists(event_path):
            os.remove(event_path)

    def rename_event(self, old_event_id: str, new_event_id: str):
        """
        イベントID（ファイル名）を変更する。
        """
        old_path = os.path.join(self.events_dir, f"{old_event_id}.json")
        new_path = os.path.join(self.events_dir, f"{new_event_id}.json")
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)

    def get_special_topics(self) -> list[str]:
        """topics.txtを読み込み、話題のリストを返す。"""
        if not os.path.exists(self.topics_character_path):
            return []
        try:
            with open(self.topics_character_path, 'r', encoding='utf-8') as f:
                # 空行や前後の空白を除去してリスト化
                topics = [line.strip() for line in f if line.strip()]
            return topics
        except Exception as e:
            print(f"専用話題ファイルの読み込みに失敗しました: {e}")
            return []

    def update_special_topics(self, topics: list[str]):
        """専用話題のリストをtopics.txtに上書き保存する。"""
        try:
            with open(self.topics_character_path, 'w', encoding='utf-8') as f:
                # 各話題を改行で区切って書き込む
                f.write('\n'.join(topics))
        except Exception as e:
            print(f"専用話題ファイルの保存に失敗しました: {e}")
            raise # エラーを呼び出し元に伝える
