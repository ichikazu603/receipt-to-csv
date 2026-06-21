import anthropic
import base64
import json
import re
from pathlib import Path


def _encode_image(image_bytes: bytes, media_type: str) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def parse_receipt(image_bytes: bytes, filename: str) -> dict:
    """Claude Haiku でレシート画像から経費情報を抽出する。"""
    ext = Path(filename).suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    client = anthropic.Anthropic()

    prompt = """以下のレシート・領収書画像から経費情報を抽出し、必ずJSON形式だけで返してください。
マークダウンや説明文は一切含めず、JSONオブジェクトのみを返してください。

抽出するフィールド（読み取れない場合は空文字 "" を入れてください）:
- date: 日付（YYYY/MM/DD形式）
- amount: 金額・合計（税込、数値のみ・カンマなし）
- tax: 消費税額（数値のみ。記載がなければ空文字）
- store: 店名・取引先名
- description: 品目・摘要（複数ある場合はカンマ区切りでまとめる）
- payment_method: 支払方法（現金 / クレジットカード / 電子マネー / その他 のどれか）

返答例:
{"date":"2024/06/15","amount":1980,"tax":180,"store":"セブンイレブン渋谷店","description":"食料品","payment_method":"現金"}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": _encode_image(image_bytes, media_type),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # JSONブロック（```json ... ```）が混入した場合に対応
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    return {
        "date": str(data.get("date", "")),
        "amount": data.get("amount", ""),
        "tax": data.get("tax", ""),
        "store": str(data.get("store", "")),
        "description": str(data.get("description", "")),
        "payment_method": str(data.get("payment_method", "")),
        "filename": filename,
    }
