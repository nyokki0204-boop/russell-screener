import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import datetime
import os
warnings.filterwarnings('ignore')

EMA_FAST        = 10
EMA_MID         = 20
EMA_SLOW        = 40
VOL_LOOKBACK    = 15
VOL_AVG_LEN     = 20
VOL_MULTIPLIER  = 2.0
RS_LEN          = 52
BENCHMARK       = 'SPY'
ADV_LEN         = 20
ADV_MIN_MIL     = 10.0
RS_MULTIPLIER   = 1.1
HIGH52_PCT_MIN  = 10.0
HIGH52_PCT_MAX  = 30.0
PERIOD          = '3y'

def get_monex_tickers():
    try:
        for enc in ['shift_jis', 'cp932', 'utf-8']:
            try:
                df = pd.read_csv(
                    'Monex_US_LIST.csv',
                    header=None,
                    skiprows=1,
                    encoding=enc,
                    on_bad_lines='skip'
                )
                tickers = df[0].dropna().astype(str).str.strip()
                tickers = tickers[tickers.str.match(r'^[A-Z]{1,5}$')]
                if len(tickers) > 100:
                    print(f'読み込み成功({enc}): {len(tickers)}銘柄')
                    return tickers.tolist()
            except Exception as e:
                print(f'{enc}失敗: {e}')
                continue
        return []
    except Exception as e:
        print(f'CSV読み込み失敗: {e}')
        return []

def get_sector(ticker):
    try:
        info     = yf.Ticker(ticker).info
        sector   = info.get('sector', 'その他') or 'その他'
        industry = info.get('industry', '') or ''
        return sector, industry
    except Exception:
        return 'その他', ''

def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def screen_ticker(ticker, spx_close, sector_cache=None):
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

        ema_f    = calc_ema(close, EMA_FAST)
        ema_m    = calc_ema(close, EMA_MID)
        ema_s    = calc_ema(close, EMA_SLOW)
        cond_ema = bool(ema_f.iloc[-1] > ema_m.iloc[-1] > ema_s.iloc[-1])

        vol_avg     = volume.rolling(VOL_AVG_LEN).mean()
        recent_vols = volume.iloc[-VOL_LOOKBACK:].values
        recent_avgs = vol_avg.iloc[-VOL_LOOKBACK:].values
        cond_volume = bool(np.any(recent_vols >= recent_avgs * VOL_MULTIPLIER))
        vol_ratio   = float(volume.iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 0.0

        spx_al = spx_close.reindex(close.index, method='ffill').dropna()
        common = close.index.intersection(spx_al.index)
        if len(common) < RS_LEN + 2:
            return None
        stk_rs  = float(close[common].iloc[-1] / close[common].iloc[-RS_LEN-1])
        spx_rs  = float(spx_al[common].iloc[-1] / spx_al[common].iloc[-RS_LEN-1])
        cond_rs = bool(stk_rs > spx_rs * RS_MULTIPLIER)

        dollar_vol     = close * volume
        avg_dollar_vol = float(dollar_vol.rolling(ADV_LEN).mean().iloc[-1])
        adv_mil        = avg_dollar_vol / 1000000.0
        cond_adv       = bool(adv_mil >= ADV_MIN_MIL)

        high52        = float(high.iloc[-52:].max()) if len(high) >= 52 else float(high.max())
        current_close = float(close.iloc[-1])
        pct_from_high = (high52 - current_close) / high52 * 100
        cond_52wk     = bool(HIGH52_PCT_MIN <= pct_from_high <= HIGH52_PCT_MAX)

        conds    = [cond_ema, cond_volume, cond_rs, cond_adv, cond_52wk]
        score    = sum(conds)
        all_pass = all(conds)

        if sector_cache is not None and ticker in sector_cache.index:
            sector   = sector_cache.loc[ticker, 'sector']
            industry = sector_cache.loc[ticker, 'industry']
        else:
            sector, industry = get_sector(ticker)

        return {
            'ticker'        : ticker,
            'sector'        : sector,
            'industry'      : industry,
            'score'         : score,
            'all_pass'      : all_pass,
            '①EMA並び'      : '✅' if cond_ema    else '❌',
            '②出来高急増'    : '✅' if cond_volume else '❌',
            '③RS優位'       : '✅' if cond_rs     else '❌',
            '④売買代金'      : '✅' if cond_adv    else '❌',
            '⑤高値圏10-30%' : '✅' if cond_52wk   else '❌',
            '現在値'         : round(current_close, 2),
            '52週高値'       : round(high52, 2),
            '高値乖離%'      : round(pct_from_high, 1),
            '出来高倍率'     : round(vol_ratio, 2),
            '売買代金(M$)'   : round(adv_mil, 1),
            '銘柄RS'         : round(stk_rs, 3),
            'SPY_RS'         : round(spx_rs, 3),
            'RS倍率'         : round(stk_rs / spx_rs, 3) if spx_rs > 0 else 0,
        }
    except Exception as e:
        print(f'{ticker} error: {e}')
        return None

def save_history(df, today):
    history_path = 'data/history.csv'
    total    = len(df)
    all_pass = int(df['all_pass'].sum())
    score4   = int((df['score'] >= 4).sum())
    avg_rs   = round(float(df['銘柄RS'].mean()), 3)

    sector_counts = df[df['all_pass']].groupby('sector')['ticker'].count().to_dict()

    row = {
        'date'      : today,
        'total'     : total,
        'all_pass'  : all_pass,
        'score4plus': score4,
        'avg_rs'    : avg_rs,
    }
    for sec, cnt in sector_counts.items():
        col = f'sec_{sec[:15]}'
        row[col] = cnt

    new_row = pd.DataFrame([row])

    if os.path.exists(history_path):
        history = pd.read_csv(history_path)
        history = history[history['date'] != today]
        history = pd.concat([history, new_row], ignore_index=True)
    else:
        history = new_row

    history = history.sort_values('date')
    history.to_csv(history_path, index=False, encoding='utf-8-sig')
    print(f'履歴保存完了: {len(history)}週分')

def save_pass_history(df, today):
    pass_path = 'data/pass_history.csv'
    df_pass = df[df['all_pass']][['ticker','sector','industry','銘柄RS','RS倍率','高値乖離%']].copy()
    df_pass['date'] = today
    df_pass = df_pass[['date','ticker','sector','industry','銘柄RS','RS倍率','高値乖離%']]

    if os.path.exists(pass_path):
        old = pd.read_csv(pass_path)
        old = old[old['date'] != today]
        all_data = pd.concat([old, df_pass], ignore_index=True)
    else:
        all_data = df_pass

    all_data.to_csv(pass_path, index=False, encoding='utf-8-sig')
    print(f'クリア銘柄履歴保存: {len(df_pass)}銘柄 / 累計{len(all_data)}行')

if __name__ == '__main__':
    print('SPY取得中...')
    spx_raw = yf.download(BENCHMARK, period=PERIOD, interval='1wk',
                          progress=False, auto_adjust=True)
    if isinstance(spx_raw.columns, pd.MultiIndex):
        spx_raw.columns = spx_raw.columns.get_level_values(0)
    spx_close = spx_raw['Close'].astype(float).dropna()

    sector_cache = None
    if os.path.exists('data/sector_cache.csv'):
        sector_cache = pd.read_csv('data/sector_cache.csv').set_index('ticker')
        print(f'セクターキャッシュ読み込み: {len(sector_cache)}銘柄')
    elif os.path.exists('sector_cache.csv'):
        sector_cache = pd.read_csv('sector_cache.csv').set_index('ticker')
        print(f'セクターキャッシュ読み込み: {len(sector_cache)}銘柄')
    else:
        print('セクターキャッシュなし→都度取得')

    print('マネックス銘柄リスト読み込み中...')
    tickers = get_monex_tickers()

    if len(tickers) == 0:
        print('銘柄リスト取得失敗')
        exit(1)

    print(f'{len(tickers)}銘柄をスキャン中...')
    results = []
    for idx, ticker in enumerate(tickers, 1):
        result = screen_ticker(ticker, spx_close, sector_cache)
        if result:
            results.append(result)
        if idx % 100 == 0:
            passed = sum(1 for r in results if r['all_pass'])
            print(f'{idx}/{len(tickers)} 完了 | クリア: {passed}銘柄')

    if len(results) == 0:
        print('結果が0件')
        exit(1)

    df = pd.DataFrame(results).sort_values(['score','銘柄RS'], ascending=[False,False])
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/results.csv', index=False, encoding='utf-8-sig')

    today = datetime.date.today().strftime('%Y-%m-%d')
    with open('data/last_updated.txt', 'w') as f:
        f.write(today)

    save_history(df, today)
    save_pass_history(df, today)
    print(f'完了！全条件クリア: {df["all_pass"].sum()}銘柄')
