"""
Room positions for New College West buildings extracted from floor plan images.
All coordinates are (x, y) pixel positions in the full 2048x1326 floor plan images.
Positions represent approximate center of each room.

Buildings:
- Kanji Hall (prefix B) - levels 00, 02, 03, 04, 05, 06
- Kwanza Jones Hall (prefix C) - levels 00, 01, 02, 03, 04, 05, 06
- Addy Hall (prefix A) - levels 03, 04, 05, 06, 07

Floor plan images are at:
  data-scraping/archived_images/Room_Plans/New_College_West/{Hall_Name}/level_{NN}.png
"""

# =============================================================================
# KANJI HALL (Building B)
# Image dimensions: 2048x1326
# L-shaped building:
#   Left wing runs upper-left to lower-right: x~200-1050, y~680-1000
#   Right wing runs vertically downward: x~1050-1450, y~100-1050
# =============================================================================
kanji_floors = {
    "G": {  # level_00 - Ground floor (left wing only)
        "B002": (280, 750),
        "B003": (350, 880),
        "B004": (480, 750),
        "B005": (580, 750),
        "B006": (700, 880),
    },
    "2": {  # level_02 - Second floor (full L-shape)
        # Left wing - upper row (north side)
        "B204": (310, 730),
        "B205": (430, 730),
        # Left wing - lower row (south side)
        "B203": (250, 890),
        "B202": (400, 840),
        "B202B": (530, 910),
        "B201B": (680, 910),
        "B201": (780, 900),
        "B201A": (870, 910),
        # Junction / center rooms
        "B210": (810, 750),
        "B212": (990, 740),
        "B213": (1090, 740),
        "B229C": (940, 880),
        "B229": (1000, 920),
        "B229A": (1100, 940),
        # Right wing - left column (west side, going south)
        "B221": (1130, 340),
        "B220": (1130, 430),
        "B219": (1130, 510),
        "B218": (1130, 590),
        "B217B": (1130, 665),
        "B217": (1130, 735),
        "B217A": (1130, 810),
        "B216": (1130, 880),
        # Right wing - right column (east side, going south)
        "B223B": (1350, 230),
        "B223A": (1350, 330),
        "B224A": (1350, 420),
        "B224": (1350, 505),
        "B224B": (1350, 580),
        "B225A": (1350, 650),
        "B225": (1350, 725),
        "B225B": (1370, 820),
        "B227": (1370, 930),
    },
    "3": {  # level_03 - Third floor (full L-shape)
        # Left wing - upper row
        "B304": (310, 730),
        "B305": (430, 730),
        # Left wing - lower row
        "B303": (250, 890),
        "B302": (400, 840),
        "B302B": (530, 910),
        "B301B": (680, 910),
        "B301": (780, 900),
        "B301A": (870, 910),
        # Junction / center rooms
        "B310": (810, 750),
        "B312": (990, 740),
        "B313": (1090, 740),
        "B329": (1000, 900),
        "B329A": (1100, 940),
        # Right wing - left column (west side, going south)
        "B321": (1130, 340),
        "B320": (1130, 430),
        "B319": (1130, 510),
        "B318": (1130, 590),
        "B317B": (1130, 665),
        "B317": (1130, 735),
        "B317A": (1130, 810),
        "B316": (1130, 880),
        # Right wing - right column (east side, going south)
        "B323B": (1350, 230),
        "B323A": (1350, 330),
        "B324A": (1350, 420),
        "B324": (1350, 505),
        "B324B": (1350, 580),
        "B325A": (1350, 650),
        "B325": (1350, 725),
        "B325B": (1370, 820),
        "B326": (1370, 890),
        "B327": (1370, 960),
    },
    "4": {  # level_04 - Fourth floor (reduced right wing)
        # Left wing - upper row
        "B403": (310, 730),
        "B408": (430, 730),
        # Left wing - lower row
        "B401": (250, 890),
        "B402": (400, 840),
        "B402B": (530, 910),
        # Junction / right side
        "B410": (680, 810),
        "B410A": (780, 810),
        "B411": (920, 820),
        "B411B": (1000, 800),
        "B411A": (1090, 810),
        "B415": (1100, 920),
        "B415A": (1100, 980),
    },
    "5": {  # level_05 - Fifth floor (left wing + partial right)
        # Left wing - upper row
        "B503": (310, 730),
        "B508": (430, 730),
        "B510": (580, 730),
        # Left wing - lower row
        "B501": (250, 890),
        "B502": (400, 840),
        "B502B": (530, 910),
        # Right side
        "B516": (1100, 870),
    },
    "6": {  # level_06 - Sixth floor (left wing + partial right)
        # Left wing - upper row
        "B603": (310, 730),
        "B608": (430, 730),
        "B610": (580, 730),
        # Left wing - lower row
        "B601": (250, 890),
        "B602": (400, 840),
        "B602B": (530, 910),
        # Right side
        "B612": (1150, 950),
    },
}


# =============================================================================
# KWANZA JONES HALL (Building C)
# Image dimensions: 2048x1326
# Angular/curved building with horizontal wing + vertical stem:
#   Horizontal wing: x~350-1100, y~380-660
#   Vertical stem (going south): x~870-1200, y~600-1100
# =============================================================================
jones_floors = {
    "G": {  # level_00 - Ground floor
        # Horizontal wing - top row (north) - left to right
        "C003": (570, 505),
        "C004": (660, 505),
        "C005": (735, 505),
        "C006": (810, 505),
        "C007": (890, 505),
        # Horizontal wing - bottom row (south) - left to right
        "C001B": (505, 610),
        "C001": (565, 610),
        "C001A": (625, 610),
        "C009B": (680, 610),
        # Right area / junction rooms
        "C008": (960, 610),
        "C009": (960, 700),
        # Stem - left column (going south)
        "C023": (920, 780),
        "C022": (920, 840),
        "C021": (920, 900),
        "C020": (920, 960),
        "C019": (920, 1020),
        # Stem - right column (going south)
        "C016B": (1070, 780),
        "C016A": (1070, 840),
        "C017B": (1070, 900),
        "C017": (1070, 960),
        "C017A": (1070, 1040),
    },
    "1": {  # level_01 - First floor
        # Horizontal wing - top row (north) - left to right
        "C108": (435, 440),
        "C110": (680, 440),
        "C111": (770, 440),
        "C112": (860, 440),
        # Horizontal wing - bottom row (south) - left to right
        "C108B": (420, 580),
        "C102": (490, 580),
        "C102A": (570, 580),
        "C101B": (650, 580),
        "C101": (730, 580),
        "C101A": (800, 580),
        "C109B": (870, 580),
        # Right side / junction
        "C113": (975, 530),
        "C115": (975, 600),
        # Stem - left column (going south)
        "C125B": (920, 730),
        "C125": (920, 790),
        "C125A": (920, 860),
        "C124": (920, 1010),
        # Stem - right column (going south)
        "C116": (1070, 670),
        "C120B": (1070, 730),
        "C120A": (1070, 800),
        "C121B": (1070, 860),
        "C121A": (1070, 930),
        "C122": (1100, 1020),
    },
    "2": {  # level_02 - Second floor
        # Horizontal wing - top row (north)
        "C208": (470, 430),
        "C209": (800, 430),
        # Horizontal wing - bottom row (south) - left to right
        "C208B": (420, 580),
        "C202": (490, 580),
        "C202A": (570, 580),
        "C201B": (650, 580),
        "C201": (730, 580),
        "C201A": (800, 580),
        "C209B": (870, 580),
        # Right side / junction
        "C210": (950, 500),
        "C205": (1020, 550),
        "C211": (1050, 640),
        # Stem - left column (going south)
        "C225": (920, 700),
        "C223A": (920, 770),
        "C223": (920, 830),
        "C222A": (920, 890),
        "C222": (920, 950),
        # Stem - right column (going south)
        "C218B": (1070, 700),
        "C214B": (1070, 760),
        "C218A": (1070, 830),
        "C219B": (1070, 890),
        "C219A": (1070, 950),
        "C220": (1100, 1030),
    },
    "3": {  # level_03 - Third floor (horizontal wing only, no stem)
        # Horizontal wing - top row (north)
        "C308": (470, 430),
        "C306": (800, 430),
        # Horizontal wing - bottom row (south) - left to right
        "C308B": (420, 580),
        "C302": (490, 580),
        "C302A": (570, 580),
        "C301B": (650, 580),
        "C301": (730, 580),
        "C301A": (800, 580),
        "C318": (870, 580),
        # Right area rooms - two rows
        "C310": (950, 500),
        "C311": (1000, 580),
        "C313B": (960, 620),
        "C316": (1070, 530),
        "C316A": (1070, 600),
        "C314B": (1140, 570),
    },
    "4": {  # level_04 - Fourth floor (horizontal wing only)
        # Horizontal wing - top row
        "C408": (470, 430),
        "C406": (800, 430),
        # Horizontal wing - bottom row
        "C408B": (420, 580),
        "C402": (490, 580),
        "C402A": (570, 580),
        "C401B": (650, 580),
        "C401": (730, 580),
        "C401A": (800, 580),
        "C418": (870, 580),
        # Right area rooms
        "C410": (950, 500),
        "C413B": (960, 600),
        "C411": (1000, 580),
        "C416": (1070, 530),
        "C416A": (1070, 600),
        "C414B": (1140, 570),
    },
    "5": {  # level_05 - Fifth floor (horizontal wing, reduced right)
        # Horizontal wing - top row
        "C503": (430, 430),
        "C501A": (690, 430),
        "C510": (810, 430),
        # Horizontal wing - bottom row
        "C502B": (420, 580),
        "C502": (490, 580),
        "C502A": (570, 580),
        "C501B": (650, 580),
        "C501": (730, 580),
        "C509A": (800, 580),
        "C509B": (870, 580),
        # Right side
        "C510C": (960, 530),
        "C515": (960, 600),
        "C513": (1030, 590),
    },
    "6": {  # level_06 - Sixth floor (horizontal wing, reduced right)
        # Horizontal wing - top row
        "C603": (430, 430),
        "C600": (570, 430),
        "C601A": (690, 430),
        "C610": (810, 430),
        # Horizontal wing - bottom row
        "C602B": (420, 580),
        "C602": (490, 580),
        "C602A": (570, 580),
        "C601B": (650, 580),
        "C601": (730, 580),
        "C609A": (800, 580),
        "C618": (870, 580),
        # Right side
        "C610C": (960, 530),
        "C615": (960, 600),
        "C613": (1030, 590),
    },
}


# =============================================================================
# ADDY HALL (Building A)
# Image dimensions: 2048x1326
# Curved/L-shaped building running from upper-left to lower-right:
#   Left arm: x~350-700, y~200-600
#   Center: x~600-1000, y~400-800
#   Right arm: x~1000-1450, y~600-950
# =============================================================================
addy_floors = {
    "3": {  # level_03 - Third floor
        # Left arm (upper-left)
        "A308A": (415, 280),
        "A308": (480, 370),
        "A308B": (570, 370),
        "A307": (440, 480),
        # Center
        "A306": (620, 530),
        "A310": (720, 500),
        "A312": (940, 660),
        # Center-right
        "A305": (760, 640),
        "A304": (860, 720),
        # Right arm
        "A314A": (1120, 700),
        "A314": (1180, 740),
        "A314B": (1230, 710),
        "A315": (1300, 700),
    },
    "4": {  # level_04 - Fourth floor
        # Left arm
        "A408A": (415, 290),
        "A408": (480, 370),
        "A408B": (570, 380),
        "A407": (440, 480),
        # Center
        "A406": (620, 530),
        "A410": (720, 510),
        "A412": (940, 660),
        # Center-right
        "A405": (760, 640),
        "A404": (860, 720),
        # Right arm - upper row
        "A414A": (1120, 700),
        "A414": (1180, 740),
        "A414B": (1230, 710),
        "A415": (1270, 700),
        "A416": (1340, 690),
        # Right arm - lower row
        "A420": (1200, 810),
        "A419": (1270, 810),
        "A418": (1360, 810),
    },
    "5": {  # level_05 - Fifth floor
        # Left arm
        "A508A": (415, 270),
        "A508": (480, 360),
        "A508B": (570, 370),
        "A507": (440, 470),
        # Center
        "A506": (620, 530),
        "A510": (720, 510),
        "A512": (940, 660),
        # Center-right
        "A505": (760, 640),
        "A504": (860, 720),
        # Right arm - upper row
        "A514A": (1120, 700),
        "A514": (1180, 740),
        "A514B": (1230, 710),
        "A515B": (1310, 680),
        "A515C": (1370, 680),
        # Right arm - lower row
        "A516": (1200, 800),
        "A515E": (1270, 810),
        "A515": (1340, 790),
        "A515D": (1350, 850),
    },
    "6": {  # level_06 - Sixth floor
        # Left arm
        "A609A": (415, 280),
        "A609": (450, 370),
        "A610": (550, 370),
        "A611": (600, 370),
        "A607": (440, 470),
        # Center
        "A606A": (620, 540),
        "A613": (720, 510),
        "A615": (1000, 660),
        "A615A": (1060, 680),
        # Center-right
        "A606": (700, 600),
        "A605": (760, 640),
        "A604": (860, 710),
        "A604A": (910, 760),
        # Right arm - upper row
        "A617A": (1120, 700),
        "A617": (1180, 740),
        "A617B": (1230, 710),
        "A618B": (1310, 680),
        "A618C": (1370, 680),
        # Right arm - lower row
        "A618E": (1270, 810),
        "A618": (1340, 790),
        "A618D": (1350, 850),
    },
    "7": {  # level_07 - Seventh floor (reduced - left/center only)
        # Left arm
        "A709A": (415, 280),
        "A709": (450, 370),
        "A710": (550, 370),
        "A711": (600, 370),
        "A708": (440, 470),
        "A707": (440, 530),
        # Center
        "A706A": (620, 540),
        "A713": (720, 510),
        "A715": (1000, 660),
        "A715A": (1060, 680),
        # Center-right
        "A706": (700, 600),
        "A705": (760, 640),
        "A704": (860, 710),
        "A704A": (910, 760),
    },
}
