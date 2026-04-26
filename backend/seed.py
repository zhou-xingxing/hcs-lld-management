"""
Seed script: populate the database with sample data for development/testing.
Run with: python seed.py
"""

from app.database import SessionLocal, engine, Base
from app.models import Region, NetworkPlaneType, RegionNetworkPlane, IPAllocation


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(Region).count() > 0:
            print("Database already has data, skipping seed.")
            return

        # Create network plane types
        plane_types_data = [
            ("管理平面", "用于HCS管理节点的网络通信"),
            ("业务平面", "用于租户业务流量的网络通信"),
            ("存储平面", "用于存储节点之间的数据同步"),
            ("内部通信平面", "用于HCS内部组件之间的通信"),
            ("BMC平面", "用于服务器BMC管理口网络"),
        ]

        plane_types = {}
        for name, desc in plane_types_data:
            pt = NetworkPlaneType(name=name, description=desc)
            db.add(pt)
            db.flush()
            plane_types[name] = pt
            print(f"  Created plane type: {name}")

        # Create regions
        regions_data = [
            ("HCS华北-北京", "华北区域生产环境"),
            ("HCS华东-上海", "华东区域生产环境"),
        ]

        created_regions = {}
        for name, desc in regions_data:
            region = Region(name=name, description=desc)
            db.add(region)
            db.flush()
            created_regions[name] = region
            print(f"  Created region: {name}")

            # Enable all plane types for each region (with CIDR)
            plane_cidrs = {
                "管理平面": "10.10.0.0/16",
                "业务平面": "172.16.0.0/16",
                "存储平面": "192.168.10.0/24",
                "内部通信平面": "10.20.0.0/16",
                "BMC平面": "192.168.100.0/24",
            }
            for pt_name, pt in plane_types.items():
                rp = RegionNetworkPlane(
                    region_id=region.id,
                    plane_type_id=pt.id,
                    cidr=plane_cidrs.get(pt_name),
                )
                db.add(rp)

        db.flush()

        # Collect created planes for plane_id mapping
        region_planes = {
            (rp.region_id, rp.plane_type_id): rp.id
            for rp in db.query(RegionNetworkPlane).all()
        }

        # Create sample allocations
        allocations_data = [
            {
                "region": "HCS华北-北京",
                "plane": "管理平面",
                "ip_range": "10.10.0.0/16",
                "vlan_id": 100,
                "gateway": "10.10.0.1",
                "subnet_mask": "255.255.0.0",
                "purpose": "管理节点网络",
                "status": "active",
            },
            {
                "region": "HCS华北-北京",
                "plane": "业务平面",
                "ip_range": "172.16.0.0/16",
                "vlan_id": 200,
                "gateway": "172.16.0.1",
                "subnet_mask": "255.255.0.0",
                "purpose": "租户业务网络",
                "status": "active",
            },
            {
                "region": "HCS华北-北京",
                "plane": "存储平面",
                "ip_range": "192.168.10.0/24",
                "vlan_id": 300,
                "gateway": "192.168.10.1",
                "subnet_mask": "255.255.255.0",
                "purpose": "存储后端网络",
                "status": "active",
            },
            {
                "region": "HCS华北-北京",
                "plane": "内部通信平面",
                "ip_range": "10.20.0.0/16",
                "vlan_id": 400,
                "gateway": "10.20.0.1",
                "subnet_mask": "255.255.0.0",
                "purpose": "组件间通信",
                "status": "active",
            },
            {
                "region": "HCS华北-北京",
                "plane": "BMC平面",
                "ip_range": "192.168.100.0/24",
                "vlan_id": 500,
                "gateway": "192.168.100.1",
                "subnet_mask": "255.255.255.0",
                "purpose": "服务器BMC管理",
                "status": "active",
            },
            {
                "region": "HCS华东-上海",
                "plane": "管理平面",
                "ip_range": "10.30.0.0/16",
                "vlan_id": 101,
                "gateway": "10.30.0.1",
                "subnet_mask": "255.255.0.0",
                "purpose": "管理节点网络",
                "status": "active",
            },
            {
                "region": "HCS华东-上海",
                "plane": "业务平面",
                "ip_range": "172.20.0.0/16",
                "vlan_id": 201,
                "gateway": "172.20.0.1",
                "subnet_mask": "255.255.0.0",
                "purpose": "租户业务网络",
                "status": "reserved",
            },
        ]

        for item in allocations_data:
            region = created_regions[item["region"]]
            pt = plane_types[item["plane"]]
            plane_key = (region.id, pt.id)
            allocation = IPAllocation(
                region_id=region.id,
                plane_type_id=pt.id,
                plane_id=region_planes.get(plane_key),
                ip_range=item["ip_range"],
                vlan_id=item["vlan_id"],
                gateway=item["gateway"],
                subnet_mask=item["subnet_mask"],
                purpose=item["purpose"],
                status=item["status"],
            )
            db.add(allocation)

        db.commit()
        print(f"\nSeed completed successfully!")
        print(f"  Regions: {len(created_regions)}")
        print(f"  Plane Types: {len(plane_types)}")
        print(f"  Allocations: {len(allocations_data)}")

    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database...")
    seed()
