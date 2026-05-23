import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Russell 2000 Screener", page_icon="📈", layout="wide")
st.title("📈 Russell 2000 スクリーナー")
st.caption("強い上昇トレンド銘柄を自動スキャン（週次更新）")

# ============================================================
#  データ読み込み
# ============================================================
DATA_PATH    = 'data/results.csv'
UPDATED_PATH = 'data/last_updated.txt'

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)

    # 最終更新日
    if os.path.exists(UPDATED_PATH):
        with open(UPDATED_PATH) as f:
            last_updated = f.read().strip()
    else:
        last_updated = '不明'

    st.info(f'📅 最終スキャン日: {last_updated}　（毎週土曜日に自動更新）')

    # ============================================================
    #  サマリー
    # ============================================================
    col1, col2, col3 = st.columns(3)
    col1.metric('スキャン銘柄数', f'{len(df)}銘柄')
    col2.metric('全条件クリア', f'{df["all_pass"].sum()}銘柄')
    col3.metric('スコア4以上', f'{(df["score"]>=4).sum()}銘柄')

    # ============================================================
    #  タブ表示
    # ============================================================
    tab1, tab2, tab3 = st.tabs(['🚀 全条件クリア', '🔶 スコア4以上', '📋 全銘柄'])

    cols_display = ['ticker','sector','score','①EMA並び','②出来高急増',
                    '③RS優位','④売買代金','⑤高値圏','現在値',
                    '高値乖離%','出来高倍率','売買代金(M$)','銘柄RS']

    def color_score(val):
        if val == 5: return 'background-color:#1a6e1a;color:white'
        if val == 4: return 'background-color:#4a7a1a;color:white'
        if val == 3: return 'background-color:#7a6a1a;color:white'
        return ''

    def color_check(val):
        if val == '✅': return 'background-color:#1a4a1a;color:#00ff88'
        if val == '❌': return 'background-color:#4a1a1a;color:#ff6b6b'
        return ''

    check_cols = ['①EMA並び','②出来高急増','③RS優位','④売買代金','⑤高値圏']

    with tab1:
        df_pass = df[df['all_pass']].reset_index(drop=True)
        df_pass.index += 1
        st.subheader(f'🚀 全条件クリア: {len(df_pass)}銘柄')
        if len(df_pass) > 0:
            st.dataframe(
                df_pass[cols_display].style
                .map(color_score, subset=['score'])
                .map(color_check, subset=check_cols),
                use_container_width=True, height=500
            )
            # TradingView用
            tickers_str = ','.join(df_pass['ticker'].tolist())
            st.subheader('📋 TradingViewウォッチリスト用')
            st.code(tickers_str)
        else:
            st.warning('該当銘柄なし')

    with tab2:
        df_near = df[(df['score']>=4) & (~df['all_pass'])].reset_index(drop=True)
        df_near.index += 1
        st.subheader(f'🔶 スコア4以上: {len(df_near)}銘柄')
        if len(df_near) > 0:
            st.dataframe(
                df_near[cols_display].style
                .map(color_score, subset=['score'])
                .map(color_check, subset=check_cols),
                use_container_width=True, height=500
            )
            tickers_str4 = ','.join(df_near['ticker'].tolist())
            st.subheader('📋 TradingViewウォッチリスト用（4以上）')
            st.code(tickers_str4)
        else:
            st.warning('該当銘柄なし')

    with tab3:
        st.subheader(f'📋 全銘柄: {len(df)}銘柄')
        score_filter = st.slider('最低スコア', 0, 5, 0)
        df_filtered = df[df['score'] >= score_filter].reset_index(drop=True)
        df_filtered.index += 1
        st.dataframe(
            df_filtered[cols_display].style
            .map(color_score, subset=['score'])
            .map(color_check, subset=check_cols),
            use_container_width=True, height=600
        )

    # ============================================================
    #  セクター別サマリー
    # ============================================================
    st.subheader('📂 セクター別サマリー')
    sector_summary = (
        df.groupby('sector')
        .agg(総銘柄数=('ticker','count'),
             全条件クリア=('all_pass','sum'),
             平均スコア=('score','mean'))
        .sort_values('全条件クリア', ascending=False)
        .round(2)
    )
    st.dataframe(sector_summary, use_container_width=True)

else:
    st.warning('⚠️ まだスキャン結果がありません。')
    st.info('GitHub Actionsが毎週土曜日に自動スキャンします。初回は手動で実行してください。')
    st.code('''
# Google Colabで以下を実行してください：
# 1. screener.py の内容をColabにコピー
# 2. 実行後、data/results.csv をGitHubにアップロード
    ''')
