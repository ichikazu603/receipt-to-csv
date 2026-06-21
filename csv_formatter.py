import io
import pandas as pd

# 弥生会計 Next 仕訳インポート形式（27列 A〜AA）
# https://support.yayoi-kk.co.jp/subcontents.html?page_id=29611
COLUMNS = [
    "識別フラグ",   # A: 必須 "2000"
    "伝票No",       # B: 取込まない
    "決算",         # C: 空欄
    "取引日付",     # D: 必須
    "借方勘定科目", # E: 必須
    "借方補助科目", # F:
    "借方部門",     # G:
    "借方税区分",   # H: 必須
    "借方税込金額", # I: 必須
    "借方消費税額", # J:
    "貸方勘定科目", # K: 必須
    "貸方補助科目", # L:
    "貸方部門",     # M:
    "貸方税区分",   # N: 必須
    "貸方税込金額", # O: 必須
    "貸方消費税額", # P:
    "摘要",         # Q:
    "番号",         # R: 取込まない
    "期日",         # S: 取込まない
    "タイプ",       # T: 取込まない
    "生成元",       # U: 取込まない
    "仕訳メモ",     # V: 取込まない
    "付箋1",        # W:
    "付箋2",        # X: 取込まない
    "調整",         # Y: 取込まない
    "借方取引先名", # Z:
    "貸方取引先名", # AA:
]

# 支払方法 → 貸方勘定科目のマッピング
_CREDIT_ACCOUNT = {
    "現金": "現金",
    "クレジットカード": "未払金",
    "電子マネー": "未払金",
    "その他": "現金",
}

# 品目キーワード → 借方勘定科目のマッピング（上から順に一致チェック）
_DEBIT_ACCOUNT_RULES = [
    (["交通", "電車", "バス", "タクシー", "新幹線", "航空"], "旅費交通費"),
    (["食事", "飲食", "ランチ", "ディナー", "カフェ", "コーヒー", "弁当"], "会議費"),
    (["接待", "贈答", "ギフト"], "接待交際費"),
    (["文具", "事務", "コピー", "印刷", "インク", "用紙"], "消耗品費"),
    (["書籍", "本", "雑誌", "新聞"], "新聞図書費"),
    (["通信", "電話", "インターネット", "ネット"], "通信費"),
    (["ガソリン", "駐車", "高速", "ガス"], "車両費"),
]
DEFAULT_DEBIT_ACCOUNT = "雑費"


def _guess_debit_account(description: str, store: str) -> str:
    text = (description + store).replace("　", " ")
    for keywords, account in _DEBIT_ACCOUNT_RULES:
        if any(kw in text for kw in keywords):
            return account
    return DEFAULT_DEBIT_ACCOUNT


def _safe_int(val) -> str:
    """数値を整数文字列に変換。変換できない場合は空文字を返す。"""
    try:
        return str(int(float(str(val).replace(",", ""))))
    except (ValueError, TypeError):
        return ""


def to_yayoi_csv(records: list[dict]) -> bytes:
    """パース済みレシートデータを弥生会計 Next 仕訳インポート用CSVに変換する。"""
    rows = []
    for r in records:
        amount = _safe_int(r.get("amount", ""))
        tax = _safe_int(r.get("tax", ""))
        payment = r.get("payment_method", "その他")
        credit_account = _CREDIT_ACCOUNT.get(payment, "現金")
        debit_account = _guess_debit_account(
            r.get("description", ""), r.get("store", "")
        )
        summary = r.get("store", "")
        if r.get("description"):
            summary += "　" + r["description"]

        row = {col: "" for col in COLUMNS}
        row.update(
            {
                "識別フラグ": "2000",
                "取引日付": r.get("date", ""),
                "借方勘定科目": debit_account,
                "借方税区分": "課税仕入れ10%",
                "借方税込金額": amount,
                "借方消費税額": tax,
                "貸方勘定科目": credit_account,
                "貸方税区分": "対象外",
                "貸方税込金額": amount,
                "摘要": summary[:256],
            }
        )
        rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNS)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")  # BOM付きUTF-8（Excel対応）
    return buf.getvalue()
