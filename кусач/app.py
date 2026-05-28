from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from flask import flash, request
from models import db, User, Tour, Booking

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на свой секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.before_request
def create_tables():
    db.create_all()
    # Вручную добавьте администратора, если его еще нет
    # Пример:
    #
    #if not User.query.filter_by(username='admin').first():
    ###   admin.set_password('admin')
       #  db.session.add(admin)
        # db.session.commit()

# Декоратор для проверки входа
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки роли администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            return "Доступ запрещен", 403
        return f(*args, **kwargs)
    return decorated_function

# Главная страница со списком туров
@app.route('/')
@login_required
def index():
    print('Session:', session)
    tours = Tour.query.all()
    bookings = Booking.query.all()
    users = User.query.all()
    return render_template('index.html', tours=tours, bookings=bookings, users=users,  username=session.get('username'))


@app.route('/tours')
def tours():
    # Получаем все туры из базы
    all_tours = Tour.query.all()
    return render_template('tours.html', tours=all_tours)

@app.route('/book/<int:tour_id>', methods=['POST'])
@login_required
def book_tour(tour_id):
    from datetime import date
    new_booking = Booking(user_id=session['user_id'], tour_id=tour_id, booking_date=date.today())
    db.session.add(new_booking)
    db.session.commit()
    flash('Бронирование успешно!')
    return redirect(request.referrer or url_for('index'))

# Редактировать бронирование
@app.route('/booking/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_booking(id):
    booking = Booking.query.get_or_404(id)
    if request.method == 'POST':
        # Обновляем данные
        user_id = request.form['user_id']
        tour_id = request.form['tour_id']
        booking_date_str = request.form['booking_date']
        from datetime import datetime
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()

        booking.user_id = user_id
        booking.tour_id = tour_id
        booking.booking_date = booking_date
        db.session.commit()
        return redirect(url_for('index'))
    users = User.query.all()
    tours = Tour.query.all()
    return render_template('edit_booking.html', booking=booking, users=users, tours=tours)

# Удаление бронирования
@app.route('/booking/delete/<int:id>')
@login_required
@admin_required
def delete_booking(id):
    booking = Booking.query.get_or_404(id)
    db.session.delete(booking)
    db.session.commit()
    return redirect(url_for('index'))

# Редактировать пользователя
@app.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']
        user.username = username
        user.email = email
        user.role = role
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_user.html', user=user)

# Удаление пользователя
@app.route('/user/delete/<int:id>')
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('index'))

# Регистрация нового пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            error = 'Пользователь с таким именем уже существует'
            return render_template('register.html', error=error)
        user = User(username=username, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            # Перенаправление по роли
            if user.role == 'admin':
                return redirect(url_for('index'))  # исправлено
            else:
                return redirect(url_for('tours'))
        else:
            error = 'Неверное имя пользователя или пароль'
            return render_template('login.html', error=error)
    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Добавление тура
@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tour():
    if request.method == 'POST':
        destination = request.form['destination']
        price = float(request.form['price'])
        duration = request.form['duration']
        description = request.form['description']
        new_tour = Tour(destination=destination, price=price, duration=duration, description=description)
        db.session.add(new_tour)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_tour.html')

# Редактирование тура (только для админа)
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_tour(id):
    tour = Tour.query.get_or_404(id)
    if request.method == 'POST':
        tour.destination = request.form['destination']
        tour.price = float(request.form['price'])
        tour.duration = request.form['duration']
        tour.description = request.form['description']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_tour.html', tour=tour)

# Удаление тура (только для админа)
@app.route('/delete/<int:id>')
@login_required
@admin_required
def delete_tour(id):
    tour = Tour.query.get_or_404(id)
    db.session.delete(tour)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)