"""ChatGPT に1回質問して答えを表示する小さなツール。

Claude Code（このチャットの Claude）が ChatGPT と議論するときに使う。
  python ask_gpt.py "質問"                 # 単発
  python ask_gpt.py -t topic "質問"        # 会話を threads/topic.json に保存して続ける
  echo "長い質問" | python ask_gpt.py -t topic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import openai

MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.2-sol")
THREADS = Path(__file__).parent / "threads"
SYSTEM = (
    "あなたは Claude と協力・議論して、ユーザーの質問に対する最も正確で役立つ答えを導く役です。"
    "日本語で、根拠を示して具体的に答えてください。相手の意見に誤りがあれば遠慮なく理由付きで指摘し、"
    "不確かな点は不確かだと明言してください。"
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("prompt", nargs="*")
    p.add_argument("-t", "--thread", help="会話を続けるためのスレッド名")
    args = p.parse_args()
    prompt = " ".join(args.prompt) or sys.stdin.read()
    if not prompt.strip():
        sys.exit("質問が空です")

    path = THREADS / f"{args.thread}.json" if args.thread else None
    history = json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else []

    # クラウド環境では本物のキーは通信時にプロキシが差し込むので、仮の値で足りる
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or "proxy-injected")
    messages = [{"role": "system", "content": SYSTEM}, *history, {"role": "user", "content": prompt}]
    resp = client.chat.completions.create(model=MODEL, messages=messages)
    answer = (resp.choices[0].message.content or "").strip()
    print(answer)

    if path:
        THREADS.mkdir(exist_ok=True)
        history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}]
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
