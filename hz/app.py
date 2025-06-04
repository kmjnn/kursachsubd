from decimal import Decimal
from flask import Flask, render_template, redirect, request, flash, session, url_for
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
import bcrypt
from forms import LoginForm, RegistrationForm
from models import OrderContent, Orders, Product, User, Base
app = Flask(__name__)
app.secret_key = 'secret_key'

# Подключение к PostgreSQL
engine = create_engine('postgresql://postgres:0000@localhost/delivery_db')
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
Base.metadata.create_all(engine)

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data.encode('utf-8')  # Преобразовываем пароль в байты
        
        user = Session.query(User).filter_by(email=email).first()
        if user:
            # Преобразуем сохранённый хэшированный пароль в байты
            hashed_password = user.hashed_password.encode('utf-8')
            
            # Проверяем пароль
            if bcrypt.checkpw(password, hashed_password):
                session['logged_in'] = True
                session['user_id'] = user.id
                flash('Вы успешно вошли!', category='success')
                return redirect(url_for('index'))
            else:
                flash('Неверный e-mail или пароль.', category='danger')
        else:
            flash('Неверный e-mail или пароль.', category='danger')
    return render_template('login.html', form=form)


@app.route('/catalog')
def catalog():
    products = Session.query(Product).all()
    return render_template('catalog.html', products=products)

@app.route('/logout')
def logout():
    # Очищаем сессию пользователя
    session.pop('logged_in', None)
    session.pop('user_id', None)
    flash('Вы вышли из аккаунта.', category='info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            hashed_password=hashed_password.decode('utf-8'),
            role="client"
        )
        try:
            db_session = Session()
            db_session.add(new_user)
            db_session.commit()
            flash(f'Пользователь {new_user.username} зарегистрирован!', category='success')
            return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash('Ошибка регистрации пользователя.', category='danger')
    return render_template('register.html', form=form)

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    cart = session.get('cart', [])
    cart.append(product_id)
    session['cart'] = cart
    flash('Товар добавлен в корзину!', category='success')
    return redirect(url_for('catalog'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('logged_in'):
        flash('Войдите в аккаунт для оформления заказа.', category='warning')
        return redirect(url_for('login'))

    cart_items = []
    total_price = Decimal('0.00')

    if 'cart' in session:
        for item_id in session['cart']:
            product = Session.query(Product).get(item_id)
            if product:
                cart_items.append(product)
                total_price += product.price

    if request.method == 'POST':
        # Оформляем заказ
        order = Orders(
            courier_id=None,  # Курьера назначит администрация
            client_id=session['user_id'],
            order_cost=float(total_price),
            delivery_address=''  # Адрес доставки задаётся вручную клиентом
        )
        Session.add(order)
        Session.flush()  # Предварительно записываем ID заказа
        for product in cart_items:
            content = OrderContent(
                order_id=order.order_id,
                product_id=product.product_id
            )
            Session.add(content)
        Session.commit()
        del session['cart']
        flash('Ваш заказ принят!', category='success')
        return redirect(url_for('index'))

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)
@app.route('/orders')
def my_orders():
    if not session.get('logged_in'):
        flash('Войдите в аккаунт для просмотра заказов.', category='warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    orders = Session.query(Orders).filter_by(client_id=user_id).all()
    return render_template('orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)