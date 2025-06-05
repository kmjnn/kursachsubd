from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from datetime import datetime
import bcrypt
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(50), nullable=False)  # 'admin', 'courier', 'client'
    full_name = Column(String(255))
    phone = Column(String(20))
    delivery_address = Column(Text)

    def set_password(self, password):
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        self.hashed_password = hashed_password.decode('utf-8')

    def check_password(self, password):
        password_bytes = password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, self.hashed_password.encode('utf-8'))

class Product(Base):
    __tablename__ = 'product'
    
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    product_type = Column(String(20), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

class Orders(Base):
    __tablename__ = 'orders'
    
    order_id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    courier_id = Column(Integer, ForeignKey('users.id'))
    order_cost = Column(Numeric(10, 2), nullable=False)
    delivery_address = Column(Text, nullable=False)
    status = Column(String(20), default='pending')  # pending, assigned, in_progress, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Добавляем связь с клиентом и курьером
    client = relationship("User", foreign_keys=[client_id])
    courier = relationship("User", foreign_keys=[courier_id])

class OrderContent(Base):
    __tablename__ = 'order_contents'
    
    content_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.product_id'), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

class Vehicle(Base):
    __tablename__ = 'vehicles'
    
    vehicle_id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey('users.id'))
    model = Column(String(50), nullable=False)
    number = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)