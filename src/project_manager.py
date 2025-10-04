# src/project_manager.py

import os
import re

class ProjectManager:
    """
    キャラクタープロジェクト（フォルダ）の管理を行うクラス。
    """
    def __init__(self, base_dir: str):
        self.characters_dir = os.path.join(base_dir, "characters")
        os.makedirs(self.characters_dir, exist_ok=True)

    def list_projects(self):
        """既存のキャラクタープロジェクトのリストを返します。"""
        try:
            return sorted([d for d in os.listdir(self.characters_dir) if os.path.isdir(os.path.join(self.characters_dir, d))])
        except FileNotFoundError:
            return []

    def create_new_project(self, project_id: str):
        """
        新しいキャラクタープロジェクト（フォルダ）を作成します。
        
        Args:
            project_id (str): 新しいキャラクターのID。
        
        Raises:
            ValueError: IDが不正または既に使用されている場合。
        """
        # ファイル名として使用できない文字をチェック
        invalid_chars = r'[\\/:*?"<>|]'
        if re.search(invalid_chars, project_id):
            raise ValueError(f"IDにファイル名として使用できない文字が含まれています。\n({invalid_chars})")

        project_path = os.path.join(self.characters_dir, project_id)
        if os.path.exists(project_path):
            raise ValueError(f"ID '{project_id}' は既に使用されています。")

        # キャラクターの基本フォルダ構造を作成
        os.makedirs(project_path)
        os.makedirs(os.path.join(project_path, "default"))
        os.makedirs(os.path.join(project_path, "hearts"))
        os.makedirs(os.path.join(project_path, "stills"))
        
        print(f"プロジェクトフォルダを作成しました: {project_path}")
