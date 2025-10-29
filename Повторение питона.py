def analyze_text(text):
    length = len(text)
    words = len(text.split())
    count_a = text.lower().count('а')
    return f"Длина: {length}\nСлов: {words}\nБукв 'а': {count_a}"


def create_message(user, topic):
    return f"Привет, {user}! Сегодня мы изучаем {topic}."


def format_news(title, body):
    title = title.upper()
    body = body.replace("!", "🔥")
    if len(body) > 100:
        body = body[:100] + "..."
    return f"📢 {title}\n\n{body}"

print(analyze_text("Айжан учится в колледже"))
print(create_message("Айжан", "функции в Python"))
print(format_news("Важно!", "Сегодня стартует новый курс по программированию! Успей зарегистрироваться до конца недели!"))