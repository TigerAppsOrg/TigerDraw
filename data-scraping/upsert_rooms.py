"""
Upsert room data from RoomInfo_RoomViewer.csv into TigerDraw's database.

Preserves all historical data (reviews, favorites, groups, draw times)
by matching on (building, room_no) and keeping existing room_ids.

Also loads image URLs from room_images.json into the room_images table.

Usage:
    DATABASE_URL=postgresql://... python upsert_rooms.py

    Or set DATABASE_URL in your environment / .env file.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Paths
ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / "RoomInfo_RoomViewer.csv"
IMAGES_PATH = ROOT / "data-scraping" / "room_images.json"
CHANGELOG_PATH = ROOT / "data-scraping" / "upsert_changelog.json"

# DB setup
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    # Try reading from config
    sys.path.insert(0, str(ROOT))
    try:
        import config
        DATABASE_URL = config.DATABASE_URL
    except Exception:
        pass

if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL environment variable")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_size=2, max_overflow=0)
Session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()


# Mirror the models from display.py
class Room(Base):
    __tablename__ = "tigerden_rooms_data"
    room_id = Column(Integer, primary_key=True)
    building = Column(String)
    room_no = Column(String)
    occupancy = Column(String)
    sq_footage = Column(Integer)
    res_college = Column(String)
    taken = Column(Boolean)
    elevator = Column(String)
    bathroom = Column(String)
    ac = Column(String)
    floor = Column(Integer)
    wawa = Column(Integer)
    ustore = Column(Integer)
    __table_args__ = {'quote': True}
    nassau_street = Column('Nassau Street', Integer)
    jadwin_gym = Column('Jadwin Gym', Integer)
    frist = Column(Integer)
    street = Column(Integer)
    equad = Column(Integer)
    dillon = Column(Integer)
    independent_only = Column(Boolean, default=False)


class RoomChange(Base):
    __tablename__ = "room_changes"
    id = Column(Integer, primary_key=True)
    building = Column(String)
    room_no = Column(String)
    field = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    changed_at = Column(DateTime(timezone=True), default=func.now())


class RoomImage(Base):
    __tablename__ = "room_images"
    id = Column(Integer, primary_key=True)
    building = Column(String)
    room_no = Column(String)
    image_type = Column(String)
    url = Column(String)
    media_type = Column(String)
    is_360 = Column(Boolean, default=False)


def create_tables():
    """Create new tables if they don't exist (room_changes, room_images)."""
    RoomChange.__table__.create(engine, checkfirst=True)
    RoomImage.__table__.create(engine, checkfirst=True)
    print("  Tables room_changes and room_images ready.")


def load_csv():
    """Load new room data from CSV."""
    rooms = []
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rooms.append(row)
    return rooms


def load_images():
    """Load image data from JSON."""
    with open(IMAGES_PATH) as f:
        return json.load(f)


def upsert_rooms(session, new_rooms):
    """Upsert rooms, preserving room_ids and tracking changes."""
    # Build lookup of existing rooms by (building, room_no)
    existing = {}
    for room in session.query(Room).all():
        existing[(room.building, room.room_no)] = room

    # Track the max room_id for new inserts
    max_id = session.query(func.max(Room.room_id)).scalar() or 0

    changelog = {"updated": [], "inserted": [], "deactivated": [], "unchanged": 0}
    new_keys = set()

    # Fields we track changes for
    tracked_fields = {
        "occupancy": "Type",
        "sq_footage": "Sqft",
        "res_college": "College",
    }
    # Fields we update silently
    update_fields = {
        "elevator": "Elevator",
        "bathroom": "Bathroom",
        "ac": "AC",
        "floor": "Floor",
        "wawa": "Wawa",
        "ustore": "UStore",
        "nassau_street": "Nassau Street",
        "jadwin_gym": "Jadwin Gym",
        "frist": "Frist",
        "street": "Street",
        "equad": "EQuad",
        "dillon": "Dillon",
    }

    for row in new_rooms:
        building = row["Hall"]
        room_no = row["Room"]
        key = (building, room_no)
        new_keys.add(key)

        if key in existing:
            # UPDATE existing room
            room = existing[key]
            changes = []

            # Check tracked fields for changes
            for db_field, csv_field in tracked_fields.items():
                old_val = str(getattr(room, db_field) or "")
                new_val = str(row.get(csv_field, ""))
                if old_val != new_val and new_val:
                    changes.append(RoomChange(
                        building=building, room_no=room_no,
                        field=db_field, old_value=old_val, new_value=new_val,
                    ))
                    setattr(room, db_field, new_val if db_field != "sq_footage" else int(new_val))

            # Update other fields silently
            for db_field, csv_field in update_fields.items():
                new_val = row.get(csv_field, "")
                if new_val:
                    if db_field in ("sq_footage", "floor", "wawa", "ustore",
                                    "nassau_street", "jadwin_gym", "frist",
                                    "street", "equad", "dillon"):
                        try:
                            setattr(room, db_field, int(new_val))
                        except (ValueError, TypeError):
                            pass
                    else:
                        setattr(room, db_field, new_val)

            # Update res_college
            if row.get("College"):
                room.res_college = row["College"]

            if changes:
                for c in changes:
                    session.add(c)
                changelog["updated"].append({
                    "building": building, "room_no": room_no,
                    "changes": [{
                        "field": c.field, "old": c.old_value, "new": c.new_value
                    } for c in changes]
                })
            else:
                changelog["unchanged"] += 1

        else:
            # INSERT new room
            max_id += 1
            new_room = Room(
                room_id=max_id,
                building=building,
                room_no=room_no,
                occupancy=row.get("Type", ""),
                sq_footage=int(row.get("Sqft", 0) or 0),
                res_college=row.get("College", ""),
                taken=False,
                elevator=row.get("Elevator", "NO"),
                bathroom=row.get("Bathroom", "NONE"),
                ac=row.get("AC", "NO"),
                floor=int(row.get("Floor", 0) or 0),
                wawa=int(row.get("Wawa", 0) or 0),
                ustore=int(row.get("UStore", 0) or 0),
                nassau_street=int(row.get("Nassau Street", 0) or 0),
                jadwin_gym=int(row.get("Jadwin Gym", 0) or 0),
                frist=int(row.get("Frist", 0) or 0),
                street=int(row.get("Street", 0) or 0),
                equad=int(row.get("EQuad", 0) or 0),
                dillon=int(row.get("Dillon", 0) or 0),
                independent_only=False,
            )
            session.add(new_room)
            changelog["inserted"].append({"building": building, "room_no": room_no, "room_id": max_id})

    # Deactivate rooms no longer in the new data (soft delete)
    for key, room in existing.items():
        if key not in new_keys:
            if not room.taken:
                room.taken = True
                changelog["deactivated"].append({"building": key[0], "room_no": key[1], "room_id": room.room_id})

    return changelog


def load_room_images(session, images_data):
    """Load image URLs into room_images table, replacing existing data."""
    # Clear existing images
    session.query(RoomImage).delete()

    count = 0
    for room_id_str, imgs in images_data.items():
        # Parse room_id string to get building + room_no
        # Format is like "Fu B219", "1901101", "GrousbeckC110"
        # We need to match these to the CSV Hall+Room format
        for img in imgs:
            # Extract building and room from the image data
            # The room_id keys match the RoomID column in the CSV
            # We need to find the corresponding (building, room_no)
            building = None
            room_no = None

            # Try to find the room in the DB
            # The RoomID format is {Hall}{Room} with no separator
            # We'll parse it by checking against known building names
            pass

        # Actually, let's use the raw data which has building->rooms mapping
        pass

    # Better approach: iterate the CSV to build RoomID -> (building, room_no) map
    room_id_map = {}
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["RoomID"]
            room_id_map[rid] = (row["Hall"], row["Room"])

    for room_id_str, imgs in images_data.items():
        if room_id_str not in room_id_map:
            continue
        building, room_no = room_id_map[room_id_str]

        for img in imgs:
            url = img.get("url", "")
            if not url:
                continue
            session.add(RoomImage(
                building=building,
                room_no=room_no,
                image_type=img.get("type", ""),
                url=url,
                media_type=img.get("mediaType", ""),
                is_360=img.get("is360External", False),
            ))
            count += 1

    return count


def main():
    print("=" * 60)
    print("TigerDraw Room Data Upsert")
    print("=" * 60)

    # Step 1: Create new tables
    print("\n[1] Creating tables (if needed)...")
    create_tables()

    # Step 2: Load new data
    print("[2] Loading new CSV data...")
    new_rooms = load_csv()
    print(f"    {len(new_rooms)} rooms in CSV")

    print("    Loading image data...")
    images_data = load_images()
    print(f"    {len(images_data)} rooms with images")

    # Step 3: Upsert
    session = Session()
    try:
        print("\n[3] Upserting rooms...")
        existing_count = session.query(Room).count()
        print(f"    {existing_count} rooms currently in DB")

        changelog = upsert_rooms(session, new_rooms)

        print(f"\n    Results:")
        print(f"      Updated:     {len(changelog['updated'])}")
        print(f"      Inserted:    {len(changelog['inserted'])}")
        print(f"      Deactivated: {len(changelog['deactivated'])}")
        print(f"      Unchanged:   {changelog['unchanged']}")

        # Step 4: Load images
        print("\n[4] Loading room images...")
        img_count = load_room_images(session, images_data)
        print(f"    {img_count} image records loaded")

        # Step 5: Commit
        print("\n[5] Committing to database...")
        session.commit()
        print("    Done!")

        # Save changelog
        with open(CHANGELOG_PATH, "w") as f:
            json.dump(changelog, f, indent=2, default=str)
        print(f"\n    Changelog saved to {CHANGELOG_PATH}")

        # Final count
        final_count = session.query(Room).count()
        print(f"\n    Final room count: {final_count}")

    except Exception as e:
        session.rollback()
        print(f"\n    ERROR: {e}")
        raise
    finally:
        session.close()

    # Print notable changes
    if changelog["updated"]:
        print(f"\n  Notable changes:")
        for change in changelog["updated"][:20]:
            for c in change["changes"]:
                print(f"    {change['building']} {change['room_no']}: {c['field']} {c['old']} → {c['new']}")

    if changelog["inserted"]:
        print(f"\n  New rooms (first 20):")
        for ins in changelog["inserted"][:20]:
            print(f"    {ins['building']} {ins['room_no']} (id={ins['room_id']})")


if __name__ == "__main__":
    main()
