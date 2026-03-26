"""
Generate room_positions.json from visually-extracted room positions.

Each building has:
- polygon: geographic coordinates [lat, lng]
- drawing_bounds: (x, y, w, h) of actual drawing area in the image
- image_size: (width, height) of the source image
- orientation: how the floor plan maps to geography
  'NE_right' means right side of image = NE, left = SW (most Yeh/NCW buildings)
- rooms: dict of room_no -> (px, py) pixel position in full image
"""

import json
import math

# ===== BUILDING DATA =====
# Each entry: polygon coords, drawing bounds, image size, rooms by floor

BUILDINGS = {}

# ===== HARIRI HALL (Yeh College) =====
# Polygon runs NE to SW. Building is long, oriented roughly NE-SW.
# In the floor plan: left = NW/W end, right = E/NE end
# Top of image = north side of building, bottom = south side
HARIRI_POLYGON = [
    [40.3428141, -74.6543544], [40.3427746, -74.6543364],
    [40.3426632, -74.6547579], [40.3425660, -74.6547137],
    [40.3426433, -74.6544202], [40.3426774, -74.6542922],
    [40.3427154, -74.6543097], [40.3428083, -74.6539583],
    [40.3429069, -74.6540032], [40.3428141, -74.6543544],
]
HARIRI_DRAW_BOUNDS = (50, 300, 2850, 1200)  # x, y, w, h in 3400x2200 image

# Hariri anchor points: the floor plan is rotated ~20° from axis-aligned.
# Building runs NE-SW. In image: left=SW, right=NE, top=NW side, bottom=SE side.
# top_left of drawing = NW corner of SW end ≈ vertex 3 area
# top_right of drawing = N corner of NE end ≈ vertex 9
# bottom_left of drawing = S corner of SW end ≈ vertex 4
HARIRI_ANCHORS = {
    'top_left':    [40.3427100, -74.6547800],  # NW end of main wing
    'top_right':   [40.3429069, -74.6540032],  # NE end (northernmost point)
    'bottom_left': [40.3425400, -74.6546500],  # SW end, south side
}

BUILDINGS["HARIRI"] = {
    "polygon": HARIRI_POLYGON,
    "draw_bounds": HARIRI_DRAW_BOUNDS,
    "image_size": (3400, 2200),
    "anchors": HARIRI_ANCHORS,
    "floors": {
        "3": {
            # Top row (north side) - left to right
            "A317": (350, 880), "A318": (520, 840),
            "A320A": (800, 780), "A320": (920, 780), "A320B": (1070, 780),
            # Bottom row (south side) - left to right
            "A316B": (240, 1130), "A316": (420, 1130),
            "A316A": (580, 1130), "A315": (850, 1130),
            # Middle section - top row
            "A301A": (1530, 820), "A301": (1670, 820), "A301B": (1820, 820),
            "A303A": (2000, 820), "A303": (2120, 820),
            # Middle section - bottom
            "A311A": (1630, 1000), "A311B": (1800, 1000),
            # Right section (NE end)
            "A304": (2350, 830), "A305": (2480, 830), "A306": (2620, 800),
            "A308": (2560, 1070),
        },
        "4": {
            "A401A": (1680, 790), "A402": (1870, 790),
            "A403A": (2050, 790), "A403": (2170, 790), "A403B": (2290, 790),
            "A404": (2420, 790), "A405": (2580, 790),
            "A407": (2700, 1100),
            "A410A": (1700, 1000), "A410": (1850, 1000),
            "A412": (1350, 1100),
            "A416": (950, 1150), "A417": (650, 1200),
            "A418A": (520, 1200), "A418": (380, 1050), "A418B": (380, 870),
            "A419": (570, 870),
            "A421A": (770, 870), "A421": (900, 870), "A421B": (1030, 870),
        },
        "5": {
            "A501": (1680, 790), "A502": (1870, 790),
            "A503A": (2050, 790), "A503": (2170, 790), "A503B": (2290, 790),
            "A504": (2420, 790), "A505": (2580, 790),
            "A507": (2700, 1100),
            "A510A": (1700, 1000), "A510B": (1850, 1000),
            "A512": (1350, 1100),
            "A516": (950, 1150), "A517": (650, 1200),
            "A518A": (520, 1200), "A518": (380, 1050), "A518B": (380, 870),
            "A519": (570, 870),
            "A521A": (770, 870), "A521": (900, 870), "A521B": (1030, 870),
        },
        "6": {
            "A601A": (1530, 790), "A601": (1670, 790), "A601B": (1810, 790),
            "A603A": (1980, 790), "A603": (2120, 790),
            "A604": (2270, 790), "A605": (2420, 790), "A606": (2600, 790),
            "A608": (2700, 1100),
            "A613A": (1700, 1000), "A613B": (1850, 1000),
            "A614": (1350, 1150), "A615": (1250, 1150),
        },
    }
}

# ===== ADDY HALL (New College West) =====
ADDY_POLYGON = [
    [40.3426246, -74.6556793], [40.3425674, -74.6557058],
    [40.3425532, -74.6556531], [40.3425154, -74.6556706],
    [40.3424554, -74.6554483], [40.3424560, -74.6551458],
    [40.34231, -74.65509], [40.34236, -74.65493],
    [40.3425200, -74.6549952], [40.3425198, -74.6550154],
    [40.3425554, -74.6550156], [40.3425553, -74.6550527],
    [40.3425833, -74.6550528], [40.3425828, -74.6553948],
    [40.3425542, -74.6553947], [40.3425541, -74.6554169],
    [40.3426246, -74.6556793],
]

# ===== MANNION HALL (Yeh College) =====
# Building is L-shaped. Main body runs E-W, wing goes south on east end.
# In floor plan: left=west, right=east, top=north, bottom=south
MANNION_POLYGON = [
    [40.3415058, -74.6539918], [40.3415069, -74.6536476],
    [40.3415479, -74.6536486], [40.3415478, -74.6533825],
    [40.3416558, -74.6533867], [40.3416545, -74.6537323],
    [40.3416263, -74.6537317], [40.3416233, -74.6539069],
    [40.3416781, -74.6539285], [40.3416333, -74.6540997],
    [40.3415968, -74.6540699], [40.3415283, -74.6543114],
    [40.3414308, -74.6542706], [40.3415058, -74.6539918],
]
MANNION_DRAW_BOUNDS = (50, 300, 2700, 1300)  # approximate for 3400x2200

# Mannion runs roughly N-S with a wing going east. The floor plan has
# the main body horizontal (left=west, right=east), wing going down (south).
# Looking at polygon: the building is roughly axis-aligned but slightly tilted.
MANNION_ANCHORS = {
    'top_left':    [40.3416781, -74.6542500],  # NW corner
    'top_right':   [40.3416558, -74.6533825],  # NE corner
    'bottom_left': [40.3414308, -74.6543114],  # SW corner
}

BUILDINGS["MANNION"] = {
    "polygon": MANNION_POLYGON,
    "draw_bounds": MANNION_DRAW_BOUNDS,
    "image_size": (3400, 2200),
    "anchors": MANNION_ANCHORS,
    "floors": {
        "1": {
            # Top row (north) - west to east
            "D103C": (200, 890), "D103D": (350, 890), "D104B": (470, 890),
            "D104": (620, 890), "D107": (1050, 780),
            # Middle row
            "D103": (230, 990),
            # North-east section (upper)
            "D109": (1300, 850), "D110": (1470, 900),
            "D112A": (1720, 850), "D112": (1850, 850), "D112B": (2000, 850),
            "D113": (2150, 880),
            # Bottom row (south) - west to east
            "D103B": (200, 1280), "D103A": (370, 1280),
            "D102B": (500, 1280), "D102": (680, 1280),
            # South-east section
            "D125B": (1210, 1080), "D125": (1300, 1080), "D125A": (1420, 1080),
            "D123": (1750, 1100), "D122": (1900, 1150),
            "D115": (2350, 1090), "D115A": (2550, 1100),
            "D118": (2300, 1250), "D117": (2450, 1320),
        },
    }
}

# ===== FU HALL (Yeh College) =====
FU_POLYGON = [
    [40.3426433, -74.6544202], [40.3426774, -74.6542922],
    [40.3424389, -74.6541827], [40.3424712, -74.6540617],
    [40.3424341, -74.6540446], [40.3424995, -74.6537954],
    [40.3424024, -74.6537515], [40.3423369, -74.6540007],
    [40.3423700, -74.6540152], [40.3423166, -74.6542153],
    [40.3423054, -74.6542129], [40.3422355, -74.6543235],
    [40.3421467, -74.6544640], [40.3421125, -74.6545180],
    [40.3421950, -74.6546079], [40.3423880, -74.6543028],
]

# ===== GROUSBECK HALL (Yeh College) =====
GROUSBECK_POLYGON = [
    [40.3416333, -74.6540997], [40.3416781, -74.6539285],
    [40.3417794, -74.6535625], [40.3419149, -74.6536294],
    [40.3419153, -74.6534899], [40.3420222, -74.6534951],
    [40.3420237, -74.6537130], [40.3419828, -74.6537144],
    [40.3419817, -74.6541569], [40.3419756, -74.6541998],
    [40.3422355, -74.6543235], [40.3421467, -74.6544640],
    [40.3419492, -74.6543724], [40.3419167, -74.6544333],
    [40.3418066, -74.6543522], [40.3418446, -74.6542028],
    [40.3416333, -74.6540997],
]


def pixel_to_geo(px, py, draw_bounds, polygon, anchors=None):
    """Convert pixel position to lat/lng using affine transformation.

    If anchors are provided, uses 3 geographic anchor points for the
    transformation (handles rotated buildings):
      anchors = {
        'top_left': [lat, lng],     # geographic point at drawing top-left
        'top_right': [lat, lng],    # geographic point at drawing top-right
        'bottom_left': [lat, lng],  # geographic point at drawing bottom-left
      }

    Otherwise falls back to axis-aligned bounding box mapping.
    """
    dx, dy, dw, dh = draw_bounds

    # Normalize to 0-1 within drawing area
    norm_x = max(0, min(1, (px - dx) / dw)) if dw > 0 else 0.5
    norm_y = max(0, min(1, (py - dy) / dh)) if dh > 0 else 0.5

    if anchors:
        # Affine: P = top_left + norm_x * (top_right - top_left) + norm_y * (bottom_left - top_left)
        tl = anchors['top_left']
        tr = anchors['top_right']
        bl = anchors['bottom_left']

        lat = tl[0] + norm_x * (tr[0] - tl[0]) + norm_y * (bl[0] - tl[0])
        lng = tl[1] + norm_x * (tr[1] - tl[1]) + norm_y * (bl[1] - tl[1])
    else:
        # Fallback: axis-aligned bounding box
        lats = [c[0] for c in polygon]
        lngs = [c[1] for c in polygon]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        lat = max_lat - norm_y * (max_lat - min_lat)
        lng = min_lng + norm_x * (max_lng - min_lng)

    return round(lat, 7), round(lng, 7)


def generate_positions():
    """Generate room_positions.json from visual data."""
    output = {}

    for building_name, data in BUILDINGS.items():
        polygon = data["polygon"]
        draw_bounds = data["draw_bounds"]
        anchors = data.get("anchors")
        building_rooms = {}

        for floor_key, rooms in data["floors"].items():
            for room_no, (px, py) in rooms.items():
                lat, lng = pixel_to_geo(px, py, draw_bounds, polygon, anchors)
                building_rooms[room_no] = [lat, lng]

        if building_rooms:
            output[building_name] = building_rooms
            print(f"{building_name}: {len(building_rooms)} rooms positioned")

    return output


if __name__ == "__main__":
    positions = generate_positions()

    output_path = "static/assets/js/room_positions.json"
    with open(output_path, 'w') as f:
        json.dump(positions, f, indent=2)

    total = sum(len(v) for v in positions.values())
    print(f"\nTotal: {total} rooms across {len(positions)} buildings")
    print(f"Saved to {output_path}")
