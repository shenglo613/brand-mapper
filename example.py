"""
使用範例

此檔案展示如何使用 LLM 客戶端進行對話。
"""

from llm.client import LLMClient


def main():
    # 初始化客戶端
    client = LLMClient()

    # 設定 API 金鑰
    client.model_manager.set_api_key(
        "deepseek-chat",
        "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",
    )

    # 設定當前模型
    client.model_manager.set_current_model("deepseek-chat")

    # 新增汽車分析師範本
    car_analyst_template = {
        "messages": [
            {
                "role": "system",
                "content": """
                    使用者會問給你一段文本, 你分析後以下方格式回答, 不確定的話就空白
                    你只需要回傳 json 不需要其他任何分析

                    {
                        "基本資訊 (Basic Info)": {
                            "廠牌名稱 (Brand)": "中華 / Mitsubishi",
                            "車型名稱 (Model Name)": "OUTLANDER",
                            "車型代碼 (Model Code)": "RE24H5AX",
                            "車型年份 (Model Year)": "2015",
                            "產地 (Origin)": "國產 (台灣中華汽車)",
                            "車型分類 (Vehicle Type)": "小客車(非轎式、非旅行式)",
                            "車門數 (Number of Doors)": "5D (五門)",
                            "座位數 (Seating Capacity)": "5人座"
                        },
                        "引擎規格 (Engine Specs)": {
                            "引擎型式 (Engine Type)": "新世代2.4L MIVEC引擎",
                            "總排氣量 (Displacement)": "2359.0 c.c.",
                            "最大馬力 (Max Horsepower)": "124 hp",
                            "最大馬力轉速 (Max Horsepower RPM)": "6000 rpm"
                        },
                        "傳動系統 (Transmission)": {
                            "排檔型式 (Transmission Type)": "CVT (連續可變速自動變速箱)",
                            "驅動方式 (Drive Type)": "2WD (前輪驅動)"
                        },
                        "車身規格 (Body Specs)": {
                            "車重 (Curb Weight)": "約1666.0-1671.0 kg (依資料來源有些微差異)"
                        }
                    }
                    """,
            }
        ]
    }
    client.template_manager.add_template("car_analyst", car_analyst_template)

    # 使用範本和 JSON schema 進行車輛分析
    response = client.chat(
        prompt="""
        # 中華 RE24H5AX 這是我的搜尋關鍵字 得到以下資訊 你能夠告訴我這台車子的詳細規格嗎 json 格式產生

        [
            {
                "url": "https://www.energylabel.org.tw/purchasing/nocifi/item.aspx?itemp0=26083",
                "title": "節能標章全球資訊網-證書失效產品",
                "snippet": "中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 證書號碼：. 105042. 證書有效期限：. 2016/01/29 - 2018/01/28. 廠牌名稱：. 中華. 排檔型式：. CVT. 門數：. 5D. 總排氣量：. 2359.0.",
                "published_date": null,
                "source": "www.energylabel.org.tw",
                "image_url": "https://www.energylabel.org.tw/energylbapply/_Upload/ApplyMain/ApplyP/26083/Photo1/OUTLANDER%E7%85%A7%E7%89%87.jpg",
                "extra_data": {}
            },
            {
                "url": "https://autos.yahoo.com.tw/new-cars/trim/mitsubishi-outlander-2015-%E7%B6%93%E5%85%B8%E5%9E%8B",
                "title": "2015 Mitsubishi Outlander 經典型| 車款介紹- Yahoo奇摩汽車機車",
                "snippet": "Outlander除了進口的PHEV以外，中華三菱同步推出搭載新世代2.4L MIVEC引擎的國產汽油車型，其連續可變氣門揚程系統，可有效控制氣門開閉時間與幅度，繼而表現出16.8km/ltr的 ...",
                "published_date": null,
                "source": "autos.yahoo.com.tw",
                "image_url": "https://autos.yahoo.com.tw//y/r/w880/iw/MMT/car/d56dd28dc384913d138444ffeeac2ba1_1200.jpg",
                "extra_data": {}
            },
            {
                "url": "https://www.moeaea.gov.tw/ecw/populace/content/wHandStatistics_File.ashx?statistics_id=1241&serial_no=1",
                "title": "國產小貨車、小客貨兩用車及小客車(非轎式、非旅行式)車型耗能證明 ...",
                "snippet": "13.6 中華汽車104/12/11. 1級. 中華. OUTLANDER RE24H5AX. CVT 5D. 2359.0. 1666.0. 7.7. 9.96. 15.52. 12.9 中華汽車104/12/11. 1級. 臺灣東風小康. FUWIN K01HV23SE. M5.",
                "published_date": null,
                "source": "www.moeaea.gov.tw",
                "image_url": null,
                "extra_data": {}
            },
            {
                "url": "https://www.china-motor.com.tw/cmwspublished/layout2/cmc_csr_report_2016.pdf",
                "title": "Untitled",
                "snippet": "中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 中華OUTLANDER RE24H5DA 2359c.c. CVT ... 中華OUTLANDER RE24H5AX 2359C.C. A0207E16A08-01. 尊爵黑、晶玉白、冰鑽銀 ...",
                "published_date": null,
                "source": "www.china-motor.com.tw",
                "image_url": "x-raw-image:///1db47ab19f2ff243d52bd7b1f6bda1e634e652da1c38e494c4032304bb6e8be5",
                "extra_data": {}
            },
            {
                "url": "https://www.moeaea.gov.tw/ECW/populace/content/wHandStatistics_File.ashx?statistics_id=1072&serial_no=1",
                "title": "國產小貨車、小客貨兩用車及小客車(非轎式、非旅行式)車型耗能證明 ...",
                "snippet": "OUTLANDER RE24H5AX. CVT. 5D. 2359.0. 1671.0. 8.9. 13.18. 18.96. 15.3 中華汽車103/10/07 ... 15.8 中華汽車103/10/07. 1級. 中華(註一). OUTLANDER RE24H5A. CVT. 5D.",
                "published_date": null,
                "source": "www.moeaea.gov.tw",
                "image_url": null,
                "extra_data": {}
            },
            {
                "url": "https://www.china-motor.com.tw/cmwspublished/layout2/cmc_csr_report_2014.pdf",
                "title": "CSR 封面20150625",
                "snippet": "止，中華汽車基於前項檢查結果，中華汽車的內部控制制度﹙含對子公司之監督與管理 ... OUTLANDER RE24H5AX 2359c.c. CVT 5D. OUTLANDER RE24H5DA 2359c.c. CVT 5D.",
                "published_date": null,
                "source": "www.china-motor.com.tw",
                "image_url": "x-raw-image:///ce8528612fd1e3578a929b3c9737bda4d5e9433bbd8463f336968b1cf3f556b3",
                "extra_data": {}
            },
            {
                "url": "https://sustaihubtokyo.s3-ap-northeast-1.amazonaws.com/CSRreport/Mops/03098415_%E4%B8%AD%E8%8F%AF_2204/03098415_2204_105_CSRreport.pdf",
                "title": "Untitled",
                "snippet": "中華OUTLANDER RE24H5AX 2359c.c. CVT 5D. 中華OUTLANDER RE24H5DA 2359c.c. CVT ... 中華OUTLANDER RE24H5AX 2359C.C. A0207E16A08-01. 中華OUTLANDER RE24H5DA ...",
                "published_date": null,
                "source": "sustaihubtokyo.s3-ap-northeast-1.amazonaws.com",
                "image_url": "x-raw-image:///6a1564c852055a12c087fb8f04e89d433412eed3dad0100e1c9b1fafce1b6f91",
                "extra_data": {}
            },
            {
                "url": "https://www.artc.org.tw/carmode/file/104IN_G.ods",
                "title": "無題",
                "snippet": "中華 COLT PLUS CO161SB 1499c.c. CVT 5D. 104/6/2. 69. 72. 82. 6000. 1499. B5G10507-2 ... 中華 OUTLANDER RE24H5AX 2359c.c. CVT 5D. 104/9/18. 71. 80. 124. 6000. 2359.",
                "published_date": null,
                "source": "www.artc.org.tw",
                "image_url": null,
                "extra_data": {}
            },
            {
                "url": "https://insurance.icard.ai/car/series/0734",
                "title": "(線上投保)中華車險》比較14家甲乙丙車體險、試算Outlander保費 ...",
                "snippet": "女性/ 35歲/ 中華(國產) Outlander 特仕型2WD RR351 (RE241H5DA) 2359c.c. 5D 5人座83.9萬/ 3年以上未肇事. 強制險、第三人責任險、丙式車體險. 不是你要的？",
                "published_date": null,
                "source": "insurance.icard.ai",
                "image_url": null,
                "extra_data": {}
            },
            {
                "url": "https://www.mitsubishi-motors.com.tw/download.php",
                "title": "車主手冊下載",
                "snippet": "得利卡貨車. 車主手冊. 車主手冊. 中華堅兵. 車主手冊. 車主手冊. GRAND LANCER. 車主手冊. 車主手冊. New Outlander. 車主手冊. 車主手冊 ...",
                "published_date": null,
                "source": "www.mitsubishi-motors.com.tw",
                "image_url": "https://www.mitsubishi-motors.com.tw/cmcpublished/usebook/download_p2022b_ASpu.jpg",
                "extra_data": {}
            }
        ]
       
        """,
        template_name="car_analyst",
    )

    print(response)


if __name__ == "__main__":
    main()
