import json
import re


def parse_json_input(input_str: str) -> dict[str]:
    """
    處理輸入字串，能讀取 markdown code block 或純 JSON 字串。
    回傳 Python dict。


    # ✅ 測試 markdown 包裝格式
    markdown_input = '''```json
    {
    "key": "value"
    }
    ```'''

    # ✅ 測試純 JSON 格式
    plain_json_input = '''
    {
    "key": "value"
    }
    '''
    """
    # 嘗試從 markdown code block 中提取 JSON
    match = re.search(r"```json\n(.*?)\n```", input_str, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = input_str  # 如果不是 markdown，就直接當作 JSON 處理

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(json_str)
        raise ValueError(f"無法解析 JSON：{e}")
