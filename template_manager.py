"""
範本管理器

此模組負責管理 LLM 對話的範本。
"""

import json
from typing import Dict, List, Optional
from pathlib import Path
from core.logger import get_logger

# 使用共用的 logger
logger = get_logger()


class TemplateManager:
    """
    管理 LLM 對話範本的類別

    屬性：
        templates (Dict[str, Dict]): 儲存的範本
        template_file (str): 範本檔案的路徑
    """

    def __init__(self, template_file: str = "templates.json"):
        """
        初始化範本管理器

        參數：
            template_file (str): 範本檔案的路徑
        """
        self.template_file = template_file
        self.templates: Dict[str, Dict] = {}
        self.load_templates()

    def load_templates(self) -> None:
        """
        從檔案載入範本
        """
        if Path(self.template_file).exists():
            with open(self.template_file, "r", encoding="utf-8") as f:
                self.templates = json.load(f)

    def save_templates(self) -> None:
        """
        將範本儲存到檔案
        """
        with open(self.template_file, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)

    def add_template(self, name: str, template: Dict) -> None:
        """
        新增範本

        參數：
            name (str): 範本名稱
            template (Dict): 範本內容
        """
        self.templates[name] = template
        self.save_templates()

    def get_template(self, name: str) -> Optional[Dict]:
        """
        獲取範本

        參數：
            name (str): 範本名稱

        返回：
            Optional[Dict]: 範本內容
        """
        return self.templates.get(name)

    def delete_template(self, name: str) -> bool:
        """
        刪除範本

        參數：
            name (str): 範本名稱

        返回：
            bool: 是否成功刪除
        """
        if name in self.templates:
            del self.templates[name]
            self.save_templates()
            return True
        return False

    def list_templates(self) -> List[str]:
        """
        列出所有範本名稱

        返回：
            List[str]: 範本名稱列表
        """
        return list(self.templates.keys())
