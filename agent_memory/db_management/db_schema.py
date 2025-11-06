from pytz import timezone
import uuid
from datetime import datetime

from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import (
    Boolean,
    Integer,
    create_engine,
    Column,
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    DateTime,
    JSON,
    Enum,
)
from sqlalchemy import Enum as SQLEnum
from enum import Enum as PyEnum


tz = timezone('Asia/Ho_Chi_Minh')
Base = declarative_base()


class SenderType(PyEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


# simple user, password to fastly implement other parts
class User(Base):
    __tablename__ = "users"
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(Text, nullable=False)
    user_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    # Relationship
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Foreign Key
    user_id = Column(String, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    # Relationship
    user = relationship("User", back_populates="sessions")


class Message(Base):
    __tablename__ = "message"
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Foreign Key
    session_id = Column(String, ForeignKey('sessions.id'))

    sender_type = Column(SQLEnum(SenderType), nullable=False)
    # name or id of sender
    sender_id = Column(String)
    # message content
    content = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship
    session = relationship("Session", back_populates="messages")
