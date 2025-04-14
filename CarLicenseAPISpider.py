"""
搜尋 API 服務，支援多種搜尋引擎如 Brave、Google、Bing 等。
提供統一接口進行網頁搜尋，並可根據配置靈活切換不同的搜尋引擎。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union
import os
import json
import requests
import time
from functools import wraps
from pydantic import BaseModel, Field

# 速率限制配置
RATE_LIMITS = {
    "brave": {
        "calls_per_second": 1,  # Brave API 限制每秒 1 次請求
        "calls_per_minute": 60,
        "calls_per_day": 1000,
    },
    "google": {
        "calls_per_second": 1,  # Google API 限制每秒 1 次請求
        "calls_per_minute": 60,
        "calls_per_day": 100,
    },
    "bing": {
        "calls_per_second": 1,  # Bing API 限制每秒 1 次請求
        "calls_per_minute": 60,
        "calls_per_day": 1000,
    },
}


class RateLimitError(Exception):
    """速率限制錯誤"""

    pass


def rate_limit(provider: str):
    """
    速率限制裝飾器

    參數:
        provider: 搜尋提供商名稱
    """

    def decorator(func):
        last_call_time = 0
        call_count = 0
        last_reset_time = time.time()

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_call_time, call_count, last_reset_time

            current_time = time.time()
            limits = RATE_LIMITS.get(provider, {})

            # 檢查每秒限制
            if current_time - last_call_time < 1 / limits.get("calls_per_second", 1):
                time.sleep(
                    1 / limits.get("calls_per_second", 1)
                    - (current_time - last_call_time)
                )

            # 檢查每分鐘限制
            if current_time - last_reset_time >= 60:
                call_count = 0
                last_reset_time = current_time
            elif call_count >= limits.get("calls_per_minute", 60):
                time.sleep(60 - (current_time - last_reset_time))
                call_count = 0
                last_reset_time = time.time()

            # 更新計數器和時間
            last_call_time = time.time()
            call_count += 1

            return func(*args, **kwargs)

        return wrapper

    return decorator


class SearchResultItem(BaseModel):
    """搜尋結果項目模型"""

    url: str = Field(..., description="搜尋結果的網址")
    title: str = Field(..., description="搜尋結果的標題")
    snippet: str = Field(..., description="搜尋結果的摘要片段")
    published_date: Optional[datetime] = Field(None, description="內容發布日期（如有）")
    source: Optional[str] = Field(None, description="來源網站名稱（如有）")
    image_url: Optional[str] = Field(None, description="相關圖片網址（如有）")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="其他詳細資訊")


class SearchResults(BaseModel):
    """搜尋結果集合模型"""

    items: List[SearchResultItem] = Field(
        default_factory=list, description="搜尋結果列表"
    )
    total_results: Optional[int] = Field(None, description="搜尋結果總數（如有）")
    search_time: Optional[float] = Field(None, description="搜尋所花費的時間（秒）")
    next_page_token: Optional[str] = Field(None, description="下一頁的標記（如有）")
    provider: str = Field(..., description="使用的搜尋提供商")


class SearchTimeRange(Enum):
    """搜尋時間範圍選項"""

    ANY = auto()  # 任何時間
    PAST_DAY = auto()  # 過去一天
    PAST_WEEK = auto()  # 過去一週
    PAST_MONTH = auto()  # 過去一個月
    PAST_YEAR = auto()  # 過去一年
    CUSTOM = auto()  # 自定義時間範圍


class SearchRegion(Enum):
    """搜尋地區選項"""

    GLOBAL = auto()  # 全球
    TAIWAN = auto()  # 台灣
    CHINA = auto()  # 中國
    HONG_KONG = auto()  # 香港
    USA = auto()  # 美國
    JAPAN = auto()  # 日本
    CUSTOM = auto()  # 自定義地區


class SearchLanguage(Enum):
    """搜尋語言選項"""

    ANY = auto()  # 任何語言
    CHINESE = auto()  # 中文
    ENGLISH = auto()  # 英文
    JAPANESE = auto()  # 日文
    CUSTOM = auto()  # 自定義語言


class SearchParams(BaseModel):
    """搜尋參數配置"""

    query: str = Field(..., description="搜尋關鍵字")
    results_per_page: int = Field(10, description="每頁結果數")
    page: int = Field(1, description="頁碼")
    time_range: SearchTimeRange = Field(SearchTimeRange.ANY, description="搜尋時間範圍")
    custom_start_date: Optional[datetime] = Field(None, description="自定義開始日期")
    custom_end_date: Optional[datetime] = Field(None, description="自定義結束日期")
    region: SearchRegion = Field(SearchRegion.GLOBAL, description="搜尋地區")
    custom_region: Optional[str] = Field(None, description="自定義地區代碼")
    language: SearchLanguage = Field(SearchLanguage.ANY, description="搜尋語言")
    custom_language: Optional[str] = Field(None, description="自定義語言代碼")
    safe_search: bool = Field(True, description="安全搜尋過濾")
    additional_params: Dict[str, Any] = Field(
        default_factory=dict, description="額外的搜尋參數"
    )


class APIKeyManager:
    """API 金鑰管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化 API 金鑰管理器

        參數:
            config_file: API 金鑰配置文件路徑，若為 None 則使用環境變數
        """
        self.config_file = config_file or os.environ.get(
            "API_KEYS_CONFIG", "api_keys.json"
        )
        self.api_keys = {}
        self.load_keys()

    def load_keys(self) -> None:
        """從配置文件載入 API 金鑰"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.api_keys = json.load(f)
            else:
                # 嘗試從環境變數載入
                for key in os.environ:
                    if key.startswith("SEARCH_API_"):
                        provider = key.replace("SEARCH_API_", "").lower()
                        self.api_keys[provider] = {
                            "api_key": os.environ[key],
                            "active": True,
                        }
        except Exception as e:
            print(f"載入 API 金鑰時發生錯誤: {e}")
            self.api_keys = {}

    def save_keys(self) -> None:
        """保存 API 金鑰到配置文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.api_keys, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存 API 金鑰時發生錯誤: {e}")

    def get_key(self, provider: str) -> Optional[str]:
        """
        獲取指定提供商的 API 金鑰

        參數:
            provider: 搜尋提供商名稱

        返回:
            API 金鑰，若不存在或未啟用則返回 None
        """
        provider = provider.lower()
        if provider in self.api_keys and self.api_keys[provider].get("active", False):
            return self.api_keys[provider]["api_key"]
        return None

    def add_key(self, provider: str, api_key: str, active: bool = True) -> None:
        """
        添加或更新 API 金鑰

        參數:
            provider: 搜尋提供商名稱
            api_key: API 金鑰
            active: 是否啟用此 API 金鑰
        """
        provider = provider.lower()
        self.api_keys[provider] = {"api_key": api_key, "active": active}
        self.save_keys()

    def remove_key(self, provider: str) -> bool:
        """
        移除 API 金鑰

        參數:
            provider: 搜尋提供商名稱

        返回:
            是否成功移除
        """
        provider = provider.lower()
        if provider in self.api_keys:
            del self.api_keys[provider]
            self.save_keys()
            return True
        return False

    def toggle_key_status(self, provider: str, active: Optional[bool] = None) -> bool:
        """
        切換 API 金鑰啟用狀態

        參數:
            provider: 搜尋提供商名稱
            active: 設置啟用狀態，若為 None 則切換當前狀態

        返回:
            操作後的啟用狀態
        """
        provider = provider.lower()
        if provider in self.api_keys:
            if active is None:
                active = not self.api_keys[provider].get("active", False)
            self.api_keys[provider]["active"] = active
            self.save_keys()
            return active
        return False

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有已配置的搜尋提供商

        返回:
            提供商配置信息字典
        """
        return self.api_keys


class SearchProvider(ABC):
    """搜尋提供商抽象基類"""

    def __init__(self, api_key_manager: APIKeyManager):
        """
        初始化搜尋提供商

        參數:
            api_key_manager: API 金鑰管理器實例
        """
        self.api_key_manager = api_key_manager
        self.last_call_time = 0
        self.call_count = 0
        self.last_reset_time = time.time()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名稱"""
        pass

    @abstractmethod
    @rate_limit("provider_name")
    def search(self, params: SearchParams) -> SearchResults:
        """
        執行搜尋

        參數:
            params: 搜尋參數

        返回:
            搜尋結果
        """
        pass

    def get_api_key(self) -> Optional[str]:
        """獲取此提供商的 API 金鑰"""
        return self.api_key_manager.get_key(self.provider_name)


class BraveSearchProvider(SearchProvider):
    """Brave 搜尋引擎提供商"""

    @property
    def provider_name(self) -> str:
        return "brave"

    def search(self, params: SearchParams) -> SearchResults:
        """
        使用 Brave 搜尋引擎執行搜尋

        參數:
            params: 搜尋參數

        返回:
            搜尋結果
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError(f"未設置或未啟用 {self.provider_name} API 金鑰")

        # Brave Search API 端點
        url = "https://api.search.brave.com/res/v1/web/search"

        # 檢查頁碼限制 - Brave API 通常有最大頁數限制
        # 預設設置一個較大但合理的值作為安全限制
        max_page = 20
        if params.page > max_page:
            raise ValueError(
                f"Brave 搜尋請求頁碼 {params.page} 超過了安全限制 {max_page}，請使用小於此值的頁碼"
            )

        # 計算 offset 參數
        offset = (params.page - 1) * params.results_per_page
        max_offset = 1000  # 預設設置一個較大但合理的值作為安全限制
        if offset > max_offset:
            raise ValueError(
                f"Brave 搜尋 offset 參數 {offset} 超過了安全限制 {max_offset}"
            )

        # 準備請求參數
        request_params = {
            "q": params.query,
            "count": params.results_per_page,
            "offset": offset,
            # 按需映射其他參數
            "search_lang": self._map_language(params.language, params.custom_language),
            "country": self._map_region(params.region, params.custom_region),
            "safe_search": "strict" if params.safe_search else "off",
        }

        # 添加時間範圍過濾
        if params.time_range != SearchTimeRange.ANY:
            request_params["freshness"] = self._map_time_range(params.time_range)
        elif params.custom_start_date and params.custom_end_date:
            # Brave Search API 可能不直接支持自定義日期範圍
            # 這裡只是示例，實際使用時需查閱 API 文檔
            pass

        # 添加其他自定義參數
        for key, value in params.additional_params.items():
            request_params[key] = value

        # 發送請求
        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
        try:
            start_time = datetime.now()
            response = requests.get(url, params=request_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            search_time = (datetime.now() - start_time).total_seconds()

            # 解析結果
            results = SearchResults(
                items=[],
                total_results=data.get("totalResults"),
                search_time=search_time,
                provider=self.provider_name,
            )

            # 處理搜尋結果
            for item in data.get("results", []):
                result_item = SearchResultItem(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    extra_data={
                        "brave_page_rank": item.get("pageRank"),
                        "brave_page_age": item.get("age"),
                    },
                )

                # 添加其他可用信息（如有）
                if "publishedDate" in item:
                    result_item.published_date = datetime.fromisoformat(
                        item["publishedDate"]
                    )
                if "source" in item:
                    result_item.source = item["source"]

                results.items.append(result_item)

            return results

        except requests.RequestException as e:
            # 處理網絡請求錯誤
            status_code = e.response.status_code if hasattr(e, "response") else None
            error_msg = f"Brave 搜尋時發生錯誤"

            if status_code:
                error_msg += f": HTTP {status_code}"
                if status_code == 400:
                    error_msg += " - 請求參數無效，請檢查搜尋關鍵字和頁碼設置"
                elif status_code == 401:
                    error_msg += " - API 金鑰驗證失敗，請檢查金鑰是否正確"
                elif status_code == 429:
                    error_msg += " - 已超出 API 呼叫限制，請稍後再試"

            # 嘗試從響應中獲取更多錯誤詳情
            if hasattr(e, "response") and hasattr(e.response, "text"):
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, dict) and "errors" in error_data:
                        error_msg += f"\n詳細錯誤: {error_data['errors']}"
                except:
                    error_msg += f"\n原始錯誤: {str(e)}"
            else:
                error_msg += f"\n錯誤詳情: {str(e)}"

            print(error_msg)
            return SearchResults(items=[], provider=self.provider_name, search_time=0)
        except Exception as e:
            # 處理其他錯誤
            print(f"Brave 搜尋時發生未知錯誤: {str(e)}")
            return SearchResults(items=[], provider=self.provider_name, search_time=0)

    def _map_time_range(self, time_range: SearchTimeRange) -> str:
        """映射時間範圍到 Brave API 參數"""
        mapping = {
            SearchTimeRange.PAST_DAY: "pd",
            SearchTimeRange.PAST_WEEK: "pw",
            SearchTimeRange.PAST_MONTH: "pm",
            SearchTimeRange.PAST_YEAR: "py",
        }
        return mapping.get(time_range, "a")  # 'a' for 'any time'

    def _map_region(self, region: SearchRegion, custom_region: Optional[str]) -> str:
        """映射地區到 Brave API 參數"""
        if region == SearchRegion.CUSTOM and custom_region:
            return custom_region

        mapping = {
            SearchRegion.GLOBAL: "all",
            SearchRegion.TAIWAN: "tw",
            SearchRegion.CHINA: "cn",
            SearchRegion.HONG_KONG: "hk",
            SearchRegion.USA: "us",
            SearchRegion.JAPAN: "jp",
        }
        return mapping.get(region, "all")

    def _map_language(
        self, language: SearchLanguage, custom_language: Optional[str]
    ) -> str:
        """映射語言到 Brave API 參數"""
        if language == SearchLanguage.CUSTOM and custom_language:
            return custom_language

        mapping = {
            SearchLanguage.ANY: "all",
            SearchLanguage.CHINESE: "zh",
            SearchLanguage.ENGLISH: "en",
            SearchLanguage.JAPANESE: "ja",
        }
        return mapping.get(language, "all")


class GoogleSearchProvider(SearchProvider):
    """Google 搜尋引擎提供商"""

    @property
    def provider_name(self) -> str:
        return "google"

    def search(self, params: SearchParams) -> SearchResults:
        """
        使用 Google 搜尋引擎執行搜尋

        參數:
            params: 搜尋參數

        返回:
            搜尋結果
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError(f"未設置或未啟用 {self.provider_name} API 金鑰")

        # 獲取 Google CSE ID (自定義搜尋引擎 ID)
        cx = self.api_key_manager.api_keys.get("google", {}).get("cx")
        if not cx:
            raise ValueError("未設置 Google 自定義搜尋引擎 ID (cx)")

        # Google Custom Search API 端點
        url = "https://www.googleapis.com/customsearch/v1"

        # 檢查頁碼限制 - Google API 限制只能獲取前 100 個結果
        # 每頁最多 10 筆，所以最大頁碼是 10
        max_page = 10
        if params.page > max_page:
            raise ValueError(
                f"Google 搜尋 API 限制最大頁碼為 {max_page}，當前請求頁碼: {params.page}"
            )

        # 計算 start 參數值，確保不超過 Google API 的限制 (最大值為 91)
        start = ((params.page - 1) * params.results_per_page) + 1
        max_start = 91  # Google API 允許的最大 start 值 (獲取結果 91-100)
        if start > max_start:
            raise ValueError(
                f"Google 搜尋 API 限制 start 參數最大值為 {max_start}，當前計算值: {start}"
            )

        # 準備請求參數
        request_params = {
            "key": api_key,
            "cx": cx,
            "q": params.query,
            "num": min(params.results_per_page, 10),  # Google API 限制每頁最多 10 筆
            "start": start,
            "safe": "active" if params.safe_search else "off",
            "hl": self._map_language(params.language, params.custom_language),
            "gl": self._map_region(params.region, params.custom_region),
        }

        # 添加時間範圍過濾
        if params.time_range != SearchTimeRange.ANY:
            request_params["dateRestrict"] = self._map_time_range(params.time_range)

        # 添加其他自定義參數
        for key, value in params.additional_params.items():
            request_params[key] = value

        # 發送請求
        try:
            start_time = datetime.now()
            response = requests.get(url, params=request_params)
            response.raise_for_status()
            data = response.json()
            search_time = (datetime.now() - start_time).total_seconds()

            # 解析結果
            results = SearchResults(
                items=[],
                total_results=int(
                    data.get("searchInformation", {}).get("totalResults", 0)
                ),
                search_time=search_time,
                provider=self.provider_name,
            )

            # 處理搜尋結果
            for item in data.get("items", []):
                result_item = SearchResultItem(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    extra_data={},
                )

                # 添加圖片 URL（如有）
                if "pagemap" in item and "cse_image" in item["pagemap"]:
                    result_item.image_url = item["pagemap"]["cse_image"][0].get("src")

                # 添加來源和其他可能的信息
                if "displayLink" in item:
                    result_item.source = item["displayLink"]

                results.items.append(result_item)

            return results

        except requests.RequestException as e:
            # 處理網絡請求錯誤
            status_code = e.response.status_code if hasattr(e, "response") else None
            error_msg = f"Google 搜尋時發生錯誤"

            if status_code:
                error_msg += f": HTTP {status_code}"
                if status_code == 400:
                    error_msg += " - 請求參數無效，請檢查搜尋關鍵字和頁碼設置"
                elif status_code == 401 or status_code == 403:
                    error_msg += " - API 金鑰驗證失敗或無權訪問，請檢查金鑰是否正確"
                elif status_code == 429:
                    error_msg += " - 已超出 API 使用配額或呼叫速率限制，請稍後再試"

            # 嘗試從響應中獲取更多錯誤詳情
            if hasattr(e, "response") and hasattr(e.response, "text"):
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"]
                        if isinstance(error_detail, dict):
                            if "message" in error_detail:
                                error_msg += f"\n詳細錯誤: {error_detail['message']}"
                            if "errors" in error_detail and error_detail["errors"]:
                                for err in error_detail["errors"]:
                                    if "reason" in err:
                                        error_msg += f"\n錯誤原因: {err['reason']}"
                        else:
                            error_msg += f"\n詳細錯誤: {error_detail}"
                except:
                    error_msg += f"\n原始錯誤: {str(e)}"
            else:
                error_msg += f"\n錯誤詳情: {str(e)}"

            print(error_msg)
            return SearchResults(items=[], provider=self.provider_name, search_time=0)
        except Exception as e:
            # 處理其他錯誤
            print(f"Google 搜尋時發生未知錯誤: {str(e)}")
            return SearchResults(items=[], provider=self.provider_name, search_time=0)

    def _map_time_range(self, time_range: SearchTimeRange) -> str:
        """映射時間範圍到 Google API 參數"""
        mapping = {
            SearchTimeRange.PAST_DAY: "d1",
            SearchTimeRange.PAST_WEEK: "w1",
            SearchTimeRange.PAST_MONTH: "m1",
            SearchTimeRange.PAST_YEAR: "y1",
        }
        return mapping.get(time_range, "")

    def _map_region(self, region: SearchRegion, custom_region: Optional[str]) -> str:
        """映射地區到 Google API 參數"""
        if region == SearchRegion.CUSTOM and custom_region:
            return custom_region

        mapping = {
            SearchRegion.TAIWAN: "tw",
            SearchRegion.CHINA: "cn",
            SearchRegion.HONG_KONG: "hk",
            SearchRegion.USA: "us",
            SearchRegion.JAPAN: "jp",
        }
        return mapping.get(region, "")

    def _map_language(
        self, language: SearchLanguage, custom_language: Optional[str]
    ) -> str:
        """映射語言到 Google API 參數"""
        if language == SearchLanguage.CUSTOM and custom_language:
            return custom_language

        mapping = {
            SearchLanguage.CHINESE: "zh-TW",
            SearchLanguage.ENGLISH: "en",
            SearchLanguage.JAPANESE: "ja",
        }
        return mapping.get(language, "")


class BingSearchProvider(SearchProvider):
    """Bing 搜尋引擎提供商"""

    @property
    def provider_name(self) -> str:
        return "bing"

    def search(self, params: SearchParams) -> SearchResults:
        """
        使用 Bing 搜尋引擎執行搜尋

        參數:
            params: 搜尋參數

        返回:
            搜尋結果
        """
        api_key = self.get_api_key()
        if not api_key:
            raise ValueError(f"未設置或未啟用 {self.provider_name} API 金鑰")

        # Bing Search API 端點
        url = "https://api.bing.microsoft.com/v7.0/search"

        # 檢查頁碼限制 - Bing API 有限制
        # 根據 Bing API 文檔，offset 參數最大值為 1000
        max_page = 50  # 假設每頁 20 筆，總共可請求 50 頁
        if params.page > max_page:
            raise ValueError(
                f"Bing 搜尋請求頁碼 {params.page} 超過了安全限制 {max_page}，請使用小於此值的頁碼"
            )

        # 計算 offset 參數
        offset = (params.page - 1) * params.results_per_page
        max_offset = 1000  # Bing API 的 offset 參數最大值
        if offset > max_offset:
            raise ValueError(
                f"Bing 搜尋 offset 參數 {offset} 超過了最大限制 {max_offset}"
            )

        # 準備請求參數
        request_params = {
            "q": params.query,
            "count": params.results_per_page,
            "offset": offset,
            "mkt": self._map_market(
                params.region,
                params.language,
                params.custom_region,
                params.custom_language,
            ),
            "safeSearch": "Strict" if params.safe_search else "Off",
        }

        # 添加時間範圍過濾
        if params.time_range != SearchTimeRange.ANY:
            request_params["freshness"] = self._map_time_range(params.time_range)

        # 添加其他自定義參數
        for key, value in params.additional_params.items():
            request_params[key] = value

        # 發送請求
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        try:
            start_time = datetime.now()
            response = requests.get(url, params=request_params, headers=headers)
            response.raise_for_status()
            data = response.json()
            search_time = (datetime.now() - start_time).total_seconds()

            # 解析結果
            results = SearchResults(
                items=[],
                total_results=data.get("webPages", {}).get("totalEstimatedMatches"),
                search_time=search_time,
                provider=self.provider_name,
            )

            # 處理搜尋結果
            for item in data.get("webPages", {}).get("value", []):
                result_item = SearchResultItem(
                    url=item.get("url", ""),
                    title=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    extra_data={},
                )

                # 添加其他可能的信息
                if "datePublished" in item:
                    try:
                        result_item.published_date = datetime.fromisoformat(
                            item["datePublished"].replace("Z", "+00:00")
                        )
                    except:
                        pass

                results.items.append(result_item)

            return results

        except requests.RequestException as e:
            # 處理網絡請求錯誤
            status_code = e.response.status_code if hasattr(e, "response") else None
            error_msg = f"Bing 搜尋時發生錯誤"

            if status_code:
                error_msg += f": HTTP {status_code}"
                if status_code == 400:
                    error_msg += " - 請求參數無效，請檢查搜尋關鍵字和頁碼設置"
                elif status_code == 401:
                    error_msg += " - API 金鑰驗證失敗，請檢查金鑰是否正確"
                elif status_code == 403:
                    error_msg += " - 無權訪問此 API 或 API 金鑰無效"
                elif status_code == 429:
                    error_msg += " - 已超出 API 呼叫限制，請稍後再試"

            # 嘗試從響應中獲取更多錯誤詳情
            if hasattr(e, "response") and hasattr(e.response, "text"):
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_msg += f"\n詳細錯誤: {error_data['error']['message'] if 'message' in error_data['error'] else error_data['error']}"
                except:
                    error_msg += f"\n原始錯誤: {str(e)}"
            else:
                error_msg += f"\n錯誤詳情: {str(e)}"

            print(error_msg)
            return SearchResults(items=[], provider=self.provider_name, search_time=0)
        except Exception as e:
            # 處理其他錯誤
            print(f"Bing 搜尋時發生未知錯誤: {str(e)}")
            return SearchResults(items=[], provider=self.provider_name, search_time=0)

    def _map_time_range(self, time_range: SearchTimeRange) -> str:
        """映射時間範圍到 Bing API 參數"""
        mapping = {
            SearchTimeRange.PAST_DAY: "Day",
            SearchTimeRange.PAST_WEEK: "Week",
            SearchTimeRange.PAST_MONTH: "Month",
            SearchTimeRange.PAST_YEAR: "Year",
        }
        return mapping.get(time_range, "")

    def _map_market(
        self,
        region: SearchRegion,
        language: SearchLanguage,
        custom_region: Optional[str],
        custom_language: Optional[str],
    ) -> str:
        """映射市場（地區和語言）到 Bing API 參數"""
        # 對於自定義設置
        if region == SearchRegion.CUSTOM and language == SearchLanguage.CUSTOM:
            if custom_region and custom_language:
                return f"{custom_language}-{custom_region}"

        # 預定義組合
        region_code = ""
        if region == SearchRegion.TAIWAN:
            region_code = "TW"
        elif region == SearchRegion.CHINA:
            region_code = "CN"
        elif region == SearchRegion.HONG_KONG:
            region_code = "HK"
        elif region == SearchRegion.USA:
            region_code = "US"
        elif region == SearchRegion.JAPAN:
            region_code = "JP"

        lang_code = ""
        if language == SearchLanguage.CHINESE:
            lang_code = "zh"
        elif language == SearchLanguage.ENGLISH:
            lang_code = "en"
        elif language == SearchLanguage.JAPANESE:
            lang_code = "ja"

        if region_code and lang_code:
            return f"{lang_code}-{region_code}"

        # 默認返回全球英文
        return "en-US"


class SearchAPI:
    """搜尋 API 統一接口"""

    def __init__(self, api_key_manager: Optional[APIKeyManager] = None):
        """
        初始化搜尋 API

        參數:
            api_key_manager: API 金鑰管理器實例，若為 None 則創建新實例
        """
        self.api_key_manager = api_key_manager or APIKeyManager()
        self.providers = {}

        # 註冊搜尋提供商
        self._register_provider(BraveSearchProvider(self.api_key_manager))
        self._register_provider(GoogleSearchProvider(self.api_key_manager))
        self._register_provider(BingSearchProvider(self.api_key_manager))

    def _register_provider(self, provider: SearchProvider) -> None:
        """註冊搜尋提供商"""
        self.providers[provider.provider_name] = provider

    def search(self, query: str, provider: str = "brave", **kwargs) -> SearchResults:
        """
        執行搜尋

        參數:
            query: 搜尋關鍵字
            provider: 搜尋提供商名稱
            **kwargs: 其他搜尋參數

        返回:
            搜尋結果

        異常:
            ValueError: 當提供商不支援或參數無效時拋出
        """
        provider = provider.lower()
        if provider not in self.providers:
            raise ValueError(f"不支援的搜尋提供商: {provider}")

        try:
            # 構建搜尋參數
            params = SearchParams(query=query, **kwargs)

            # 使用指定提供商執行搜尋
            return self.providers[provider].search(params)
        except ValueError as e:
            # 重新拋出參數相關錯誤，添加更多上下文
            error_msg = str(e)
            if (
                "頁碼" in error_msg
                or "page" in error_msg
                or "offset" in error_msg
                or "start" in error_msg
            ):
                raise ValueError(
                    f"搜尋參數超出限制: {error_msg} 請調整頁碼或每頁結果數"
                ) from e
            elif "API 金鑰" in error_msg:
                raise ValueError(f"API 金鑰錯誤: {error_msg}") from e
            else:
                raise
        except requests.RequestException as e:
            # 網絡請求錯誤處理
            status_code = (
                getattr(e.response, "status_code", None)
                if hasattr(e, "response")
                else None
            )
            error_message = f"{provider.capitalize()} 搜尋時發生網絡錯誤"

            if status_code:
                error_message += f": {status_code}"

                # 對常見的 HTTP 錯誤提供更具體的說明
                if status_code == 400:
                    error_message += (
                        " (Bad Request) - 請求參數可能無效，檢查搜尋關鍵字或頁碼設置"
                    )
                elif status_code == 401:
                    error_message += " (Unauthorized) - API 金鑰無效或已過期"
                elif status_code == 403:
                    error_message += " (Forbidden) - 無權訪問此 API 或已超出使用配額"
                elif status_code == 429:
                    error_message += (
                        " (Too Many Requests) - 已超出 API 呼叫限制，請稍後再試"
                    )
                elif status_code >= 500:
                    error_message += (
                        f" (Server Error) - {provider.capitalize()} 搜尋服務暫時不可用"
                    )

            # 添加詳細錯誤信息
            if hasattr(e, "response") and hasattr(e.response, "text"):
                try:
                    # 嘗試解析 JSON 錯誤響應
                    error_data = e.response.json()
                    if "error" in error_data:
                        if (
                            isinstance(error_data["error"], dict)
                            and "message" in error_data["error"]
                        ):
                            error_message += (
                                f"\n詳細錯誤: {error_data['error']['message']}"
                            )
                        else:
                            error_message += f"\n詳細錯誤: {error_data['error']}"
                except:
                    # 若無法解析為 JSON，則使用原始錯誤文本
                    error_message += f"\n原始錯誤: {e}"

            # 返回空結果並記錄錯誤，而不是拋出異常
            print(error_message)
            return SearchResults(items=[], provider=provider, search_time=0)

    def get_key_manager(self) -> APIKeyManager:
        """獲取 API 金鑰管理器實例"""
        return self.api_key_manager

    def list_providers(self) -> List[str]:
        """
        列出所有已註冊的搜尋提供商

        返回:
            提供商名稱列表
        """
        return list(self.providers.keys())


# 使用示例
if __name__ == "__main__":
    # 創建 API 金鑰管理器（從配置文件或環境變數載入）
    key_manager = APIKeyManager()

    # 添加 API 金鑰（如果需要）
    # key_manager.add_key("brave", "你的Brave_API金鑰")
    # key_manager.add_key("google", "你的Google_API金鑰")
    # key_manager.add_key("bing", "你的Bing_API金鑰")

    # 創建搜尋 API
    search_api = SearchAPI(key_manager)

    # 執行搜尋
    # results = search_api.search(
    #     query="台灣車牌規格",
    #     provider="brave",
    #     results_per_page=5,
    #     time_range=SearchTimeRange.PAST_YEAR,
    #     region=SearchRegion.TAIWAN,
    #     language=SearchLanguage.CHINESE
    # )

    # 輸出搜尋結果
    # print(f"找到大約 {results.total_results} 筆結果 (耗時 {results.search_time:.2f} 秒)")
    # for i, item in enumerate(results.items, 1):
    #     print(f"{i}. {item.title}")
    #     print(f"   URL: {item.url}")
    #     print(f"   摘要: {item.snippet}")
    #     print("")
