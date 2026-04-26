from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

likes = Table(
    "likes",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("tweet_id", ForeignKey("tweets.id"), primary_key=True),
)

# Переименовали переменную, чтобы не путалась с названием связи
followers_table = Table(
    "followers",
    Base.metadata,
    Column("follower_id", ForeignKey("users.id"), primary_key=True),
    Column("following_id", ForeignKey("users.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)

    tweets = relationship("Tweet", back_populates="author")

    following = relationship(
        "User",
        secondary=followers_table,
        primaryjoin=(id == followers_table.c.follower_id),
        secondaryjoin=(id == followers_table.c.following_id),
        back_populates="followers"
    )

    followers = relationship(
        "User",
        secondary=followers_table,
        primaryjoin=(id == followers_table.c.following_id),
        secondaryjoin=(id == followers_table.c.follower_id),
        back_populates="following"
    )


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"))

    author = relationship("User", back_populates="tweets")
    liked_by = relationship("User", secondary=likes, backref="liked_tweets")
    attachments = relationship("Media", back_populates="tweet")


class Media(Base):
    __tablename__ = "medias"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=True)

    tweet = relationship("Tweet", back_populates="attachments")