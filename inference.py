import polars as pl
from loguru import logger

from llm.client import LLMClient
from llm.utility import parse_json_input
from core.logger import get_logger

# 使用共用的 logger
logger = get_logger()


def normalize_car_model_to_robins_brand_model(
    llm_client: LLMClient, car_model_prompt_data: list[tuple[str, str, str]]
) -> list[dict[str, str]]:
    """
    Output:
    [
        {
            "brand": "Mitsubishi",
            "model": "OUTLANDER",
        }
    ]

    Example car_model_prompt_data:
    [
        ('Bentley 賓利', 'Bentley Continental', 'GT'),
        ('Hyundai 現代', 'Hyundai Ioniq 5', 'EV600'),
        ('Kia 起亞', 'Kia Euro Star', '1.1 星動版'),
        ('Ford 福特', 'Ford Kuga', '2.0 TDCi柴油CP360型'),
        ('Ferrari 法拉利', 'Ferrari 458 Spider', 'V8'),
        ('Honda 本田', 'Honda Civic', '1.8 LX'),
        ('M-Benz 賓士', 'M-Benz GLB', '200七人座'),
        ('Lexus 凌志', 'Lexus CT', '200h 豪華版'),
        ('Ford 福特', 'Ford Kuga', 'EcoBoost 250 AWD Vignale(客貨車版)'),
        ('Maserati 瑪莎拉蒂', 'Maserati Grecale', 'GT Launch Edition')
    ]
    """

    llm_client.model_manager.set_current_model("deepseek-chat")

    car_model_analyst_template = {
        "messages": [
            # "role": "system",
            # "content": """
            #     使用者會給你資料如 ('裕隆(國產)', 'KICKS 旗艦版 P15FVA B1-C 1598c.c. 5D 5人座')
            #     第一個通常是生產廠商, 第二個是車型名稱
            #     你分析後以下方格式回答
            #     生產廠商(Brand) 以全世界最通用的英文名稱回答 命名為 brand
            #     車型名稱(ModelName) 以全世界最通用的英文名稱回答 命名為 model
            #     不確定的話就空白
            #     你只需要回傳 json 不需要其他任何分析
            #     [
            #         {
            #             "brand": "",
            #             "model": "",
            #         }
            #     ]
            #     """,
            # {
            #     "role": "system",
            #     "content": """
            #     您是一位專門從事汽車品牌與型號標準化的高級數據分析專家。您的核心任務是根據用戶提供的資訊，精確提取全球標準化的汽車品牌和型號名稱。
            #     ## 核心職責
            #     - 分析用戶提供的汽車資訊
            #     - 標準化品牌名稱為全球通用的英文名稱
            #     - 提取最廣泛認可的簡化型號名稱
            #     - 確保數據一致性和準確性
            #     ## 輸入數據格式
            #     用戶將提供汽車條目列表，每個條目包含:
            #     - source_brand: 原始品牌輸入（可能是當地經銷商或製造商）
            #     - source_type: 原始型號輸入（可能包含額外描述）
            #     - 描述性提示：提供額外背景資訊
            #     ## 輸出標準
            #     1. **品牌標準化**:
            #     - 使用全球最廣泛認可的英文品牌名稱
            #     - 將當地經銷商（如"國瑞"）映射到正確的全球品牌
            #     2. **型號標準化**:
            #     - 使用簡潔、全球通用的英文型號名稱
            #     - 排除配置等級、引擎類型、驅動系統等技術描述符
            #     - 例如：使用"Corolla Cross"而非"Corolla Cross Hybrid"或"Corolla Cross ZVG10L"
            #     - 例如：使用"RAV4"而非"RAV4 Plug-in Hybrid"或"RAV4 LE AWD"
            #     3. **數據一致性**:
            #     - 確保相同型號始終產生相同的標準化輸出
            #     - 無法確定時返回空字符串""
            #     ## 回應格式
            #     僅返回以下格式的JSON陣列:
            #     [
            #         {
            #             "source_brand": "原始品牌輸入",
            #             "source_type": "原始型號輸入",
            #             "brand": "標準化英文品牌名稱",
            #             "model": "簡化的全球認可型號名稱"
            #         },
            #         ...
            #     ]
            #     **重要提示:** 不要提供任何解釋或額外文字，僅返回最終JSON陣列。如無法確定品牌或型號，請返回空字符串。
            #     """
            # }
            {
                "role": "system",
                "content": """
                You are an advanced data specialist focused on standardizing car brands and models. Your core task is to accurately extract globally standardized car brand and model names based on user-provided information.

                ## Core Responsibilities
                - Analyze car information provided by users
                - Standardize brand names to globally recognized English names
                - Extract the most widely recognized simplified model names
                - Ensure data consistency and accuracy

                ## Input Data Format
                Users will provide a list of car entries, each containing:
                - source_brand: Original brand input (may be local distributor or manufacturer)
                - source_type: Original model input (may contain additional descriptions)
                - Descriptive prompt: Providing additional background information

                ## Output Standards
                1. **Brand Standardization**: 
                - Use the most widely recognized global English brand name
                - Map local distributors (e.g., "國瑞") to the correct global brand
                2. **Model Standardization**:
                - Use concise, globally recognized English model names
                - Exclude trim levels, engine types, drivetrain systems, and technical descriptors
                - Example: Use "Corolla Cross" instead of "Corolla Cross Hybrid" or "Corolla Cross ZVG10L"
                - Example: Use "RAV4" instead of "RAV4 Plug-in Hybrid" or "RAV4 LE AWD"
                3. **Data Consistency**:
                - Ensure the same model always produces the same standardized output
                - Return an empty string "" when uncertain

                ## Response Format
                Return only a JSON array in the following format:

                [
                    {
                        "source_brand": "Original brand input",
                        "source_type": "Original model input",
                        "brand": "Standardized English brand name",
                        "model": "Simplified, globally recognized model name"
                    },
                    ...
                ]

                **Important Note:** Do not provide any explanations or additional text. Return only the final JSON array. If you cannot determine a brand or model with confidence, return an empty string.
                """,
            }
        ]
    }
    llm_client.template_manager.add_template(
        "car_model_analyst", car_model_analyst_template
    )

    # 使用範本和 JSON schema 進行車輛分析
    response = llm_client.chat(
        prompt=str(car_model_prompt_data),
        template_name="car_model_analyst",
    )

    ans = response["choices"][0]["message"]["content"]
    ans = parse_json_input(ans)

    ret = []
    for i, j in enumerate(ans):
        j["input"] = car_model_prompt_data[i]
        ret.append(j)

    return ret


def normalize_car_code_to_robins_brand_model(
    llm_client: LLMClient, car_code_prompt_data: list[tuple[str, str]]
) -> list[dict[str, str]]:
    """
    Output:
    [
        {
            "brand": "Mitsubishi",
            "model": "OUTLANDER",
        }
    ]

    Example car_code_prompt_data:
    [
        ('中華(國產)', '新威利:1.1 CM6242W 2人座貨車 木床      *'),
        ('馬自達(國產)', 'E2200 9人座客貨車      註1'),
        ('福特(國產)', 'Ixion MAV 1.8  Gli  5D (A)'),
        ('納智捷(Luxgen)(國產)', 'Luxgen n7 LR 5人粹鍊+版 230hp 5D 5人座'),
        ('Ford(德國)', 'Focus ST 2.0L 1999c.c.六速手排 5人座'),
        ('裕隆(國產)', 'KICKS 旗艦版 P15FVA B1-C 1598c.c. 5D 5人座'),
        ('國瑞(國產)', 'Camry 2.4L EL'),
        ('BMW(德國)', 'i3 REX i01 647c.c. 5D 5人座 (油電車)'),
    ]
    """

    llm_client.model_manager.set_current_model("deepseek-chat")

    car_code_analyst_template = {
        "messages": [
            # {
            #     "role": "system",
            #     "content": """
            #         使用者會給你資料如 ('裕隆(國產)', 'KICKS 旗艦版 P15FVA B1-C 1598c.c. 5D 5人座')
            #         第一個通常是生產廠商, 第二個是車型名稱
            #         你分析後以下方格式回答
            #         生產廠商(Brand) 以全世界最通用的英文名稱回答 命名為 brand
            #         車型名稱(ModelName) 以全世界最通用的英文名稱回答 命名為 model
            #         不確定的話就空白
            #         你只需要回傳 json 不需要其他任何分析
            #         [
            #             {
            #                 "brand": "Mitsubishi",
            #                 "model": "OUTLANDER",
            #             }
            #         ]
            #         """,
            # }
            #########################################################
            # {
            #     "role": "system",
            #     "content": """
            #     你是一個專門從使用者提供的資訊中提取汽車標準化品牌和型號名稱的助手。
            #     使用者會提供一系列汽車項目，每項包含 source_brand（來源品牌）、source_type（來源型號）和描述性提示。
            #     你的任務是根據國際命名慣例提取全球品牌和最廣泛認可的簡化型號名稱（英文）。
            #     僅以以下 JSON 格式數組回應：
            #     [
            #         {
            #             "source_brand": "原始品牌輸入",
            #             "source_type": "原始型號輸入",
            #             "brand": "標準化的英文品牌名稱",
            #             "model": "簡化的全球認可型號名稱"
            #         },
            #         ...
            #     ]
            #     **指南：**
            #     1. 始終返回品牌和型號最廣泛認可的全球英文名稱。
            #     2. 保持 `model` 值簡短清晰。**避免包含裝飾等級、引擎類型、傳動系統、混合動力/電動狀態或技術描述符**。
            #     - 例如：使用 "Corolla Cross" 而非 "Corolla Cross Hybrid" 或 "Corolla Cross ZVG10L"。
            #     - 例如：使用 "RAV4"，而非 "RAV4 Plug-in Hybrid" 或 "RAV4 LE AWD"。
            #     3. 如果 `source_brand` 是當地經銷商（如「國瑞」），則使用提示內容將其映射到正確的全球品牌。
            #     4. 如果無法確定品牌或型號，則返回空字符串 `""`。
            #     5. 確保命名一致性 — 相同型號應始終產生相同的 `model` 輸出。
            #     6. **不要**包含任何解釋或額外文字。僅返回最終 JSON 數組。
            #     """
            # }
            #########################################################
            {
                "role": "system",
                "content": """
                You are an assistant that extracts the standardized brand and model name of cars based on user-provided information.

                The user provides a list of car entries, each including a source_brand, source_type, and a descriptive prompt.

                Your task is to extract the global brand and the most widely recognized, simplified model name (in English) based on international naming conventions.

                Respond only with a JSON array in the following format:

                [
                    {
                        "source_brand": "Original brand input",
                        "source_type": "Original model input",
                        "brand": "Standardized brand name in English",
                        "model": "Simplified, globally recognized model name"
                    },
                    ...
                ]

                **Guidelines:**
                1. Always return the most widely recognized global English name for both brand and model.
                2. Keep the `model` value short and clean. **Avoid including trim levels, engine types, drivetrain, hybrid/electric status, or technical descriptors**.
                - Example: Use "Corolla Cross" instead of "Corolla Cross Hybrid" or "Corolla Cross ZVG10L".
                - Example: Use "RAV4", not "RAV4 Plug-in Hybrid" or "RAV4 LE AWD".
                3. If `source_brand` is a local distributor (e.g. 國瑞), map it to the correct global brand using prompt content.
                4. If you cannot confidently determine the brand or model, return an empty string `""`.
                5. Ensure consistent naming — the same model should always produce the same `model` output.
                6. Do **not** include any explanations or extra text. Only return the final JSON array.
                """,
            }
        ]
    }
    llm_client.template_manager.add_template(
        "car_code_analyst", car_code_analyst_template
    )

    # 使用範本和 JSON schema 進行車輛分析
    response = llm_client.chat(
        prompt=str(car_code_prompt_data),
        template_name="car_code_analyst",
    )

    ans = response["choices"][0]["message"]["content"]
    ans = parse_json_input(ans)

    ret = []
    for i, j in enumerate(ans):
        j["input"] = car_code_prompt_data[i]
        ret.append(j)

    return ret


def normalize_car_robins_search_result_to_robins_brand_model(
    llm_client: LLMClient, car_robins_search_result_prompt_data: list[str] | str
) -> dict[str]:
    """
    Output:
    {
        "brand": "",
        "model": "",
    }

    Example car_robins_search_result_prompt_data:
    car_robins_search_result_prompt_data = [
        '中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 證書號碼：. 105042. 證書有效期限：. 2016/01/29 - 2018/01/28. 廠牌名稱：. 中華. 排檔型式：. CVT. 門數：. 5D. 總排氣量：. 2359.0.',
        'Outlander除了進口的PHEV以外，中華三菱同步推出搭載新世代2.4L MIVEC引擎的國產汽油車型，其連續可變氣門揚程系統，可有效控制氣門開閉時間與幅度，繼而表現出16.8km/ltr的 ...',
        '13.6 中華汽車104/12/11. 1級. 中華. OUTLANDER RE24H5AX. CVT 5D. 2359.0. 1666.0. 7.7. 9.96. 15.52. 12.9 中華汽車104/12/11. 1級. 臺灣東風小康. FUWIN K01HV23SE. M5.',
        '中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 中華OUTLANDER RE24H5DA 2359c.c. CVT ... 中華OUTLANDER RE24H5AX 2359C.C. A0207E16A08-01. 尊爵黑、晶玉白、冰鑽銀 ...',
        'OUTLANDER RE24H5AX. CVT. 5D. 2359.0. 1671.0. 8.9. 13.18. 18.96. 15.3 中華汽車103/10/07 ... 15.8 中華汽車103/10/07. 1級. 中華(註一). OUTLANDER RE24H5A. CVT. 5D.',
        '止，中華汽車基於前項檢查結果，中華汽車的內部控制制度﹙含對子公司之監督與管理 ... OUTLANDER RE24H5AX 2359c.c. CVT 5D. OUTLANDER RE24H5DA 2359c.c. CVT 5D.',
        '中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 中華OUTLANDER RE24H5DA 2359c.c. CVT ... 中華OUTLANDER RE24H5AX 2359C.C. A0207E16A08-01. 中華OUTLANDER RE24H5DA ...',
        '中華 COLT PLUS CO161SB 1499c.c. CVT 5D. 104/6/2. 69. 72. 82. 6000. 1499. B5G10507-2 ... 中華 OUTLANDER RE24H5AX 2359c.c. CVT 5D. 104/9/18. 71. 80. 124. 6000. 2359.',
        '女性/ 35歲/ 中華(國產) Outlander 特仕型2WD RR351 (RE241H5DA) 2359c.c. 5D 5人座83.9萬/ 3年以上未肇事. 強制險、第三人責任險、丙式車體險. 不是你要的？',
        '得利卡貨車. 車主手冊. 車主手冊. 中華堅兵. 車主手冊. 車主手冊. GRAND LANCER. 車主手冊. 車主手冊. New Outlander. 車主手冊. 車主手冊 ...'
    ]
    """

    llm_client.model_manager.set_current_model("deepseek-chat")

    car_search_result_analyst_template = {
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
    llm_client.template_manager.add_template(
        "car_search_result_analyst", car_search_result_analyst_template
    )

    # 使用範本和 JSON schema 進行車輛分析
    response = llm_client.chat(
        prompt=str(car_robins_search_result_prompt_data),
        template_name="car_search_result_analyst",
    )

    ans = response["choices"][0]["message"]["content"]

    return parse_json_input(ans)


def normalize_car_robins_search_result_full_text(
    llm_client: LLMClient, car_robins_search_result_prompt_data: list[str] | str
) -> dict[str]:

    llm_client.model_manager.set_current_model("deepseek-chat")

    car_code_analyst_template = {
        "messages": [
            # {
            #     "role": "system",
            #     "content": """
            #         你分析使用者給你資料後以下方格式回答
            #         廠牌名稱(Brand) 以全世界最通用的英文名稱回答 命名為 brand
            #         車型名稱(ModelName) 以全世界最通用的英文名稱回答 命名為 model
            #         不確定的話就空白
            #         你只需要回傳 json 不需要其他任何分析
            #         [{
            #             "source_brand":source_brand,
            #             "source_type":source_type,
            #             "brand": "",
            #             "model": "",
            #         },]
            #         """,
            # }
            # {
            #     "role": "system",
            #     "content": """
            #     你是一個能夠根據使用者提供的汽車資訊進行品牌與車型辨識的助手。使用者會提供一個包含多筆車輛資料的列表，每筆資料都包含原始廠牌(source_brand)、原始車型(source_type)、與一段相關描述(prompt)。
            #     請根據以下規則進行分析並只回傳純 JSON 格式的結果，格式如下：
            #     [
            #         {
            #             "source_brand": "原始廠牌",
            #             "source_type": "原始車型",
            #             "brand": "標準化英文品牌名稱",
            #             "model": "標準化英文車型名稱"
            #         },
            #         ...
            #     ]
            #     **規則：**
            #     1. `brand` 與 `model` 請盡可能根據全世界通用的英文名稱標準化。
            #     2. 如果 `source_brand` 是代理商名稱（例如：國瑞、裕隆等），請根據 `prompt` 內的資訊轉換成正確的汽車品牌（如：國瑞 → Toyota）。
            #     3. 車型名稱請從 `source_type` 與 `prompt` 描述中提取最常見的通用車型名稱（如：RAV4、Corolla Cross）。
            #     4. 如果無法確定品牌或車型，請保留空白字串 ""。
            #     5. 你**只需要回傳符合格式的 JSON 陣列，不需要任何額外說明、註解或分析文字**。
            #     """
            # }
            {
                "role": "system",
                "content": """
                You are an assistant that extracts the standardized brand and model name of cars based on user-provided information.

                The user provides a list of car entries, each including a source_brand, source_type, and a descriptive prompt.

                Your task is to extract the global brand and the most widely recognized, simplified model name (in English) based on international naming conventions.

                Respond only with a JSON array in the following format:

                [
                    {
                        "source_brand": "Original brand input",
                        "source_type": "Original model input",
                        "brand": "Standardized brand name in English",
                        "model": "Simplified, globally recognized model name"
                    },
                    ...
                ]

                **Guidelines:**
                1. Always return the most widely recognized global English name for both brand and model.
                2. Keep the `model` value short and clean. **Avoid including trim levels, engine types, drivetrain, hybrid/electric status, or technical descriptors**.
                - Example: Use "Corolla Cross" instead of "Corolla Cross Hybrid" or "Corolla Cross ZVG10L".
                - Example: Use "RAV4", not "RAV4 Plug-in Hybrid" or "RAV4 LE AWD".
                3. If `source_brand` is a local distributor (e.g. 國瑞), map it to the correct global brand using prompt content.
                4. If you cannot confidently determine the brand or model, return an empty string `""`.
                5. Ensure consistent naming — the same model should always produce the same `model` output.
                6. Do **not** include any explanations or extra text. Only return the final JSON array.
            """,
            }
        ]
    }
    llm_client.template_manager.add_template(
        "car_code_analyst", car_code_analyst_template
    )

    # 使用範本和 JSON schema 進行車輛分析
    response = llm_client.chat(
        prompt=str(car_robins_search_result_prompt_data),
        template_name="car_code_analyst",
    )

    ans = response["choices"][0]["message"]["content"]

    return parse_json_input(ans)
