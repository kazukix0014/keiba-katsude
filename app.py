import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

st.set_page_config(page_title="競馬データ KATSUDE", layout="wide")

# ---------------------------------------------------------
# 🎨 スタイリング・カラーリングの調整（背景は白、ヘッダーは超モダン）
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* 全体の背景を白（デフォルト）に戻す */
    .stApp {
        background-color: #FFFFFF;
        color: #0F172A;
    }
    
    /* ヘッダー・タイトルエリア：今風のハイテク＆ミニマルなダークデザイン */
    .hero-banner {
        background: linear-gradient(135deg, #111827 0%, #0F172A 100%);
        padding: 4.5rem 2rem;
        border-radius: 20px;
        color: #FFFFFF;
        margin-bottom: 2.5rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(52, 211, 153, 0.3);
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    /* 光るアクセントライン（近未来感） */
    .hero-banner::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #34D399, #3B82F6, #6366F1);
    }
    
    /* 大迫力のタイトル文字 */
    .app-title {
        font-size: 5.8rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        line-height: 1.05;
        background: linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    /* 各セクション見出し（サブヘッダー）の装飾 */
    h3 {
        color: #1E293B !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        border-left: 4px solid #34D399;
        padding-left: 12px;
        margin-top: 2rem !important;
        margin-bottom: 0.75rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 🔍 強制クリアボタン
if st.button("🔄 スプレッドシートの最新データを強制再読み込み"):
    st.cache_data.clear()
    st.rerun()


# 鍵のフォーマットを完璧に補正・再構築する関数
def clean_private_key(key_str: str) -> str:
    if not key_str:
        return key_str
    
    key_str = key_str.strip()
    if (key_str.startswith('"') and key_str.endswith('"')) or (key_str.startswith("'") and key_str.endswith("'")):
        key_str = key_str[1:-1].strip()
    
    key_str = key_str.replace("\\n", "\n")
    
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    if header in key_str and footer in key_str:
        parts = key_str.split(header)
        body = parts[1].split(footer)[0]
        body_clean = "".join(body.split())
        key_str = f"{header}\n{body_clean}\n{footer}\n"
        
    return key_str


# 1. データ読み込み（自動復元対応）
@st.cache_data(ttl=60)
def load_data():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Streamlit Cloud上に secrets 設定があればそれを使用
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["private_key"] = clean_private_key(str(creds_info.get("private_key", "")))
        
        creds = Credentials.from_service_account_info(
            creds_info, scopes=scopes
        )
    else:
        creds = Credentials.from_service_account_file(
            "secret-key.json", scopes=scopes
        )

    gc = gspread.authorize(creds)
    sh = gc.open("競馬データ")
    df = pd.DataFrame(sh.get_worksheet(0).get_all_records())

    def clean_val(x):
        if isinstance(x, str):
            return "".join(x.split()).strip()
        return x

    df = df.map(clean_val)

    if "日付" in df.columns:
        df["日付_dt"] = pd.to_datetime(df["日付"], errors="coerce")

    return df


try:
    df = load_data()

    # ---------------------------------------------------------
    # タイトル（超モダン・特大バナー）
    # ---------------------------------------------------------
    st.markdown(
        """
        <div class="hero-banner">
            <h1 class="app-title">🐎 競馬データ KATSUDE</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # 📅 期間・条件ラジオボタン
    # ---------------------------------------------------------
    st.subheader("📅 表示期間・特別条件")

    period_option = st.radio(
        "表示期間を選択してください（1つ選択）",
        [
            "全期間",
            "過去1年以内",
            "過去2年以内",
            "過去3年以内",
            "過去4年以内",
            "過去5年以内",
            "☀️ 夏競馬のみ（6月〜9月）",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. 検索用のマルチセレクト
    # ---------------------------------------------------------
    st.subheader("🔍 コース・条件指定（複数選択可）")
    cols_search = st.columns(5)

    def get_options(col_name):
        if col_name in df.columns:
            return sorted(
                list(set([str(x) for x in df[col_name].unique() if str(x).strip() != ""]))
            )
        return []

    s_course = cols_search[0].multiselect(
        "競馬場", get_options("競馬場"), placeholder="すべて"
    )
    s_track = cols_search[1].multiselect(
        "コース", get_options("コース"), placeholder="すべて"
    )
    s_dist = cols_search[2].multiselect(
        "距離", get_options("距離"), placeholder="すべて"
    )
    s_cond = cols_search[3].multiselect(
        "馬場状態", get_options("馬場状態"), placeholder="すべて"
    )
    s_class = cols_search[4].multiselect(
        "クラス", get_options("クラス"), placeholder="すべて"
    )

    # ---------------------------------------------------------
    # 🔍 フリーテキストキーワード検索 & ソート順指定
    # ---------------------------------------------------------
    st.subheader("🔤 フリーワード検索 & 表示順設定")
    c_kw, c_sort = st.columns([2, 1])

    with c_kw:
        search_keyword = st.text_input(
            "キーワード入力（該当する名前が含まれる項目のみ表示します）",
            placeholder="例: キタサンブラック、ルメール など",
            label_visibility="collapsed",
        )

    with c_sort:
        sort_target = st.selectbox(
            "📊 並び替えの基準（高い順）",
            ["出走数", "勝率", "連対率", "三連対率"],
            index=0,
            label_visibility="collapsed",
        )

    st.markdown("---")

    # 3. 絞り込み処理
    d = df.copy()

    if "日付_dt" in d.columns and not d["日付_dt"].dropna().empty:
        today = datetime.datetime.now()

        if period_option == "過去1年以内":
            cutoff = today - pd.DateOffset(years=1)
            d = d[d["日付_dt"] >= cutoff]
        elif period_option == "過去2年以内":
            cutoff = today - pd.DateOffset(years=2)
            d = d[d["日付_dt"] >= cutoff]
        elif period_option == "過去3年以内":
            cutoff = today - pd.DateOffset(years=3)
            d = d[d["日付_dt"] >= cutoff]
        elif period_option == "過去4年以内":
            cutoff = today - pd.DateOffset(years=4)
            d = d[d["日付_dt"] >= cutoff]
        elif period_option == "過去5年以内":
            cutoff = today - pd.DateOffset(years=5)
            d = d[d["日付_dt"] >= cutoff]
        elif period_option == "☀️ 夏競馬のみ（6月〜9月）":
            d = d[d["日付_dt"].dt.month.isin([6, 7, 8, 9])]

    if s_course and "競馬場" in d.columns:
        d = d[d["競馬場"].astype(str).isin(s_course)]

    if s_track and "コース" in d.columns:
        d = d[d["コース"].astype(str).isin(s_track)]

    if s_dist and "距離" in d.columns:
        d = d[d["距離"].astype(str).isin(s_dist)]

    if s_cond and "馬場状態" in d.columns:
        d = d[d["馬場状態"].astype(str).isin(s_cond)]

    if s_class and "クラス" in d.columns:
        d = d[d["クラス"].astype(str).isin(s_class)]

    st.info(f"🔍 該当件数: {len(d):,} 件")

    # 4. ランキング表示関数
    def show_rank(data, target_col, title, keyword="", sort_by="出走数"):
        st.subheader(title)
        if target_col not in df.columns or "順位" not in df.columns:
            st.caption(f"※{target_col} 列がシートにありません")
            return
        if data.empty:
            st.caption("※該当データがありません")
            return

        tmp = data.copy()

        if keyword.strip():
            kw = keyword.strip()
            tmp = tmp[tmp[target_col].astype(str).str.contains(kw, case=False, na=False)]

        if tmp.empty:
            st.caption("※該当するデータがありません")
            return

        tmp["順位数値"] = pd.to_numeric(
            tmp["順位"].astype(str).str.replace("着", ""), errors="coerce"
        )

        summary = tmp.groupby(target_col).agg(
            出走数=("順位数値", "count"),
            一着=("順位数値", lambda x: (x == 1).sum()),
            連対=("順位数値", lambda x: (x <= 2).sum()),
            三連=("順位数値", lambda x: (x <= 3).sum()),
        )

        summary["勝率_num"] = (summary["一着"] / summary["出走数"]) * 100
        summary["連対率_num"] = (summary["連対"] / summary["出走数"]) * 100
        summary["三連対率_num"] = (summary["三連"] / summary["出走数"]) * 100

        sort_column_map = {
            "出走数": "出走数",
            "勝率": "勝率_num",
            "連対率": "連対率_num",
            "三連対率": "三連対率_num",
        }
        target_sort = sort_column_map.get(sort_by, "出走数")

        summary = summary.sort_values(
            by=[target_sort, "出走数"], ascending=[False, False]
        )

        summary["勝率"] = summary["勝率_num"]
        summary["連対率"] = summary["連対率_num"]
        summary["三連対率"] = summary["三連対率_num"]

        res_df = summary.reset_index()[
            [target_col, "出走数", "勝率", "連対率", "三連対率"]
        ]

        st.dataframe(
            res_df,
            column_config={
                "出走数": st.column_config.NumberColumn(format="%d"),
                "勝率": st.column_config.NumberColumn(format="%.1f%%"),
                "連対率": st.column_config.NumberColumn(format="%.1f%%"),
                "三連対率": st.column_config.NumberColumn(format="%.1f%%"),
            },
            width="stretch",
            hide_index=True,
            height=210,
        )

    # 5. ランキング表示（縦に1列で並べる）
    kw = search_keyword.strip()

    show_rank(d, "父父", "🧬 父父ランキング", kw, sort_target)
    show_rank(d, "母父", "🧬 母父ランキング", kw, sort_target)
    show_rank(d, "年齢", "🎂 年齢ランキング", kw, sort_target)
    show_rank(d, "騎手", "🏇 騎手ランキング", kw, sort_target)
    show_rank(d, "調教師名", "👔 調教師ランキング", kw, sort_target)
    show_rank(d, "性別", "🐎 性別ランキング", kw, sort_target)
    show_rank(d, "所属", "🏠 所属ランキング（美浦・栗東）", kw, sort_target)

except Exception as e:
    st.error(f"データの読み込み中にエラーが発生しました: {e}")
