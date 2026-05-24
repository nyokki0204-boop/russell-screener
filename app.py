import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
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

if not os.path.exists(DATA_PATH):
    st.warning('⚠️ まだスキャン結果がありません。')
    st.info('GitHub Actionsが毎週土曜日に自動スキャンします。')
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

# ============================================================
#  列名の確認（高値条件の列名が変わっている場合に対応）
# ============================================================
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    '🚀 全条件クリア',
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
        st.subheader('📋 TradingViewウォッチリスト用（4以上）')
        st.code(','.join(df_near['ticker'].tolist()))
    else:
        st.warning('該当銘柄なし')

with tab3:
    st.subheader('📂 セクター別表示')
    sectors  = sorted(df['sector'].dropna().unique().tolist())
    selected = st.selectbox('セクターを選択', ['全セクター'] + sectors)
    score_min = st.slider('最低スコア', 0, 5, 3)

    df_sec = df[df['score'] >= score_min] if selected == '全セクター' \
             else df[(df['sector'] == selected) & (df['score'] >= score_min)]
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
        st.info('履歴データがまだありません。スキャンを重ねると表示されます。')
    else:
        hist = pd.read_csv(HISTORY_PATH)
        hist['date'] = pd.to_datetime(hist['date'])
        hist = hist.sort_values('date')

        # ── 全体推移グラフ ──────────────────────────────
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

        # ── セクター別推移 ──────────────────────────────
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

        # ── 前週比テーブル ──────────────────────────────
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
        st.dataframe(disp.iloc[::-1].reset_index(drop=True),
                     use_container_width=True)

with tab5:
    st.subheader(f'📋 全銘柄: {len(df)}銘柄')
    score_filter = st.slider('最低スコア ', 0, 5, 0)
    df_filtered = df[df['score'] >= score_filter].reset_index(drop=True)
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
