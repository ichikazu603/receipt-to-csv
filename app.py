import os
import streamlit as st
from receipt_parser import parse_receipt
from csv_formatter import to_yayoi_csv

# Streamlit Cloud は st.secrets から、ローカルは .env から APIキーを取得
def _load_api_key() -> str | None:
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.getenv("ANTHROPIC_API_KEY")

api_key = _load_api_key()
if api_key:
    os.environ["ANTHROPIC_API_KEY"] = api_key

st.set_page_config(page_title="レシートCSV変換", page_icon="🧾", layout="centered")
st.title("🧾 レシートCSV変換ツール")
st.caption("レシート写真をアップロード → 弥生会計 Next 仕訳インポート用CSVを出力")

if not api_key:
    st.error("ANTHROPIC_API_KEY が設定されていません。Streamlit Cloud の Secrets 設定を確認してください。")
    st.stop()

uploaded_files = st.file_uploader(
    "レシート画像を選択（複数可）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    if st.button("OCR解析を実行", type="primary"):
        results = []
        progress = st.progress(0, text="解析中...")

        for i, f in enumerate(uploaded_files):
            progress.progress((i) / len(uploaded_files), text=f"解析中: {f.name}")
            try:
                data = parse_receipt(f.read(), f.name)
                results.append(data)
            except Exception as e:
                st.warning(f"{f.name} の解析に失敗しました: {e}")

        progress.progress(1.0, text="完了")
        st.session_state["results"] = results

if "results" in st.session_state and st.session_state["results"]:
    st.subheader("解析結果（直接編集できます）")

    display_columns = {
        "date": "日付",
        "amount": "金額（税込）",
        "tax": "消費税額",
        "store": "店名",
        "description": "品目・摘要",
        "payment_method": "支払方法",
    }

    import pandas as pd
    df = pd.DataFrame(st.session_state["results"])[list(display_columns.keys())]
    df = df.rename(columns=display_columns)

    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

    # 編集結果をresultsに反映して出力
    inv_map = {v: k for k, v in display_columns.items()}
    edited_df = edited_df.rename(columns=inv_map)
    merged = edited_df.to_dict(orient="records")

    csv_bytes = to_yayoi_csv(merged)

    st.download_button(
        label="📥 CSVをダウンロード（弥生クラウド経費用）",
        data=csv_bytes,
        file_name="receipts_yayoi.csv",
        mime="text/csv",
        type="primary",
    )

    st.info(
        "ダウンロードしたCSVを弥生クラウド経費の「経費取込」>「CSVインポート」からアップロードしてください。\n"
        "列の並びが合わない場合は csv_formatter.py の YAYOI_COLUMNS を調整してください。"
    )
