import datetime
from decimal import Decimal
from flask import Flask, render_template, redirect, request, flash, session, url_for
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
import bcrypt
from forms import AdminUserForm, LoginForm, RegistrationForm
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


@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    users = Session.query(User).all()
    product = Session.query(Product).all()
    orders = Session.query(Orders).all()
    
    return render_template('admin_dashboard.html', 
                         users=users, 
                         product=product, 
                         orders=orders)

@app.route('/courier/orders')
def courier_orders():
    if not session.get('logged_in') or session.get('user_role') != 'courier':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    db_session = Session()
    try:
        courier_id = session['user_id']
        print(f"DEBUG: Checking orders for courier {courier_id}")
        
        # Активные заказы (включая pending)
        active_orders = db_session.query(Orders).filter(
            Orders.courier_id == courier_id,
            Orders.status.in_(['pending', 'assigned', 'in_progress'])  # Добавлено 'pending'
        ).order_by(Orders.created_at.desc()).all()
        
        print(f"DEBUG: Active orders count: {len(active_orders)}")
        
        # Завершенные заказы
        completed_orders = db_session.query(Orders).filter(
            Orders.courier_id == courier_id,
            Orders.status == 'completed'
        ).order_by(Orders.created_at.desc()).limit(10).all()
        
        # Подготовка данных
        def prepare_orders(orders):
            result = []
            for order in orders:
                client = db_session.query(User).get(order.client_id)
                contents = db_session.query(OrderContent).filter_by(
                    order_id=order.order_id
                ).all()
                
                products = []
                for content in contents:
                    product = db_session.query(Product).get(content.product_id)
                    if product:
                        products.append({
                            'name': product.product_name,
                            'quantity': content.quantity,
                            'price': float(product.price)
                        })
                
                result.append({
                    'order_id': order.order_id,
                    'client': client.username if client else 'Неизвестен',
                    'address': order.delivery_address,
                    'cost': float(order.order_cost),
                    'status': order.status,
                    'created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
                    'products': products
                })
            return result
        
        return render_template('courier_orders.html',
                            active_orders=prepare_orders(active_orders),
                            completed_orders=prepare_orders(completed_orders))
    
    except Exception as e:
        print(f"Ошибка при загрузке заказов курьера: {e}")
        flash('Ошибка при загрузке заказов', 'danger')
        return redirect(url_for('index'))
    finally:
        db_session.close()
    
@app.route('/courier/order/<int:order_id>/start')
def start_delivery(order_id):
    if not session.get('logged_in') or session.get('user_role') != 'courier':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    try:
        order = Session.query(Orders).filter_by(  # Исправлено на Orders
            order_id=order_id,
            courier_id=session['user_id']
        ).first()
        
        if not order:
            flash('Заказ не найден или не назначен вам', 'danger')
            return redirect(url_for('courier_orders'))
        
        order.status = 'in_progress'
        Session.commit()
        flash('Заказ взят в работу', 'success')
    
    except Exception as e:
        Session.rollback()
        print(f"Ошибка при старте доставки: {e}")
        flash('Ошибка при обновлении статуса', 'danger')
    
    return redirect(url_for('courier_orders'))

@app.route('/courier/order/<int:order_id>/complete')
def complete_delivery(order_id):
    if not session.get('logged_in') or session.get('user_role') != 'courier':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))

    db_session = Session()
    try:
        order = db_session.query(Orders).filter_by(
            order_id=order_id,
            courier_id=session['user_id']
        ).first()
        
        if not order:
            flash('Заказ не найден или не назначен вам', 'danger')
            return redirect(url_for('courier_orders'))
        
        order.status = 'completed'
        order.completed_at = datetime.datetime.utcnow()
        db_session.commit()
        flash('Заказ успешно завершен', 'success')
    except Exception as e:
        db_session.rollback()
        print(f"Ошибка при завершении заказа: {e}")
        flash('Ошибка при обновлении статуса', 'danger')
    finally:
        db_session.close()
    
    return redirect(url_for('courier_orders'))

@app.route('/catalog')
def catalog():
    product = Session.query(Product).all()
    return render_template('catalog.html', product=product)

@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    if not session.get('logged_in'):
        flash('Войдите в систему для управления корзиной', 'warning')
        return redirect(url_for('login'))
    
    if 'cart' not in session:
        return redirect(url_for('view_cart'))
    
    cart = session['cart']
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
        flash('Товар удалён из корзины', 'info')
    
    return redirect(url_for('view_cart'))

@app.route('/clear-cart')
def clear_cart():
    if 'cart' in session:
        session.pop('cart')
        flash('Корзина очищена', 'info')
    return redirect(url_for('view_cart'))

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
        # Проверяем, нет ли уже пользователя с таким email
        existing_user = Session.query(User).filter_by(email=form.email.data).first()
        if existing_user:
            flash('Пользователь с таким email уже существует', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role='client'  # По умолчанию все новые пользователи - клиенты
        )
        new_user.set_password(form.password.data)
        
        try:
            Session.add(new_user)
            Session.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            Session.rollback()
            flash('Ошибка при регистрации пользователя', 'danger')
            print(f"Ошибка регистрации: {e}")
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Session.query(User).filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['username'] = user.username
            
            flash('Вы успешно вошли в систему!', 'success')
            
            # Перенаправляем в зависимости от роли
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'courier':
                return redirect(url_for('courier_orders'))
            else:
                return redirect(url_for('catalog'))
        else:
            flash('Неверный email или пароль', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if not session.get('logged_in'):
        flash('Войдите в систему, чтобы добавлять товары в корзину', 'warning')
        return redirect(url_for('login'))
    
    # Получаем информацию о товаре
    product = Session.query(Product).get(product_id)
    if not product:
        flash('Товар не найден', 'danger')
        return redirect(url_for('catalog'))
    
    # Инициализируем корзину в сессии, если её нет
    if 'cart' not in session:
        session['cart'] = {}
    
    # Добавляем товар в корзину или увеличиваем количество
    cart = session['cart']
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    
    flash(f'Товар "{product.product_name}" добавлен в корзину', 'success')
    return redirect(url_for('catalog'))

@app.route('/cart')
def view_cart():
    if not session.get('logged_in'):
        flash('Войдите в систему, чтобы просматривать корзину', 'warning')
        return redirect(url_for('login'))
    
    cart_items = []
    total_price = 0.0
    
    if 'cart' in session:
        for product_id, quantity in session['cart'].items():
            product = Session.query(Product).get(int(product_id))
            if product:
                item_total = float(product.price)
                cart_items.append({
                    'product': product,
                    'item_total': item_total
                })
                total_price += item_total
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('logged_in'):
        flash('Войдите в систему для оформления заказа', 'warning')
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        flash('Ваша корзина пуста', 'warning')
        return redirect(url_for('catalog'))
    
    # Подсчет общей стоимости
    total_price = 0.0
    cart_items = []
    for product_id, quantity in session['cart'].items():
        product = Session.query(Product).get(int(product_id))
        if product:
            item_total = float(product.price) * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            total_price += item_total
    
    if request.method == 'POST':
        try:
            # Создаем заказ (courier_id оставляем NULL)
            new_order = Orders(
                client_id=session['user_id'],
                order_cost=total_price,
                delivery_address=request.form.get('address', ''),
                status='pending'
            )
            Session.add(new_order)
            Session.flush()  # Чтобы получить order_id
            
            # Добавляем товары в заказ
            for product_id, quantity in session['cart'].items():
                product = Session.query(Product).get(int(product_id))
                if product:
                    order_content = OrderContent(
                        order_id=new_order.order_id,
                        product_id=product.product_id,
                    )
                    Session.add(order_content)
            
            Session.commit()
            
            # Очищаем корзину
            session.pop('cart', None)
            
            flash('Ваш заказ успешно оформлен!', 'success')
            return redirect(url_for('my_orders'))
        except Exception as e:
            Session.rollback()
            flash('Произошла ошибка при оформлении заказа', 'danger')
            print(f"Ошибка оформления заказа: {e}")
    
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

@app.route('/orders')
def my_orders():
    if not session.get('logged_in'):
        flash('Войдите в аккаунт для просмотра заказов.', category='warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    orders = Session.query(Orders).filter_by(client_id=user_id).all()
    return render_template('orders.html', orders=orders)

@app.route('/admin/users')
def admin_users():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    users = Session.query(User).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/product')
def admin_product():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    product = Session.query(Product).all()
    return render_template('admin_products.html', product=product)

@app.route('/admin/orders')
def admin_orders():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Получаем все заказы с информацией о клиентах и курьерах
        orders = Session.query(Orders).order_by(Orders.created_at.desc()).all()
        orders_data = []
        
        for order in orders:
            try:
                client = Session.query(User).get(order.client_id)
                courier = Session.query(User).get(order.courier_id) if order.courier_id else None
                available_couriers = Session.query(User).filter_by(role='courier').all()
                
                # Получаем содержимое заказа
                order_contents = Session.query(OrderContent).filter_by(order_id=order.order_id).all()
                product_info = []
                for content in order_contents:
                    product = Session.query(Product).get(content.product_id)
                    if product:
                        product_info.append({
                            'name': product.product_name,
                            'type': product.product_type,
                            'price': product.price,
                            'quantity': content.quantity
                        })
                
                orders_data.append({
                    'order_id': order.order_id,
                    'order_cost': order.order_cost,
                    'delivery_address': order.delivery_address,
                    'status': order.status,
                    'created_at': order.created_at,
                    'client': client.username if client else 'Неизвестен',
                    'courier': courier.username if courier else 'Не назначен',
                    'available_couriers': available_couriers,
                    'product': product_info
                })
                
            except Exception as e:
                print(f"Ошибка обработки заказа {order.order_id if order else 'N/A'}: {e}")
                continue
        
        return render_template('admin_orders.html', orders_data=orders_data)
    
    except Exception as e:
        print(f"Ошибка при получении заказов: {e}")
        flash('Произошла ошибка при загрузке заказов', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/orders/<int:order_id>')
def admin_order_details(order_id):
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    order = Session.query(Orders).get(order_id)
    if not order:
        flash('Заказ не найден', category='danger')
        return redirect(url_for('admin_orders'))
    
    client = Session.query(User).get(order.client_id)
    courier = Session.query(User).get(order.courier_id) if order.courier_id else None
    
    # Получаем содержимое заказа
    order_contents = Session.query(OrderContent).filter_by(order_id=order_id).all()
    product = [Session.query(Product).get(oc.product_id) for oc in order_contents]
    
    return render_template('admin_order_details.html', 
                         order=order,
                         client=client,
                         courier=courier,
                         product=product)

@app.route('/admin/order/<int:order_id>/assign', methods=['POST'])
def assign_courier(order_id):
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    courier_id = request.form.get('courier_id')
    db_session = Session()
    
    try:
        order = db_session.query(Orders).get(order_id)
        if not order:
            flash('Заказ не найден', category='danger')
            return redirect(url_for('admin_orders'))
        
        if courier_id:
            courier = db_session.query(User).get(courier_id)
            if not courier or courier.role != 'courier':
                flash('Указанный курьер не существует или не является курьером', category='danger')
                return redirect(url_for('admin_orders'))
        
        order.courier_id = courier_id if courier_id else None
        order.status = 'assigned'  # Добавьте эту строку для изменения статуса
        db_session.commit()
        
        if courier_id:
            flash(f'Курьер {courier.username} назначен на заказ!', category='success')
        else:
            flash('Назначение курьера отменено', category='info')
            
    except Exception as e:
        db_session.rollback()
        print(f"Ошибка при назначении курьера: {e}")
        flash('Произошла ошибка при назначении курьера', category='danger')
    finally:
        db_session.close()
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/product/add', methods=['GET', 'POST'])
def admin_add_product():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            new_product = Product(
                product_name=request.form['product_name'],
                product_type=request.form['product_type'],
                price=request.form['price']
            )
            db_session = Session()  # Используем сессию для работы с БД
            db_session.add(new_product)
            db_session.commit()  # Важно: не забываем commit!
            flash('Товар успешно добавлен!', category='success')
            return redirect(url_for('admin_product'))
        except Exception as e:
            print(f"Ошибка при добавлении товара: {e}")
            flash('Ошибка при добавлении товара', category='danger')
    
    return render_template('admin_add_product.html')

# Маршрут для редактирования товара
@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
def admin_edit_product(product_id):
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    product = Session.query(Product).get(product_id)
    
    if not product:
        flash('Товар не найден', category='danger')
        return redirect(url_for('admin_product'))
    
    if request.method == 'POST':
        try:
            product.product_name = request.form['product_name']
            product.product_type = request.form['product_type']
            product.price = request.form['price']
            Session.commit()
            flash('Товар успешно обновлён!', category='success')
            return redirect(url_for('admin_product'))
        except Exception as e:
            print(e)
            flash('Ошибка при обновлении товара', category='danger')
    
    return render_template('admin_edit_product.html', product=product)

# Маршрут для удаления товара
@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', category='danger')
        return redirect(url_for('index'))
    
    product = Session.query(Product).get(product_id)
    
    if product:
        try:
            Session.delete(product)
            Session.commit()
            flash('Товар успешно удалён!', category='success')
        except Exception as e:
            print(e)
            flash('Ошибка при удалении товара', category='danger')
    else:
        flash('Товар не найден', category='danger')
    
    return redirect(url_for('admin_product'))


@app.route('/admin/users/add', methods=['GET', 'POST'])
def admin_add_user():
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    form = AdminUserForm()
    if form.validate_on_submit():
        # Проверяем, нет ли уже пользователя с таким email или именем
        existing_email = Session.query(User).filter_by(email=form.email.data).first()
        existing_username = Session.query(User).filter_by(username=form.username.data).first()
        
        if existing_email or existing_username:
            flash('Пользователь с таким email или именем уже существует', 'danger')
            return redirect(url_for('admin_add_user'))
        
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        new_user.set_password(form.password.data)
        
        try:
            Session.add(new_user)
            Session.commit()
            flash(f'Пользователь {new_user.username} успешно создан!', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            Session.rollback()
            flash('Ошибка при создании пользователя', 'danger')
            print(f"Ошибка создания пользователя: {e}")
    
    return render_template('admin_add_user.html', form=form)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not session.get('logged_in') or session.get('user_role') != 'admin':
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    
    user = Session.query(User).get(user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            user.email = request.form['email']
            user.role = request.form['role']
            
            Session.commit()
            flash('Данные пользователя успешно обновлены!', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            Session.rollback()
            flash('Ошибка при обновлении данных пользователя', 'danger')
            print(f"Ошибка обновления пользователя: {e}")
    
    return render_template('admin_edit_user.html', user=user)



if __name__ == '__main__':
    app.run(debug=True)