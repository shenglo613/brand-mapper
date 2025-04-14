import polars as pl
from typing import List, Dict, Tuple
from llm.client import LLMClient


class NormalizationService:

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self._initialize_templates()
        self.llm_client.model_manager.set_current_model("deepseek-chat")
        self.normalization_cache = {}

    def _initialize_templates(self):
        car_code_analyst_template = {
            "messages": [
                {
                    "role": "system",
                    "content": """
                        使用者會給你資料如 ('裕隆(國產)', 'KICKS 旗艦版 P15FVA B1-C 1598c.c. 5D 5人座')
                        第一個通常是生產廠商, 第二個是車型名稱
                        你分析後以下方格式回答
                        生產廠商(Brand) 以全世界最通用的英文名稱回答 命名為 brand
                        車型名稱(ModelName) 以全世界最通用的英文名稱回答 命名為 model
                        不確定的話就空白
                        你只需要回傳 json 不需要其他任何分析
                        [
                            {
                                "brand": "",
                                "model": "",
                            }
                        ]
                    """,
                }
            ]
        }

        search_result_template = {
            "messages": [
                {
                    "role": "system",
                    "content": """
                        你分析使用者給你資料後以下方格式回答
                        廠牌名稱(Brand) 以全世界最通用的英文名稱回答 命名為 brand
                        車型名稱(ModelName) 以全世界最通用的英文名稱回答 命名為 model
                        不確定的話就空白
                        你只需要回傳 json 不需要其他任何分析
                        {
                            "brand": "",
                            "model": "",
                        }
                    """,
                }
            ]
        }

        self.llm_client.template_manager.add_template("car_code_analyst", car_code_analyst_template)
        self.llm_client.template_manager.add_template("search_result_analyst", search_result_template)

    def _parse_llm_response(self, response: Dict) -> List[Dict]:
        try:
            content = response["choices"][0]["message"]["content"]
            from llm.utility import parse_json_input
            return parse_json_input(content)
        except (KeyError, IndexError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def normalize_car_model_to_robins_brand_model(
            self, car_model_data: List[Tuple[str, str, str]]
    ) -> List[Dict[str, str]]:
        cache_key = f"car_model:{str(car_model_data)}"
        if cache_key in self.normalization_cache:
            return self.normalization_cache[cache_key]

        try:
            self.llm_client.model_manager.set_current_model("deepseek-chat")

            response = self.llm_client.chat(
                prompt=str(car_model_data),
                template_name="car_code_analyst",
            )

            results = self._parse_llm_response(response)

            ret = []
            for i, result in enumerate(results):
                if i < len(car_model_data):
                    result["input"] = car_model_data[i]
                    ret.append(result)

            self.normalization_cache[cache_key] = ret
            return ret

        except Exception as e:
            print(f"Error in normalize_car_model_to_robins_brand_model: {e}")
            return []

    def normalize_car_code_to_robins_brand_model(
            self, car_code_data: List[Tuple[str, str]]
    ) -> List[Dict[str, str]]:
        cache_key = f"car_code:{str(car_code_data)}"
        if cache_key in self.normalization_cache:
            return self.normalization_cache[cache_key]

        try:
            self.llm_client.model_manager.set_current_model("deepseek-chat")

            response = self.llm_client.chat(
                prompt=str(car_code_data),
                template_name="car_code_analyst",
            )

            results = self._parse_llm_response(response)

            ret = []
            for i, result in enumerate(results):
                if i < len(car_code_data):
                    result["input"] = car_code_data[i]
                    ret.append(result)

            self.normalization_cache[cache_key] = ret
            return ret

        except Exception as e:
            print(f"Error in normalize_car_code_to_robins_brand_model: {e}")
            return []

    def normalize_car_robins_search_result_to_robins_brand_model(
            self, search_results: List[str]
    ) -> Dict[str, str]:
        cache_key = f"search_result:{str(search_results)}"
        if cache_key in self.normalization_cache:
            return self.normalization_cache[cache_key]

        try:
            self.llm_client.model_manager.set_current_model("deepseek-chat")

            response = self.llm_client.chat(
                prompt=str(search_results),
                template_name="search_result_analyst",
            )

            result = self._parse_llm_response(response)

            if isinstance(result, list) and result:
                result = result[0]
            elif not isinstance(result, dict):
                result = {"brand": "", "model": ""}

            self.normalization_cache[cache_key] = result
            return result

        except Exception as e:
            print(f"Error in normalize_car_robins_search_result_to_robins_brand_model: {e}")
            return {"brand": "", "model": ""}

    def extract_brands_and_models_with_source_info(self, data: Dict[str, pl.DataFrame]) -> Tuple[pl.DataFrame, List[Dict]]:
        try:
            df_car_brand = data["car_brand"].rename({"name": "brand"})
            df_car_type = data["car_type"].rename({"kind": "model"})
            df_car_search_result = data["car_robins_search_result"].rename({"source_brand": "brand", "source_type": "model"})

            df_car_code_merged = (
                data["car_code"]
                .join(df_car_brand, on="code1", how="left")
                .join(df_car_type, on=["code1", "code2"], how="left")
            )

            df_car_code = df_car_code_merged.select(["brand", "model"]).unique()
            df_car_model = data["car_model"].select(["brand", "model"]).unique()
            df_car_search_result = df_car_search_result.select(["brand", "model"]).unique()

            car_code_pairs = [(row["brand"], row["model"]) for row in df_car_code.to_dicts()]
            car_model_pairs = [(row["brand"], row["model"], "") for row in df_car_model.to_dicts()]
            car_license_pairs = [(row["brand"], row["model"], row["result"]) for row in df_car_search_result.to_dicts()]

            mappings = []
            normalized_code_results = []
            if car_code_pairs:
                for i in range(0, len(car_code_pairs), 20):
                    batch = car_code_pairs[i:min(i + 20, len(car_code_pairs))]
                    if not batch:
                        continue
                    batch_results = self.normalize_car_code_to_robins_brand_model(batch)
                    normalized_code_results.extend(batch_results)

                    for result in batch_results:
                        if not result.get("brand") or not result.get("model") or "input" not in result:
                            continue
                        mappings.append({
                            "source": "car_code",
                            "source_brand": result["input"][0],
                            "source_model": result["input"][1],
                            "target_brand": result["brand"].upper(),
                            "target_model": result["model"].upper()
                        })

            normalized_model_results = []
            if car_model_pairs:
                for i in range(0, len(car_model_pairs), 20):
                    batch = car_model_pairs[i:min(i + 20, len(car_model_pairs))]
                    if not batch:
                        continue
                    batch_results = self.normalize_car_model_to_robins_brand_model(batch)
                    normalized_model_results.extend(batch_results)

                    for result in batch_results:
                        if not result.get("brand") or not result.get("model") or "input" not in result:
                            continue
                        mappings.append({
                            "source": "car_model",
                            "source_brand": result["input"][0],
                            "source_model": result["input"][1],
                            "target_brand": result["brand"].upper(),
                            "target_model": result["model"].upper()
                        })

            if car_license_pairs:
                for pair in car_license_pairs:
                    result = self.normalize_car_robins_search_result_to_robins_brand_model([pair[2]])
                    brand = result.get("brand", "")
                    model = result.get("model", "")
                    if brand and model:
                        mappings.append({
                            "source": "car_license_plate_info",
                            "source_brand": pair[0],
                            "source_model": pair[1],
                            "target_brand": brand.upper(),
                            "target_model": model.upper()
                        })

            unique_pairs = set()
            for mapping in mappings:
                unique_pairs.add((mapping["target_brand"], mapping["target_model"]))

            df = pl.DataFrame(
                [{"brand": brand, "model": model} for brand, model in unique_pairs],
                schema=["brand", "model"]
            )

            return df, mappings
        except Exception as e:
            print(f"Error in extract_brands_and_models_with_source_info: {e}")
            return pl.DataFrame(schema=["brand", "model"]), []