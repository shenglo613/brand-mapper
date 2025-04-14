"""
模型管理器

此模組負責管理不同的 LLM 模型，包括模型切換和 API 金鑰管理。
"""

import os
import json
from typing import Dict, Optional, Literal
from pathlib import Path
from dataclasses import dataclass
from core.logger import get_logger

# 使用共用的 logger
logger = get_logger()


@dataclass
class ModelConfig:
    """模型配置資料類別"""

    url: str
    is_free: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7


class ModelManager:
    """
    管理 LLM 模型和 API 金鑰的類別

    屬性：
        api_keys (Dict[str, str]): 儲存 API 金鑰的字典
        current_model (str): 當前使用的模型
        available_models (Dict[str, ModelConfig]): 可用的模型列表
    """

    def __init__(self, api_keys_file: str = "api_keys.json"):
        """
        初始化模型管理器

        參數：
            api_keys_file (str): API 金鑰檔案的路徑
        """
        self.api_keys_file = Path(api_keys_file)
        self.api_keys: Dict[str, str] = {}
        self.current_model: Optional[str] = None
        self.available_models: Dict[str, ModelConfig] = {
            "deepseek-chat": ModelConfig(
                url="deepseek/deepseek-chat-v3-0324:free", is_free=True, max_tokens=4096
            ),
            "llama-70b": ModelConfig(
                url="meta-llama/llama-3.1-70b-instruct:free",
                is_free=True,
                max_tokens=4096,
            ),
        }
        self.load_api_keys()

    def load_api_keys(self) -> None:
        """
        從檔案載入 API 金鑰

        異常：
            FileNotFoundError: 當 API 金鑰檔案不存在時
            json.JSONDecodeError: 當 JSON 格式錯誤時
        """
        try:
            if self.api_keys_file.exists():
                with open(self.api_keys_file, "r", encoding="utf-8") as f:
                    self.api_keys = json.load(f)
                logger.info(f"成功載入 API 金鑰檔案: {self.api_keys_file}")
            else:
                logger.warning(f"API 金鑰檔案不存在: {self.api_keys_file}")
        except json.JSONDecodeError as e:
            logger.error(f"API 金鑰檔案格式錯誤: {e}")
            raise
        except Exception as e:
            logger.error(f"載入 API 金鑰時發生錯誤: {e}")
            raise

    def save_api_keys(self) -> None:
        """
        將 API 金鑰儲存到檔案

        異常：
            IOError: 當寫入檔案失敗時
        """
        try:
            with open(self.api_keys_file, "w", encoding="utf-8") as f:
                json.dump(self.api_keys, f, indent=2, ensure_ascii=False)
            logger.info(f"成功儲存 API 金鑰到檔案: {self.api_keys_file}")
        except Exception as e:
            logger.error(f"儲存 API 金鑰時發生錯誤: {e}")
            raise

    def set_api_key(self, model: str, api_key: str) -> None:
        """
        設定特定模型的 API 金鑰

        參數：
            model (str): 模型名稱
            api_key (str): API 金鑰

        異常：
            ValueError: 當模型名稱無效時
        """
        if model not in self.available_models:
            raise ValueError(f"無效的模型名稱: {model}")
        self.api_keys[model] = api_key
        self.save_api_keys()
        logger.info(f"已設定模型 {model} 的 API 金鑰")

    def get_api_key(self, model: str) -> Optional[str]:
        """
        獲取特定模型的 API 金鑰

        參數：
            model (str): 模型名稱

        返回：
            Optional[str]: API 金鑰，如果不存在則返回 None

        異常：
            ValueError: 當模型名稱無效時
        """
        if model not in self.available_models:
            raise ValueError(f"無效的模型名稱: {model}")
        return self.api_keys.get(model)

    def set_current_model(self, model: str) -> bool:
        """
        設定當前使用的模型

        參數：
            model (str): 模型名稱

        返回：
            bool: 是否成功設定
        """
        if model in self.available_models:
            self.current_model = model
            logger.info(f"已切換到模型: {model}")
            return True
        logger.warning(f"嘗試切換到無效的模型: {model}")
        return False

    def get_current_model(self) -> Optional[str]:
        """
        獲取當前使用的模型

        返回：
            Optional[str]: 當前模型名稱
        """
        return self.current_model

    def get_model_config(self, model: str) -> Optional[ModelConfig]:
        """
        獲取模型的配置資訊

        參數：
            model (str): 模型名稱

        返回：
            Optional[ModelConfig]: 模型配置資訊
        """
        return self.available_models.get(model)

    def get_model_url(self, model: str) -> Optional[str]:
        """
        獲取模型的 API URL

        參數：
            model (str): 模型名稱

        返回：
            Optional[str]: 模型 URL
        """
        config = self.get_model_config(model)
        return config.url if config else None
