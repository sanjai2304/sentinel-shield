"""SQLAlchemy database models for SentinelShield."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    """User accounts supporting RBAC ('admin', 'analyst')."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="analyst", index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(64), default="Security Operations", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    access_events: Mapped[list["AccessEvent"]] = relationship("AccessEvent", back_populates="user")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Resource(Base):
    """Protected and sensitive resources tracked by the system."""
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(String(32), index=True, default="INTERNAL", nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mock_data_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    access_events: Mapped[list["AccessEvent"]] = relationship("AccessEvent", back_populates="resource")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "resource_key": self.resource_key,
            "name": self.name,
            "resource_type": self.resource_type,
            "sensitivity_level": self.sensitivity_level,
            "is_sensitive": self.is_sensitive,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AccessEvent(Base):
    """Raw stream of user access events across protected resources."""
    __tablename__ = "access_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_role: Mapped[str] = mapped_column(String(32), default="analyst", nullable=False)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("resources.id", ondelete="SET NULL"), nullable=True)
    resource_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="READ", nullable=False)
    client_ip: Mapped[str] = mapped_column(String(45), default="127.0.0.1", nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="access_events")
    resource: Mapped[Optional["Resource"]] = relationship("Resource", back_populates="access_events")
    anomalies: Mapped[list["Anomaly"]] = relationship("Anomaly", back_populates="event")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "resource_id": self.resource_id,
            "resource_key": self.resource_key,
            "resource_type": self.resource_type,
            "sensitivity_level": self.sensitivity_level,
            "action": self.action,
            "client_ip": self.client_ip,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "is_synthetic": self.is_synthetic,
        }


class AuditLog(Base):
    """Immutable audit log of all access to sensitive resources."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_resource: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    route_path: Mapped[str] = mapped_column(String(255), nullable=False)
    http_method: Mapped[str] = mapped_column(String(16), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "actor_id": self.actor_id,
            "actor_username": self.actor_username,
            "actor_role": self.actor_role,
            "action": self.action,
            "target_resource": self.target_resource,
            "resource_classification": self.resource_classification,
            "client_ip": self.client_ip,
            "route_path": self.route_path,
            "http_method": self.http_method,
            "response_status": self.response_status,
            "metadata_json": self.metadata_json,
        }


class Anomaly(Base):
    """Flagged anomaly records generated by real-time detector engines."""
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("access_events.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resource_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM", index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event: Mapped[Optional["AccessEvent"]] = relationship("AccessEvent", back_populates="anomalies")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "username": self.username,
            "resource_id": self.resource_id,
            "resource_key": self.resource_key,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "score": round(self.score, 2),
            "explanation": self.explanation,
            "details_json": self.details_json,
            "is_resolved": self.is_resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
        }
