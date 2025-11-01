from pytz import timezone
import uuid
from datetime import datetime

from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from passlib.context import CryptContext
from sqlalchemy import (
    Boolean,
    Integer,
    create_engine,
    Column,
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    Enum,
)

tz = timezone('Asia/Ho_Chi_Minh')
Base = declarative_base()


# simple user, password to fastly implement other parts
class User(Base):
    __tablename__ = "user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(Text, nullable=False)
    user_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class Session(Base):
    __tablename__ = "session"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
