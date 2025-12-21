from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
from datetime import datetime

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    channel_id = Column(String(255), unique=True, nullable=False, index=True)
    channel_name = Column(String(255), nullable=False)
    channel_url = Column(String(512), nullable=False)
    description = Column(Text)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    videos = relationship('Video', back_populates='channel', cascade='all, delete-orphan')

class Video(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False)
    video_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    thumbnail_url = Column(String(512))
    duration = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Search vectors
    title_search_vector = Column(TSVECTOR)
    description_search_vector = Column(TSVECTOR)

    channel = relationship('Channel', back_populates='videos')
    transcript = relationship('Transcript', back_populates='video', uselist=False, cascade='all, delete-orphan')
    transcript_errors = relationship('TranscriptError', back_populates='video', cascade='all, delete-orphan')

class Transcript(Base):
    __tablename__ = 'transcripts'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False, unique=True)
    text = Column(Text, nullable=False)
    snippets = Column(JSONB, nullable=False)
    language_code = Column(String(10))
    is_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Search vector
    text_search_vector = Column(TSVECTOR)

    video = relationship('Video', back_populates='transcript')

class TranscriptError(Base):
    __tablename__ = 'transcript_errors'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship('Video', back_populates='transcript_errors')

class WebSubSubscription(Base):
    __tablename__ = 'websub_subscriptions'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False, unique=True, index=True)
    topic_url = Column(String(512), nullable=False)  # The YouTube feed URL
    callback_url = Column(String(512), nullable=False)  # Our webhook endpoint
    verify_token = Column(String(255), nullable=False)  # For hub verification
    secret = Column(String(255), nullable=False)  # For HMAC signature verification
    subscribed_at = Column(DateTime)
    expires_at = Column(DateTime, index=True)  # For finding expiring subscriptions
    lease_seconds = Column(Integer)  # How long the subscription lasts
    status = Column(String(50), nullable=False, default='pending')  # 'pending', 'active', 'expired', 'failed'
    last_notification_at = Column(DateTime)
    last_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    channel = relationship('Channel', backref='websub_subscription')