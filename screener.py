import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import warnings
import datetime
import os
warnings.filterwarnings('ignore')

# ============================================================
#  設定
# ============================================================
EMA_FAST       = 10
EMA_MID        = 20
EMA_SLOW       = 40
VOL_LOOKBACK   = 15
VOL_AVG_LEN    = 20
VOL_MULTIPLIER = 2.0
RS_LEN         = 52
BENCHMARK      = 'SPY'
ADV_LEN        = 20
ADV_MIN_MIL    = 5.0
HIGH52_PCT     = 20.0
PERIOD         = '3y'

# ============================================================
#  Russell 2000銘柄リスト取得
# ============================================================
def get_russell2000_tickers():
    url = 'https://www.ishares.com/us/products/239710/ISHARES-RUSSELL-2000-ETF/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        lines = r.text.splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith('Ticker,'))
        from io import StringIO
        df = pd.read_csv(StringIO('\n'.join(lines[start:])), on_bad_lines='skip')
        df = df[['Ticker', 'Name', 'Sector']].dropna()
        df = df[df['Ticker'].str.match(r'^[A-Z]{1,5}$')]
        df.columns = ['ticker', 'name', 'sector']
        if len(df) > 100:
            print(f'✅ {len(df)}銘柄取得')
            return df.reset_index(drop=True)
    except Exception as e:
        print(f'⚠️ 取得失敗: {e}')
    return pd.DataFrame(columns=['ticker','name','sector'])

# ============================================================
#  スクリーニング関数
# ============================================================
def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def screen_ticker(ticker, sector, spx_close):
    try:
        raw = yf.download(ticker, period=PERIOD, interval='1wk',
                          progress=False, auto_adjust=True)
        if raw is None or len(raw) < EMA_SLOW + 10:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        df = raw[['Close','High','Volume']].copy().dropna()
        if len(df) < EMA_SLOW + 5:
            return None

        close  = df['Close'].astype(float)
        high   = df['High'].astype(float)
        volume = df['Volume'].astype(float)

        # ① EMA
        ema_f = calc_ema(close, EMA_FAST)
        ema_m = calc_ema(close, EMA_MID)
        ema_s = calc_ema(close, EMA_SLOW)
        cond_ema = bool(ema_f.iloc[-1] > ema_m.iloc[-1] > ema_s.iloc[-1])

        # ② 出来高急増
        vol_avg     = volume.rolling(VOL_AVG_LEN).mean()
        recent_vols = volume.iloc[-VOL_LOOKBACK:].values
        recent_avgs = vol_avg.iloc[-VOL_LOOKBACK:].values
        cond_volume = bool(np.any(recent_vols >= recent_avgs * VOL_MULTIPLIER))
        vol_ratio   = float(volume.iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 0.0

        # ③ RS
        spx_al = spx_close.reindex(close.index, method='ffill').dropna()
        common = close.index.intersection(spx_al.index)
        if len(common) < RS_LEN + 2:
            return None
        stk_rs = float(close[common].iloc[-1] / close[common].iloc[-RS_LEN-1])
        spx_rs = float(spx_al[common].iloc[-1] / spx_al[common].iloc[-RS_LEN-1])
        cond_rs = bool(stk_rs > spx_rs)

        # ④ 平均売買代金
        dollar_vol     = close * volume
        avg_dollar_vol = float(dollar_vol.rolling(ADV_LEN).mean().iloc[-1])
        adv_mil        = avg_dollar_vol / 1000000.0
        cond_adv       = bool(adv_mil >= ADV_MIN_MIL)

        # ⑤ 52週高値圏
        high52        = float(high.iloc[-52:].max()) if len(high) >= 52 else float(high.max())
        current_close = float(close.iloc[-1])
        pct_from_high = (high52 - current_close) / high52 * 100
        cond_52wk     = bool(pct_from_high <= HIGH52_PCT)

        conds    = [cond_ema, cond_volume, cond_rs, cond_adv, cond_52wk]
        score    = sum(conds)
        all_pass = all(conds)

        return {
            'ticker'      : ticker,
            'sector'      : sector,
            'score'       : score,
            'all_pass'    : all_pass,
            '①EMA並び'    : '✅' if cond_ema    else '❌',
            '②出来高急増'  : '✅' if cond_volume else '❌',
            '③RS優位'     : '✅' if cond_rs     else '❌',
            '④売買代金'    : '✅' if cond_adv    else '❌',
            '⑤高値圏'     : '✅' if cond_52wk   else '❌',
            '現在値'       : round(current_close, 2),
            '52週高値'     : round(high52, 2),
            '高値乖離%'    : round(pct_from_high, 1),
            '出来高倍率'   : round(vol_ratio, 2),
            '売買代金(M$)' : round(adv_mil, 1),
            '銘柄RS'       : round(stk_rs, 3),
            'SPY_RS'       : round(spx_rs, 3),
        }
    except Exception:
        return None

# ============================================================
#  メイン実行
# ============================================================
if __name__ == '__main__':
    print('📥 SPY取得中...')
    spx_raw = yf.download(BENCHMARK, period=PERIOD, interval='1wk',
                          progress=False, auto_adjust=True)
    if isinstance(spx_raw.columns, pd.MultiIndex):
        spx_raw.columns = spx_raw.columns.get_level_values(0)
    spx_close = spx_raw['Close'].astype(float).dropna()

    print('📋 銘柄リスト取得中...')
    russell = get_russell2000_tickers()
    print(f'対象: {len(russell)}銘柄')

    results = []
    total   = len(russell)
    for idx, row in russell.iterrows():
        ticker = row['ticker']
        sector = row['sector']
        result = screen_ticker(ticker, sector, spx_close)
        if result:
            results.append(result)
        if (idx + 1) % 20 == 0:
            passed = sum(1 for r in results if r['all_pass'])
            print(f'  {idx+1}/{total} 完了 | クリア: {passed}銘柄')

    df = pd.DataFrame(results).sort_values(['score','銘柄RS'], ascending=[False,False])

    os.makedirs('data', exist_ok=True)
    df.to_csv('data/results.csv', index=False, encoding='utf-8-sig')

    today = datetime.date.today().strftime('%Y-%m-%d')
    with open('data/last_updated.txt', 'w') as f:
        f.write(today)

    print(f'✅ 完了！全条件クリア: {df["all_pass"].sum()}銘柄')
    print(f'   data/results.csv に保存しました')
