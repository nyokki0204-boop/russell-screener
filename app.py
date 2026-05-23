import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Monex Screener", page_icon="📈", layout="wide")
st.title("📈 Monex US Stock Screener")
st.caption("マネックス証券 米国株 強い上昇トレンド銘柄（週次更新）")

DATA_PATH    = 'data/results.csv'
UPDATED_PATH = 'data/last_updated.txt'

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)

    if os.path.exists(UPDATED_PATH):
        with open(UPDATED_PATH) as f:
            last_updated = f.read().strip()
    else:
        last_updated = '不明'

    st.info(f'📅 最終スキャン日: {last_updated}　（毎週土曜日に自動更新）')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('スキャン銘柄数', f'{len(df)}銘柄')
    col2.metric('全条件クリア', f'{df["all_pass"].sum()}銘柄')
    col3.metric('スコア4以上', f'{(df["score"]>=4).sum()}銘柄')
    col4.metric('セクター数', f'{df["sector"].nunique()}')

    cols_display = ['ticker','sector','industry','score','①EMA並び','②出来高急増',
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

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        '🚀 全条件クリア',
        '🔶 スコア4以上',
        '📂 セクター別',
        '📋 全銘柄',
        '📊 セクターサマリー'
    ])

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
            st.subheader('📋 TradingViewウォッチリスト用')
            st.code(','.join(df_pass['ticker'].tolist()))
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
            st.subheader('📋 TradingViewウォッチリスト用（4以上）')
            st.code(','.join(df_near['ticker'].tolist()))
        else:
            st.warning('該当銘柄なし')

    with tab3:
        st.subheader('📂 セクター別表示')
        sectors = sorted(df['sector'].dropna().unique().tolist())
        selected = st.selectbox('セクターを選択', ['全セクター'] + sectors)

        score_min = st.slider('最低スコア', 0, 5, 3)

        if selected == '全セクター':
            df_sec = df[df['score'] >= score_min].reset_index(drop=True)
        else:
            df_sec = df[(df['sector'] == selected) & (df['score'] >= score_min)].reset_index(drop=True)

        df_sec.index += 1
        st.write(f'{len(df_sec)}銘柄')
        st.dataframe(
            df_sec[cols_display].style
            .map(color_score, subset=['score'])
            .map(color_check, subset=check_cols),
            use_container_width=True, height=500
        )
        if len(df_sec) > 0:
            st.subheader('📋 TradingViewウォッチリスト用')
            st.code(','.join(df_sec['ticker'].tolist()))

    with tab4:
        st.subheader(f'📋 全銘柄: {len(df)}銘柄')
        score_filter = st.slider('最低スコア ', 0, 5, 0)
        df_filtered = df[df['score'] >= score_filter].reset_index(drop=True)
        df_filtered.index += 1
        st.dataframe(
            df_filtered[cols_display].style
            .map(color_score, subset=['score'])
            .map(color_check, subset=check_cols),
            use_container_width=True, height=600
        )

    with tab5:
        st.subheader('📊 セクター別サマリー')
        sector_summary = (
            df.groupby('sector')
            .agg(
                総銘柄数=('ticker', 'count'),
                全条件クリア=('all_pass', 'sum'),
                スコア4以上=('score', lambda x: (x>=4).sum()),
                平均スコア=('score', 'mean'),
                平均RS=('銘柄RS', 'mean'),
            )
            .sort_values('全条件クリア', ascending=False)
            .round(3)
        )
        st.dataframe(sector_summary, use_container_width=True)

        st.subheader('📊 業種(Industry)別サマリー')
        if 'industry' in df.columns:
            industry_summary = (
                df[df['all_pass']].groupby('industry')
                .agg(
                    全条件クリア=('ticker', 'count'),
                    平均RS=('銘柄RS', 'mean'),
                )
                .sort_values('全条件クリア', ascending=False)
                .round(3)
            )
            st.dataframe(industry_summary, use_container_width=True)

else:
    st.warning('⚠️ まだスキャン結果がありません。')
    st.info('GitHub Actionsが毎週土曜日に自動スキャンします。')

st.caption(f'最終更新: {pd.Timestamp.now().strftime("%Y/%m/%d %H:%M")}  |  データ: yfinance  |  対象: マネックス証券取扱銘柄')
