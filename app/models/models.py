# app/models/models.py
#
# Mirrors the original Laravel schema (users, topics, perceptions, likes,
# comments, follows, topic_follows, notifications, motivations, messages)
# field-for-field, so no data-shape surprises versus what the frontend
# already expects.
import uuid
from datetime import datetime

from enum import Enum

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    Boolean,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column("password", String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(255), nullable=True)
    professional_focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analytics_specialties: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    primary_analytics_topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verification_status: Mapped[str] = mapped_column(String(32), default="NOT_APPLIED", nullable=False)
    verification_badge: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    perceptions: Mapped[list["Perception"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    perceptions: Mapped[list["Perception"]] = relationship(back_populates="topic")


class Perception(TimestampMixin, Base):
    __tablename__ = "perceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user: Mapped["User"] = relationship(back_populates="perceptions")
    topic: Mapped["Topic | None"] = relationship(back_populates="perceptions")
    likes: Mapped[list["Like"]] = relationship(back_populates="perception", cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(back_populates="perception", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_perceptions_topic_created", "topic_id", "created_at"),)


class Like(TimestampMixin, Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "perception_id", name="uq_like_user_perception"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    perception_id: Mapped[int] = mapped_column(ForeignKey("perceptions.id", ondelete="CASCADE"), index=True)

    user: Mapped["User"] = relationship(back_populates="likes")
    perception: Mapped["Perception"] = relationship(back_populates="likes")


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    perception_id: Mapped[int] = mapped_column(ForeignKey("perceptions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user: Mapped["User"] = relationship()
    perception: Mapped["Perception"] = relationship(back_populates="comments")
    replies: Mapped[list["Comment"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    parent: Mapped["Comment | None"] = relationship(back_populates="replies", remote_side=[id])


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    followed_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TopicFollow(Base):
    __tablename__ = "topic_follows"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSON)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Motivation(Base):
    __tablename__ = "motivations"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(1024))
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_messages_pair", "from_user_id", "to_user_id", "created_at"),)


class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (Index("ix_conversation_state_user", "user_id"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    peer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AnalyticsTopic(Base):
    __tablename__ = "user_analytics_topics"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    topic: Mapped["Topic"] = relationship()


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(1024))
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    interval: Mapped[str] = mapped_column(String(16), default="month")
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    max_topics: Mapped[int] = mapped_column(Integer, default=0)
    verification_included: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    provider: Mapped[str] = mapped_column(String(32), default="internal_trial")
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()
    plan: Mapped["Plan"] = relationship()


class BillingEvent(Base):
    __tablename__ = "billing_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_billing_event_provider_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VerificationApplication(Base):
    __tablename__ = "verification_applications"
    __table_args__ = (
        Index("ix_verification_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profession: Mapped[str] = mapped_column(String(255))
    focus: Mapped[str] = mapped_column(String(255))
    primary_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    requested_topic_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    badge: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship()
    primary_topic: Mapped["Topic | None"] = relationship()


class PerceptionInteraction(Base):
    __tablename__ = "perception_interactions"
    __table_args__ = (
        UniqueConstraint(
            "actor_user_id",
            "perception_id",
            "event_type",
            "occurred_on",
            name="uq_interaction_user_perception_type_day",
        ),
        Index("ix_interactions_perception_type", "perception_id", "event_type"),
        Index("ix_interactions_occurred_on", "occurred_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    perception_id: Mapped[int] = mapped_column(ForeignKey("perceptions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    occurred_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
