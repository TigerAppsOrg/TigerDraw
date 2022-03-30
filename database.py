import psycopg2
from parse import load_txt
import datetime


def connect():
    try:
        conn = psycopg2.connect(
            database="test",
            user="postgres",
            password="0000",
            host="localhost",
            port="5432",
        )

        cur = conn.cursor()

    except (Exception, psycopg2.DatabaseError) as error:
        print("Error while connecting", error)

    return conn, cur


def create_tables(conn):
    # Create draw_time
    try:
        query = "CREATE TABLE draw_time (room_id INT, year INT, draw_time TIMESTAMP, PRIMARY KEY (room_id, year))"
        cur.execute(query)
    except:
        print("Error while creating draw_time")

    # Create building
    try:
        query = "CREATE TABLE building (room_id INT PRIMARY KEY, building TEXT, room_no TEXT)"
        cur.execute(query)
    except:
        print("Error while creating building")

    # Create res_college
    try:
        query = "CREATE TABLE res_college (college TEXT PRIMARY KEY, dorms TEXT[])"
        cur.execute(query)
    except:
        print("Error while creating res_college")

    conn.commit()


def get_roomid(bldg, room_no):
    return 0


def read_txt(year):
    pass


def read_pdf(year):
    pass


def main():
    conn, cur = connect()
    # create_tables(conn)

    data2017 = load_txt("roomdraw-2017.txt")
    month = 4
    year = 2017

    for row in data2017:
        try:
            # inserting values into the date_time table
            if row:
                dt = str(
                    datetime.date(int(year), int(month), int(row[2]))
                )
                timestr = row[3]

                if len(timestr) == 5:
                    hour = int(timestr[:1])
                    minute = int(timestr[1:3])
                    second = int(timestr[3:5])
                else:
                    hour = int(timestr[:2])
                    minute = int(timestr[2:4])
                    second = int(timestr[4:6])

                dt += " " + str(datetime.time(hour, minute, second))
                # cur.execute('INSERT INTO draw_time VALUES(%s, %s, %s)', (room_id, 2017, dt))
                cur.execute(
                    "INSERT INTO draw_time VALUES(%s, %s, %s)",
                    (get_roomid(row[0], row[1]), 2018, dt),
                )

        except Exception as e:
            print("Error loading draw_time: ", e)

        room_id += 1

    conn.commit()


if __name__ == "__main__":
    main()
