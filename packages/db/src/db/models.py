"""
Example database models

This file contains example models to demonstrate SQLAlchemy patterns.
Feel free to delete the Dog model and replace with your own models.
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from .database import Base


class Dog(Base):
    """
    Example model - feel free to delete this and add your own models.

    This demonstrates:
    - Table definition with __tablename__
    - Primary key with auto-increment
    - String columns with max length
    - Timestamp columns with server defaults
    """
    __tablename__ = "dog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    breed = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Dog(id={self.id}, name='{self.name}', breed='{self.breed}')>"
