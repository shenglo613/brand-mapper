import polars as pl
from typing import Dict, Optional
from sqlalchemy import text

from db.dbHelper import DBHelper
from db.models import (
    CarRobinsBrandModel,
    CarRobinsBrandModelMapping,
    CarRobinsSearchResult,
)


class CarDataService:
    def __init__(self, db_helper: DBHelper):
        self.db = db_helper
        self.data_cache = {}

    def get_all_car_data(self) -> Dict[str, pl.DataFrame]:
        try:
            tables = [
                "car_model",
                "car_code",
                "car_license_plate_info",
                "car_brand",
                "car_type",
                "car_robins_search_result",
                "car_robins_brand_model",
                "car_robins_brand_model_mapping",
                "car_robins_llm_failure",
            ]

            result = {}
            for table in tables:
                query = f"SELECT * FROM {table}"
                result[table] = self.db.execute_select(query, disconnect=False)

            result["car_code_with_brand"] = result["car_brand"].join(
                result["car_code"], on="code1"
            )

            return result
        except Exception as e:
            raise ValueError(f"Failed to get car data: {str(e)}")

    def get_target_brand_type_by_plate(
        self, data: Dict[str, pl.DataFrame], plate: str, mapping_df: pl.DataFrame
    ) -> Dict:
        if not plate or not isinstance(plate, str):
            return {}

        try:
            df_plate = data["car_license_plate_info"].filter(
                pl.col("car_number") == plate
            )

            if df_plate.is_empty():
                return {}

            row_data = df_plate.to_dicts()[0]
            brand = row_data.get("brand", "")
            car_type = row_data.get("type", "")

            licensing_date = row_data.get("licensing_date", "")
            next_inspection_date = row_data.get("next_inspection_date", "")

            licensing_year = None
            next_inspection_year = None

            try:
                if licensing_date and len(licensing_date) >= 3:
                    licensing_year = int(licensing_date[:3]) + 1911
                if next_inspection_date and len(next_inspection_date) >= 3:
                    next_inspection_year = int(next_inspection_date[:3]) + 1911
            except ValueError:
                pass

            target_row = mapping_df.filter(
                (pl.col("source") == "car_license_plate_info")
                & (pl.col("source_brand") == brand)
                & (pl.col("source_type") == car_type)
            )

            if target_row.shape[0] > 1:
                raise ValueError(
                    f"Found multiple brand mappings: {target_row.to_dicts()}"
                )
            elif target_row.shape[0] == 1:
                target_data = target_row.to_dicts()[0]

                if licensing_year:
                    target_data["licensing_year"] = licensing_year
                if next_inspection_year:
                    target_data["next_inspection_year"] = next_inspection_year

                return target_data
            else:
                return {}
        except Exception as e:
            print(f"Error in get_target_brand_type_by_plate: {str(e)}")
            return {}

    def find_car_models_in_year_range(
        self,
        data: Dict[str, pl.DataFrame],
        target_brand_type: Dict,
        mapping_df: pl.DataFrame,
    ) -> pl.DataFrame:
        brand = target_brand_type.get("target_brand")
        car_type = target_brand_type.get("target_type")
        licensing_year = target_brand_type.get("licensing_year")
        next_inspection_year = target_brand_type.get("next_inspection_year")

        if not all([brand, car_type, licensing_year, next_inspection_year]):
            return pl.DataFrame()

        mapping_rows = mapping_df.filter(
            (pl.col("target_brand") == brand)
            & (pl.col("target_type") == car_type)
            & (pl.col("source") == "car_model")
        )

        if mapping_rows.is_empty():
            return pl.DataFrame()

        mapping_dict = mapping_rows.to_dicts()[0]
        source_brand = mapping_dict.get("source_brand")
        source_type = mapping_dict.get("source_type")

        if not source_brand or not source_type:
            return pl.DataFrame()

        df_models = data["car_model"].filter(
            (pl.col("brand") == source_brand)
            & (pl.col("type") == source_type)
            & (pl.col("year") >= licensing_year)
            & (pl.col("year") <= next_inspection_year)
        )

        return df_models

    @staticmethod
    def first_nonnull_price(row: Dict) -> Optional[float]:
        for col_name in [
            "reset_price",
            "reset_price2",
            "reset_price3",
            "reset_price4",
            "reset_price5",
        ]:
            val = row.get(col_name)
            if val is not None:
                return val
        return None

    def match_models_to_closest_car_code(
        self,
        df_models: pl.DataFrame,
        data: Dict[str, pl.DataFrame],
        target_brand_type: Dict,
        mapping_df: pl.DataFrame,
    ) -> pl.DataFrame:
        results = []

        for row in df_models.to_dicts():
            brand = target_brand_type.get("target_brand")
            car_type = target_brand_type.get("target_type")
            list_price = row.get("list_price")

            if list_price is None:
                continue

            mapping_df_filtered = mapping_df.filter(
                (pl.col("target_brand") == brand)
                & (pl.col("target_type") == car_type)
                & (pl.col("source") == "car_code")
            )

            if mapping_df_filtered.is_empty():
                continue

            best_diff = float("inf")
            best_car_code_row = None

            for mapping_row in mapping_df_filtered.to_dicts():
                source_brand = mapping_row["source_brand"]
                source_type = mapping_row["source_type"]

                matching_code_df = data["car_code"].filter(
                    (pl.col("brand") == source_brand) & (pl.col("type") == source_type)
                )

                if matching_code_df.is_empty():
                    continue

                for code_row in matching_code_df.to_dicts():
                    reset_val = self.first_nonnull_price(code_row)
                    if reset_val is None:
                        continue

                    diff = abs(reset_val - list_price)
                    if diff < best_diff:
                        best_diff = diff
                        best_car_code_row = code_row

            if best_car_code_row:
                results.append(best_car_code_row)

        return pl.DataFrame(results) if results else pl.DataFrame()

    def find_car_code_from_target_brand_type(
        self,
        data: Dict[str, pl.DataFrame],
        target_brand_type: Dict,
        mapping_df: pl.DataFrame,
    ) -> pl.DataFrame:
        target_brand = target_brand_type.get("target_brand")
        target_type = target_brand_type.get("target_type")

        if not target_brand or not target_type:
            return pl.DataFrame()

        mapping_matches = mapping_df.filter(
            (pl.col("target_brand") == target_brand)
            & (pl.col("target_type") == target_type)
            & (pl.col("source") == "car_code")
        )

        if mapping_matches.is_empty():
            return pl.DataFrame()

        df_car_code = data["car_code"]
        dfs_to_concat = []

        for row in mapping_matches.to_dicts():
            source_brand = row["source_brand"]
            source_type = row["source_type"]

            matched_car_codes = df_car_code.filter(
                (pl.col("brand") == source_brand) & (pl.col("type") == source_type)
            )

            if not matched_car_codes.is_empty():
                dfs_to_concat.append(matched_car_codes)

        return (
            pl.concat(dfs_to_concat, how="vertical")
            if dfs_to_concat
            else pl.DataFrame()
        )

    def save_car_robins_brand_model(self, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0

        insert_sql = self.db.generate_insert_conflict_query(
            df=df,
            table_name="car_robins_brand_model",
            unique_key=["brand", "model"],
            update_cols=[],
        )

        if not insert_sql:
            return 0

        return self.db.execute_update(insert_sql, {}, disconnect=False)

    def save_car_robins_search_result(
        self, data: list[CarRobinsSearchResult] | CarRobinsSearchResult
    ) -> int:
        """
        儲存車輛搜尋結果，並處理資料驗證、欄位處理、以及資料庫插入的邏輯。
        1. 使用 Pydantic 驗證資料。
        2. 移除 id 欄位以便資料庫自動建立 ID。
        3. 若 unique key 重複，將更新 result 和 create_ts 欄位。

        參數:
            data: 單一或多筆 `CarRobinsSearchResult` 物件，需進行儲存。

        回傳:
            儲存結果的影響筆數，若無 SQL 生成則回傳 0。
        """
        # 檢查輸入資料型別，如果是 list 則遍歷並進行 Pydantic 驗證
        if isinstance(data, list):
            data = [CarRobinsSearchResult.model_validate(item) for item in data]
        # 如果是單一物件則直接進行 Pydantic 驗證並轉換成 list
        elif isinstance(data, CarRobinsSearchResult):
            data = [CarRobinsSearchResult.model_validate(data)]
        else:
            # 若資料型別無效則拋出錯誤
            raise ValueError("Invalid data type")

        # 使用 Polars 轉換資料為 DataFrame 並移除 'id' 欄位，讓資料庫自動生成 id
        df = pl.DataFrame(data).drop("id")

        # 生成 SQL 插入語句，處理 unique key 重複的情況
        insert_sql = self.db.generate_insert_conflict_query(
            df=df,
            table_name="car_robins_search_result",
            unique_key=[
                "source",
                "source_brand",
                "source_type",
            ],  # 定義 unique key，若重複則更新
            update_cols=["result", "create_ts"],  # 指定更新欄位，若為空則不更新其他欄位
        )

        if not insert_sql:
            return 0

        self.db.execute_raw_sql(text(insert_sql), df.to_dicts())
        self.db.session.commit()
        return 1
