import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

try:
    import japanize_matplotlib
except:
    pass

st.set_page_config(page_title="Monex Screener", page_icon="📈", layout="wide")
st.title("📈 Monex US Stock Screener")
st.caption("マネックス証券 米国株 強い上昇トレンド銘柄（週次更新）")

DATA_PATH    = 'data/results.csv'
UPDATED_PATH = 'data/last_updated.txt'
HISTORY_PATH = 'data/history.csv'
PASS_PATH    = 'data/pass_history.csv'

if not os.path.exists(DATA_PATH):
    st.warning('⚠️ まだスキャン結果がありません。')
    st.stop()

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

high_col = '⑤高値圏10-30%' if '⑤高値圏10-30%' in df.columns else '⑤高値圏'
check_cols = ['①EMA並び','②出来高急増','③RS優位','④売買代金', high_col]

cols_display = ['ticker','sector','industry','score',
                '①EMA並び','②出来高急増','③RS優位','④売買代金',
                high_col,'現在値','高値乖離%','出来高倍率','売買代金(M$)','銘柄RS']
cols_display = [c for c in cols_display if c in df.columns]

def color_score(val):
    if val == 5: return 'background-color:#1a6e1a;color:white'
    if val == 4: return 'background-color:#4a7a1a;color:white'
    if val == 3: return 'background-color:#7a6a1a;color:white'
    return ''

def color_check(val):
    if val == '✅': return 'background-color:#1a4a1a;color:#00ff88'
    if val == '❌': return 'background-color:#4a1a1a;color:#ff6b6b'
    return ''

# ============================================================
#  タブ
# ============================================================
tab1, tab_new, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    '🚀 全条件クリア',
    '🆕 新規・脱落',
    '🔶 スコア4以上',
    '📂 セクター別',
    '📈 推移グラフ',
    '📋 全銘柄',
    '📊 セクターサマリー',
])

with tab1:
    df_pass = df[df['all_pass']].reset_index(drop=True)
    df_pass.index += 1
    st.subheader(f'🚀 全条件クリア: {len(df_pass)}銘柄')
    if len(df_pass) > 0:
        st.dataframe(
            df_pass[cols_display].style
            .map(color_score, subset=['score'])
            .map(color_check, subset=[c for c in check_cols if c in df_pass.columns]),
            use_container_width=True, height=500
        )
        st.subheader('📋 TradingViewウォッチリスト用')
        st.code(','.join(df_pass['ticker'].tolist()))
    else:
        st.warning('該当銘柄なし')

with tab_new:
    st.subheader('🆕 新規クリア・📤 脱落銘柄')
    if not os.path.exists(PASS_PATH):
        st.info('履歴データがまだありません。次回スキャンから表示されます。')
    else:
        ph = pd.read_csv(PASS_PATH)
        dates = sorted(ph['date'].unique())

        if len(dates) < 2:
            st.info('比較データがまだありません。2週分以上のデータが必要です。')
        else:
            this_week = dates[-1]
            last_week = dates[-2]

            this_set = set(ph[ph['date']==this_week]['ticker'])
            last_set = set(ph[ph['date']==last_week]['ticker'])

            new_tickers  = this_set - last_set
            out_tickers  = last_set - this_set
            cont_tickers = this_set & last_set

            c1, c2, c3 = st.columns(3)
            c1.metric('🆕 新規クリア', f'{len(new_tickers)}銘柄')
            c2.metric('✅ 継続', f'{len(cont_tickers)}銘柄')
            c3.metric('📤 脱落', f'{len(out_tickers)}銘柄')

            st.caption(f'比較: {this_week}（今週）vs {last_week}（先週）')

            # 新規クリア銘柄
            st.subheader(f'🆕 新規クリア: {len(new_tickers)}銘柄')
            if len(new_tickers) > 0:
                df_new = df[df['ticker'].isin(new_tickers)].reset_index(drop=True)
                df_new.index += 1
                st.dataframe(
                    df_new[cols_display].style
                    .map(color_score, subset=['score'])
                    .map(color_check, subset=[c for c in check_cols if c in df_new.columns]),
                    use_container_width=True, height=350
                )
                st.code(','.join(df_new['ticker'].tolist()))
            else:
                st.write('新規銘柄なし')

            # 脱落銘柄
            st.subheader(f'📤 脱落: {len(out_tickers)}銘柄')
            if len(out_tickers) > 0:
                # 先週のデータから情報を取得
                df_out = ph[(ph['date']==last_week) & (ph['ticker'].isin(out_tickers))].copy()
                df_out = df_out[['ticker','sector','industry','銘柄RS']].reset_index(drop=True)
                df_out.index += 1
                # 今週のスコアを追加
                df_out = df_out.merge(df[['ticker','score']], on='ticker', how='left')
                df_out['今週のスコア'] = df_out['score'].fillna('未スキャン')
                df_out = df_out.drop(columns=['score'])
                st.dataframe(df_out, use_container_width=True, height=350)
            else:
                st.write('脱落銘柄なし')

            # 継続銘柄
            with st.expander(f'✅ 継続: {len(cont_tickers)}銘柄'):
                if len(cont_tickers) > 0:
                    df_cont = df[df['ticker'].isin(cont_tickers)].reset_index(drop=True)
                    df_cont.index += 1
                    st.dataframe(
                        df_cont[cols_display].style
                        .map(color_score, subset=['score'])
                        .map(color_check, subset=[c for c in check_cols if c in df_cont.columns]),
                        use_container_width=True, height=400
                    )

with tab2:
    df_near = df[(df['score']>=4) & (~df['all_pass'])].reset_index(drop=True)
    df_near.index += 1
    st.subheader(f'🔶 スコア4以上: {len(df_near)}銘柄')
    if len(df_near) > 0:
        st.dataframe(
            df_near[cols_display].style
            .map(color_score, subset=['score'])
            .map(color_check, subset=[c for c in check_cols if c in df_near.columns]),
            use_container_width=True, height=500
        )
        st.subheader('📋 TradingViewウォッチリスト用')
        st.code(','.join(df_near['ticker'].tolist()))
    else:
        st.warning('該当銘柄なし')

with tab3:
    st.subheader('📂 セクター別表示')
    sectors  = sorted(df['sector'].dropna().unique().tolist())
    selected = st.selectbox('セクターを選択', ['全セクター'] + sectors)

    score_filter = st.selectbox('スコアで絞り込み', ['すべて', '5（全条件クリア）', '4のみ', '3のみ', '2以下'])

    if selected == '全セクター':
        df_sec = df.copy()
    else:
        df_sec = df[df['sector'] == selected].copy()

    if score_filter == '5（全条件クリア）':
        df_sec = df_sec[df_sec['score'] == 5]
    elif score_filter == '4のみ':
        df_sec = df_sec[df_sec['score'] == 4]
    elif score_filter == '3のみ':
        df_sec = df_sec[df_sec['score'] == 3]
    elif score_filter == '2以下':
        df_sec = df_sec[df_sec['score'] <= 2]

    df_sec = df_sec.reset_index(drop=True)
    df_sec.index += 1

    st.write(f'{len(df_sec)}銘柄')
    st.dataframe(
        df_sec[cols_display].style
        .map(color_score, subset=['score'])
        .map(color_check, subset=[c for c in check_cols if c in df_sec.columns]),
        use_container_width=True, height=500
    )
    if len(df_sec) > 0:
        st.subheader('📋 TradingViewウォッチリスト用')
        st.code(','.join(df_sec['ticker'].tolist()))

with tab4:
    st.subheader('📈 条件クリア銘柄数の推移')

    if not os.path.exists(HISTORY_PATH):
        st.info('履歴データがまだありません。')
    else:
        hist = pd.read_csv(HISTORY_PATH)
        hist['date'] = pd.to_datetime(hist['date'])
        hist = hist.sort_values('date')

        fig, ax = plt.subplots(figsize=(12, 4), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')
        ax.tick_params(colors='#aaaaaa', labelsize=9)
        ax.grid(True, alpha=0.12, color='#444444')
        for spine in ax.spines.values():
            spine.set_color('#2a2a2a')

        ax.plot(hist['date'], hist['all_pass'], color='#00ff88', linewidth=2.5,
                marker='o', markersize=5, label='全条件クリア')
        ax.plot(hist['date'], hist['score4plus'], color='#ffd93d', linewidth=2.0,
                marker='o', markersize=4, label='スコア4以上', linestyle='--')
        ax.set_title('条件クリア銘柄数の推移', color='white', fontsize=12, fontweight='bold')
        ax.set_ylabel('銘柄数', color='#aaaaaa')
        ax.legend(facecolor='#1a1a1a', labelcolor='white', fontsize=9)
        plt.xticks(rotation=30)
        plt.tight_layout()
        st.pyplot(fig)

        st.subheader('📂 セクター別クリア銘柄数の推移')
        sec_cols = [c for c in hist.columns if c.startswith('sec_')]

        if sec_cols:
            fig2, ax2 = plt.subplots(figsize=(12, 5), facecolor='#0d1117')
            ax2.set_facecolor('#0d1117')
            ax2.tick_params(colors='#aaaaaa', labelsize=9)
            ax2.grid(True, alpha=0.12, color='#444444')
            for spine in ax2.spines.values():
                spine.set_color('#2a2a2a')

            palette = ['#00ff88','#ff6b6b','#4ecdc4','#ffd93d','#a29bfe',
                       '#fd79a8','#74b9ff','#e17055','#55efc4','#fdcb6e','#b2bec3']

            for i, col in enumerate(sec_cols):
                label = col.replace('sec_', '')
                if hist[col].sum() > 0:
                    ax2.plot(hist['date'], hist[col].fillna(0),
                             color=palette[i % len(palette)],
                             linewidth=2.0, marker='o', markersize=4, label=label)

            ax2.set_title('セクター別 全条件クリア銘柄数の推移',
                          color='white', fontsize=12, fontweight='bold')
            ax2.set_ylabel('銘柄数', color='#aaaaaa')
            ax2.legend(facecolor='#1a1a1a', labelcolor='white', fontsize=8,
                       loc='upper left', ncol=2)
            plt.xticks(rotation=30)
            plt.tight_layout()
            st.pyplot(fig2)

        st.subheader('📊 週次サマリー（前週比）')
        disp = hist[['date','all_pass','score4plus','avg_rs']].copy()
        disp['date'] = disp['date'].dt.strftime('%Y-%m-%d')
        disp['前週比(クリア)'] = disp['all_pass'].diff().apply(
            lambda x: f'+{int(x)}' if x > 0 else (f'{int(x)}' if x < 0 else '－') if pd.notna(x) else '-'
        )
        disp = disp.rename(columns={
            'date'      : '日付',
            'all_pass'  : '全条件クリア',
            'score4plus': 'スコア4以上',
            'avg_rs'    : '平均RS',
        })
        st.dataframe(disp.iloc[::-1].reset_index(drop=True), use_container_width=True)

with tab5:
    st.subheader(f'📋 全銘柄: {len(df)}銘柄')
    score_filter2 = st.selectbox('スコアで絞り込み ', ['すべて', '5（全条件クリア）', '4のみ', '3のみ', '2以下'])
    if score_filter2 == '5（全条件クリア）':
        df_filtered = df[df['score'] == 5]
    elif score_filter2 == '4のみ':
        df_filtered = df[df['score'] == 4]
    elif score_filter2 == '3のみ':
        df_filtered = df[df['score'] == 3]
    elif score_filter2 == '2以下':
        df_filtered = df[df['score'] <= 2]
    else:
        df_filtered = df
    df_filtered = df_filtered.reset_index(drop=True)
    df_filtered.index += 1
    st.dataframe(
        df_filtered[cols_display].style
        .map(color_score, subset=['score'])
        .map(color_check, subset=[c for c in check_cols if c in df_filtered.columns]),
        use_container_width=True, height=600
    )

with tab6:
    st.subheader('📊 セクター別サマリー')
    sector_summary = (
        df.groupby('sector')
        .agg(
            総銘柄数      = ('ticker', 'count'),
            全条件クリア  = ('all_pass', 'sum'),
            スコア4以上   = ('score', lambda x: (x>=4).sum()),
            平均スコア    = ('score', 'mean'),
            平均RS        = ('銘柄RS', 'mean'),
        )
        .sort_values('全条件クリア', ascending=False)
        .round(3)
    )
    st.dataframe(sector_summary, use_container_width=True)

    if 'industry' in df.columns:
        st.subheader('📊 業種別サマリー（全条件クリアのみ）')
        industry_summary = (
            df[df['all_pass']].groupby('industry')
            .agg(
                全条件クリア = ('ticker', 'count'),
                平均RS       = ('銘柄RS', 'mean'),
            )
            .sort_values('全条件クリア', ascending=False)
            .round(3)
        )
        st.dataframe(industry_summary, use_container_width=True)

st.caption(f'最終更新: {pd.Timestamp.now().strftime("%Y/%m/%d %H:%M")}  |  データ: yfinance  |  対象: マネックス証券取扱銘柄')
