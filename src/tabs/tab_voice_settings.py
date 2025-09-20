# src/tabs/tab_voice_settings.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import platform
if platform.system() == "Windows": import winsound
import ast
from .tab_base import TabBase

class TabVoiceSettings(TabBase):
    def create_widgets(self):
        parent = self.scrollable_frame
        parent.columnconfigure(1, weight=1)
        
        style = ttk.Style(self)
        style.configure("Tab.TLabel", font=self.app.font_normal)
        style.configure("Tab.TButton", font=self.app.font_normal)
        style.configure("Bold.TLabel", font=self.app.font_title)

        pady = self.app.padding_small
        
        ttk.Label(parent, text="音声エンジン:", style="Tab.TLabel").grid(row=0, column=0, sticky="w", pady=pady)
        engine_combo = ttk.Combobox(parent, textvariable=self.editor.selected_engine, values=["voicevox", "aivisspeech"], state="readonly", font=self.app.font_normal)
        engine_combo.grid(row=0, column=1, sticky="ew", pady=pady, padx=(0, self.app.padding_small))
        engine_combo.bind("<<ComboboxSelected>>", self.on_engine_selected)

        ttk.Label(parent, text="話者名:", style="Tab.TLabel").grid(row=1, column=0, sticky="w", pady=pady)
        speaker_combo = ttk.Combobox(parent, textvariable=self.editor.selected_speaker, state="disabled", font=self.app.font_normal)
        speaker_combo.grid(row=1, column=1, sticky="ew", pady=pady, padx=(0, self.app.padding_small))
        speaker_combo.bind("<<ComboboxSelected>>", self.on_speaker_selected)

        ttk.Label(parent, text="スタイル:", style="Tab.TLabel").grid(row=2, column=0, sticky="w", pady=pady)
        style_combo = ttk.Combobox(parent, textvariable=self.editor.selected_style, state="disabled", font=self.app.font_normal)
        style_combo.grid(row=2, column=1, sticky="ew", pady=pady, padx=(0, self.app.padding_small))

        test_frame = ttk.Frame(parent)
        test_frame.grid(row=3, column=1, sticky="ew", pady=self.app.padding_normal)
        test_frame.columnconfigure(0, weight=1)
        test_entry = ttk.Entry(test_frame, font=self.app.font_normal)
        test_entry.insert(0, "この声で話します。")
        test_entry.grid(row=0, column=0, sticky="ew", padx=(0, self.app.padding_normal))
        test_button = ttk.Button(test_frame, text="テスト再生", command=self.test_speech, style="Tab.TButton")
        test_button.grid(row=0, column=1)

        ttk.Separator(parent, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=self.app.padding_large)
        
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        ttk.Label(header_frame, text="基本の声質調整 (normal)", font=self.app.font_title).pack(side="left")
        reset_button = ttk.Button(header_frame, text="初期値に戻す", command=self.reset_voice_params, style="Tab.TButton")
        reset_button.pack(side="right")
        
        param_frame = ttk.Frame(parent)
        param_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=self.app.padding_normal)
        param_frame.columnconfigure(1, weight=1)
        
        params_info = {
            "speedScale": {"name": "話速", "min": 0.5, "max": 2.0, "default": 1.0},
            "pitchScale": {"name": "高さ", "min": -0.15, "max": 0.15, "default": 0.0},
            "intonationScale": {"name": "抑揚", "min": 0.0, "max": 2.0, "default": 1.0},
            "volumeScale": {"name": "音量", "min": 0.0, "max": 2.0, "default": 1.0}
        }
        param_widgets = {}
        row_count = 0
        for key, info in params_info.items():
            ttk.Label(param_frame, text=info["name"], style="Tab.TLabel").grid(row=row_count, column=0, sticky="w", padx=(0, self.app.padding_normal))
            entry_var = tk.StringVar()
            value_entry = ttk.Entry(param_frame, textvariable=entry_var, width=6, font=self.app.font_normal)
            value_entry.grid(row=row_count, column=2, padx=(self.app.padding_small,0))
            scale = ttk.Scale(param_frame, from_=info["min"], to=info["max"], orient="horizontal")
            scale.grid(row=row_count, column=1, sticky="ew")
            def on_scale_change(value, e_var=entry_var): e_var.set(f"{float(value):.2f}")
            def on_entry_change(*args, s=scale, e_var=entry_var, i=info):
                try:
                    val = float(e_var.get())
                    clamped_val = max(i["min"], min(i["max"], val))
                    s.set(clamped_val)
                    if val != clamped_val: e_var.set(f"{clamped_val:.2f}")
                except (ValueError, tk.TclError): pass
            scale.config(command=on_scale_change)
            entry_var.trace_add("write", on_entry_change)
            param_widgets[key] = {"scale": scale, "entry_var": entry_var, "info": info}
            row_count += 1
        
        self.widgets = {
            'engine_combo': engine_combo, 'speaker_combo': speaker_combo, 'style_combo': style_combo,
            'test_button': test_button, 'reset_button': reset_button, 'params': param_widgets,'test_entry': test_entry
        }

    def load_data(self):
        # 1. 保存されているエンジン設定を読み込む
        saved_engine = self.character_data.get('VOICE', 'engine', fallback='voicevox')
        self.editor.selected_engine.set(saved_engine)

        # 2. APIの応答を待たずに、まず保存されている話者名とスタイルをStringVarに直接設定する
        #    これにより、エンジンが未起動でもUIに既存の設定値が表示される
        section = 'VOICE_VOX' if saved_engine == 'voicevox' else 'AIVIS_SPEECH'
        saved_speaker = self.character_data.get(section, 'speaker_name')
        saved_style = self.character_data.get(section, 'speaker_style')
        
        # StringVarに値をセット（Comboboxはこれに連動して表示が変わる）
        self.editor.selected_speaker.set(saved_speaker)
        self.editor.selected_style.set(saved_style)

        # 3. 基本の音声パラメータを読み込む
        params_str = self.character_data.get('VOICE_PARAMS', 'normal')
        if params_str:
            try:
                params = ast.literal_eval(params_str)
                param_ui = self.widgets['params']
                for key, value in params.items():
                    if key in param_ui: param_ui[key]['scale'].set(float(value))
            except (ValueError, SyntaxError) as e:
                self.reset_voice_params()
        else:
            self.reset_voice_params()
        
        # 4. この後、非同期で話者リストの「選択肢」の取得を試みる
        self.editor.after(100, self.init_voice_settings)

    def collect_data(self):
        engine = self.editor.selected_engine.get()
        speaker = self.editor.selected_speaker.get()
        style = self.editor.selected_style.get()
        self.character_data.set('VOICE', 'engine', engine)
        if engine == 'voicevox':
            self.character_data.set('VOICE_VOX', 'speaker_name', speaker); self.character_data.set('VOICE_VOX', 'speaker_style', style)
        elif engine == 'aivisspeech':
            self.character_data.set('AIVIS_SPEECH', 'speaker_name', speaker); self.character_data.set('AIVIS_SPEECH', 'speaker_style', style)
        param_ui = self.widgets['params']
        params_dict = {}
        for key, widgets in param_ui.items():
            try: params_dict[key] = round(float(widgets['entry_var'].get()), 2)
            except ValueError: params_dict[key] = widgets['info']['default']
        self.character_data.set('VOICE_PARAMS', 'normal', str(params_dict))

    def reset_voice_params(self):
        for key, widgets in self.widgets.get('params', {}).items():
            widgets['scale'].set(widgets['info']['default'])

    def init_voice_settings(self):
        threading.Thread(target=self._fetch_speaker_data, args=(self.editor.selected_engine.get(),), daemon=True).start()

    def _fetch_speaker_data(self, engine_name):
        if not engine_name or engine_name in self.editor.speaker_data_cache:
            self.editor.after(0, self.update_speaker_list); return
        urls = {'voicevox': 'http://127.0.0.1:50021/speakers', 'aivisspeech': 'http://127.0.0.1:10101/speakers'}
        if not (url := urls.get(engine_name)): return
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            self.editor.speaker_data_cache[engine_name] = response.json()
        except requests.exceptions.RequestException:
            self.editor.speaker_data_cache[engine_name] = []
        self.editor.after(0, self.update_speaker_list)

    def on_engine_selected(self, event=None):
        engine = self.editor.selected_engine.get()
        self.widgets['speaker_combo'].set(''); self.widgets['style_combo'].set('')
        self.widgets['style_combo']['values'] = []
        if engine not in self.editor.speaker_data_cache:
            self.widgets['speaker_combo'].config(state="disabled"); self.widgets['speaker_combo'].set("情報取得中...")
            threading.Thread(target=self._fetch_speaker_data, args=(engine,), daemon=True).start()
        else: self.update_speaker_list()
    
    def update_speaker_list(self):
        engine = self.editor.selected_engine.get()
        speakers = self.editor.speaker_data_cache.get(engine)
        combo = self.widgets['speaker_combo']
        
        if speakers is None: 
            # データ取得中は、コンボボックスを無効化するがテキストはStringVarの値が維持される
            combo.set("（情報取得中...）")
            combo.config(state="disabled")
            return
            
        if not speakers: 
            # 取得に失敗した場合もコンボボックスを無効化するが、テキストは維持
            combo.config(state="disabled")
            return

        # 取得に成功した場合、選択肢を更新して有効化
        speaker_names = sorted([s['name'] for s in speakers])
        combo['values'] = speaker_names
        combo.config(state="readonly")
        
        # 選択済みの話者に基づいて、スタイルのリストも更新を試みる
        # load_dataで設定済みの値がStringVarに残っているため、再セットは不要
        self.update_style_list()
  
    def on_speaker_selected(self, event=None):
        self.widgets['style_combo'].set(''); self.update_style_list()

    def update_style_list(self):
        engine, speaker_name = self.editor.selected_engine.get(), self.editor.selected_speaker.get()
        speakers = self.editor.speaker_data_cache.get(engine)
        style_combo = self.widgets['style_combo']

        if not speaker_name or not speakers:
            style_combo.config(state="disabled")
            return
            
        styles = []
        for speaker in speakers:
            if speaker['name'] == speaker_name:
                styles = sorted([s['name'] for s in speaker['styles']])
                break
        
        style_combo['values'] = styles
        style_combo.config(state="readonly" if styles else "disabled")

    def test_speech(self):
        params_dict = {}
        for key, widgets in self.widgets['params'].items():
            try: params_dict[key] = float(widgets['entry_var'].get())
            except ValueError: params_dict[key] = widgets['info']['default']
        self.widgets['test_button'].config(state="disabled", text="生成中...")
        self.editor.trigger_test_speech(
            text=self.widgets['test_entry'].get(),
            params_override=params_dict,
            on_finish_callback=lambda: self.widgets['test_button'].config(state="normal", text="テスト再生")
        )