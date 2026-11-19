import datetime as dt
import enum

from sqlalchemy import JSON, TIMESTAMP, BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoteEnum(str, enum.Enum):
    like = "like"
    dislike = "dislike"
    never_seen = "never_seen"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    country: Mapped[str] = mapped_column(String(5), default="IT", nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="it", nullable=False)
    owned_services_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mood_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    taste_profile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMP, default=dt.datetime.utcnow)


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    vote_enum: Mapped[VoteEnum] = mapped_column(Enum(VoteEnum, name="vote_enum"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMP, default=dt.datetime.utcnow)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(TIMESTAMP, default=dt.datetime.utcnow)


class CacheEntry(Base):
    __tablename__ = "cache"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(TIMESTAMP, nullable=False, index=True)
