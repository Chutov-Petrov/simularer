from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'political_simulator_2024'


def init_db():
    conn = sqlite3.connect('political_game.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        experience INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        games_played INTEGER DEFAULT 0,
        best_score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        score INTEGER DEFAULT 0,
        economy INTEGER DEFAULT 50,
        social INTEGER DEFAULT 50,
        environment INTEGER DEFAULT 50,
        popularity INTEGER DEFAULT 50,
        budget INTEGER DEFAULT 50,
        turns INTEGER DEFAULT 0,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect('political_game.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# 40 игровых сценариев - ВСЕГДА используем "description" вместо "desc"
SCENARIOS = [
    # Экономические (8)
    {"id": 1, "title": "Экономический кризис", "description": "Безработица 15%, ВВП падает", "options": [
        {"text": "Снизить налоги для бизнеса", "effects": {"economy": 10, "social": -5, "budget": -15}},
        {"text": "Увеличить пособия", "effects": {"economy": -5, "social": 10, "budget": -10}},
        {"text": "Инвестировать в инфраструктуру", "effects": {"economy": 5, "popularity": 5, "budget": -20}}
    ]},
    {"id": 2, "title": "Инфляция 20%", "description": "Цены растут быстрее зарплат", "options": [
        {"text": "Повысить ключевую ставку", "effects": {"economy": -5, "budget": 5, "social": -10}},
        {"text": "Ввести ценовые ограничения", "effects": {"economy": -10, "social": 5, "popularity": 5}},
        {"text": "Увеличить соцвыплаты", "effects": {"social": 10, "budget": -20, "economy": -5}}
    ]},
    {"id": 3, "title": "Валютный кризис", "description": "Нацвалюта обесценилась на 30%", "options": [
        {"text": "Ввести валютные ограничения", "effects": {"economy": -10, "budget": 5, "popularity": -10}},
        {"text": "Продать резервы", "effects": {"economy": 5, "budget": -15, "popularity": -5}},
        {"text": "Обратиться к МВФ", "effects": {"budget": 10, "economy": -10, "popularity": -15}}
    ]},
    {"id": 4, "title": "Падение экспорта", "description": "Партнеры вводят санкции", "options": [
        {"text": "Найти новых партнеров", "effects": {"economy": -5, "social": -5, "popularity": 5}},
        {"text": "Развивать внутренний рынок", "effects": {"economy": 10, "social": 5, "budget": -10}},
        {"text": "Увеличить пошлины", "effects": {"budget": 10, "economy": -10, "popularity": -10}}
    ]},
    {"id": 5, "title": "Девальвация", "description": "Курс валюты резко падает", "options": [
        {"text": "Поддержать валюту", "effects": {"budget": -20, "economy": 5, "popularity": -5}},
        {"text": "Пустить на самотек", "effects": {"economy": -15, "social": -10, "popularity": -15}},
        {"text": "Деноминация", "effects": {"economy": -10, "popularity": -20, "social": -5}}
    ]},
    {"id": 6, "title": "Налоговая реформа", "description": "Нужно изменить налоговую систему", "options": [
        {"text": "Ввести прогрессивный налог", "effects": {"social": 15, "economy": -10, "popularity": 10}},
        {"text": "Упростить налоговую систему", "effects": {"economy": 10, "popularity": 5, "budget": -5}},
        {"text": "Повысить НДС", "effects": {"budget": 15, "popularity": -15, "social": -10}}
    ]},
    {"id": 7, "title": "Инвестиционный спад", "description": "Иностранные инвесторы уходят", "options": [
        {"text": "Создать налоговые каникулы", "effects": {"economy": 15, "budget": -20, "popularity": 5}},
        {"text": "Улучшить бизнес-климат", "effects": {"economy": 10, "popularity": 10, "budget": -10}},
        {"text": "Госинвестиции", "effects": {"economy": 5, "budget": -25, "social": 5}}
    ]},
    {"id": 8, "title": "Банковский кризис", "description": "Банки прекращают выдачу кредитов", "options": [
        {"text": "Санация банков", "effects": {"budget": -30, "economy": 10, "popularity": -10}},
        {"text": "Создать госбанк", "effects": {"economy": 5, "budget": -25, "social": 5}},
        {"text": "Пустить на банкротство", "effects": {"economy": -20, "social": -15, "popularity": -20}}
    ]},

    # Социальные (8)
    {"id": 9, "title": "Социальные протесты", "description": "Тысячи людей требуют реформ", "options": [
        {"text": "Пойти на диалог", "effects": {"social": 15, "popularity": 10, "economy": -5}},
        {"text": "Ужесточить меры", "effects": {"social": -15, "popularity": -20, "economy": 5}},
        {"text": "Предложить реформы", "effects": {"economy": -10, "social": 10, "budget": -15}}
    ]},
    {"id": 10, "title": "Забастовка врачей", "description": "Медики требуют повышения зарплат", "options": [
        {"text": "Повысить зарплаты", "effects": {"social": 20, "budget": -25, "popularity": 15}},
        {"text": "Найти компромисс", "effects": {"social": 10, "budget": -15, "popularity": 5}},
        {"text": "Применить силу", "effects": {"social": -20, "popularity": -25, "budget": 5}}
    ]},
    {"id": 11, "title": "Образовательный кризис", "description": "Школы не хватает учителей", "options": [
        {"text": "Повысить зарплаты учителям", "effects": {"social": 15, "budget": -20, "popularity": 10}},
        {"text": "Пригласить иностранных учителей", "effects": {"social": 10, "budget": -15, "popularity": 5}},
        {"text": "Увеличить нагрузку", "effects": {"social": -15, "popularity": -20, "budget": 10}}
    ]},
    {"id": 12, "title": "Пенсионная реформа", "description": "Пенсионный фонд в дефиците", "options": [
        {"text": "Повысить пенсионный возраст", "effects": {"budget": 20, "popularity": -30, "social": -20}},
        {"text": "Увеличить взносы", "effects": {"budget": 15, "economy": -10, "popularity": -15}},
        {"text": "Госдотации", "effects": {"social": 15, "budget": -25, "popularity": 10}}
    ]},
    {"id": 13, "title": "Миграционный кризис", "description": "В страну прибыли тысячи беженцев", "options": [
        {"text": "Принять беженцев", "effects": {"social": -10, "budget": -20, "popularity": -15}},
        {"text": "Закрыть границы", "effects": {"social": -15, "popularity": -20, "economy": -5}},
        {"text": "Создать лагеря", "effects": {"social": -5, "budget": -15, "popularity": -10}}
    ]},
    {"id": 14, "title": "Жилищный кризис", "description": "Очередь на жилье - 10 лет", "options": [
        {"text": "Строить социальное жилье", "effects": {"social": 20, "budget": -30, "popularity": 15}},
        {"text": "Ипотечные льготы", "effects": {"social": 10, "economy": 5, "budget": -20}},
        {"text": "Приватизировать жилье", "effects": {"budget": 15, "social": -10, "popularity": -15}}
    ]},
    {"id": 15, "title": "Эпидемия", "description": "Распространяется опасный вирус", "options": [
        {"text": "Ввести карантин", "effects": {"social": -10, "economy": -20, "popularity": -15}},
        {"text": "Массовая вакцинация", "effects": {"social": 15, "budget": -25, "popularity": 10}},
        {"text": "Ничего не делать", "effects": {"social": -25, "popularity": -30, "environment": -10}}
    ]},
    {"id": 16, "title": "Культурный конфликт", "description": "Разные группы требуют прав", "options": [
        {"text": "Пойти на уступки", "effects": {"social": 15, "popularity": 10, "budget": -10}},
        {"text": "Запретить дискуссию", "effects": {"social": -20, "popularity": -25, "budget": 5}},
        {"text": "Национальный диалог", "effects": {"social": 10, "popularity": 5, "budget": -5}}
    ]},

    # Экологические (8)
    {"id": 17, "title": "Экологическая катастрофа", "description": "Утечка нефти в заповеднике", "options": [
        {"text": "Мобилизовать все силы", "effects": {"environment": 15, "budget": -25, "popularity": 10}},
        {"text": "Экологический налог", "effects": {"environment": 5, "economy": -10, "budget": 10}},
        {"text": "Скрыть инцидент", "effects": {"popularity": -20, "economy": 5, "social": -10}}
    ]},
    {"id": 18, "title": "Загрязнение воздуха", "description": "Города в смоге, рост болезней", "options": [
        {"text": "Закрыть заводы", "effects": {"environment": 20, "economy": -25, "social": -10}},
        {"text": "Экологические стандарты", "effects": {"environment": 10, "economy": -15, "popularity": 5}},
        {"text": "Ничего не делать", "effects": {"environment": -20, "social": -15, "popularity": -20}}
    ]},
    {"id": 19, "title": "Дефицит воды", "description": "Реки мелеют, засуха", "options": [
        {"text": "Строить водохранилища", "effects": {"environment": -10, "budget": -20, "social": 5}},
        {"text": "Ввести нормирование", "effects": {"environment": 10, "popularity": -15, "social": -10}},
        {"text": "Опреснение морской воды", "effects": {"environment": 5, "budget": -30, "economy": -10}}
    ]},
    {"id": 20, "title": "Лесные пожары", "description": "Горят тысячи гектаров леса", "options": [
        {"text": "Мобилизовать армию", "effects": {"environment": 15, "budget": -20, "popularity": 10}},
        {"text": "Просить международную помощь", "effects": {"environment": 10, "popularity": -10, "budget": -5}},
        {"text": "Пустить на самотек", "effects": {"environment": -25, "popularity": -30, "social": -15}}
    ]},
    {"id": 21, "title": "Ядерные отходы", "description": "Некуда девать опасные отходы", "options": [
        {"text": "Строить хранилище", "effects": {"environment": -5, "budget": -25, "popularity": -20}},
        {"text": "Экспортировать отходы", "effects": {"environment": 10, "popularity": -25, "budget": 5}},
        {"text": "Перерабатывать на месте", "effects": {"environment": 15, "budget": -30, "economy": -10}}
    ]},
    {"id": 22, "title": "Изменение климата", "description": "Учащаются природные катаклизмы", "options": [
        {"text": "Инвестировать в зеленую энергетику", "effects": {"environment": 20, "budget": -25, "economy": -10}},
        {"text": "Международные соглашения", "effects": {"environment": 15, "popularity": 10, "economy": -5}},
        {"text": "Игнорировать проблему", "effects": {"environment": -25, "popularity": -20, "social": -15}}
    ]},
    {"id": 23, "title": "Вымирание видов", "description": "Исчезают редкие животные", "options": [
        {"text": "Создать заповедники", "effects": {"environment": 15, "budget": -15, "popularity": 5}},
        {"text": "Борьба с браконьерством", "effects": {"environment": 10, "budget": -10, "social": -5}},
        {"text": "Разрешить контролируемую охоту", "effects": {"environment": -10, "budget": 10, "popularity": -15}}
    ]},
    {"id": 24, "title": "Пластиковое загрязнение", "description": "Океаны заполнены пластиком", "options": [
        {"text": "Запретить пластик", "effects": {"environment": 20, "economy": -15, "popularity": -10}},
        {"text": "Переработка отходов", "effects": {"environment": 15, "budget": -20, "social": 5}},
        {"text": "Экспортировать отходы", "effects": {"environment": -15, "budget": 10, "popularity": -20}}
    ]},

    # Политические (8)
    {"id": 25, "title": "Международный конфликт", "description": "Соседнее государство предъявляет претензии", "options": [
        {"text": "Начать переговоры", "effects": {"popularity": 5, "economy": -5, "social": 5}},
        {"text": "Усилить военное присутствие", "effects": {"popularity": -10, "budget": -30, "social": -15}},
        {"text": "Обратиться в ООН", "effects": {"popularity": 15, "economy": -10, "environment": -5}}
    ]},
    {"id": 26, "title": "Коррупционный скандал", "description": "Министры замешаны в коррупции", "options": [
        {"text": "Уволить министров", "effects": {"popularity": 15, "economy": -10, "social": 5}},
        {"text": "Создать антикоррупционный комитет", "effects": {"popularity": 10, "budget": -15, "social": 10}},
        {"text": "Игнорировать скандал", "effects": {"popularity": -25, "social": -20, "budget": -10}}
    ]},
    {"id": 27, "title": "Выборы", "description": "Приближаются президентские выборы", "options": [
        {"text": "Начать предвыборную кампанию", "effects": {"popularity": 15, "budget": -20, "social": 5}},
        {"text": "Популистские обещания", "effects": {"popularity": 20, "budget": -25, "economy": -15}},
        {"text": "Игнорировать выборы", "effects": {"popularity": -30, "social": -15, "economy": -10}}
    ]},
    {"id": 28, "title": "Конституционный кризис", "description": "Парламент против президента", "options": [
        {"text": "Распустить парламент", "effects": {"popularity": -25, "social": -20, "budget": -15}},
        {"text": "Пойти на компромисс", "effects": {"popularity": 10, "social": 10, "economy": -5}},
        {"text": "Референдум", "effects": {"popularity": 15, "budget": -20, "social": 5}}
    ]},
    {"id": 29, "title": "Шпионский скандал", "description": "Обнаружены иностранные шпионы", "options": [
        {"text": "Выслать дипломатов", "effects": {"popularity": 10, "economy": -15, "social": -10}},
        {"text": "Тайные переговоры", "effects": {"popularity": -10, "budget": -10, "social": -5}},
        {"text": "Игнорировать", "effects": {"popularity": -20, "social": -15, "economy": -10}}
    ]},
    {"id": 30, "title": "Террористическая угроза", "description": "Террористы угрожают атаками", "options": [
        {"text": "Усилить безопасность", "effects": {"social": 10, "budget": -25, "popularity": 5}},
        {"text": "Переговоры", "effects": {"popularity": -15, "social": -10, "budget": -10}},
        {"text": "Военная операция", "effects": {"social": -20, "budget": -30, "popularity": -25}}
    ]},
    {"id": 31, "title": "Информационная война", "description": "Иностранные СМИ клевещут на страну", "options": [
        {"text": "Заблокировать иностранные СМИ", "effects": {"popularity": -20, "social": -15, "economy": -10}},
        {"text": "Создать контрпропаганду", "effects": {"popularity": 10, "budget": -15, "social": 5}},
        {"text": "Игнорировать", "effects": {"popularity": -15, "social": -10, "economy": -5}}
    ]},
    {"id": 32, "title": "Сепаратизм", "description": "Регион требует независимости", "options": [
        {"text": "Военное подавление", "effects": {"social": -30, "budget": -35, "popularity": -25}},
        {"text": "Переговоры об автономии", "effects": {"social": 10, "popularity": 5, "budget": -10}},
        {"text": "Экономические санкции", "effects": {"economy": -20, "social": -15, "popularity": -20}}
    ]},

    # Финансовые (8)
    {"id": 33, "title": "Бюджетный дефицит", "description": "Госдолг достиг критического уровня", "options": [
        {"text": "Урезать соцпрограммы", "effects": {"budget": 20, "social": -25, "popularity": -20}},
        {"text": "Повысить налоги", "effects": {"budget": 15, "economy": -15, "popularity": -10}},
        {"text": "Взять новый кредит", "effects": {"budget": -20, "economy": -5, "popularity": -15}}
    ]},
    {"id": 34, "title": "Дефолт", "description": "Нечем платить по внешним долгам", "options": [
        {"text": "Объявить дефолт", "effects": {"economy": -30, "popularity": -35, "social": -25}},
        {"text": "Реструктуризация долга", "effects": {"budget": -10, "economy": -15, "popularity": -20}},
        {"text": "Продать госимущество", "effects": {"budget": 25, "economy": -20, "popularity": -25}}
    ]},
    {"id": 35, "title": "Финансовые пирамиды", "description": "Мошенники обманули тысячи людей", "options": [
        {"text": "Компенсировать потери", "effects": {"social": 20, "budget": -30, "popularity": 15}},
        {"text": "Наказать организаторов", "effects": {"social": 10, "budget": -10, "popularity": 5}},
        {"text": "Пустить на самотек", "effects": {"social": -25, "popularity": -30, "economy": -15}}
    ]},
    {"id": 36, "title": "Налоговые недоимки", "description": "Крупные компании не платят налоги", "options": [
        {"text": "Жесткие меры", "effects": {"budget": 20, "economy": -15, "popularity": -10}},
        {"text": "Амнистия", "effects": {"budget": 10, "popularity": 5, "economy": -5}},
        {"text": "Переговоры", "effects": {"budget": 5, "economy": -10, "popularity": -5}}
    ]},
    {"id": 37, "title": "Спекуляции на рынке", "description": "Крупные игроки манипулируют ценами", "options": [
        {"text": "Ввести госрегулирование", "effects": {"economy": -10, "social": 10, "popularity": 5}},
        {"text": "Национализировать компании", "effects": {"budget": -25, "social": 15, "popularity": -10}},
        {"text": "Ничего не делать", "effects": {"economy": -20, "social": -15, "popularity": -20}}
    ]},
    {"id": 38, "title": "Криптовалютный бум", "description": "Граждане массово инвестируют в крипту", "options": [
        {"text": "Запретить криптовалюты", "effects": {"economy": -15, "popularity": -20, "social": -10}},
        {"text": "Регулировать рынок", "effects": {"budget": 10, "economy": 5, "popularity": -5}},
        {"text": "Создать госкриптовалюту", "effects": {"budget": -20, "economy": 10, "popularity": -10}}
    ]},
    {"id": 39, "title": "Фондовый крах", "description": "Биржевые индексы упали на 40%", "options": [
        {"text": "Выкупить акции", "effects": {"budget": -30, "economy": 10, "popularity": -15}},
        {"text": "Приостановить торги", "effects": {"economy": -20, "popularity": -25, "social": -15}},
        {"text": "Пустить на самотек", "effects": {"economy": -25, "social": -20, "popularity": -30}}
    ]},
    {"id": 40, "title": "Золотовалютные резервы", "description": "Резервы стремительно тают", "options": [
        {"text": "Продать золото", "effects": {"budget": 15, "popularity": -20, "economy": -10}},
        {"text": "Ввести ограничения", "effects": {"economy": -15, "social": -10, "popularity": -15}},
        {"text": "Просить помощи", "effects": {"budget": 10, "popularity": -25, "economy": -20}}
    ]}
]


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if len(username) < 3:
            return render_template('register.html', error="Имя должно быть минимум 3 символа")
        if len(password) < 6:
            return render_template('register.html', error="Пароль должен быть минимум 6 символов")

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            session['user_id'] = user_id
            session['username'] = username
            session['level'] = 1
            session['experience'] = 0

            return redirect('/dashboard')
        except:
            return render_template('register.html', error="Имя уже занято")
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                            (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['level'] = user['level']
            session['experience'] = user['experience']
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Неверный логин или пароль")

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    # Последние 5 игр
    games = conn.execute('''
        SELECT * FROM games 
        WHERE user_id = ? AND completed = 1 
        ORDER BY created_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()

    # Статистика
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_games,
            AVG(score) as avg_score,
            MAX(score) as best_score
        FROM games 
        WHERE user_id = ? AND completed = 1
    ''', (session['user_id'],)).fetchone()

    conn.close()

    return render_template('dashboard.html',
                           user=dict(user),
                           games=games,
                           stats=stats)


@app.route('/new_game')
def new_game():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()

    # Создаем новую игру
    conn.execute('''
        INSERT INTO games (user_id, economy, social, environment, popularity, budget)
        VALUES (?, 50, 50, 50, 50, 50)
    ''', (session['user_id'],))

    game_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    # Инициализируем игру
    session['current_game_id'] = game_id
    session['current_turn'] = 0
    session['used_scenarios'] = []
    session['game_stats'] = {'economy': 50, 'social': 50, 'environment': 50, 'popularity': 50, 'budget': 50}

    return redirect('/game')


@app.route('/game')
def game():
    if 'user_id' not in session:
        return redirect('/login')

    if 'current_game_id' not in session:
        return redirect('/new_game')

    current_turn = session.get('current_turn', 0)

    if current_turn >= 5:  # 5 ходов в игре
        return redirect('/game_result')

    # Выбираем случайный сценарий из неиспользованных
    used = session.get('used_scenarios', [])
    available = [s for s in SCENARIOS if s['id'] not in used]

    if not available:
        # Если все сценарии использованы, начинаем сначала
        available = SCENARIOS
        session['used_scenarios'] = []

    scenario = random.choice(available)
    session['used_scenarios'] = used + [scenario['id']]

    return render_template('game.html',
                           scenario=scenario,
                           turn=current_turn + 1,
                           stats=session.get('game_stats', {}))


@app.route('/make_decision', methods=['POST'])
def make_decision():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Войдите в систему'})

    data = request.json
    scenario_id = data.get('scenario_id')
    option_index = data.get('option_index')

    # Находим сценарий и вариант
    scenario = next((s for s in SCENARIOS if s['id'] == scenario_id), None)
    if not scenario or option_index < 0 or option_index >= 3:
        return jsonify({'success': False, 'message': 'Неверный выбор'})

    option = scenario['options'][option_index]

    # Применяем эффекты
    stats = session.get('game_stats', {})
    for stat, value in option['effects'].items():
        if stat in stats:
            stats[stat] = max(0, min(100, stats[stat] + value))

    session['game_stats'] = stats
    current_turn = session.get('current_turn', 0) + 1
    session['current_turn'] = current_turn

    # Проверяем завершение
    if current_turn >= 5:  # 5 ходов в игре
        save_game_result()
        return jsonify({
            'success': True,
            'game_completed': True,
            'stats': stats
        })

    return jsonify({
        'success': True,
        'game_completed': False,
        'stats': stats
    })


def save_game_result():
    stats = session.get('game_stats', {})

    # Расчет итогового счета
    total_score = sum(stats.values()) // 5

    conn = get_db()

    try:
        # Обновляем игру
        conn.execute('''
            UPDATE games 
            SET score = ?, 
                economy = ?, 
                social = ?, 
                environment = ?, 
                popularity = ?, 
                budget = ?,
                turns = ?,
                completed = 1
            WHERE id = ? AND user_id = ?
        ''', (
            total_score,
            stats.get('economy', 0),
            stats.get('social', 0),
            stats.get('environment', 0),
            stats.get('popularity', 0),
            stats.get('budget', 0),
            session.get('current_turn', 0),
            session['current_game_id'],
            session['user_id']
        ))

        # Получаем текущие данные пользователя
        user = conn.execute("SELECT experience, best_score FROM users WHERE id = ?",
                            (session['user_id'],)).fetchone()

        if user:
            current_experience = user['experience'] or 0
            current_best = user['best_score'] or 0

            # Добавляем опыт
            new_experience = current_experience + total_score

            # Обновляем лучший результат если нужно
            new_best = max(current_best, total_score)

            # Рассчитываем новый уровень (каждые 1000 опыта = 1 уровень)
            new_level = new_experience // 1000 + 1

            # Обновляем пользователя
            conn.execute('''
                UPDATE users 
                SET games_played = games_played + 1,
                    experience = ?,
                    best_score = ?,
                    level = ?
                WHERE id = ?
            ''', (new_experience, new_best, new_level, session['user_id']))

        conn.commit()

        # Обновляем данные в сессии
        if user:
            session['experience'] = new_experience
            session['level'] = new_level

    except Exception as e:
        conn.rollback()
        print(f"Ошибка при сохранении игры: {e}")
        raise
    finally:
        conn.close()


@app.route('/game_result')
def game_result():
    if 'user_id' not in session:
        return redirect('/login')

    game_id = session.get('current_game_id')

    conn = get_db()
    if game_id:
        game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    else:
        game = conn.execute('''
            SELECT * FROM games 
            WHERE user_id = ? AND completed = 1 
            ORDER BY created_at DESC LIMIT 1
        ''', (session['user_id'],)).fetchone()

    if not game:
        return redirect('/new_game')

    stats = {
        'economy': game['economy'],
        'social': game['social'],
        'environment': game['environment'],
        'popularity': game['popularity'],
        'budget': game['budget']
    }

    total_score = game['score']

    # Очищаем игровую сессию
    session.pop('current_game_id', None)
    session.pop('current_turn', None)
    session.pop('game_stats', None)
    session.pop('used_scenarios', None)

    conn.close()

    return render_template('game_result.html',
                           stats=stats,
                           total_score=total_score,
                           game_id=game['id'])


@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    games = conn.execute('''
        SELECT * FROM games 
        WHERE user_id = ? AND completed = 1 
        ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()

    conn.close()

    return render_template('history.html', games=games)


# УДАЛЕН маршрут /leaderboard

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)