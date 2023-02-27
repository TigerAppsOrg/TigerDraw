## Convert Princeton's .pdf room draw time format to a more usable .csv
## author: Daniel Carter
## Do whatever you want with this code.

from PyPDF2 import PdfFileReader


def college_to_csv(college, group_no_included=False):
    """Convert {college}.pdf to {college}.csv"""
    path_in = college + ".pdf"
    path_out = college + ".csv"

    # First row of table (different for Spelman)
    if group_no_included:
        boilerplate = "PUID\nClass Year\nLast Name\nFirst Name\nGroup #\nDraw Time\n"
    else:
        boilerplate = "PUID\nClass Year\nLast Name\nFirst Name\nDraw Time\n"

    # Read pdf and convert to a list of rows
    pdf_reader = PdfFileReader(path_in)
    rows = []
    for page_index in range(pdf_reader.getNumPages()):
        s = pdf_reader.getPage(page_index).extractText()
        if s.startswith(boilerplate):
            s = s[len(boilerplate) :]
            rows.append(boilerplate.strip().split("\n"))
        while s:  # Extract rows from a page
            puid = s[:9]
            s = s[9:]
            # For some reason Joy Cho doesn't have a class year.
            if s[0].isdigit():
                year = s[:4]
                s = s[4:]
            else:
                year = ""
            num_index = 0
            while not s[num_index].isdigit():
                num_index += 1
            name = s[:num_index].strip().replace("\n", ",")
            # Fix weird cases where there is no separation between first and last name
            #  by splitting at the second capital letter.
            # This will fail for people that don't have exactly one capital letter
            #  in their first name. Oh well.
            if "," not in name:
                for i in range(len(name) - 1, 0, -1):
                    if name[i].isupper():
                        name = name[:i] + "," + name[i:]
                        break
                else:
                    name += ","
            s = s[num_index:]
            n_index = s.index("\n")
            # Spelman also included Group #
            if group_no_included:
                group = s[:5]
                s = s[5:]
                n_index -= 5
            time = s[:n_index]
            s = s[n_index + 1 :]
            if group_no_included:
                rows.append([puid, year, name, group, time])
            else:
                rows.append([puid, year, name, time])
    # Write rows as .csv
    out = open(path_out, "w")
    for row in rows:
        out.write(",".join(row) + "\n")
    out.close()


DORMS = [
    "1901",
    "1903",
    "1967",
    "1976",
    "1981",
    "99ALEXANDER",
    "Addy Hall",
    "Aliya Kanji Hall",
    "BAKER",
    "BLAIR",
    "BLOOMBERG",
    "BOGLE",
    "Bosque Hall",
    "BROWN",
    "BUYERS",
    "CAMPBELL",
    "CUYLER",
    "DOD",
    "EDWARDS",
    "FEINBERG",
    "FISHER",
    "FORBES",
    "FOULKE",
    "Grousbeck Hall",
    "H Hall",
    "HAMILTON",
    "HARGADON",
    "HENRY",
    "HOLDER",
    "JOLINE",
    "Jose Enrique Feliciano Hall",
    "Kwanza Marion Jones Hall",
    "LAUGHLIN",
    "LAURITZEN",
    "LITTLE",
    "LOCKHART",
    "Mannion Hall",
    "MURLEY",
    "PATTON",
    "PYNE",
    "SCULLY",
    "SPELMAN",
    "WALKER",
    "WENDELL",
    "WILF",
    "WITHERSPOON",
    "WRIGHT",
    "YOSELOFF",
]

# There are no instances of 7PERSON and 8PERSON rooms in this list, but I think they exist.
SIZES = [
    "SINGLE",
    "DOUBLE",
    "TRIPLE",
    "QUAD",
    "QUINT",
    "6PERSON",
    "7PERSON",
    "8PERSON",
    "DA",
]
# Also, what is "DA"?

COLLEGES = [
    "Upperclass",
    "Butler College",
    "Whitman College",
    "Forbes College",
    "New College West",
    "Mathey College",
    "New College East",
    "Rockefeller College",
]


def rooms_to_csv(filename):
    """Convert the available rooms list to a .csv.
    filename should not include the .pdf extension."""
    path_in = filename + ".pdf"
    path_out = filename + ".csv"

    boilerplate = "Dormitory\nRoom #\nUnit Type\nSq Feet\nAffilliation\n# of Bedrooms\nCommon Room?\n"

    pdf_reader = PdfFileReader(path_in)
    rows = []
    for page_index in range(pdf_reader.getNumPages()):
        s = pdf_reader.getPage(page_index).extractText()
        if s.startswith(boilerplate):
            s = s[len(boilerplate) :]
            rows.append(boilerplate.strip().split("\n"))
        s = s.replace("\n", "")
        while s:  # Extract rows from a page
            for dorm in DORMS:
                if s.startswith(dorm):
                    s = s[len(dorm) :]
                    break
            else:  # Preamble on page 1 ends up at the end of s
                break
            i = 0
            while not any(s.startswith(size, i) for size in SIZES):
                i += 1
            room = s[:i]
            s = s[i:]
            for size in SIZES:
                if s.startswith(size):
                    s = s[len(size) :]
                    break
            i = 0
            while not any(s.startswith(college, i) for college in COLLEGES):
                i += 1
            sqft = s[:i]
            s = s[i:]
            for college in COLLEGES:
                if s.startswith(college):
                    s = s[len(college) :]
                    break
            bedrooms = s[0]
            s = s[1:]
            if s.startswith("Yes"):
                common = "Yes"
                s = s[3:]
            elif s.startswith("No"):
                common = "No"
                s = s[2:]
            else:
                common = ""
            rows.append([dorm, room, size, sqft, college, bedrooms, common])
    # Write rows as .csv
    out = open(path_out, "w")
    for row in rows:
        out.write(",".join(row) + "\n")
    out.close()


if __name__ == "__main__":
    for college in [
        "ButlerTimeOrder2022",
        "ForbesDrawOrder2022",
        "IndependentTimeOrder2022",
        "MatheyDrawOrder2022",
        "NCEDrawOrder2022",
        "NCWDrawOrder2022",
        "RockyDrawOrder2022",
        "SpelmanTimeOrder2022",
        "UpperclassDrawOrder2022",
        "WhitmanDrawOrder2022",
    ]:
        college_to_csv(college, college == "SpelmanTimeOrder2022")
        print(college, "done")

    rooms_to_csv("AvailableRoomsList2022")
    print("Available rooms done")
