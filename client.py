"""
LLM 客戶端

此模組提供與 LLM API 互動的主要功能。
"""

import json
import time
from typing import Dict, List, Optional, Union, Any
import requests
from requests.exceptions import RequestException
from .model_manager import ModelManager, ModelConfig
from .template_manager import TemplateManager
from core.logger import get_logger

# 使用共用的 logger
logger = get_logger()


class RequestHandler:
    """
    處理HTTP請求的工具類，負責發送請求並實現重試邏輯。
    """

    def __init__(
        self, max_retries: int = 3, retry_delay: float = 1.0, timeout: float = 15.0
    ):
        """
        初始化請求處理器

        參數：
            max_retries (int): 最大重試次數
            retry_delay (float): 重試間隔（秒）
            timeout (float): 請求超時時間（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    def send_request(
        self, url: str, headers: Dict[str, str], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        發送HTTP請求並處理重試邏輯

        參數：
            url (str): API端點URL
            headers (Dict[str, str]): 請求標頭
            data (Dict[str, Any]): 請求資料

        返回：
            Dict[str, Any]: API回應

        異常：
            TimeoutError: 當請求超時且重試次數用盡時
            RequestException: 當請求失敗且重試次數用盡時
        """
        for retry_count in range(self.max_retries + 1):
            try:
                logger.info(f"發送請求到 {url}, data: {data}")
                # 改用獨立requests調用而非session
                response = requests.post(
                    url, headers=headers, json=data, timeout=self.timeout
                )
                logger.info("收到回應")
                response.raise_for_status()
                logger.info("回應已處理")
                return response.json()

            except requests.Timeout as e:
                logger.warning(f"請求超時: {e}")
                if retry_count >= self.max_retries:
                    logger.error(f"請求超時且重試次數已用盡: {e}")
                    raise TimeoutError(f"請求超時且重試次數已用盡: {e}")

            except RequestException as e:
                logger.warning(f"請求失敗: {e}")
                if retry_count >= self.max_retries:
                    logger.error(f"請求失敗，已達到最大重試次數: {e}")
                    raise

            # 在重試之前等待
            logger.warning(f"正在重試 ({retry_count + 1}/{self.max_retries})")
            time.sleep(self.retry_delay)


class LLMClient:
    """
    LLM API 客戶端類別

    屬性：
        model_manager (ModelManager): 模型管理器
        template_manager (TemplateManager): 範本管理器
        request_handler (RequestHandler): 請求處理器
    """

    def __init__(
        self,
        api_keys_file: str = "api_keys.json",
        template_file: str = "templates.json",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 15.0,
    ):
        """
        初始化 LLM 客戶端

        參數：
            api_keys_file (str): API 金鑰檔案的路徑
            template_file (str): 範本檔案的路徑
            max_retries (int): 最大重試次數
            retry_delay (float): 重試間隔（秒）
            timeout (float): 請求超時時間（秒）
        """
        self.model_manager = ModelManager(api_keys_file)
        self.template_manager = TemplateManager(template_file)
        self.request_handler = RequestHandler(
            max_retries=max_retries, retry_delay=retry_delay, timeout=timeout
        )

        # 保留這些屬性以維持兼容性
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    def _prepare_request_data(
        self,
        prompt: str,
        model_config: ModelConfig,
        template_name: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        準備API請求數據

        參數：
            prompt (str): 用戶輸入的提示
            model_config (ModelConfig): 模型配置
            template_name (Optional[str]): 要使用的範本名稱
            response_format (Optional[Dict[str, Any]]): 回應格式設定
            **kwargs: 其他參數

        返回：
            Dict[str, Any]: 請求數據
        """
        # 準備消息
        messages = []

        # 如果有使用範本，加入範本內容
        if template_name:
            template = self.template_manager.get_template(template_name)
            if template:
                messages.extend(template.get("messages", []))

        # 加入用戶輸入
        messages.append({"role": "user", "content": prompt})

        # 準備請求參數
        request_data = {
            "model": model_config.url,
            "messages": messages,
            "max_tokens": model_config.max_tokens,
            "temperature": model_config.temperature,
            **kwargs,
        }

        # 如果有設定回應格式，加入請求參數
        if response_format:
            request_data["response_format"] = response_format

        return request_data

    def _make_request(
        self, url: str, headers: Dict[str, str], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用請求處理器發送API請求

        參數：
            url (str): API端點URL
            headers (Dict[str, str]): 請求標頭
            data (Dict[str, Any]): 請求資料

        返回：
            Dict[str, Any]: API回應
        """
        return self.request_handler.send_request(url, headers, data)

    def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        template_name: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        發送聊天請求

        參數：
            prompt (str): 用戶輸入的提示
            model (Optional[str]): 要使用的模型名稱
            template_name (Optional[str]): 要使用的範本名稱
            response_format (Optional[Dict[str, Any]]): 回應格式設定
            **kwargs: 其他參數

        返回：
            Dict[str, Any]: API 回應

        異常：
            ValueError: 當模型未設定或 API 金鑰不存在時
            RequestException: 當 API 請求失敗時
            TimeoutError: 當請求超時時
        """
        # 設定或獲取當前模型
        if model:
            if not self.model_manager.set_current_model(model):
                raise ValueError(f"無效的模型名稱: {model}")
        current_model = self.model_manager.get_current_model()

        if not current_model:
            raise ValueError("未設定模型")

        # 獲取模型配置
        model_config = self.model_manager.get_model_config(current_model)
        if not model_config:
            raise ValueError(f"找不到模型配置: {current_model}")

        # 準備請求數據
        request_data = self._prepare_request_data(
            prompt=prompt,
            model_config=model_config,
            template_name=template_name,
            response_format=response_format,
            **kwargs,
        )

        # 獲取API金鑰
        api_key = self.model_manager.get_api_key(current_model)
        if not api_key:
            raise ValueError(f"未設定 {current_model} 的 API 金鑰")

        # 設置請求標頭
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Car Analysis App",
        }

        try:
            # 發送請求
            response = self._make_request(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=request_data,
            )

            logger.info(response)  # FIXME debug 用 可以移除

            return response
        except Exception as e:
            logger.error(f"請求失敗: {e}")
            raise
