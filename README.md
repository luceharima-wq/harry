# harry

ChatGPT と Claude を**対話・議論させて**、質問に対する最高の答えを導くツールです。

## しくみ

1. ChatGPT と Claude がそれぞれ独立に回答
2. 互いの回答を読んで批評し、自分の回答を改善（相互レビュー）
3. Claude が両者の最終案を統合して、1つの最終回答を出す

追加質問をすると、前の答えを踏まえて続けて議論します。やり取りは `logs/` に JSON で保存されます。

## 準備

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="..."      # https://platform.openai.com/api-keys
export ANTHROPIC_API_KEY="..."   # https://console.anthropic.com/
```

※ ChatGPT Plus などの月額プランとは別に、API の利用料（従量課金）がかかります。

## 使い方

```bash
python harry.py                          # 対話モード（続けて何度も質問できる）
python harry.py "副業で月5万円稼ぐ現実的な方法は？"   # 1回だけ質問
python harry.py -r 2 "..."               # 相互レビューを2往復（より慎重に）
python harry.py -q "..."                 # 途中経過を隠して最終回答だけ表示
```

## 設定（環境変数・任意）

| 変数 | 既定値 | 内容 |
|---|---|---|
| `OPENAI_MODEL` | `gpt-5` | 使う ChatGPT のモデル |
| `CLAUDE_MODEL` | `claude-opus-5-5` | 使う Claude のモデル |
| `CLAUDE_EFFORT` | `high` | Claude の思考の深さ（`low`〜`max`） |
