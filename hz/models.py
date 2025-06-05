import bcrypt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric
from datetime import datetime
from sympy import Float
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(128))
    role = Column(String(50))  # Роли пользователя ("admin", "courier", "client")

    def set_password(self, password):
        """Устанавливает хэшированный пароль"""
        # Преобразование строки пароля в байты
        password_bytes = password.encode('utf-8')
        # Генерация соли и хэша пароля
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        # Преобразование обратно в строку для сохранения в базе данных
        self.hashed_password = hashed_password.decode('utf-8')

    def check_password(self, password):
        """Проверяет введенный пароль с хранимым хэшем"""
        # Преобразование пароля в байты
        password_bytes = password.encode('utf-8')
        # Проверка пароля
        return bcrypt.checkpw(password_bytes, self.hashed_password.encode('utf-8'))
    def is_admin(self):
        return self.role == 'admin'

class Client(Base):
    __tablename__ = 'clients'
    client_id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(11), nullable=False)
    delivery_address = Column(String(255), nullable=False)

class Courier(Base):
    __tablename__ = 'couriers'
    courier_id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    status = Column(String(10), nullable=False)
    phone = Column(String(11), nullable=False)

class Product(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    product_type = Column(String(20), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

class Orders(Base):
    __tablename__ = 'orders'
    
    order_id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey('users.id'))
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_cost = Column(Numeric(10, 2), nullable=False)
    delivery_address = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # Добавляем поле статуса
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderContent(Base):
    __tablename__ = 'order_contents'
    content_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)

class Vehicle(Base):
    __tablename__ = 'vehicles'
    vehicle_id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey('couriers.courier_id'), nullable=True)
    model = Column(String(50), nullable=False)
    number = Column(String(20), nullable=False)
    status = Column(String(10), nullable=False)