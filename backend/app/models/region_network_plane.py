import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RegionNetworkPlane(Base):
    __tablename__ = "region_network_planes"
    # 数据库级唯一约束已移除，改为应用层校验：
    # 同一 (region_id, plane_type_id) 最多一个 root 节点 (parent_id IS NULL)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    region_id = Column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    plane_type_id = Column(
        String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"), nullable=False
    )
    # CIDR 网络地址段，如 "10.0.0.0/22"；nullable 兼容旧数据
    cidr = Column(String(43), nullable=True)
    # 父平面节点 ID，自引用 FK；nullable 表示根节点
    parent_id = Column(
        String(36), ForeignKey("region_network_planes.id", ondelete="CASCADE"), nullable=True
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # relationships
    region = relationship("Region", back_populates="region_planes")
    plane_type = relationship("NetworkPlaneType", back_populates="region_planes")
    # 父平面（自引用）
    parent = relationship(
        "RegionNetworkPlane", remote_side="RegionNetworkPlane.id", back_populates="children"
    )
    # 子平面列表（级联删除：删父平面时自动删子平面及其 IP 分配）
    children = relationship(
        "RegionNetworkPlane", back_populates="parent", cascade="all, delete-orphan"
    )
    # 此平面节点下的 IP 分配（级联删除：删平面时自动删关联分配）
    allocations = relationship(
        "IPAllocation", back_populates="plane", cascade="all, delete-orphan"
    )
