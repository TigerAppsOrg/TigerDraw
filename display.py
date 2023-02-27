import os
from sys import argv, stderr, exit
from sqlalchemy import create_engine, and_
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import psycopg2
from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    MetaData,
    Boolean,
    insert,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import exists
import collections
from sqlalchemy.types import DateTime
from collections import defaultdict
from flask import current_app as app
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import QueuePool
from sqlalchemy import func
import config

# TODO : make this an environ var
DATABASE_URL = config.DATABASE_URL

# avoid sqlalchemy error for old postgres URIs
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

db = create_engine(
    DATABASE_URL,
    pool_size=4,
    max_overflow=0,
    pool_recycle=60,
    pool_timeout=180,
    isolation_level="READ COMMITTED",
)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=db))
Base = declarative_base()


class Room(Base):
    __tablename__ = "room_info"
    room_id = Column(Integer, primary_key=True)
    building = Column(String)
    room_no = Column(String)
    occupancy = Column(String)
    sq_footage = Column(Integer)
    res_college = Column(String)
    taken = Column(Boolean)


# class ReviewCount(Base):
#     __tablename__ = "review_count"
#     building_name = Column(String)
#     room_number = Column(String)
#     cnt = Column(Integer)
#     id = Column(Integer, primary_key=True)


# class Room_Ben(Base):
#     __tablename__ = 'room_info'
#     room_id = Column(Integer, primary_key=True)
#     building = Column(String)
#     room_no = Column(String)
#     occupancy = Column(Integer)
#     sq_footage = Column(Integer)
#     res_college = Column(String)


class Reviews(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    building_name = Column(String)
    content = Column(String)
    date = Column(DateTime(timezone=True), default=func.now())
    rating = Column(Integer)
    room_bathroomtype = Column(String)
    room_floor = Column(Integer)
    room_number = Column(String)
    room_numrooms = Column(Integer)
    room_occ = Column(Integer)
    room_sqft = Column(Integer)
    room_subfree = Column(Boolean)
    net_id = Column(String)


class FavoriteRoom(Base):
    __tablename__ = "favorites"
    room_id = Column(Integer, primary_key=True)
    building = Column(String)
    room_no = Column(String)
    occupancy = Column(Integer)
    sq_footage = Column(Integer)


class DrawTime(Base):
    __tablename__ = "draw_time"
    room_id = Column(Integer)
    year = Column(Integer)
    draw_time = Column(Integer, primary_key=True)


class User(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True)
    rooms = Column(postgresql.ARRAY(Integer))
    group_ids = Column(postgresql.ARRAY(Integer))


class Groups(Base):
    __tablename__ = "groups"
    group_id = Column(Integer, primary_key=True)
    name = Column(String)
    accepted = Column(postgresql.ARRAY(String))
    pending = Column(postgresql.ARRAY(String))
    room_ids = Column(postgresql.ARRAY(Integer))
    users_that_added = Column(postgresql.ARRAY(String))


class Buildings(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    res_college = Column(String)


meta = MetaData(db)


# Base.metadata.create_all(db)


def getUserRooms(username):
    sqlalchemy_session = db_session

    # CAS is weird and sometimes has newline char in the username
    # Postgres doesn't like that so just strip it of whitespace
    username = username.strip()

    # check is user is in user table
    user_exists = sqlalchemy_session.query(
        exists().where(User.username == username)
    ).scalar()

    # if not, add them to user table
    if not user_exists:
        table = Table("users", meta)
        ins_command = insert(User).values(username=username, rooms=[], group_ids=[])
        conn = db.connect()
        conn.execute(ins_command)
        conn.close()

    # get user's favorite rooms
    user_fav_room_query = sqlalchemy_session.query(User.rooms)
    user_fav_room_query = user_fav_room_query.filter(User.username == username)
    user_rooms = list(user_fav_room_query.all())

    if len(user_rooms) == 0:
        return []

    user_rooms = list(user_rooms[0])
    if len(user_rooms) == 0:
        return []

    return user_rooms[0]


def allRooms(
    username,
    college,
    firstranking,
    lastranking,
    occupancy,
    building,
    year,
):
    sqlalchemy_session = db_session

    # get user's favorite rooms
    user_rooms = getUserRooms(username)

    rooms = []

    query = sqlalchemy_session.query(
        Room, DrawTime, Room.room_id.in_(user_rooms)
    ).outerjoin(DrawTime, DrawTime.room_id == Room.room_id)
    # filter out any Wilson College entries
    query = query.filter(Room.res_college != "Wilson College")

    if college:
        query = query.filter(Room.res_college == college)
    # if occupancy:
    # 	query = query.filter(Room.occupancy == int(occupancy))
    # if building:
    # 	query = query.filter(Room.buiding == building)
    if year:
        query = query.filter(DrawTime.year == year)

    rooms = query.all()

    # if college:
    # 	query = query.filter(Room.res_college == college)
    # if year:
    # 	query = query.filter(DrawTime.year == year)
    # query = query.order_by(DrawTime.draw_time)
    # else:
    # 	# query = query.group_by(Room.room_id, DrawTime.room_id).order_by(func.avg(DrawTime.draw_time))
    # 	query = query.order_by(Room.room_id)

    # rooms = query.all()

    # # print(rooms)

    # # give rankings 1-last draw time for chosen year
    # if year:
    # 	for i, room in enumerate(rooms):
    # 		room.DrawTime.draw_time = i+1
    # 	# if not lastranking:
    # 	# 	lastranking = len(rooms)

    # # compute average across years
    # else:
    # 	seen = set()
    # 	trimmed_rooms = []
    # 	for i, room in enumerate(rooms):
    # 		rankings[room.Room.room_id].append(room.DrawTime.draw_time)
    # 	for room in rooms:
    # 		if room.Room.room_id not in seen:
    # 			mean = np.mean(rankings[room.Room.room_id])
    # 			room.DrawTime.draw_time = mean
    # 			trimmed_rooms.append(room)
    # 			seen.add(room.Room.room_id)

    # 	trimmed_rooms.sort(key = lambda x : x.DrawTime.draw_time)

    # 	rooms = trimmed_rooms.copy()
    # 	# for i, room in enumerate(rooms):
    # 	# 	room.DrawTime.draw_time = i + 1

    # 	# 	rooms.append(room)
    # 		# room.DrawTime.draw_time = i + 1
    # 	# for i, room in enumerate(rooms):
    # 	# 	room.DrawTime.draw_time = i+1

    # 	# for i,room in enumerate(rooms):
    # 	# 	rankings[room.Room.room_id].append(room.DrawTime.draw_time)
    # 	# 	if i != len(rooms)-1:
    # 	# 		if (rooms[i+1].Room.room_id != room.Room.room_id):
    # 	# 			room.DrawTime.draw_time = np.mean(rankings[room.Room.room_id])

    # # print(rankings)

    rooms.sort(
        key=lambda x: float("inf") if x.DrawTime is None else x.DrawTime.draw_time
    )
    for i, room in enumerate(rooms):
        if room.DrawTime is None:
            pass
        else:
            room.DrawTime.draw_time = i + 1

    return rooms


def getFavoriteRooms(username):
    sqlalchemy_session = db_session

    # get list ids for user's favorite rooms
    user_rooms = getUserRooms(username)

    # get favorite rooms, with the relevant ranking
    query = sqlalchemy_session.query(Room, DrawTime, Room.room_id.in_(user_rooms)).join(
        DrawTime, DrawTime.room_id == Room.room_id
    )
    query = query.filter(Room.room_id.in_(user_rooms))
    fav_rooms = query.all()

    # averaging the rankings so that one room shows up
    rankings = collections.defaultdict(list)
    rankings_list = collections.defaultdict(int)
    seen = set()

    # getting a list of all the rankings with the room id as key
    for room in fav_rooms:
        rankings[room.Room.room_id].append(room.DrawTime.draw_time)
    for room in rankings:
        curr_sum = 0
        num_rooms = 0
        for r in rankings[room]:
            curr_sum += r
            num_rooms += 1
        avg_rank = curr_sum / num_rooms
        rankings_list[room] = int(avg_rank)

    # got the average rankings, now to remove the duplicate roomids
    deduped_list = []
    for room in fav_rooms:
        if room.Room.room_id not in seen:
            seen.add(room.Room.room_id)
            room.DrawTime.draw_time = rankings_list[room.Room.room_id]
            deduped_list.append(room)

    return deduped_list


def allFavoriteRooms(username):
    sqlalchemy_session = db_session

    # get list ids for user's favorite rooms
    user_rooms = getUserRooms(username)

    # making sure to get the ranking (average of all years) as well

    # get favorite rooms
    query = sqlalchemy_session.query(Room, DrawTime, Room.room_id.in_(user_rooms)).join(
        DrawTime, DrawTime.room_id == Room.room_id
    )
    query = query.filter(Room.room_id.in_(user_rooms))
    fav_rooms = query.all()

    return fav_rooms


def changeFavorite(room_id, username, remove):
    sqlalchemy_session = db_session

    # CAS is weird and sometimes has newline char in the username
    # Postgres doesn't like that so just strip it of whitespace
    username = username.strip()

    # get user's favorite rooms
    user_fav_room_query = sqlalchemy_session.query(User)
    user = user_fav_room_query.filter(User.username == username).first()

    # add/remove to user's fav rooms
    if remove:
        if int(room_id) in user.rooms:
            user.rooms.remove(int(room_id))
    else:
        user.rooms.append(int(room_id))
    flag_modified(user, "rooms")  # this is needed b/c we're changing an array

    sqlalchemy_session.commit()


def addFavorite(room_id, username):
    changeFavorite(room_id, username, False)


def removeFavorite(room_id, username):
    changeFavorite(room_id, username, True)


def editGroupInfo(group_id, name, members):
    db_session()
    db_session.commit()

    # check if the group exists - should never occur, but just in case
    group_exists = db_session.query(
        exists().where(Groups.group_id == group_id)
    ).scalar()
    if not group_exists:
        return

    group_query = db_session.query(Groups)
    group = group_query.filter(Groups.group_id == group_id).first()
    group.name = name
    prev_members = set(group.accepted)
    removed_members = prev_members - set(members)
    added_members = set(members) - prev_members

    removed_member_query = db_session.query(User)
    removed_member_query = removed_member_query.filter(
        User.username.in_(removed_members)
    )
    removed_members = removed_member_query.all()

    for member in list(removed_members):
        if int(group_id) in member.group_ids:
            member.group_ids = [m for m in member.group_ids if m != int(group_id)]
            flag_modified(member, "group_ids")

    added_member_query = db_session.query(User)
    added_member_query = added_member_query.filter(User.username.in_(added_members))
    added_members = added_member_query.all()
    for member in list(added_members):
        member.group_ids.append(group_id)
        flag_modified(member, "group_ids")

    group.accepted = members
    flag_modified(group, "accepted")

    db_session.commit()
    db_session.flush()
    db_session.close()
    db_session.remove()


def addNewGroup(members, name, username):
    flag = True
    sqlalchemy_session = db_session

    # generating the group id
    count = sqlalchemy_session.query(Groups).count()
    if count == 0:
        new_id = 0
    else:
        q = sqlalchemy_session.query(func.max(Groups.group_id).label("max_score"))
        r = q.one()
        new_id = r.max_score + 1

    sqlalchemy_session.add(
        Groups(
            group_id=new_id,
            name=name,
            accepted=members,
            pending=[],
            room_ids=[],
            users_that_added=[],
        )
    )

    # now that we added the group, we need to add the group ids to the corresponding users
    sqlalchemy_session = db_session

    # get every group member's data
    for member in members:
        member_query = sqlalchemy_session.query(User)

        # if not, add them to user table
        user_exists = sqlalchemy_session.query(
            exists().where(User.username == member)
        ).scalar()

        if not user_exists:
            ins_command = insert(User).values(username=username, rooms=[], group_ids=[])
            conn = db.connect()
            conn.execute(ins_command)
            conn.close()

        member_data = member_query.filter(User.username == member).first()

        if flag == True:
            # no data in the groupids yet
            if member_data.group_ids is None:
                new_group_ids = []
                new_group_ids.append(int(new_id))
                member_data.group_ids = new_group_ids
            else:
                member_data.group_ids.append(int(new_id))
        else:
            member_data.group_ids.remove(int(new_id))

        flag_modified(member_data, "group_ids")

    sqlalchemy_session.commit()


def getUserGroups(username):
    username = username.strip()

    # check is user is in user table
    user_exists = db_session.query(exists().where(User.username == username)).scalar()

    # if not, add them to user table
    if not user_exists:
        ins_command = insert(User).values(username=username, rooms=[], group_ids=[])
        conn = db.connect()
        conn.execute(ins_command)
        conn.close()

    # get user's groups
    query = db_session.query(User.group_ids).where(User.username == username)
    groups = query.first()
    groups = groups[0]

    # user has a "groups" column but it's an empty array
    if len(groups) == 0:
        return False

    # user has groups, so we should get the data for it
    groups_dict = (
        {}
    )  # note the difference between groups_dict here and group_dict within the for loop!
    for g_id in groups:
        # get group info
        query = db_session.query(Groups).where(Groups.group_id == g_id)

        # TODO - error handling where the group somehow doesn't exist?
        group = query.first()
        group_dict = {}
        group_dict["name"] = group.name

        # get group's users names
        user_ids = group.accepted
        query = db_session.query(User.username).where(User.username.in_(user_ids))
        users = query.all()
        group_dict["accepted"] = list(zip(*users))[0]

        # get group's rooms' details
        room_ids = group.room_ids
        query = db_session.query(Room).where(Room.room_id.in_(room_ids))
        rooms = query.all()
        group_dict["rooms"] = rooms

        groups_dict[g_id] = group_dict

    return groups_dict


def addRoomToGroup(username, room_id, group_id):
    changeGroupRooms(room_id, username, group_id, False)


def removeRoomFromGroup(username, room_id, group_id):
    changeGroupRooms(room_id, username, group_id, True)


def changeGroupRooms(room_id, username, group_id, remove):
    sqlalchemy_session = db_session
    username = username.strip()

    # get the relevant group that we are adding or removing a room from
    query = db_session.query(Groups).where(Groups.group_id == group_id)
    groups = query.first()

    # add/remove group's room list
    if remove:
        if int(room_id) in groups.room_ids:
            index = groups.room_ids.index(int(room_id))
            groups.room_ids.remove(int(room_id))
            del groups.users_that_added[index]
    else:
        groups.room_ids.append(int(room_id))
        groups.users_that_added.append(username)
    flag_modified(groups, "room_ids")  # this is needed b/c we're changing an array
    flag_modified(groups, "users_that_added")

    sqlalchemy_session.commit()

    # rooms = []
    # room_query = db_session.query(Room)


def getUserGroupsJSON(username):
    username = username.strip()

    # check is user is in user table
    user_exists = db_session.query(exists().where(User.username == username)).scalar()

    # if not, add them to user table
    if not user_exists:
        table = Table("users", meta)
        ins_command = insert(User).values(username=username, rooms=[], group_ids=[])
        conn = db.connect()
        conn.execute(ins_command)
        conn.close()

    # get user's groups
    query = db_session.query(User.group_ids).where(User.username == username)
    groups = query.first()
    groups = groups[0]

    # user has a "groups" column but it's an empty array
    if len(groups) == 0:
        return []

    # user has groups, so we should get the data for it
    groups_array = []
    for g_id in groups:
        # get group info
        query = db_session.query(Groups).where(Groups.group_id == g_id)

        # TODO - error handling where the group somehow doesn't exist?
        group = query.first()
        group_dict = {"group_id": g_id}
        group_dict["name"] = group.name

        # get group's users names
        user_ids = group.accepted
        query = db_session.query(User.username).where(User.username.in_(user_ids))
        users = query.all()
        group_dict["accepted"] = list(zip(*users))[0]

        # get group's rooms' details
        room_ids = group.room_ids
        query = db_session.query(Room).where(Room.room_id.in_(room_ids))
        rooms = query.all()
        room_array = []
        for idx, room in enumerate(rooms):
            user_that_added = group.users_that_added[idx]
            room_dict = {
                "room_id": room.room_id,
                "building": room.building,
                "room_no": room.room_no,
                "res_college": room.res_college,
                "occupancy": room.occupancy,
                "sq_footage": room.sq_footage,
                "user_that_added": user_that_added,
                "taken": room.taken,
                "favorited": True if int(room.room_id) in room_ids else False,
            }
            room_array.append(room_dict)
        group_dict["rooms"] = room_array

        groups_array.append(group_dict)

    return groups_array


def deleteGroup(group_id):
    # get all members in the group
    members = (
        db_session.query(Groups.accepted).where(Groups.group_id == group_id).first()
    )
    if members is not None and len(members) > 0:
        members = members[0]
    else:
        return False

    # delete group from group table
    query = (
        db_session.query(Groups)
        .filter(Groups.group_id == group_id)
        .delete(synchronize_session=False)
    )

    # delete group from the group lists in users table
    users = db_session.query(User).where(User.username.in_(members))
    for user in users:
        if int(group_id) in user.group_ids:
            user.group_ids.remove(int(group_id))
        flag_modified(user, "group_ids")  # this is needed b/c we're changing an array

    db_session.commit()
    return True


def updateTakenRooms(room_ids):
    sqlalchemy_session = db_session

    rooms = db_session.query(Room).where(Room.room_id.in_(room_ids))
    for room in rooms:
        room.taken = True
    db_session.commit()

    rooms = db_session.query(Room).all()
    for room in rooms:
        room.taken = False
    db_session.commit()


def clearRoomStatuses():
    sqlalchemy_session = db_session

    rooms = db_session.query(Room).all()
    for room in rooms:
        room.taken = False
    db_session.commit()


def populate_buildings():
    import json

    f = open("data/buildings.json")
    data = json.load(f)
    for building_dict in data:
        building_id = building_dict["id"]
        building_name = building_dict["name"]
        db_session.add(Buildings(id=building_id, name=building_name))
        db_session.commit()


def convert_building(building_id):
    sqlalchemy_session = db_session

    building = (
        db_session.query(Buildings).filter(Buildings.id == int(building_id)).first()
    )

    return building.name, building.res_college


def populate_rooms():
    # __tablename__ = 'room_info_new'
    # room_id = Column(Integer, primary_key=True)
    # building = Column(String)  # misspelled, TODO fix
    # room_no = Column(String)
    # occupancy = Column(Integer)
    # sq_footage = Column(Integer)
    # res_college = Column(String)
    import json

    f = open("data/rooms.json")
    f2 = open("data/old_reviews.json")
    data = json.load(f)
    print(len(data))
    reviews_data = json.load(f2)
    count = 0
    for room_dict in data:
        room_no = room_dict["number"]
        sq_footage = int(room_dict["sqft"])
        rooms = (
            db_session.query(Room)
            .filter(Room.room_no == room_no, Room.sq_footage == sq_footage)
            .all()
        )
        # if len(rooms) > 1:
        #     for room in rooms:
        #         print(room.room_id, room.building)
        #     print()
        # if len(rooms) == 1:
        #     room = rooms.first()

        # if rooms are not in database, add them into room_info_new
    #     if len(rooms) == 0:
    #         print(f"{room_no} {sq_footage}")
    #         building, building_res_college = convert_building(room_dict["building_id"])
    #         occupancy = room_dict["occ"]
    #         db_session.add(Room_Ben(building=building, room_no=room_no, sq_footage=sq_footage, res_college=building_res_college,
    #                                 occupancy=occupancy))
    #         db_session.commit()
    #         count += 1
    # print(count)

    # if len(rooms) == 0:
    #     db_session.add(Room_Ben(room_no=room_no, building=room_dict[]))
    # print(f"Room {rooms}")

    # room_id = room_dict['id']
    # building_name = room_dict['name']
    # db_session.add(Buildings(id=room_id, name=building_name))
    # db_session.commit()


if __name__ == "__main__":
    # rooms = allRooms("", "", "", "", "", "", "")
    populate_rooms()
