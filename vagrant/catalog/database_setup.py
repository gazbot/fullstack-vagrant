# import os
# import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


# User related objects
class Person(Base):
    __tablename__ = 'person'

    person_id = Column(Integer, primary_key=True)
    first_name = Column(String(250), nullable=False)
    middle_name = Column(String(250))
    last_name = Column(String(250), nullable=False)
    gender = Column(String(250))
    birth_date = Column(DateTime)

    @property
    def serialize(self):
        """ Return object data in easily serializable format"""
        return {
            'person_id': self.person_id,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name:': self.last_name,
            'gender': self.gender,
            'birth_date': self.birth_date
        }


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    email_address = Column(String(250), nullable=False)
    person_id = Column(Integer, ForeignKey('person.person_id'))
    person = relationship(Person)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'user_id': self.user_id,
            'email_address': self.username
        }


class Catalog(Base):
    __tablename__ = 'catalog'

    catalog_id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'catalog_id': self.catalog_id,
            'name': self.name,
            'description': self.description
        }


class Category(Base):
    __tablename__ = 'category'

    category_id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250), nullable=True)
    catalog_id = Column(Integer, ForeignKey('catalog.catalog_id'))
    creation_user_id = Column(Integer, ForeignKey('users.user_id'))
    modified_user_id = Column(Integer, ForeignKey('users.user_id'))

    @property
    def serializable(self):
        """Return object data in easily serializable format"""
        return {
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'catalog_id': self.catalog_id,
            'creation_user_id': self.creation_user_id,
            'modified_user_id': self.modified_user_id
        }


class Item(Base):
    __tablename__ = 'items'

    item_id = Column(Integer, primary_key=True)
    catalog_id = Column(Integer, ForeignKey('catalog.catalog_id'))
    category_id = Column(Integer, ForeignKey('category.category_id'))
    name = Column(String(250), nullable=False)
    description = Column(String(250))
    creation_user_id = Column(Integer, ForeignKey('users.user_id'))
    creation_date = Column(DateTime, default=datetime.datetime.utcnow)
    modified_user_id = Column(Integer, ForeignKey('users.user_id'))
    modified_date = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'name': self.name,
            'item_id': self.item_id,
            'description': self.description,
            'catalog_id': self.catalog_id,
            'category_id': self.category_id,
            'creation_user': self.creation_user_id,
            'creation_date': self.creation_date,
            'modified_user': self.modified_user_id,
            'modified_date': self.modified_date
        }

engine = create_engine('sqlite:///itemcatalog.db')

Base.metadata.create_all(engine)