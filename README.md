# WEAREMS AI NEWS

Google & Anthropic/Claude 最新AIニュースキュレーション PWA

## Features
- Google / Gemini / DeepMind ニュースの自動取得
- Anthropic / Claude ニュースの自動取得
- 毎日 12:00 / 20:00 (JST) に自動更新
- PWA対応（ホーム画面に追加可能）
- プレミアムダークテーマUI

## Tech Stack
- Vanilla HTML/CSS/JS (PWA)
- Python (RSS feed fetcher)
- GitHub Actions (cron scheduler)
- GitHub Pages (hosting)

## Auto-Update
GitHub Actionsが毎日2回（JST 12:00 / 20:00）にニュースRSSフィードを取得し、
`data/news.json` を自動更新します。

## License
Private — WEAREMS / SAT
