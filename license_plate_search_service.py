from typing import List, Dict, Optional
import polars as pl
from loguru import logger

from db.dbHelper import DBHelper
from db.models import CarRobinsSearchResult
from service.car_data_service import CarDataService
from search.CarLicenseAPISpider import SearchAPI


class LicensePlateSearchService:
    def __init__(self, db_helper: DBHelper, search_api: SearchAPI):
        self.db = db_helper
        self.search_api = search_api

    def get_all_license_plates(self) -> pl.DataFrame:
        try:
            query = "SELECT * FROM car_license_plate_info"
            return self.db.execute_select(query, disconnect=False)
        except Exception as e:
            logger.error(f"獲取車牌資訊失敗: {e}")
            return pl.DataFrame()

    def generate_search_query(brand: str, car_type: str) -> str:
        if brand.upper() in car_type.upper():
            query = f"{car_type}"
        else:
            query = f"{brand} {car_type}"

        return " ".join(query.split())

    def search_license_plate_info(self,
                                  plate_info: Dict,
                                  provider: str = "google") -> Optional[str]:
        plate_number = plate_info.get("car_number", "")
        brand = plate_info.get("brand", "")
        car_type = plate_info.get("type", "")

        if not plate_number:
            logger.warning("車牌號碼為空")
            return None

        query = self.generate_search_query(brand, car_type)

        try:
            results = self.search_api.search(
                query=query,
                provider=provider,
                results_per_page=50,
                page=1,
            )

            if results and results.items:
                combined_result = "\n\n".join([
                    f"標題: {item.title}\n網址: {item.url}\n摘要: {item.snippet}"
                    for item in results.items
                ])
                return combined_result

        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return None

        return None

    def process_license_plates(self, batch_size: int = 10, skip_existing: bool = True) -> int:
        license_plates_df = self.get_all_license_plates()

        if license_plates_df.is_empty():
            logger.warning("無車牌資訊可處理")
            return 0

        existing_records = set()
        if skip_existing:
            try:
                query = "SELECT source, source_brand, source_type FROM car_robins_search_result WHERE source = 'car_license_plate_info'"
                existing_df = self.db.execute_select(query, disconnect=False)

                for row in existing_df.to_dicts():
                    key = (row["source"], row["source_brand"], row["source_type"])
                    existing_records.add(key)

                logger.info(f"已跳過 {len(existing_records)} 條已存在的記錄")
            except Exception as e:
                logger.error(f"獲取已存在記錄失敗: {e}")

        processed_count = 0
        results_to_save = []

        for i, plate_info in enumerate(license_plates_df.to_dicts()):
            plate_number = plate_info.get("car_number", "")
            brand = plate_info.get("brand", "")
            car_type = plate_info.get("type", "")

            if not plate_number or not brand or not car_type:
                continue

            if skip_existing and ("car_license_plate_info", brand, car_type) in existing_records:
                logger.debug(f"跳過已存在的記錄: {plate_number}, {brand}, {car_type}")
                continue

            search_result = self.search_license_plate_info(plate_info)

            if search_result:
                result = CarRobinsSearchResult(
                    source="car_license_plate_info",
                    source_brand=brand,
                    source_type=car_type,
                    result=search_result
                )

                results_to_save.append(result)
                processed_count += 1

                if len(results_to_save) >= batch_size:
                    try:
                        self.save_search_results(results_to_save)
                        logger.info(
                            f"已保存 {len(results_to_save)} 條搜尋結果（總進度: {i + 1}/{license_plates_df.shape[0]}）")
                        results_to_save = []
                    except Exception as e:
                        logger.error(f"保存搜尋結果失敗: {e}")

            if (i + 1) % 10 == 0:
                logger.info(f"已處理 {i + 1}/{license_plates_df.shape[0]} 條車牌記錄")

        if results_to_save:
            try:
                self.save_search_results(results_to_save)
                logger.info(f"已保存剩餘 {len(results_to_save)} 條搜尋結果")
            except Exception as e:
                logger.error(f"保存搜尋結果失敗: {e}")

        return processed_count

    def save_search_results(self, results: List[CarRobinsSearchResult]) -> None:
        car_data_service = CarDataService(self.db)
        car_data_service.save_car_robins_search_result(results)