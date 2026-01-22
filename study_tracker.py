from datetime import datetime

def ask_int(prompt: str, min_value: int = 0, max_value: int = 24) -> int:
    """整数入力を安全に受け取る（範囲チェック付き）"""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("数字で入力してください（例：2）")
            continue

        if value < min_value or value > max_value:
            print(f"{min_value}〜{max_value}の範囲で入力してください")
            continue

        return value

def comment_for(hours: int) -> str:
    """学習時間に応じたコメントを返す"""
    if hours >= 3:
        return "すごすぎる！今日はもう休んでよし！"
    if hours >= 2:
        return "お疲れ！積み重ねていけてるよ！"
    if hours >= 1:
        return "今日も動けてえらい！一歩一歩が大事！"
    return "0分でもOK。環境を開いたなら前進。"

def main() -> None:
    print("=== Study Tracker ===")

    name = input("名前: ").strip() or "NoName"
    hours = ask_int("今日の学習時間(0-24): ", 0, 24)

    tasks = []
    print("タスクを入力（空Enterで終了）:")
    while True:
        t = input(" - ").strip()
        if t == "":
            break
        tasks.append(t)

    today = datetime.now().strftime("%Y-%m-%d")
    print("\n--- 結果 ---")
    print(f"日付: {today}")
    print(f"名前: {name}")
    print(f"学習時間: {hours}時間")
    print(f"コメント: {comment_for(hours)}")

    if tasks:
        print("タスク:")
        for i, t in enumerate(tasks, start=1):
            print(f"  {i}. {t}")
    else:
        print("タスク: なし")

if __name__ == "__main__":
    main()
