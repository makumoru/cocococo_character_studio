# src/tabs/tab_base.py

import tkinter as tk
from tkinter import ttk

class TabBase(ttk.Frame):
    """
    すべての設定タブが継承する基底クラス。
    """
    def __init__(self, parent, editor_instance):
        # 親のEditorWindowからappインスタンスを取得
        self.editor = editor_instance
        self.app = editor_instance.app 
        
        # 親のNotebookに直接配置されるこのフレーム自体はパディングを持たない
        super().__init__(parent)
        
        self.character_data = editor_instance.character_data

        # --- スクロール機構のセットアップ ---
        # このフレーム(self)のグリッドを設定し、Canvasが全体に広がるようにする
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Canvasと垂直Scrollbarを作成
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")

        # 実際にウィジェットが配置される、スクロール対象のフレームを作成
        # このフレームが以前の self の役割を担い、パディングも持つ
        self.scrollable_frame = ttk.Frame(self.canvas, padding=self.app.padding_large)
        self.scrollable_frame_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # scrollable_frame のサイズ変更を検知して、Canvasのスクロール範囲を更新
        def on_frame_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # canvasのサイズ変更を検知して、scrollable_frameの幅と高さを調整する
        def on_canvas_configure(event):
            # scrollable_frameの幅をcanvasの幅に合わせる（横スクロール防止）
            self.canvas.itemconfig(self.scrollable_frame_id, width=event.width)
            
            # scrollable_frameの高さを、「コンテンツの要求高さ」と「Canvasの表示高さ」の
            # うち、大きい方の値に設定する。
            new_height = max(self.scrollable_frame.winfo_reqheight(), event.height)
            self.canvas.itemconfig(self.scrollable_frame_id, height=new_height)

        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        self.widgets = {}

        # サブクラスは self.scrollable_frame にウィジェットを配置する
        self.create_widgets()

        # create_widgets() でウィジェットが生成された後に、マウスホイールイベントをバインドする
        self.bind_mouse_wheel_events()

    def bind_mouse_wheel_events(self):
        """
        マウスホイールイベントをCanvas、scrollable_frame、および
        そのすべての子孫ウィジェットに再帰的にバインドする。
        """
        def _on_mouse_wheel(event):
            # スクロールが必要かどうかを判定
            # scrollable_frame の実際の高さが canvas の表示領域より大きい場合のみ処理する
            frame_height = self.scrollable_frame.winfo_height()
            canvas_height = self.canvas.winfo_height()

            if frame_height <= canvas_height:
                return # スクロール不要なので何もしない

            # Windows/macOSではdelta属性、Linuxではnum属性で判断
            if event.delta:
                # Windowsではevent.deltaが±120の倍数、macOSでは連続的な値
                # 符号を反転させ、スクロール量を調整する
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # Linuxの場合
                if event.num == 4: # 上スクロール
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5: # 下スクロール
                    self.canvas.yview_scroll(1, "units")

        def _bind_recursively(widget):
            widget.bind("<MouseWheel>", _on_mouse_wheel) # Windows, macOS
            widget.bind("<Button-4>", _on_mouse_wheel)   # Linux (scroll up)
            widget.bind("<Button-5>", _on_mouse_wheel)   # Linux (scroll down)
            for child in widget.winfo_children():
                _bind_recursively(child)
        
        # scrollable_frameとそのすべての子ウィジェットにバインド
        _bind_recursively(self.scrollable_frame)

        # Canvas自体にもバインド（フレームがCanvasより小さい場合に備えて）
        self.canvas.bind("<MouseWheel>", _on_mouse_wheel)
        self.canvas.bind("<Button-4>", _on_mouse_wheel)
        self.canvas.bind("<Button-5>", _on_mouse_wheel)

    def create_widgets(self):
        raise NotImplementedError

    def load_data(self):
        raise NotImplementedError

    def collect_data(self):
        raise NotImplementedError
