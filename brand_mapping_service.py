import polars as pl
from typing import Dict, List
from db.dbHelper import DBHelper


class BrandMappingService:
    def __init__(self, db_helper: DBHelper):
        self.db = db_helper

    def get_brand_model_ids(self) -> Dict[str, int]:
        try:
            query = "SELECT id, brand, model FROM car_robins_brand_model"
            df = self.db.execute_select(query, disconnect=False)

            id_mapping = {}
            for row in df.to_dicts():
                key = f"{row['brand']}|{row['model']}"
                id_mapping[key] = row['id']

            return id_mapping
        except Exception as e:
            print(f"Failed to get brand model IDs: {str(e)}")
            return {}

    def save_brand_model_mappings(self, mappings: List[Dict], brand_model_ids: Dict[str, int]) -> int:
        if not mappings:
            return 0

        rows = []
        for mapping in mappings:
            key = f"{mapping['target_brand']}|{mapping['target_model']}"
            brand_model_id = brand_model_ids.get(key)

            if brand_model_id:
                rows.append({
                    "source": mapping["source"],
                    "source_brand": mapping["source_brand"],
                    "source_type": mapping["source_model"],
                    "brand_model_id": brand_model_id
                })

        if not rows:
            return 0

        df = pl.DataFrame(rows)

        insert_sql = self.db.generate_insert_conflict_query(
            df=df,
            table_name="car_robins_brand_model_mapping",
            unique_key=["source", "source_brand", "source_type"],
            update_cols=["brand_model_id"]
        )

        if not insert_sql:
            return 0

        return self.db.execute_update(insert_sql, {}, disconnect=False)