"""
PG OCCUPANCY AND BILLING ENGINE
Team T015 | PS-107 | Python 3.10+
Single-file command-line project.

Run: python main.py
Data is saved automatically in pg_data.json in the same folder.
"""

import json
import calendar
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import defaultdict

DATA_FILE = Path(__file__).with_name("pg_data.json")

RENT_CARD = {
    ("single", "AC"): 18000, ("single", "Non-AC"): 14000,
    ("double", "AC"): 12000, ("double", "Non-AC"): 9500,
    ("triple", "AC"): 9000, ("triple", "Non-AC"): 7000,
}
MEAL_RATES = {"NONE": 0, "BREAKFAST": 2000, "TWO_MEALS": 4500, "FULL": 6000}
ADDON_RATES = {"laundry": 800, "two_wheeler": 500, "car": 1500}
LATE_FEE_PER_DAY = 100
MAX_LATE_FEE = 1500
ROOM_CHANGE_FEE = 1000
CLEANING_FEE = 1000


def fresh_data():
    return {
        "properties": {}, "rooms": {}, "beds": {}, "residents": {},
        "waitlist": [], "bills": {}, "electricity": {}, "next_waitlist": 1
    }


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print("Warning: saved data could not be read. Starting with empty data.")
    return fresh_data()


db = load_data()


def save_data():
    DATA_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")


def ask_date(prompt, default_today=False):
    while True:
        value = input(prompt).strip()
        if not value and default_today:
            return date.today()
        try:
            return datetime.strptime(value, "%d-%m-%Y").date()
        except ValueError:
            print("Enter date as DD-MM-YYYY.")


def money(value):
    return int(round(value))


def active_residents_in_room(room_id):
    return [
        r for r, info in db["residents"].items()
        if info["status"] == "ACTIVE" and info.get("room_id") == room_id
    ]


def available_beds():
    return [b for b, info in db["beds"].items() if info["resident_id"] is None]


def rent_for_room(room_id):
    room = db["rooms"][room_id]
    return RENT_CARD[(room["room_type"], room["ac_type"])]


def register_property():
    pid = input("Property ID: ").strip().upper()
    if not pid or pid in db["properties"]:
        print("Invalid or duplicate property ID.")
        return
    name = input("Property name: ").strip()
    location = input("Location: ").strip()
    if not name or not location:
        print("Name and location are required.")
        return
    db["properties"][pid] = {"name": name, "location": location}
    save_data()
    print("Property registered.")


def register_room():
    pid = input("Property ID: ").strip().upper()
    if pid not in db["properties"]:
        print("Property not found.")
        return
    rid = input("Room ID: ").strip().upper()
    if not rid or rid in db["rooms"]:
        print("Invalid or duplicate room ID.")
        return
    room_type = input("Room type (single/double/triple): ").strip().lower()
    if room_type not in ("single", "double", "triple"):
        print("Invalid room type.")
        return
    ac = input("AC or Non-AC: ").strip().lower()
    if ac not in ("ac", "non-ac", "nonac"):
        print("Enter AC or Non-AC.")
        return
    ac_type = "AC" if ac == "ac" else "Non-AC"
    gender = input("Allowed gender (male/female/any): ").strip().lower()
    if gender not in ("male", "female", "any"):
        print("Invalid gender.")
        return
    try:
        floor = int(input("Floor number (0 or higher): "))
        if floor < 0:
            raise ValueError
    except ValueError:
        print("Floor must be a non-negative whole number.")
        return
    capacity = {"single": 1, "double": 2, "triple": 3}[room_type]
    db["rooms"][rid] = {
        "property_id": pid, "room_type": room_type, "ac_type": ac_type,
        "gender": gender, "floor": floor, "capacity": capacity
    }
    for n in range(1, capacity + 1):
        bid = f"{rid}-B{n}"
        db["beds"][bid] = {"room_id": rid, "resident_id": None}
    save_data()
    print(f"Room registered with {capacity} bed(s).")


def register_resident():
    rid = input("Resident ID: ").strip().upper()
    if not rid or rid in db["residents"]:
        print("Invalid or duplicate resident ID.")
        return
    name = input("Resident name: ").strip()
    gender = input("Gender (male/female): ").strip().lower()
    room_pref = input("Preferred room (any/single/double/triple): ").strip().lower()
    ac_pref = input("Preferred AC (any/ac/non-ac): ").strip().lower()
    if not name or gender not in ("male", "female"):
        print("Enter a name and valid gender.")
        return
    if room_pref not in ("any", "single", "double", "triple"):
        print("Invalid room preference.")
        return
    if ac_pref not in ("any", "ac", "non-ac"):
        print("Invalid AC preference.")
        return
    db["residents"][rid] = {
        "name": name, "gender": gender, "room_pref": room_pref,
        "ac_pref": ac_pref, "status": "REGISTERED", "bed_id": None,
        "room_id": None, "move_in": None, "notice_date": None,
        "deposit": 0, "meal_history": [], "addons": [],
        "absences": [], "room_changes": [], "damages": 0
    }
    save_data()
    print("Resident registered.")


def allocate_resident(resident_id, bed_id=None):
    resident = db["residents"][resident_id]
    choices = [b for b in available_beds() if bed_id is None or b == bed_id]
    eligible = []
    for bid in choices:
        room = db["rooms"][db["beds"][bid]["room_id"]]
        if room["gender"] not in ("any", resident["gender"]):
            continue
        room_rank = 0 if resident["room_pref"] == "any" or room["room_type"] == resident["room_pref"] else 1
        ac_rank = 0 if resident["ac_pref"] == "any" or room["ac_type"].lower() == resident["ac_pref"] else 1
        occupants = len(active_residents_in_room(db["beds"][bid]["room_id"]))
        eligible.append(((room_rank, ac_rank, room["floor"], -occupants, bid), bid))
    if not eligible:
        return None
    eligible.sort()
    selected = eligible[0][1]
    room_id = db["beds"][selected]["room_id"]
    db["beds"][selected]["resident_id"] = resident_id
    resident["bed_id"], resident["room_id"] = selected, room_id
    return selected


def allocate_menu():
    rid = input("Resident ID to allocate: ").strip().upper()
    if rid not in db["residents"]:
        print("Resident not found.")
        return
    if db["residents"][rid]["bed_id"]:
        print("Resident already has a bed.")
        return
    bed = allocate_resident(rid)
    if bed:
        save_data()
        print(f"Allocated {bed} in room {db['beds'][bed]['room_id']}.")
    else:
        print("No matching bed. Add resident to waitlist if required.")


def move_in():
    rid = input("Resident ID: ").strip().upper()
    if rid not in db["residents"]:
        print("Resident not found.")
        return
    resident = db["residents"][rid]
    if resident["status"] == "ACTIVE":
        print("Resident is already active.")
        return
    if not resident["bed_id"] and not allocate_resident(rid):
        print("No bed available; resident cannot move in.")
        return
    start = ask_date("Move-in date (DD-MM-YYYY): ")
    rent = rent_for_room(resident["room_id"])
    resident["move_in"] = start.isoformat()
    resident["deposit"] = rent * 2
    resident["status"] = "ACTIVE"
    resident["meal_history"] = [{"date": start.isoformat(), "plan": "NONE"}]
    save_data()
    print(f"Move-in complete. Monthly rent Rs.{rent}; deposit Rs.{rent * 2}.")


def change_meal_plan():
    rid = input("Active resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    plan = input("Plan (NONE/BREAKFAST/TWO_MEALS/FULL): ").strip().upper()
    if plan not in MEAL_RATES:
        print("Invalid meal plan.")
        return
    effective = ask_date("Effective date (DD-MM-YYYY): ")
    resident = db["residents"][rid]
    if effective < date.fromisoformat(resident["move_in"]):
        print("Effective date cannot be before move-in.")
        return
    resident["meal_history"].append({"date": effective.isoformat(), "plan": plan})
    resident["meal_history"].sort(key=lambda x: x["date"])
    save_data()
    print("Meal plan updated from the selected effective date.")


def manage_addons():
    rid = input("Active resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    print("Available:", ", ".join(f"{k}=Rs.{v}" for k, v in ADDON_RATES.items()))
    selected = input("Enter add-ons separated by commas (or NONE): ").strip().lower()
    db["residents"][rid]["addons"] = [] if selected == "none" else [
        x.strip() for x in selected.split(",") if x.strip() in ADDON_RATES
    ]
    save_data()
    print("Add-ons saved.")


def record_absence():
    rid = input("Active resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    start = ask_date("Absence start date: ")
    end = ask_date("Absence end date: ")
    if end < start:
        print("End date cannot be before start date.")
        return
    notified = input("Was prior notice given? (y/n): ").strip().lower() == "y"
    db["residents"][rid]["absences"].append({
        "start": start.isoformat(), "end": end.isoformat(), "notified": notified
    })
    save_data()
    print(f"Absence recorded: {(end - start).days + 1} day(s).")


def record_electricity():
    room_id = input("Room ID: ").strip().upper()
    if room_id not in db["rooms"]:
        print("Room not found.")
        return
    period = input("Billing month (YYYY-MM): ").strip()
    try:
        year, month = map(int, period.split("-"))
        if month not in range(1, 13):
            raise ValueError
    except ValueError:
        print("Enter month as YYYY-MM.")
        return
    try:
        previous = float(input("Previous meter reading: "))
        current = float(input("Current meter reading: "))
        rate = float(input("Rate per unit (Rs.): "))
        if current < previous or rate < 0:
            raise ValueError
    except ValueError:
        print("Invalid meter readings or rate.")
        return
    db["electricity"][f"{room_id}|{period}"] = {
        "units": current - previous, "rate": rate
    }
    save_data()
    print("Electricity reading saved.")


def meal_cost_for_period(resident, start, end):
    history = sorted(resident["meal_history"], key=lambda x: x["date"])
    total = 0
    for i, entry in enumerate(history):
        segment_start = max(start, date.fromisoformat(entry["date"]))
        segment_end = end
        if i + 1 < len(history):
            next_start = date.fromisoformat(history[i + 1]["date"])
            segment_end = min(segment_end, next_start - timedelta(days=1))
        if segment_start <= segment_end:
            days = (segment_end - segment_start).days + 1
            days_in_month = calendar.monthrange(segment_start.year, segment_start.month)[1]
            total += MEAL_RATES[entry["plan"]] * days / days_in_month
    return total


def generate_bill():
    rid = input("Resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    try:
        year, month = map(int, input("Billing month (YYYY-MM): ").split("-"))
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
    except ValueError:
        print("Enter a valid month as YYYY-MM.")
        return
    resident = db["residents"][rid]
    move_in = date.fromisoformat(resident["move_in"])
    start = max(first, move_in)
    end = last
    if start > end:
        print("Resident was not staying during this month.")
        return

    # Rent is prorated for move-in month. Room history is retained for future room changes.
    rent = rent_for_room(resident["room_id"])
    rent_days = (end - start).days + 1
    rent_charge = rent * rent_days / last.day

    meal_charge = meal_cost_for_period(resident, start, end)
    absence_credit = 0
    for absence in resident["absences"]:
        a = date.fromisoformat(absence["start"])
        b = date.fromisoformat(absence["end"])
        days = max(0, (min(end, b) - max(start, a)).days + 1)
        if absence["notified"] and (b - a).days + 1 >= 5 and days:
            absence_credit += MEAL_RATES.get(
                next((h["plan"] for h in reversed(resident["meal_history"])
                      if date.fromisoformat(h["date"]) <= a), "NONE"), 0
            ) * days / calendar.monthrange(year, month)[1] * 0.5

    addon_total = sum(ADDON_RATES[a] for a in resident["addons"])
    electricity_total = 0
    room_id = resident["room_id"]
    reading = db["electricity"].get(f"{room_id}|{year:04d}-{month:02d}")
    if reading:
        occupants = active_residents_in_room(room_id)
        count = max(1, len(occupants))
        electricity_total = reading["units"] * reading["rate"] / count

    total = money(rent_charge + meal_charge - absence_credit + addon_total + electricity_total)
    bill_id = f"{rid}-{year:04d}-{month:02d}"
    db["bills"][bill_id] = {
        "resident_id": rid, "month": f"{year:04d}-{month:02d}",
        "rent": money(rent_charge), "meals": money(meal_charge),
        "absence_credit": money(absence_credit), "addons": money(addon_total),
        "electricity": money(electricity_total), "late_fee": 0,
        "total": total, "paid": 0, "status": "UNPAID"
    }
    save_data()
    print_bill(bill_id)


def print_bill(bill_id):
    bill = db["bills"][bill_id]
    print("\n========== MONTHLY BILL ==========")
    print("Bill:", bill_id)
    for key in ("rent", "meals", "addons", "electricity", "late_fee"):
        print(f"{key.title():16} Rs.{bill[key]}")
    print(f"{'Absence credit':16} Rs.{bill['absence_credit']}")
    print("-" * 34)
    print(f"Total:             Rs.{bill['total']}")
    print(f"Paid:              Rs.{bill['paid']}")
    print(f"Balance:           Rs.{bill['total'] - bill['paid']}")
    print("Status:", bill["status"])
    print("==================================")


def record_payment():
    bill_id = input("Bill ID: ").strip().upper()
    if bill_id not in db["bills"]:
        print("Bill not found.")
        return
    try:
        amount = float(input("Payment amount: Rs. "))
        if amount <= 0:
            raise ValueError
    except ValueError:
        print("Enter a positive amount.")
        return
    bill = db["bills"][bill_id]
    bill["paid"] = money(bill["paid"] + amount)
    bill["status"] = "PAID" if bill["paid"] >= bill["total"] else "PARTIAL"
    save_data()
    print_bill(bill_id)


def change_room():
    rid = input("Active resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    resident = db["residents"][rid]
    new_bed = input("New available bed ID: ").strip().upper()
    if new_bed not in available_beds():
        print("Bed is not available.")
        return
    new_room = db["beds"][new_bed]["room_id"]
    room = db["rooms"][new_room]
    if room["gender"] not in ("any", resident["gender"]):
        print("Gender restriction prevents this room change.")
        return
    old_room = resident["room_id"]
    old_rent = rent_for_room(old_room)
    new_rent = rent_for_room(new_room)
    change_date = ask_date("Room change date: ")
    history = resident["room_changes"]
    fee = ROOM_CHANGE_FEE if history and (change_date - date.fromisoformat(history[-1]["date"])).days < 183 else 0
    db["beds"][resident["bed_id"]]["resident_id"] = None
    db["beds"][new_bed]["resident_id"] = rid
    resident["bed_id"], resident["room_id"] = new_bed, new_room
    resident["deposit"] = new_rent * 2
    resident["room_changes"].append({
        "date": change_date.isoformat(), "old_room": old_room,
        "new_room": new_room, "old_rent": old_rent, "new_rent": new_rent,
        "fee": fee, "deposit_adjustment": new_rent * 2 - old_rent * 2
    })
    save_data()
    print(f"Room changed. Deposit adjustment Rs.{new_rent * 2 - old_rent * 2}; fee Rs.{fee}.")
    process_waitlist()


def add_waitlist():
    rid = input("Resident ID: ").strip().upper()
    if rid not in db["residents"]:
        print("Resident not found.")
        return
    resident = db["residents"][rid]
    if resident["bed_id"]:
        print("Resident already has a bed.")
        return
    if any(x["resident_id"] == rid and x["status"] in ("WAITING", "OFFERED") for x in db["waitlist"]):
        print("Resident is already waiting.")
        return
    db["waitlist"].append({
        "number": db["next_waitlist"], "resident_id": rid,
        "request_date": date.today().isoformat(), "status": "WAITING"
    })
    db["next_waitlist"] += 1
    save_data()
    process_waitlist()


def process_waitlist():
    # Offers are kept for 48 hours. This simple version uses dates, not exact hours.
    today = date.today()
    for item in db["waitlist"]:
        if item["status"] == "OFFERED" and date.fromisoformat(item["deadline"]) < today:
            item["status"] = "WAITING"
            item["request_date"] = today.isoformat()
            item.pop("offered_bed", None)
            item.pop("deadline", None)
    waiting = [x for x in db["waitlist"] if x["status"] == "WAITING"]
    waiting.sort(key=lambda x: (
        0 if db["residents"][x["resident_id"]]["room_pref"] == "any" else 1,
        x["request_date"], x["number"]
    ))
    free = available_beds()
    for item, bed in zip(waiting, free):
        resident = db["residents"][item["resident_id"]]
        room = db["rooms"][db["beds"][bed]["room_id"]]
        if room["gender"] not in ("any", resident["gender"]):
            continue
        item["status"] = "OFFERED"
        item["offered_bed"] = bed
        item["deadline"] = (today + timedelta(days=2)).isoformat()
    save_data()


def confirm_waitlist():
    rid = input("Resident ID: ").strip().upper()
    item = next((x for x in db["waitlist"] if x["resident_id"] == rid and x["status"] == "OFFERED"), None)
    if not item:
        print("No active offer found.")
        return
    if date.today() > date.fromisoformat(item["deadline"]):
        item["status"] = "WAITING"
        print("Offer expired.")
    else:
        bed = item["offered_bed"]
        if bed not in available_beds():
            item["status"] = "WAITING"
            print("Offered bed is no longer available.")
        else:
            db["beds"][bed]["resident_id"] = rid
            db["residents"][rid]["bed_id"] = bed
            db["residents"][rid]["room_id"] = db["beds"][bed]["room_id"]
            item["status"] = "CONFIRMED"
            print("Bed offer confirmed:", bed)
    save_data()


def move_out():
    rid = input("Active resident ID: ").strip().upper()
    if rid not in db["residents"] or db["residents"][rid]["status"] != "ACTIVE":
        print("Active resident not found.")
        return
    resident = db["residents"][rid]
    notice = ask_date("Notice date: ")
    leaving = ask_date("Move-out date: ")
    move_in = date.fromisoformat(resident["move_in"])
    if notice < move_in or leaving < notice:
        print("Invalid dates.")
        return
    notice_days = (leaving - notice).days
    shortfall = max(0, 30 - notice_days)
    notice_charge = money(rent_for_room(resident["room_id"]) / 30 * shortfall)
    months_stayed = (leaving.year - move_in.year) * 12 + leaving.month - move_in.month
    if leaving.day < move_in.day:
        months_stayed -= 1
    cleaning = CLEANING_FEE if months_stayed < 3 else 0
    unused_refund = 0
    if notice_days >= 30:
        unused_days = calendar.monthrange(leaving.year, leaving.month)[1] - leaving.day
        unused_refund = money(rent_for_room(resident["room_id"]) * unused_days /
                              calendar.monthrange(leaving.year, leaving.month)[1])
    deductions = notice_charge + cleaning + money(resident["damages"])
    settlement = resident["deposit"] + unused_refund - deductions
    print("\n========== MOVE-OUT SETTLEMENT ==========")
    print("Security deposit:", resident["deposit"])
    print("Notice charge:", notice_charge)
    print("Cleaning charge:", cleaning)
    print("Damages:", money(resident["damages"]))
    print("Unused rent refund:", unused_refund)
    print("Final refund:", max(0, settlement))
    print("Additional amount due:", max(0, -settlement))
    db["beds"][resident["bed_id"]]["resident_id"] = None
    resident["status"] = "MOVED OUT"
    resident["notice_date"] = notice.isoformat()
    resident["move_out"] = leaving.isoformat()
    save_data()
    process_waitlist()


def occupancy_report():
    print("\n========== OCCUPANCY REPORT ==========")
    for pid, prop in db["properties"].items():
        print(f"\n{pid}: {prop['name']} | {prop['location']}")
        for rid, room in db["rooms"].items():
            if room["property_id"] != pid:
                continue
            print(f"\nRoom {rid}: {room['room_type']} {room['ac_type']} | Floor {room['floor']} | {room['gender']}")
            for bid, bed in db["beds"].items():
                if bed["room_id"] == rid:
                    occupant = bed["resident_id"] or "AVAILABLE"
                    print(f"  {bid}: {occupant}")
    total = len(db["beds"])
    occupied = sum(1 for x in db["beds"].values() if x["resident_id"])
    print(f"\nTotal beds: {total} | Occupied: {occupied} | Available: {total - occupied}")


def resident_ledger():
    rid = input("Resident ID: ").strip().upper()
    if rid not in db["residents"]:
        print("Resident not found.")
        return
    r = db["residents"][rid]
    print("\n========== RESIDENT LEDGER ==========")
    for key in ("name", "gender", "status", "bed_id", "move_in", "deposit"):
        print(f"{key.replace('_', ' ').title()}: {r.get(key)}")
    print("Meal history:", r["meal_history"])
    print("Add-ons:", r["addons"])
    print("Room changes:", r["room_changes"])
    print("=====================================")


def list_bills():
    if not db["bills"]:
        print("No bills generated.")
    for bill_id in db["bills"]:
        print_bill(bill_id)


def menu():
    actions = {
        "1": ("Register property", register_property),
        "2": ("Register room and beds", register_room),
        "3": ("Register resident", register_resident),
        "4": ("Allocate bed", allocate_menu),
        "5": ("Move resident in", move_in),
        "6": ("Change meal plan", change_meal_plan),
        "7": ("Manage add-ons", manage_addons),
        "8": ("Record absence", record_absence),
        "9": ("Record electricity reading", record_electricity),
        "10": ("Generate monthly bill", generate_bill),
        "11": ("Record bill payment", record_payment),
        "12": ("Change resident room", change_room),
        "13": ("Add resident to waitlist", add_waitlist),
        "14": ("Confirm waitlist offer", confirm_waitlist),
        "15": ("Move resident out", move_out),
        "16": ("Occupancy report", occupancy_report),
        "17": ("Resident ledger", resident_ledger),
        "18": ("View all bills", list_bills),
        "0": ("Exit", None),
    }
    while True:
        print("\n" + "=" * 58)
        print("       PG OCCUPANCY AND BILLING ENGINE")
        print("=" * 58)
        for key, (label, _) in actions.items():
            print(f"{key:>2}. {label}")
        choice = input("Choose command: ").strip()
        if choice == "0":
            save_data()
            print("Data saved. Goodbye!")
            break
        action = actions.get(choice)
        if action:
            try:
                action[1]()
            except (KeyError, ValueError, TypeError) as error:
                print("Could not complete that operation:", error)
            save_data()
        else:
            print("Invalid command.")


if __name__ == "__main__":
    print("PG Management System | Team T015 | PS-107")
    print("Saved data file:", DATA_FILE.name)
    menu()
