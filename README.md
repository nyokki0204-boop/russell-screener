# ラッセル候補スクリーナー

毎週のスキャンは `.github/workflows/scan.yml` で実行し、結果を `data/` に保存します。

スマホ向け画面は `site/` の静的ページです。GitHub Pages を **GitHub Actions** ソースで有効にすると、`https://nyokki0204-boop.github.io/russell-screener/` から直接開けます。iPhoneではSafariの共有メニューから「ホーム画面に追加」できます。

`pages.yml` は画面の変更時と週次スキャン完了後に、保存済みCSVを含むサイトを配信します。画面での閲覧は株価APIを呼ばず、チャートデータも一括取得しません。元のStreamlit画面 `app.py` は引き続き利用できます。
