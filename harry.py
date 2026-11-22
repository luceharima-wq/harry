"""harry - ChatGPT と Claude を対話させて「最高の答え」を導くツール

流れ（質問ごと）:
  1. ChatGPT と Claude がそれぞれ独立に回答する
  2. お互いの回答を読み、批評・修正し合う（ラウンド数は設定可能）
  3. Claude が両者の議論をまとめ、最終回答を出す

会話は続けられるので、前の答えを踏まえた追加質問もできます。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import anthropic
import openai

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
CLAUDE_EFFORT = os.environ.get("CLAUDE_EFFORT", "high")
LOG_DIR = Path(__file__).parent / "logs"

SYSTEM = (
    "あなたは別のAIと協力して、ユーザーの質問に対する最も正確で役立つ答えを導くチームの一員です。"
    "日本語で、根拠を示しながら具体的に答えてください。不確かな点は不確かだと明言してください。"
)


class Harry:
    def __init__(self, rounds: int = 1) -> None:
        self.claude = anthropic.Anthropic()
        self.gpt = openai.OpenAI()
        self.rounds = rounds
        # 確定した Q&A の履歴（追加質問の文脈として両AIに渡す）
        self.history: list[dict[str, str]] = []
        self.log: list[dict] = []

    # ---- 各AIの呼び出し -------------------------------------------------
    def ask_claude(self, prompt: str) -> str:
        messages = [*self.history, {"role": "user", "content": prompt}]
        with self.claude.beta.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=64000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": CLAUDE_EFFORT},
            # 安全フィルタで断られた場合、自動で別モデルが続きを担当する
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            return "（Claude はこの質問への回答を控えました）"
        return "".join(b.text for b in msg.content if b.type == "text").strip()

    def ask_gpt(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM},
            *self.history,
            {"role": "user", "content": prompt},
        ]
        resp = self.gpt.chat.completions.create(model=OPENAI_MODEL, messages=messages)
        return (resp.choices[0].message.content or "").strip()

    # ---- 対話の流れ -----------------------------------------------------
    def solve(self, question: str) -> str:
        step("1/3 それぞれが回答中...")
        gpt_ans = self.ask_gpt(question)
        claude_ans = self.ask_claude(question)
        show("ChatGPT の初回回答", gpt_ans)
        show("Claude の初回回答", claude_ans)
        record = {"question": question, "rounds": [{"gpt": gpt_ans, "claude": claude_ans}]}

        for r in range(self.rounds):
            step(f"2/3 相互レビュー（ラウンド {r + 1}/{self.rounds}）...")
            gpt_new = self.ask_gpt(review_prompt(question, gpt_ans, claude_ans, "Claude"))
            claude_new = self.ask_claude(review_prompt(question, claude_ans, gpt_ans, "ChatGPT"))
            gpt_ans, claude_ans = gpt_new, claude_new
            show("ChatGPT の修正版", gpt_ans)
            show("Claude の修正版", claude_ans)
            record["rounds"].append({"gpt": gpt_ans, "claude": claude_ans})

        step("3/3 最終回答をまとめています...")
        final = self.ask_claude(
            f"質問:\n{question}\n\n"
            f"【ChatGPT の最終案】\n{gpt_ans}\n\n【Claude の最終案】\n{claude_ans}\n\n"
            "2つの案を比較し、正しい点・優れた点を統合して、ユーザーへの最終回答を1つ書いてください。"
            "両者の意見が分かれた点があれば、どちらがなぜ妥当かを短く添えてください。"
        )
        record["final"] = final
        self.log.append(record)
        self.history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": final},
        ]
        return final

    def save_log(self) -> Path | None:
        if not self.log:
            return None
        LOG_DIR.mkdir(exist_ok=True)
        path = LOG_DIR / f"{dt.datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps(self.log, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def review_prompt(question: str, mine: str, other: str, other_name: str) -> str:
    return (
        f"質問:\n{question}\n\n【あなたの回答】\n{mine}\n\n【{other_name} の回答】\n{other}\n\n"
        f"{other_name} の回答を批判的に読み、誤り・抜け・より良い点を指摘したうえで、"
        "取り入れるべき点を反映した、あなたの改善版の回答を書いてください。"
        "相手が間違っていると思う点は遠慮なく理由付きで指摘してください。"
    )


def step(text: str) -> None:
    print(f"\n\033[90m… {text}\033[0m", flush=True)


def show(title: str, body: str) -> None:
    if VERBOSE:
        print(f"\n\033[36m── {title} ──\033[0m\n{body}")


VERBOSE = True


def main() -> None:
    global VERBOSE
    p = argparse.ArgumentParser(description="ChatGPT と Claude を対話させて最高の答えを導く")
    p.add_argument("question", nargs="*", help="質問（省略すると対話モード）")
    p.add_argument("-r", "--rounds", type=int, default=1, help="相互レビューの回数（既定 1）")
    p.add_argument("-q", "--quiet", action="store_true", help="途中経過を表示せず最終回答のみ表示")
    args = p.parse_args()
    VERBOSE = not args.quiet

    missing = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(k)]
    if missing:
        print("APIキーが設定されていません: " + ", ".join(missing), file=sys.stderr)
        print("README.md の「準備」を見て設定してください。", file=sys.stderr)
        sys.exit(1)

    harry = Harry(rounds=args.rounds)
    try:
        if args.question:
            print_final(harry.solve(" ".join(args.question)))
        else:
            print("harry 対話モード（終了: exit または Ctrl+C）")
            while True:
                q = input("\nあなた > ").strip()
                if q.lower() in {"exit", "quit", "終了"}:
                    break
                if q:
                    print_final(harry.solve(q))
    except (KeyboardInterrupt, EOFError):
        print()
    except (openai.APIError, anthropic.APIError) as e:
        print(f"\nAPI エラー: {e}", file=sys.stderr)
    finally:
        if path := harry.save_log():
            print(f"\n記録を保存しました: {path}")


def print_final(text: str) -> None:
    print(f"\n\033[1;32m══ 最終回答 ══\033[0m\n{text}")


if __name__ == "__main__":
    main()
