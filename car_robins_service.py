"""
汽車品牌映射服務

此模組負責處理汽車品牌和型號的標準化映射。
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger
from sqlmodel import Session, select
import polars as pl

from db.dbHelper import DBHelper
from db.models import (
    CarRobinsSearchResult,
    CarRobinsBrandModel,
    CarRobinsBrandModelMapping,
    CarCode,
    CarModel,
    CarBrand,
)
from llm.client import LLMClient
from llm.inference import (
    normalize_car_robins_search_result_full_text,
    normalize_car_code_to_robins_brand_model,
    normalize_car_model_to_robins_brand_model,
)


class CarRobinsService:
    """
    汽車品牌映射服務類別

    此類別負責處理汽車品牌和型號的標準化映射流程。
    """

    def __init__(self, db: DBHelper, llm_client: LLMClient):
        """
        初始化服務

        參數：
            db (DBHelper): 資料庫助手實例
            llm_client (LLMClient): LLM 客戶端實例
        """
        self.db = db
        self.llm_client = llm_client

    def process_search_results(self, batch_size: int = 50) -> None:
        """
        處理搜尋結果並建立品牌模型映射

        參數：
            batch_size (int): 每批次處理的資料筆數，預設為 50
        """
        with Session(self.db.engine) as session:
            # 1. 查詢未處理的搜尋結果
            statement = select(CarRobinsSearchResult).limit(batch_size)
            results = session.exec(statement).all()

            if not results:
                logger.info("沒有需要處理的搜尋結果")
                return

            # 2. 準備 LLM 分析資料
            prompt_data = [
                {
                    "source_brand": result.source_brand,
                    "source_type": result.source_type,
                    "result": result.result,
                }
                for result in results
            ]

            # 3. 使用 LLM 分析資料
            try:
                normalized_results = normalize_car_robins_search_result_full_text(
                    self.llm_client, prompt_data
                )
            except Exception as e:
                logger.error(f"LLM 分析失敗: {e}")
                return

            # 4. 處理每個標準化結果
            for result, normalized in zip(results, normalized_results):
                try:
                    self._process_single_result(session, result, normalized)
                except Exception as e:
                    logger.error(f"處理單筆結果失敗: {e}")
                    continue

            session.commit()
            logger.info(f"成功處理 {len(results)} 筆搜尋結果")

    def process_car_codes(self, batch_size: int = 50) -> None:
        """
        處理車型代碼並建立品牌模型映射

        參數：
            batch_size (int): 每批次處理的資料筆數，預設為 50
        """
        with Session(self.db.engine) as session:
            # 1. 查詢車型資料
            kw = [
                "國瑞(國產)",
                "Toyota豐田(亞洲)",
                "Toyota豐田(日本)",
                "Toyota豐田(美國)",
                "Toyota豐田(歐洲)",
                #   , "裕隆(國產)", "Nissan日產(英國)"
            ]
            statement = (
                select(CarBrand.name, CarCode.type)
                .join(CarBrand, CarCode.code1 == CarBrand.code1)
                .where(CarBrand.name.in_(kw))  # FIXME
            ).group_by(CarBrand.name, CarCode.type)
            results = session.exec(statement).all()

            if not results:
                logger.info("沒有需要處理的車型代碼")
                return

            # 2. 準備 LLM 分析資料

            # FIXME
            results = [(_name, _type) for _name, _type in results if "Lexus" in _type]

            prompt_data = results

            # 3. 使用 LLM 分析資料
            try:
                normalized_results = normalize_car_code_to_robins_brand_model(
                    self.llm_client, prompt_data
                )

                print("*" * 100, results)
            except Exception as e:
                logger.error(f"LLM 分析失敗: {e}")
                return

            # 4. 處理每個標準化結果
            for result, normalized in zip(results, normalized_results):
                try:
                    self._process_car_code_result(session, result, normalized)
                except Exception as e:
                    logger.error(f"處理單筆車型代碼失敗: {e}")
                    continue

            session.commit()
            logger.info(f"成功處理 {len(results)} 筆車型代碼")

    def process_car_models(self, batch_size: int = 50) -> None:
        """
        處理車型資料並建立品牌模型映射

        參數：
            batch_size (int): 每批次處理的資料筆數，預設為 50
        """
        with Session(self.db.engine) as session:
            # 1. 查詢車型資料
            statement = select(CarModel.brand, CarModel.model)
            results = session.exec(statement).all()

            if not results:
                logger.info("沒有需要處理的車型資料")
                return

            # 2. 準備 LLM 分析資料
            df = pl.DataFrame(results)

            # FIXME
            df = (
                df.group_by(["brand", "model"])
                .len()
                .filter(
                    pl.col("brand").str.contains("Toyota")
                    | pl.col("model").str.contains("Nis")
                )
            )

            prompt_data = [(i["brand"], i["model"]) for i in df.iter_rows(named=True)]

            # 3. 使用 LLM 分析資料
            try:
                normalized_results = normalize_car_model_to_robins_brand_model(
                    self.llm_client, prompt_data
                )
            except Exception as e:
                logger.error(f"LLM 分析失敗: {e}")
                return

            # 4. 處理每個標準化結果
            for data, normalized in zip(prompt_data, normalized_results):
                try:
                    self._process_car_model_result(session, data, normalized)
                except Exception as e:
                    logger.error(f"處理單筆車型資料失敗: {e}")
                    continue

            session.commit()
            logger.info(f"成功處理 {len(results)} 筆車型資料")

    def _process_car_code_result(
        self,
        session: Session,
        result: Tuple[str, str],
        normalized: Dict[str, str],
    ) -> None:
        """
        處理單筆車型代碼結果

        參數：
            session (Session): 資料庫會話
            result (CarCode): 車型代碼結果
            normalized (Dict[str, str]): 標準化後的品牌和型號
        """
        # 檢查品牌和型號是否有效
        if not normalized.get("brand") or not normalized.get("model"):
            logger.warning(f"無效的品牌或型號: {normalized}")
            return

        # 5. 檢查並建立品牌模型記錄
        brand_model = self._get_or_create_brand_model(
            session, normalized["brand"], normalized["model"]
        )

        # 6. 檢查並建立映射記錄
        self._create_mapping_if_not_exists(
            session,
            "car_code",  # 來源標記為 car_code
            result[0],  # 使用 code1 作為來源品牌
            result[1],  # 使用 code2 作為來源型號
            brand_model.id,
        )

    def _process_car_model_result(
        self,
        session: Session,
        data: Tuple[str, str],
        normalized: Dict[str, str],
    ) -> None:
        """
        處理單筆車型資料結果

        參數：
            session (Session): 資料庫會話
            data (Tuple[str, str]): 車型資料結果
            normalized (Dict[str, str]): 標準化後的品牌和型號
        """
        # 檢查品牌和型號是否有效
        if not normalized.get("brand") or not normalized.get("model"):
            logger.warning(f"無效的品牌或型號: {normalized}")
            return

        # 5. 檢查並建立品牌模型記錄
        brand_model = self._get_or_create_brand_model(
            session, normalized["brand"], normalized["model"]
        )

        # 6. 檢查並建立映射記錄
        self._create_mapping_if_not_exists(
            session,
            "car_model",  # 來源標記為 car_model
            data[0],  # 使用原始品牌
            data[1],  # 組合型號和款式
            brand_model.id,
        )

    def _process_single_result(
        self,
        session: Session,
        result: CarRobinsSearchResult,
        normalized: Dict[str, str],
    ) -> None:
        """
        處理單筆搜尋結果

        參數：
            session (Session): 資料庫會話
            result (CarRobinsSearchResult): 搜尋結果
            normalized (Dict[str, str]): 標準化後的品牌和型號
        """
        # 檢查品牌和型號是否有效
        if not normalized.get("brand") or not normalized.get("model"):
            logger.warning(f"無效的品牌或型號: {normalized}")
            return

        # 5. 檢查並建立品牌模型記錄
        brand_model = self._get_or_create_brand_model(
            session, normalized["brand"], normalized["model"]
        )

        # 6. 檢查並建立映射記錄
        self._create_mapping_if_not_exists(
            session,
            result.source,
            result.source_brand,
            result.source_type,
            brand_model.id,
        )

    def _get_or_create_brand_model(
        self, session: Session, brand: str, model: str
    ) -> CarRobinsBrandModel:
        """
        獲取或建立品牌模型記錄

        參數：
            session (Session): 資料庫會話
            brand (str): 品牌名稱
            model (str): 型號名稱

        返回：
            CarRobinsBrandModel: 品牌模型記錄
        """
        # 檢查是否已存在相同的品牌和型號
        statement = select(CarRobinsBrandModel).where(
            CarRobinsBrandModel.brand == brand,
            CarRobinsBrandModel.model == model,
        )
        existing = session.exec(statement).first()

        if existing:
            logger.info(
                f"品牌模型已存在，跳過建立: brand={brand}, model={model}, id={existing.id}"
            )
            return existing

        # 建立新的品牌模型記錄
        new_brand_model = CarRobinsBrandModel(
            brand=brand,
            model=model,
            create_ts=datetime.now(),
        )
        session.add(new_brand_model)
        session.flush()  # 獲取新記錄的 ID
        logger.info(
            f"建立新的品牌模型: brand={brand}, model={model}, id={new_brand_model.id}"
        )
        return new_brand_model

    def _create_mapping_if_not_exists(
        self,
        session: Session,
        source: str,
        source_brand: str,
        source_type: str,
        brand_model_id: int,
    ) -> None:
        """
        建立映射記錄（如果不存在）

        參數：
            session (Session): 資料庫會話
            source (str): 來源
            source_brand (str): 來源品牌
            source_type (str): 來源型號
            brand_model_id (int): 品牌模型 ID
        """
        # 檢查是否已存在相同的映射
        statement = select(CarRobinsBrandModelMapping).where(
            CarRobinsBrandModelMapping.source == source,
            CarRobinsBrandModelMapping.source_brand == source_brand,
            CarRobinsBrandModelMapping.source_type == source_type,
            # CarRobinsBrandModelMapping.brand_model_id == brand_model_id,
        )
        existing = session.exec(statement).first()

        if existing:
            logger.info(
                f"映射記錄已存在，跳過建立: source={source}, "
                f"source_brand={source_brand}, source_type={source_type}, "
                f"brand_model_id={brand_model_id}, id={existing.id}"
            )
            return

        # 建立新的映射記錄
        new_mapping = CarRobinsBrandModelMapping(
            source=source,
            source_brand=source_brand,
            source_type=source_type,
            brand_model_id=brand_model_id,
            create_ts=datetime.now(),
        )
        session.add(new_mapping)
        logger.info(
            f"建立新的映射記錄: source={source}, "
            f"source_brand={source_brand}, source_type={source_type}, "
            f"brand_model_id={brand_model_id}"
        )
