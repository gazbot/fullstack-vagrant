# import os
# import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True)
    username = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email
        }


class Category(Base):
    __tablename__ = 'category'
    category_id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250), nullable=True)
    creation_user_id = Column(Integer, ForeignKey('user.user_id'))
    creation_user = relationship(User)
    creation_date = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def serializable(self):
        """Return object data in easily serializable format"""
        return {
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'creation_user_id': self.creation_user_id,
            'modified_user_id': self.modified_user_id
        }


class Item(Base):
    __tablename__ = 'item'
    item_id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('category.category_id'))
    name = Column(String(250), nullable=False)
    description = Column(String(250))
    creation_user_id = Column(Integer, ForeignKey('user.user_id'))
    creation_user = relationship(User)
    creation_date = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'name': self.name,
            'item_id': self.item_id,
            'description': self.description,
            'category_id': self.category_id,
            'creation_user': self.creation_user_id,
            'creation_date': self.creation_date,
            'modified_user': self.modified_user_id,
            'modified_date': self.modified_date
        }

engine = create_engine('sqlite:///itemcatalog.db')

Base.metadata.create_all(engine)