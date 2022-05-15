from flask import (
    Flask,
    request,
    make_response,
    redirect,
    url_for,
    jsonify,
)
from flask import render_template, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
import os
import pytz
from display import (
    allRooms,
    allFavoriteRooms,
    addFavorite,
    removeFavorite,
    getFavoriteRooms,
    db_session,
    getUserGroups,
    addNewGroup,
    deleteGroup,
    editGroupInfo,
    addRoomToGroup,
    removeRoomFromGroup,
    getUserGroupsJSON,
    clearRoomStatuses,
)
from CASClient import CASClient
from sqlalchemy.orm import scoped_session, sessionmaker
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from json import dumps
import json
import collections
from updateavailable import checkRooms, changeRoomPdf
from api_access import check_is_undergrad
from collections import defaultdict
from display import db_session, Reviews
import time
import config

app = Flask(__name__)


def get_time_string_from_utc_dt(utc_dt):
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(tz=pytz.timezone("America/New_York"))
    local_dt_string = local_dt.strftime('%b %d, %Y')
    return local_dt_string


app.jinja_env.globals.update(get_time_string_from_utc_dt=get_time_string_from_utc_dt)

# Generated by os.urandom(16)
# This is needed for the CAS login
app.secret_key = (
    b"\xe7\xa3\x1c\xf2\n\xe9\xb6\xd0\xcd\xbcI\xa9\x14\x8a\x91\x86"
)


# app.config['SECRET_KEY'] = 'secret'
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
# db = create_engine(os.environ.get("DATABASE_URL"))

# db = SQLAlchemy(app)
# investigate conn pooling


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


@app.route("/get_reviews", methods=['GET', 'POST'])
def get_reviews():
    # CASClient().authenticate()
    building_name = request.args.get('building_name')
    room_number = request.args.get('room_no')

    reviews = db_session.query(Reviews).filter(Reviews.building_name == building_name,
                                               Reviews.room_number == room_number).order_by(
        Reviews.date.desc()).all()

    html = render_template("reviews_body.html", reviews=reviews, building_name=building_name,
                           room_number=room_number)
    response = make_response(html)
    return response


@app.route("/")
def index():
    return make_response(render_template("index.html"))


@app.route("/rooms", methods=["GET", "POST"])
def getRooms():
    username = CASClient().authenticate()
    username = username.lower().strip()
    return make_response(
        render_template("availablerooms.html", username=username)
    )


@app.route("/faq")
def faq():
    # CASClient().authenticate()
    return make_response(render_template("faq.html"))


@app.route("/queryrooms", methods=["GET", "POST"])
def queryRooms():
    username = CASClient().authenticate()
    username = username.lower().strip()

    college = request.args.get("college", default="")
    firstranking = request.args.get("firstranking", default="")
    lastranking = request.args.get("lastranking", default="")
    occupancy = request.args.get("occupancy", default="")
    year = request.args.get("year", default="")
    building = request.args.get("building", default="")

    data = allRooms(
        username,
        college,
        firstranking,
        lastranking,
        occupancy,
        building,
        year,
    )
    roomids = []

    # averaging code
    if not year:
        rankings = collections.defaultdict(list)
        rankmap = collections.defaultdict(int)
        seen = set()
        for room in data:
            if room.DrawTime is not None:
                rankings[room.Room.room_id].append(room.DrawTime.draw_time)
            else:
                rankings[room.Room.room_id].append(float('inf'))
        for room in data:
            if room.Room.room_id not in seen:
                mean = sum(rankings[room.Room.room_id]) / len(
                    rankings[room.Room.room_id]
                )
                rankmap[room.Room.room_id] = mean
                seen.add(room.Room.room_id)
        data.sort(key=lambda x: rankmap[x.Room.room_id])

    average_rank = list(range(1, len(data) + 1))
    ########################

    if not firstranking:
        firstranking = 0
    else:
        firstranking = int(firstranking) - 1
    if not lastranking:
        lastranking = len(data)

    if year:
        data = data[
               max(0, int(firstranking)): min(len(data), int(lastranking))
               ]

    roomsList = []

    i = 1

    # if not year:
    #     i = max(0, int(firstranking) - 1)
    for room in data:
        if not year and i > min(len(data), int(lastranking)):
            break

        # deduplication
        if room.Room.room_id in roomids:
            continue
        roomids.append(room.Room.room_id)

        # only continue if ranking permits
        if not year and i - 1 < int(firstranking):
            print(int(firstranking))
            i += 1
            continue

        if occupancy:
            if occupancy != str(room.Room.occupancy):
                i += 1
                continue
        if building:
            if building != room.Room.building:
                # print(room.Room.building)
                i += 1
                continue

        review_count = db_session.query(Reviews).filter(Reviews.room_number == room.Room.room_no,
                                                        Reviews.building_name == room.Room.building).count()

        if year:
            roomDict = {
                "ranking": room.DrawTime.draw_time,
                "res_college": room.Room.res_college,
                "building": room.Room.building,
                "room_no": room.Room.room_no,
                "occupancy": room.Room.occupancy,
                "sq_footage": room.Room.sq_footage,
                "favorite": room[2],
                "room_id": room.Room.room_id,
                "taken": room.Room.taken,
                "number_of_reviews": review_count
            }
            roomsList.append(roomDict)
        elif room.DrawTime is None:
            roomDict = {"ranking": "UNRANKED",
                        "res_college": room.Room.res_college, "building": room.Room.building,
                        "room_no": room.Room.room_no, "occupancy": room.Room.occupancy,
                        "sq_footage": room.Room.sq_footage, "favorite": room[2], "room_id": room.Room.room_id,
                        "taken": room.Room.taken, "number_of_reviews": review_count}
            roomsList.append(roomDict)
        else:
            roomDict = {
                "ranking": i,
                "res_college": room.Room.res_college,
                "building": room.Room.building,
                "room_no": room.Room.room_no,
                "occupancy": room.Room.occupancy,
                "sq_footage": room.Room.sq_footage,
                "favorite": room[2],
                "room_id": room.Room.room_id,
                "taken": room.Room.taken,
                "number_of_reviews": review_count
            }
            roomsList.append(roomDict)
            i += 1

    response = {
        "recordsTotal": len(data),
        "recordsFiltered": len(data),
        "draw": 1,
        "data": roomsList,
    }
    return jsonify(response)


@app.route("/queryfavorites", methods=["GET", "POST"])
def queryFavorites():
    username = CASClient().authenticate()
    username = username.lower().strip()
    data = getFavoriteRooms(username)

    roomsList = []
    for room in data:
        roomDict = {
            "res_college": room.Room.res_college,
            "building": room.Room.building,
            "room_no": room.Room.room_no,
            "occupancy": room.Room.occupancy,
            "sq_footage": room.Room.sq_footage,
            "favorite": room[2],
            "room_id": room.Room.room_id,
            "taken": room.Room.taken,
        }
        roomsList.append(roomDict)
    response = {
        "recordsTotal": len(data),
        "recordsFiltered": len(data),
        "draw": 1,
        "data": roomsList,
    }
    return jsonify(response)


@app.route("/addtofavorites", methods=["GET", "POST"])
def addToFavorites():
    # we should probably just pass this from the client rather than continually authenticating
    # TODO
    # and fix this in other places too.
    username = CASClient().authenticate()
    username = username.lower().strip()
    room_id = request.args.get("room_id")

    # ajax to add favorite
    if request.method == "POST":
        addFavorite(json.loads(request.get_data()), username)
    else:
        addFavorite(room_id, username)

    # TODO - should this actually return something meaningful?
    return "success"


@app.route("/removefromfavorites", methods=["GET", "POST"])
def removeFromFravorites():
    # we should probably just pass this from the client rather than continually authenticating
    # TODO
    # and fix this in other places too.
    username = CASClient().authenticate()
    username = username.lower().strip()
    room_id = request.args.get("room_id")

    # ajax to remove favorite
    if request.method == "POST":
        removeFavorite(json.loads(request.get_data()), username)
    else:
        removeFavorite(room_id, username)

    # TODO - should this actually return something meaningful?
    return "success"


@app.route("/favorites", methods=["GET"])
def favorites():
    username = CASClient().authenticate()
    username = username.lower().strip()

    # get all of the user's favorite
    fav = allFavoriteRooms(username)
    fav_headings = (
        "BUILDING",
        "ROOM NO.",
        "OCCUPANCY",
        "SQ. FOOTAGE",
        "FAVORITE",
    )
    return render_template(
        "favorites.html", headings=fav_headings, data=fav
    )


@app.route("/map")
def map():
    # CASClient().authenticate()

    allrank = defaultdict(int)
    buildingrank = defaultdict(list)
    maxrank = defaultdict(int)
    minrank = defaultdict(int)
    nolaundry = [
        "Foulke",
    ]

    dorms = [
        "Butler College",
        "Forbes College",
        "Mathey College",
        "Rockefeller College",
        "Whitman College",
        "First College",
        "Upperclass",
    ]
    for i in dorms:
        data = allRooms("", i, "", "", "", "", "2019")
        for room in data:
            building = room.Room.building
            buildingrank[building].append(int(room.DrawTime.draw_time))

    for building in buildingrank:
        allrank[building] = sum(buildingrank[building]) / len(
            buildingrank[building]
        )
        maxrank[building] = max(buildingrank[building])
        minrank[building] = min(buildingrank[building])

    return make_response(
        render_template(
            "map.html",
            allrank=allrank,
            maxrank=maxrank,
            minrank=minrank,
        )
    )


@app.route("/addgroup", methods=["GET", "POST"])
def addGroup():
    data = json.loads(request.get_data())
    username = data[2].strip()
    data[0].append(username)

    # add to groups
    if request.method == "POST":
        addNewGroup(data[0], data[1], username)
    else:
        addNewGroup(data[0], data[1], username)

    # TODO - should this actually return something meaningful?
    return "success"


@app.route("/logout", methods=["GET"])
def logout():
    casClient = CASClient()
    casClient.authenticate()
    casClient.logout()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route("/populategroups", methods=["GET"])
def populategroups():
    username = CASClient().authenticate()
    username = username.lower().strip()
    groups = getUserGroups(username)

    room_id = request.args.get("room_id", default="")

    # need to return group name and list of rooms
    groups_list = []
    if groups != False:
        for g_id, group_dict in groups.items():
            data = {}
            data["group_id"] = g_id
            data["name"] = group_dict["name"]

            room_ids_list = [r.room_id for r in group_dict["rooms"]]
            data["favorited"] = (
                True if int(room_id) in room_ids_list else False
            )
            groups_list.append(data)

    return jsonify({"data": groups_list})


@app.route("/groups", methods=["GET", "POST"])
def groups():
    username = CASClient().authenticate()
    username = username.lower().strip()
    groups = getUserGroups(username)

    has_groups = True
    if not groups:
        has_groups = False

    return make_response(
        render_template(
            "groups.html", has_groups=has_groups, groups=groups
        )
    )


@app.route("/addroomtogroup", methods=["POST"])
def addroomtogroup():
    data = json.loads(request.get_data())
    room_id = data["room_id"]
    group_id = data["group_id"]
    username = data["username"]

    addRoomToGroup(
        username,
        json.loads(request.get_data())["room_id"],
        json.loads(request.get_data())["group_id"],
    )

    # TODO - should this actually return something meaningful?
    return "yay"


@app.route("/removeroomfromgroup", methods=["POST"])
def removeroomfromgroup():
    # we should probably just pass this from the client rather than continually authenticating
    # TODO
    # and fix this in other places too.
    username = CASClient().authenticate()
    username = username.lower().strip()
    room_id = request.args.get("room_id")
    group_id = request.args.get("group_id")
    # ajax to add favorite
    if request.method == "POST":
        removeRoomFromGroup(
            username,
            json.loads(request.get_data())["room_id"],
            json.loads(request.get_data())["group_id"],
        )
    else:
        removeRoomFromGroup(username, room_id, group_id)

    # TODO - should this actually return something meaningful?
    return "yay"


@app.route("/deletegroup", methods=["GET"])
def deletegroup():
    group_id = request.args.get("group_id")
    success = deleteGroup(group_id)

    # error handling? TODO
    if success:
        return "true!"
    else:
        return "true"


# @app.route("/update")
# def update():
#     response = render_template("housing.html")
#     return make_response(response)

# checks for 3 minutes after start is pressed


# @app.route("/start", methods=['GET'])
# def startRoomDraw():
#     clearRoomStatuses()
#     i = 0
#     while i < 18:
#         print("checking")
#         checkRooms()
#         i += 1
#         time.sleep(10)
#     print("done")
#     return "success"

# @app.route("/checkonce", methods=['GET'])
# def checkOnce():
#     print("here")
#     checkRooms()
#     print("here")
#     return "success"


# @app.route("/changerooms", methods=['GET'])
# def changeHowRoomsDrew():
#     status = request.args.get('status')
#     changeRoomPdf(status)
#     return "success"


# @app.route("/clearrooms", methods=['GET'])
# def clearRooms():
#     os.remove("static/pdfs/howroomsdrew.pdf")
#     clearRoomStatuses()
#     changeRoomPdf("reset")

#     return "success"


@app.route("/isuserstudent", methods=["GET"])
def isuserstudent():
    username = request.args.get("username")
    if username is None:
        return "False"

    is_student = check_is_undergrad(username)
    if is_student:
        return "True"
    return "False"


@app.route("/editgroup", methods=["POST"])
def editGroup():
    data = json.loads(request.get_data())
    group_id = data["group_id"]
    group_name = data["group_name"]
    members = data["members"]
    editGroupInfo(group_id, group_name, members)
    return "True"


@app.route("/getgroupsjson", methods=["GET"])
def getGroupsJSON():
    username = CASClient().authenticate()
    username = username.lower().strip()
    groups = getUserGroupsJSON(username)
    username = username.strip()

    has_groups = True
    if len(groups) == 0:
        has_groups = False
    return jsonify(
        {
            "groups": groups,
            "has_groups": has_groups,
            "username": username,
        }
    )


@app.route('/submitReview', methods=['POST'])
def submit_review():
    # username = "proxy"
    username = CASClient().authenticate()
    valid_ratings = ['0', '1', '2', '3', '4', '5']
    building_name = request.form['building-name']
    room_no = request.form['room-number']
    overall_rating = request.form['overall-rating']
    written_review = request.form['written-review']
    first_checkbox = request.form.getlist('submission-check-1')
    second_checkbox = request.form.getlist('submission-check-2')
    # restrict user to one review per room
    user_search = db_session.query(Reviews).filter(Reviews.building_name == building_name,
                                                   Reviews.room_number == room_no,
                                                   Reviews.net_id == username).first()
    if user_search:
        message = "You can only submit at most one review per room. Contact it.admin@tigerapps.org to edit your current review."
        return jsonify(message=message), 400
    if overall_rating not in valid_ratings:
        message = "Your review rating was not between 1 and 5. Please submit again with" \
                  " a valid rating."
        return jsonify(message=message), 400
    if written_review == "":
        message = "You cannot leave your review empty. Please submit again with text."
        return jsonify(message=message), 400
    if first_checkbox is None or second_checkbox is None:
        message = "Both checkboxes were not checked. Be sure to understand both conditions before submitting."
        return jsonify(message=message), 400
    review = Reviews(building_name=building_name, room_number=room_no, rating=int(overall_rating),
                     content=written_review, net_id=username)
    db_session.add(review)
    db_session.commit()
    message = "Your review was successfully submitted!"
    return jsonify(message=message), 200
