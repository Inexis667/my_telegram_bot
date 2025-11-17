import os
import json

STATS_FILE = "stats.json"
stats = {}


def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats = json.load(f)
            print(f"✅ Статистика загружена: {len(stats)} пользователей")
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            stats = {}
    else:
        print("📊 Создаем новую статистику")
        stats = {}


def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")


def update_stats(user_id, command):
    user_id = str(user_id)

    print(f"📊 Обновление: user={user_id}, command={command}")

    if user_id not in stats:
        stats[user_id] = {"messages": 0, "commands": {}}

    stats[user_id]["messages"] += 1
    stats[user_id]["commands"][command] = stats[user_id]["commands"].get(command, 0) + 1

    print(f"📈 Результат: {stats[user_id]}")
    save_stats()


def get_user_stats(user_id):
    user_id = str(user_id)
    return stats.get(user_id, {"messages": 0, "commands": {}})


load_stats()