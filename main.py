import csv
import json
import os
from datetime import date, datetime, timedelta
from calendar import monthrange

# ============================================================
# PS-107 | Co-living PG Occupancy, Bed Allocation & Billing
# Team T015
#
# Put properties.csv, rooms.csv, beds.csv, residents.csv,
# meter_readings.csv and commands.txt beside this main.py.
# Run: python main.py -> choose 19 to run college simulation.
# ============================================================

DATA_FILE = "pg_data.json"
RENT_CARD = {
    ("SINGLE", True): 18000, ("SINGLE", False): 14000,
    ("DOUBLE", True): 12000, ("DOUBLE", False): 9500,
    ("TRIPLE", True): 9000, ("TRIPLE", False): 7000,
}
MEAL_RATES = {"NONE": 0, "BREAKFAST": 2000, "TWO_MEALS": 4500, "FULL": 6000}
ADDON_RATES = {"LAUNDRY": 800, "PARKING_2W": 500, "PARKING_CAR": 1500}
CSV_FILES = ["properties.csv", "rooms.csv", "beds.csv", "residents.csv", "meter_readings.csv"]
COMMANDS_FILE = "commands.txt"

# -------------------- Basic utilities --------------------

def parse_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes", "y")

def parse_date(value):
    return date.fromisoformat(str(value).strip())

def parse_ts(value):
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")

def month_days(month):
    y, m = map(int, month.split("-"))
    return monthrange(y, m)[1]

def month_start(month):
    return date.fromisoformat(month + "-01")

def month_end(month):
    return date.fromisoformat(month + f"-{month_days(month):02d}")

def months_between(start_month, end_month):
    y1, m1 = map(int, start_month.split("-"))
    y2, m2 = map(int, end_month.split("-"))
    while (y1, m1) <= (y2, m2):
        yield f"{y1:04d}-{m1:02d}"
        m1 += 1
        if m1 == 13:
            y1, m1 = y1 + 1, 1

def read_csv_rows(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")
    with open(filename, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write_csv(filename, headers, rows):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def empty_data():
    return {
        "properties": {}, "rooms": {}, "beds": {}, "residents": {},
        "waitlist": [], "bills": {}, "electricity": {}, "next_waitlist": 1,
        "allocation_output": [], "occupancy_output": [], "bill_output": [],
        "deposit_transactions": {}, "late_count": {}, "late_events": {},
        "month_billed": [], "current_sim_ts": None, "meter_rows": {},
        "guest_nights": {}, "move_out_notices": {}, "resident_order": {},
        "room_change_dates": {}, "last_bill_month": None, "pending_payments": {}, "pending_late_fees": {}
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        return empty_data()
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        data = empty_data()
        data.update(saved)
        return data
    except (OSError, json.JSONDecodeError):
        print("Warning: saved JSON unavailable; starting with fresh data.")
        return empty_data()

DATA = load_data()

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, indent=2)

def ask(prompt):
    return input(prompt).strip()

# -------------------- College dataset import --------------------

def load_college_dataset():
    """Import the provided CSV dataset into the in-memory data structures."""
    props = read_csv_rows("properties.csv")
    rooms = read_csv_rows("rooms.csv")
    beds = read_csv_rows("beds.csv")
    residents = read_csv_rows("residents.csv")
    meter_rows = read_csv_rows("meter_readings.csv")

    DATA["properties"] = {}
    for p in props:
        DATA["properties"][p["property_id"]] = {
            "name": p["property_name"], "location": p["city"], "floors": int(p["floors"])
        }

    DATA["rooms"] = {}
    for r in rooms:
        room_type = r["room_type"].strip().upper()
        ac = parse_bool(r["ac"])
        gender = r["gender"].strip().upper()
        DATA["rooms"][r["room_id"]] = {
            "property_id": r["property_id"], "room_type": room_type,
            "ac": ac, "ac_type": "ac" if ac else "non-ac",
            "gender": gender, "floor": int(r["floor"]),
            "capacity": int(r["bed_count"])
        }

    DATA["beds"] = {}
    for b in beds:
        DATA["beds"][b["bed_id"]] = {
            "room_id": b["room_id"], "resident_id": None,
            "bed_no": int(b["bed_no"])
        }

    DATA["residents"] = {}
    DATA["resident_order"] = {}
    for r in residents:
        rid = r["resident_id"]
        DATA["residents"][rid] = {
            "resident_id": rid, "initial_meal_plan": r["meal_plan"].strip().upper(), "name": r["resident_name"], "gender": r["gender"].strip().upper(),
            "mobile": r["mobile"], "request_date": r["request_date"],
            "preferred_property": r["preferred_property_id"],
            "preferred_room": r["preferred_room_type"].strip().upper(),
            "preferred_ac": parse_bool(r["preferred_ac"]),
            "any_room": parse_bool(r["any_room_flag"]),
            "meal_plan": r["meal_plan"].strip().upper(),
            "meal_history": [], "addons": [],
            "status": "registered", "bed_id": None, "move_in_date": None,
            "deposit_paid": 0.0, "absences": [], "room_changes": [],
            "payments": [], "move_out_date": None, "notice_date": None,
            "notice_move_out_date": None, "guest_stays": [],
            "late_payments": 0, "deposit_held": 0.0
        }
        addon_values = [x.strip().upper() for x in r.get("addons", "").split(";") if x.strip()]
        DATA["residents"][rid]["addons"] = [x for x in addon_values if x in ADDON_RATES]
        DATA["resident_order"][rid] = r["request_date"]

    DATA["meter_rows"] = {}
    for m in meter_rows:
        DATA["meter_rows"][f'{m["room_id"]}:{m["month"]}'] = {
            "units": float(m["units"]), "amount": float(m["amount"])
        }

    # Reset occupancy/status data when importing fresh CSVs.
    DATA["waitlist"] = []
    DATA["bills"] = {}
    DATA["electricity"] = {}
    DATA["allocation_output"] = []
    DATA["occupancy_output"] = []
    DATA["bill_output"] = []
    DATA["deposit_transactions"] = {}
    DATA["late_count"] = {}
    DATA["late_events"] = {}
    DATA["month_billed"] = []
    DATA["guest_nights"] = {}
    DATA["move_out_notices"] = {}
    DATA["room_change_dates"] = {}
    DATA["next_waitlist"] = 1
    DATA["last_bill_month"] = None
    DATA["pending_payments"] = {}
    DATA["pending_late_fees"] = {}
    save_data()
    print(f"Dataset loaded: {len(DATA['properties'])} properties, {len(DATA['rooms'])} rooms, "
          f"{len(DATA['beds'])} beds, {len(DATA['residents'])} residents, {len(DATA['meter_rows'])} meter records.")

# -------------------- Room/rent and allocation --------------------

def room_of_bed(bed_id):
    b = DATA["beds"].get(bed_id)
    return DATA["rooms"].get(b["room_id"], {}) if b else {}

def monthly_rent(room):
    return RENT_CARD.get((room.get("room_type", "TRIPLE").upper(), bool(room.get("ac", room.get("ac_type") == "ac"))), 0)

def resident_current_room(resident):
    return room_of_bed(resident.get("bed_id")) if resident.get("bed_id") else {}

def is_gender_compatible(room, resident):
    rg = room.get("gender", "ANY").upper()
    gender = resident.get("gender", "").upper()
    return rg in ("ANY", gender)

def is_room_compatible(room, resident):
    if not is_gender_compatible(room, resident):
        return False
    if room.get("property_id") != resident.get("preferred_property"):
        return False
    if not resident.get("any_room") and room.get("room_type") != resident.get("preferred_room"):
        return False
    # AC is a ranking preference, not an absolute eligibility restriction.
    return True

def allocate_for_resident(rid, timestamp, event_line):
    resident = DATA["residents"].get(rid)
    if not resident:
        log_allocation(event_line, rid, "REJECTED", "NONE", "Unknown resident ID")
        return False
    if resident.get("bed_id") or resident.get("status") in ("active", "moved_out"):
        log_allocation(event_line, rid, "REJECTED", "NONE", "Resident already allocated or moved out")
        return False

    # Dataset preferences are exact property, room type (unless ANY), and AC.
    options = []
    for bed_id, bed in DATA["beds"].items():
        if bed.get("resident_id"):
            continue
        room = DATA["rooms"].get(bed["room_id"], {})
        if is_room_compatible(room, resident):
            options.append((0 if room.get("room_type") == resident.get("preferred_room") else 1,
                            0 if room.get("ac") == resident.get("preferred_ac") else 1,
                            room.get("floor", 0),
                            -sum(bool(b.get("resident_id")) for b in DATA["beds"].values() if b["room_id"] == bed["room_id"]), bed_id, room))
    if options:
        options.sort(key=lambda x: x[:5])
        *_, bed_id, room = options[0]
        DATA["beds"][bed_id]["resident_id"] = rid
        resident["bed_id"] = bed_id
        resident["status"] = "allocated"
        resident["allocated_at"] = timestamp
        resident.setdefault("initial_bed_id", bed_id)
        log_allocation(event_line, rid, "ALLOCATED", bed_id, "Bed allocated")
        return True

    resident["status"] = "waitlisted"
    if not any(x["resident_id"] == rid and x["status"] == "WAITING" for x in DATA["waitlist"]):
        DATA["waitlist"].append({
            "resident_id": rid, "request_date": resident.get("request_date", "9999-12-31"),
            "status": "WAITING", "offer_bed": None, "offer_at": None, "deadline": None
        })
    log_allocation(event_line, rid, "WAITLISTED", "NONE", "No suitable vacant bed; added to waitlist")
    return False

def log_allocation(line_no, rid, status, bed_id, message):
    DATA["allocation_output"].append([line_no, rid, status, bed_id, message])

def free_bed(rid):
    r = DATA["residents"].get(rid)
    if r and r.get("bed_id"):
        bid = r["bed_id"]
        if bid in DATA["beds"]:
            DATA["beds"][bid]["resident_id"] = None
        r["bed_id"] = None

def find_waitlist_head(property_id=None):
    candidates = []
    for e in DATA["waitlist"]:
        if e["status"] != "WAITING":
            continue
        r = DATA["residents"].get(e["resident_id"], {})
        if property_id and r.get("preferred_property") != property_id:
            continue
        candidates.append(e)
    candidates.sort(key=lambda e: (0 if DATA["residents"].get(e["resident_id"], {}).get("any_room") else 1, e.get("request_date", "9999-12-31"), e["resident_id"]))
    return candidates[0] if candidates else None

def auto_offer_waitlist(bed_id, timestamp):
    room = DATA["rooms"][DATA["beds"][bed_id]["room_id"]]
    eligible = []
    for entry in DATA["waitlist"]:
        if entry["status"] != "WAITING":
            continue
        r = DATA["residents"].get(entry["resident_id"], {})
        if r and is_room_compatible(room, r):
            eligible.append(entry)
    eligible.sort(key=lambda e: (0 if DATA["residents"][e["resident_id"]].get("any_room") else 1, e.get("request_date", "9999-12-31"), e["resident_id"]))
    if not eligible:
        return
    entry = eligible[0]
    r = DATA["residents"][entry["resident_id"]]
    DATA["beds"][bed_id]["resident_id"] = r["resident_id"]
    r["bed_id"] = bed_id
    r["status"] = "OFFERED"
    entry["status"] = "OFFERED"
    entry["offer_bed"] = bed_id
    entry["offer_at"] = timestamp
    entry["deadline"] = (parse_ts(timestamp) + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")

# -------------------- Event commands --------------------

def command_onboard(ts, rid, move_in_date, line):
    if rid not in DATA["residents"]:
        log_allocation(line, rid, "REJECTED", "NONE", "Resident not found")
        return
    r = DATA["residents"][rid]
    if r.get("status") in ("active", "moved_out") or r.get("bed_id"):
        log_allocation(line, rid, "REJECTED", "NONE", "Duplicate ONBOARD")
        return
    if r.get("status") == "registered":
        r["move_in_date"] = move_in_date
    allocated = allocate_for_resident(rid, ts, line)
    if allocated:
        r["status"] = "active"
        r["move_in_date"] = move_in_date
        # Deposit recorded as two monthly rents, held in ledger.
        r["deposit_held"] = 2 * monthly_rent(resident_current_room(r))
        DATA["deposit_transactions"][rid] = r["deposit_held"]

def command_confirm_allocation(ts, rid, line):
    entries = [e for e in DATA["waitlist"] if e["resident_id"] == rid and e["status"] == "OFFERED"]
    if not entries:
        log_allocation(line, rid, "REJECTED", "NONE", "No active bed offer")
        return
    e = entries[0]
    if parse_ts(ts) > parse_ts(e["deadline"]):
        # Expired: release bed, remove resident from offer, place at waitlist tail.
        bid = e["offer_bed"]
        if bid and DATA["beds"][bid].get("resident_id") == rid:
            DATA["beds"][bid]["resident_id"] = None
        DATA["residents"][rid]["bed_id"] = None
        DATA["residents"][rid]["status"] = "waitlisted"
        e["status"] = "EXPIRED"
        e["request_date"] = ts[:10] + " 99:99:99"
        e["offer_bed"] = None
        log_allocation(line, rid, "REJECTED", "NONE", "Offer expired after 48 hours")
        if bid:
            auto_offer_waitlist(bid, ts)
        return
    # Confirm within 48 hours; resident is already holding the offered bed.
    DATA["residents"][rid]["status"] = "active"
    DATA["residents"][rid].setdefault("initial_bed_id", e["offer_bed"])
    DATA["residents"][rid]["move_in_date"] = ts[:10]
    room = resident_current_room(DATA["residents"][rid])
    DATA["residents"][rid]["deposit_held"] = 2 * monthly_rent(room)
    DATA["deposit_transactions"][rid] = DATA["residents"][rid]["deposit_held"]
    e["status"] = "CONFIRMED"
    log_allocation(line, rid, "ALLOCATED", e["offer_bed"], "Allocation confirmed within 48 hours")

def command_move_out_notice(ts, rid, move_out_date, line):
    r = DATA["residents"].get(rid)
    if not r:
        return
    r["notice_date"] = ts[:10]
    r["notice_move_out_date"] = move_out_date
    DATA["move_out_notices"][rid] = {"notice_date": ts[:10], "move_out_date": move_out_date}

def command_move_out(ts, rid, vacate_date, line):
    r = DATA["residents"].get(rid)
    if not r or not r.get("bed_id"):
        return
    old_bed = r["bed_id"]
    old_room = room_of_bed(old_bed)
    free_bed(rid)
    r["status"] = "moved_out"
    r["move_out_date"] = vacate_date
    # Releasing bed triggers next eligible waitlist offer.
    auto_offer_waitlist(old_bed, ts)

def command_room_change(ts, rid, room_type, ac, effective_date, line):
    r = DATA["residents"].get(rid)
    if not r or not r.get("bed_id") or r.get("status") not in ("active", "OFFERED"):
        log_allocation(line, rid, "REJECTED", "NONE", "Resident is not active/allocated")
        return
    # If twice late within a 90-day rolling period, room change blocked.
    late_dates = DATA["late_events"].get(rid, [])
    cutoff = parse_date(ts[:10]) - timedelta(days=90)
    recent_lates = [d for d in late_dates if parse_date(d) >= cutoff]
    if len(recent_lates) >= 2:
        log_allocation(line, rid, "REJECTED", "NONE", "Room change blocked due to repeated late payments")
        return
    room_type = room_type.upper()
    ac_bool = parse_bool(ac)
    current_bed = r["bed_id"]
    current_room = room_of_bed(current_bed)
    candidates = []
    for bid, b in DATA["beds"].items():
        if b.get("resident_id"):
            continue
        room = DATA["rooms"].get(b["room_id"], {})
        if room.get("property_id") != current_room.get("property_id"):
            continue
        if room.get("room_type") != room_type or room.get("ac") != ac_bool:
            continue
        if not is_gender_compatible(room, r):
            continue
        candidates.append((room.get("floor", 0), bid, room))
    if not candidates:
        log_allocation(line, rid, "REJECTED", "NONE", "No matching vacant bed for room change")
        return
    candidates.sort(key=lambda x: (x[0], x[1]))
    _, new_bed, new_room = candidates[0]
    change_dates = r.setdefault("room_changes", [])
    # 1000 charge for second room change within six months
    recent_changes = [c for c in change_dates if (parse_date(effective_date) - parse_date(c["effective_date"])).days <= 183]
    fee = 1000 if len(recent_changes) >= 1 else 0
    old_deposit = float(r.get("deposit_held", 2 * monthly_rent(current_room)))
    new_deposit = 2 * monthly_rent(new_room)
    r["deposit_held"] = new_deposit
    r.setdefault("deposit_changes", []).append({"month": effective_date[:7], "difference": new_deposit - old_deposit})
    DATA["beds"][current_bed]["resident_id"] = None
    DATA["beds"][new_bed]["resident_id"] = rid
    r["bed_id"] = new_bed
    change_dates.append({"from": current_bed, "to": new_bed, "date": ts[:10], "effective_date": effective_date, "fee": fee})
    log_allocation(line, rid, "CHANGED", new_bed, f"Room changed; fee Rs {fee:.2f}")
    auto_offer_waitlist(current_bed, ts)

def command_absence(ts, rid, start, end, notified, line):
    r = DATA["residents"].get(rid)
    if not r:
        return
    s, e = parse_date(start), parse_date(end)
    if e < s:
        return
    r.setdefault("absences", []).append({"start": start, "end": end, "notice": parse_bool(notified)})
    # absences are later used to determine monthly electricity presence and meal credit.

def command_meal_plan(ts, rid, plan, line):
    r = DATA["residents"].get(rid)
    plan = plan.strip().upper()
    if not r or plan not in MEAL_RATES:
        return
    # effective next calendar day
    effective = (parse_ts(ts).date() + timedelta(days=1)).isoformat()
    r.setdefault("meal_history", []).append({"date": effective, "plan": plan})
    # Keep initial meal plan unchanged for historical billing.

def command_addon(ts, rid, addon, action, line):
    r = DATA["residents"].get(rid)
    addon, action = addon.upper(), action.upper()
    if not r or addon not in ADDON_RATES or action not in ("ADD", "REMOVE"):
        return
    values = r.setdefault("addons", [])
    if action == "ADD" and addon not in values:
        values.append(addon)
    if action == "REMOVE" and addon in values:
        values.remove(addon)

def command_guest_stay(ts, rid, nights, line):
    r = DATA["residents"].get(rid)
    if not r:
        return
    month = ts[:7]
    key = f"{rid}:{month}"
    requested = int(nights)
    if requested < 0 or DATA["guest_nights"].get(key, 0) + requested > 3:
        print(f"WARNING: guest stay rejected (maximum 3 nights) for {rid} in {month}.")
        return
    DATA["guest_nights"][key] = DATA["guest_nights"].get(key, 0) + requested

def command_payment(ts, rid, bill_month, line):
    if rid not in DATA["residents"]:
        print(f"WARNING line {line}: unknown resident {rid}")
        return
    key = f"{rid}:{bill_month}"
    bill = DATA["bills"].get(key)
    if not bill:
        DATA["pending_payments"][key] = ts
        return
    apply_payment(rid, bill_month, ts)


def apply_payment(rid, bill_month, ts):
    bill = DATA["bills"].get(f"{rid}:{bill_month}")
    if not bill or bill.get("payment_date"):
        return
    bill["paid"] = bill["total"]
    bill["balance"] = 0.0
    bill["payment_date"] = ts[:10]
    bill["payment_ts"] = ts
    DATA["residents"][rid].setdefault("payments", []).append({"bill_month": bill_month, "amount": bill["total"], "date": ts[:10]})
    due = date.fromisoformat(bill_month + "-07")
    late_days = max(0, (parse_date(ts[:10]) - due).days)
    late_fee = min(1500, late_days * 100)
    if late_fee:
        DATA["late_events"].setdefault(rid, []).append(ts[:10])
        DATA["late_count"][rid] = DATA["late_count"].get(rid, 0) + 1
        next_month = (month_end(bill_month) + timedelta(days=1)).strftime("%Y-%m")
        k = f"{rid}:{next_month}"
        DATA["pending_late_fees"][k] = DATA["pending_late_fees"].get(k, 0) + late_fee
    bill["late_fee_to_next"] = late_fee

# -------------------- Billing calculations --------------------

def plan_for_month(r, month):
    plan = r.get("meal_plan", "NONE")
    for item in sorted(r.get("meal_history", []), key=lambda x: x["date"]):
        if item["date"] <= month_end(month).isoformat():
            plan = item["plan"]
    return plan

def addons_for_month(r, month):
    # Add-on events in this sample take effect immediately for the current month.
    return list(r.get("addons", []))

def active_days_in_month(r, month):
    start, end = month_start(month), month_end(month)
    move_in = parse_date(r["move_in_date"]) if r.get("move_in_date") else start
    move_out = parse_date(r["move_out_date"]) if r.get("move_out_date") else None
    actual_start = max(start, move_in)
    actual_end = min(end, move_out) if move_out else end
    if actual_end < actual_start:
        return 0
    return (actual_end - actual_start).days + 1

def rent_for_month(r, month):
    if not r.get("move_in_date"):
        return 0.0
    start, end = month_start(month), month_end(month)
    move_in = parse_date(r["move_in_date"])
    move_out = parse_date(r["move_out_date"]) if r.get("move_out_date") else None
    active_start = max(start, move_in)
    active_end = min(end, move_out) if move_out else end
    if active_end < active_start:
        return 0.0
    # Rent uses room held over the billing period; room change effective dates split daily.
    timeline = []
    initial_bed = r.get("initial_bed_id") or r.get("bed_id")
    if initial_bed:
        timeline.append((move_in, initial_bed))
    for c in sorted(r.get("room_changes", []), key=lambda x: x.get("effective_date", x.get("date", ""))):
        if c.get("effective_date"):
            timeline.append((parse_date(c["effective_date"]), c["to"]))
    timeline.sort(key=lambda x: x[0])
    total = 0.0
    days = month_days(month)
    for d in range((active_start - start).days, (active_end - start).days + 1):
        day = start + timedelta(days=d)
        bed_id = initial_bed
        for eff, b_id in timeline:
            if eff <= day:
                bed_id = b_id
        room = room_of_bed(bed_id) if bed_id else {}
        total += monthly_rent(room) / days
    return round(total, 2)

def meal_charge_for_month(r, month):
    plan = r.get("initial_meal_plan", r.get("meal_plan", "NONE"))
    changes = sorted(r.get("meal_history", []), key=lambda x: x["date"])
    start, end = month_start(month), month_end(month)
    move_in = parse_date(r["move_in_date"]) if r.get("move_in_date") else start
    move_out = parse_date(r["move_out_date"]) if r.get("move_out_date") else None
    first_day = max(start, move_in)
    last_day = min(end, move_out) if move_out else end
    if last_day < first_day:
        return 0.0, plan
    total = 0.0
    current = plan
    # Initial plan applies from move-in. Plan history is effective from its date.
    for change in changes:
        if parse_date(change["date"]) <= first_day:
            current = change["plan"]
    for day in range((first_day - start).days, (last_day - start).days + 1):
        d = start + timedelta(days=day)
        for change in changes:
            if parse_date(change["date"]) == d:
                current = change["plan"]
        total += MEAL_RATES.get(current, 0) / month_days(month)
        # Credit half meal value for notified absences lasting >=5 consecutive days.
        for absence in r.get("absences", []):
            if not absence.get("notice"):
                continue
            a, b = parse_date(absence["start"]), parse_date(absence["end"])
            if (b - a).days + 1 >= 5 and a <= d <= b:
                total -= MEAL_RATES.get(current, 0) / month_days(month) * 0.5
                break
    return round(max(0, total), 2), current

def bed_on_day(r, day):
    if not r.get("move_in_date") or day < parse_date(r["move_in_date"]):
        return None
    if r.get("move_out_date") and day > parse_date(r["move_out_date"]):
        return None
    bed = r.get("initial_bed_id") or r.get("bed_id")
    for c in sorted(r.get("room_changes", []), key=lambda x: x["effective_date"]):
        if parse_date(c["effective_date"]) <= day:
            bed = c["to"]
    return bed


def electricity_charges_for_month(month):
    charges = {rid: 0 for rid in DATA["residents"]}
    days = month_days(month)
    for room_id in DATA["rooms"]:
        reading = DATA["meter_rows"].get(f"{room_id}:{month}")
        if not reading:
            continue
        # Day-wise allocation; use integer paise to keep residue deterministic.
        amount_paise = round(float(reading["amount"]) * 100)
        for offset in range(days):
            day = month_start(month) + timedelta(days=offset)
            present = []
            for rid, r in DATA["residents"].items():
                bed = bed_on_day(r, day)
                if not bed or DATA["beds"].get(bed, {}).get("room_id") != room_id:
                    continue
                if any(a.get("notice") and parse_date(a["start"]) <= day <= parse_date(a["end"]) for a in r.get("absences", [])):
                    continue
                present.append(rid)
            if not present:
                continue
            daily = amount_paise // days + (1 if offset < amount_paise % days else 0)
            share, remainder = divmod(daily, len(present))
            for rid in present:
                charges[rid] += share
            longest = min(present, key=lambda rid: (DATA["residents"][rid].get("move_in_date") or "9999-12-31", rid))
            charges[longest] += remainder
    return {rid: round(paise / 100, 2) for rid, paise in charges.items()}


def bill_month(month, timestamp, line):
    if month in DATA["month_billed"]:
        print(f"WARNING: month {month} was already billed; skipping duplicate BILL_RUN.")
        return
    # Snapshot occupancy on month end; bed history is approximated from move/room change dates.
    for bed_id in sorted(DATA["beds"]):
        occupant = DATA["beds"][bed_id].get("resident_id") or "EMPTY"
        DATA["occupancy_output"].append([month, bed_id, occupant])

    electricity_by_resident = electricity_charges_for_month(month)
    residents_billed = []
    for rid, r in sorted(DATA["residents"].items()):
        if not r.get("move_in_date") or active_days_in_month(r, month) == 0:
            continue
        rent = rent_for_month(r, month)
        meal, plan = meal_charge_for_month(r, month)
        addons = sum(ADDON_RATES.get(a, 0) for a in addons_for_month(r, month))
        electricity = electricity_by_resident.get(rid, 0)
        late_fee = float(DATA["pending_late_fees"].get(f"{rid}:{month}", 0))
        prev_month = (month_start(month) - timedelta(days=1)).strftime("%Y-%m")
        previous_bill = DATA["bills"].get(f"{rid}:{prev_month}")
        if previous_bill and previous_bill.get("balance", 0) > 0:
            due = date.fromisoformat(prev_month + "-07")
            asof = parse_date(timestamp[:10])
            late_fee += min(1500, max(0, (asof - due).days) * 100)
        adjustments = 0.0
        # Room change fee stored in room change records; apply in effective month.
        for change in r.get("room_changes", []):
            if change.get("effective_date", "")[:7] == month:
                adjustments += float(change.get("fee", 0))
        adjustments += sum(c["difference"] for c in r.get("deposit_changes", []) if c["month"] == month)
        adjustments += 500 * DATA["guest_nights"].get(f"{rid}:{month}", 0)
        # Move-out notice shortfall and cleaning fee: notice <30 days, stay <3 months.
        notice = DATA["move_out_notices"].get(rid)
        if notice and notice["move_out_date"][:7] == month:
            notice_days = (parse_date(notice["move_out_date"]) - parse_date(notice["notice_date"])).days
            shortfall = max(0, 30 - notice_days)
            if shortfall:
                monthly = monthly_rent(resident_current_room(r))
                adjustments += monthly * shortfall / month_days(month)
            total_stay = (parse_date(notice["move_out_date"]) - parse_date(r["move_in_date"])).days
            if total_stay < 90:
                adjustments += 1000.0
        total = round(rent + meal + addons + electricity + late_fee + adjustments, 2)
        bill_id = f"{rid}:{month}"
        bill = {
            "resident_id": rid, "month": month, "rent": round(rent, 2),
            "meal": round(meal, 2), "meal_plan": plan, "addons": round(addons, 2),
            "electricity": round(electricity, 2), "late_fee": round(late_fee, 2),
            "adjustments": round(adjustments, 2), "total": total, "paid": 0.0,
            "balance": total, "status": "unpaid", "timestamp": timestamp
        }
        DATA["bills"][bill_id] = bill
        if bill_id in DATA["pending_payments"]:
            apply_payment(rid, month, DATA["pending_payments"].pop(bill_id))
        residents_billed.append(bill)
        # Deposit: 2x initial monthly rent, recorded as held once at first billing.
        if rid not in DATA["deposit_transactions"]:
            bed_for_deposit = r.get("initial_bed_id") or r.get("bed_id")
            deposit_room = room_of_bed(bed_for_deposit) if bed_for_deposit else {}
            deposit = 2 * monthly_rent(deposit_room)
            r["deposit_held"] = deposit
            DATA["deposit_transactions"][rid] = deposit
    for b in sorted(residents_billed, key=lambda x: x["resident_id"]):
        DATA["bill_output"].append([
            month, b["resident_id"], f'{b["rent"]:.2f}', f'{b["meal"]:.2f}',
            f'{b["addons"]:.2f}', f'{b["electricity"]:.2f}',
            f'{b["late_fee"]:.2f}', f'{b["adjustments"]:.2f}', f'{b["total"]:.2f}'
        ])
    DATA["month_billed"].append(month)
    DATA["last_bill_month"] = month
    print(f"BILL_RUN {month}: generated {len(residents_billed)} resident bills.")

# -------------------- Command file interpreter --------------------

def run_commands_file():
    if not os.path.exists(COMMANDS_FILE):
        print("commands.txt not found.")
        return
    # Start from imported dataset each time; avoids accidentally reusing old simulation.
    load_college_dataset()
    with open(COMMANDS_FILE, encoding="utf-8-sig") as f:
        lines = f.readlines()
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("|")
        cmd = parts[0].strip().upper()
        args = [x.strip() for x in parts[1:]]
        try:
            if cmd == "ONBOARD" and len(args) == 3:
                command_onboard(args[0], args[1], args[2], line_no)
            elif cmd == "CONFIRM_ALLOCATION" and len(args) == 2:
                command_confirm_allocation(args[0], args[1], line_no)
            elif cmd == "MOVE_OUT_NOTICE" and len(args) == 3:
                command_move_out_notice(args[0], args[1], args[2], line_no)
            elif cmd == "MOVE_OUT" and len(args) == 3:
                command_move_out(args[0], args[1], args[2], line_no)
            elif cmd == "ROOM_CHANGE" and len(args) == 5:
                command_room_change(args[0], args[1], args[2], args[3], args[4], line_no)
            elif cmd == "ABSENCE" and len(args) == 5:
                command_absence(args[0], args[1], args[2], args[3], args[4], line_no)
            elif cmd == "MEAL_PLAN" and len(args) == 3:
                command_meal_plan(args[0], args[1], args[2], line_no)
            elif cmd == "ADDON" and len(args) == 4:
                command_addon(args[0], args[1], args[2], args[3], line_no)
            elif cmd == "GUEST_STAY" and len(args) == 3:
                command_guest_stay(args[0], args[1], args[2], line_no)
            elif cmd == "PAYMENT" and len(args) == 3:
                command_payment(args[0], args[1], args[2], line_no)
            elif cmd == "BILL_RUN" and len(args) == 2:
                bill_month(args[1], args[0], line_no)
            else:
                print(f"WARNING line {line_no}: malformed/unknown command {cmd}")
        except Exception as exc:
            print(f"ERROR line {line_no} {cmd}: {exc}")
    export_outputs()
    save_data()
    print("Simulation complete. CSV outputs written.")

# -------------------- Output files --------------------

def export_outputs():
    write_csv("allocations.csv", ["line_no", "resident_id", "status", "bed_id", "message"], DATA["allocation_output"])
    write_csv("occupancy.csv", ["month", "bed_id", "resident_id"], DATA["occupancy_output"])
    write_csv("bills.csv", ["month", "resident_id", "rent", "meal_plan", "addons", "electricity", "late_fee", "adjustments", "total"], DATA["bill_output"])
    ledger = []
    for rid, r in sorted(DATA["residents"].items()):
        resident_bills = [b for b in DATA["bills"].values() if b["resident_id"] == rid]
        total_billed = round(sum(b["total"] for b in resident_bills), 2)
        total_paid = round(sum(b.get("paid", 0) for b in resident_bills), 2)
        deposit = float(r.get("deposit_held", DATA["deposit_transactions"].get(rid, 0)))
        balance = round(total_billed - total_paid, 2)
        ledger.append([rid, f"{deposit:.2f}", f"{total_billed:.2f}", f"{total_paid:.2f}", f"{balance:.2f}"])
    write_csv("ledger.csv", ["resident_id", "deposit_held", "total_billed", "total_paid", "balance"], ledger)

# -------------------- Existing manual menu functions --------------------

def register_property():
    pid = ask("Property ID: ")
    if not pid or pid in DATA["properties"]:
        print("Invalid or duplicate property ID."); return
    name, city = ask("Property name: "), ask("City: ")
    DATA["properties"][pid] = {"name": name, "location": city}
    save_data(); print("Property registered.")

def register_room():
    rid, pid = ask("Room ID: "), ask("Property ID: ")
    if pid not in DATA["properties"] or rid in DATA["rooms"]:
        print("Invalid property or duplicate room ID."); return
    rt = ask("Room type SINGLE/DOUBLE/TRIPLE: ").upper()
    ac = parse_bool(ask("AC? (true/false): "))
    gender = ask("Gender M/F/ANY: ").upper()
    floor = int(ask("Floor: "))
    cap = {"SINGLE": 1, "DOUBLE": 2, "TRIPLE": 3}.get(rt)
    if not cap or gender not in ("M", "F", "ANY"):
        print("Invalid room details."); return
    DATA["rooms"][rid] = {"property_id": pid, "room_type": rt, "ac": ac, "ac_type": "ac" if ac else "non-ac", "gender": gender, "floor": floor, "capacity": cap}
    for n in range(1, cap + 1):
        bid = f"{rid}-B{n}"
        DATA["beds"][bid] = {"room_id": rid, "resident_id": None, "bed_no": n}
    save_data(); print("Room registered.")

def register_resident():
    rid = ask("Resident ID: ")
    if rid in DATA["residents"]:
        print("Duplicate resident ID."); return
    name, gender = ask("Name: "), ask("Gender M/F: ").upper()
    prop, room = ask("Preferred property ID: "), ask("Room preference SINGLE/DOUBLE/TRIPLE/ANY: ").upper()
    ac = parse_bool(ask("Preferred AC true/false: "))
    meal = ask("Meal NONE/BREAKFAST/TWO_MEALS/FULL: ").upper()
    if meal not in MEAL_RATES:
        print("Invalid meal plan."); return
    DATA["residents"][rid] = {"resident_id": rid, "initial_meal_plan": meal, "name": name, "gender": gender, "preferred_property": prop, "preferred_room": room, "preferred_ac": ac, "any_room": room == "ANY", "meal_plan": meal, "meal_history": [], "addons": [], "status": "registered", "bed_id": None, "move_in_date": None, "deposit_paid": 0.0, "deposit_held": 0.0, "absences": [], "room_changes": [], "payments": []}
    save_data(); print("Resident registered.")

def allocate_bed():
    rid = ask("Resident ID: ")
    if rid not in DATA["residents"]:
        print("Resident not found."); return
    allocate_for_resident(rid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "MANUAL")

def move_in():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r or not r.get("bed_id"):
        print("Resident missing or not allocated."); return
    d = ask("Move-in date YYYY-MM-DD: ")
    parse_date(d)
    r["move_in_date"] = d; r["initial_bed_id"] = r["bed_id"]; r["status"] = "active"
    r["deposit_held"] = 2 * monthly_rent(resident_current_room(r))
    DATA["deposit_transactions"][rid] = r["deposit_held"]
    save_data(); print("Move-in recorded.")

def change_meal():
    rid, plan = ask("Resident ID: "), ask("Meal plan NONE/BREAKFAST/TWO_MEALS/FULL: ").upper()
    r = DATA["residents"].get(rid)
    if not r or plan not in MEAL_RATES:
        print("Invalid resident or meal plan."); return
    eff = ask("Effective date YYYY-MM-DD: ")
    parse_date(eff)
    r.setdefault("meal_history", []).append({"date": eff, "plan": plan})
    save_data(); print("Meal plan change saved.")

def manage_addons():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r:
        print("Resident not found."); return
    vals = ask("Add-ons semicolon-separated LAUNDRY/PARKING_2W/PARKING_CAR or NONE: ").upper()
    addons = [] if vals == "NONE" else [x.strip() for x in vals.split(";") if x.strip()]
    if any(x not in ADDON_RATES for x in addons):
        print("Unknown add-on."); return
    r["addons"] = addons; save_data(); print("Add-ons saved.")

def record_absence():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r:
        print("Resident not found."); return
    start, end = ask("Start date: "), ask("End date: ")
    s, e = parse_date(start), parse_date(end)
    if e < s:
        print("Invalid range."); return
    notice = ask("Prior notice? yes/no: ").lower() == "yes"
    r.setdefault("absences", []).append({"start": start, "end": end, "notice": notice})
    save_data(); print("Absence recorded.")

def record_electricity():
    room = ask("Room ID: ")
    month = ask("Month YYYY-MM: ")
    amount = float(ask("Amount in Rs: "))
    DATA["meter_rows"][f"{room}:{month}"] = {"amount": amount, "units": 0}
    save_data(); print("Electricity amount saved.")

def generate_bill():
    month = ask("Month YYYY-MM: ")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bill_month(month, ts, "MANUAL")
    export_outputs(); save_data()

def pay_bill():
    rid, month = ask("Resident ID: "), ask("Bill month YYYY-MM: ")
    command_payment(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid, month, "MANUAL")
    save_data()

def change_room():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r or not r.get("bed_id"):
        print("Resident has no current bed."); return
    rt, ac = ask("New room type SINGLE/DOUBLE/TRIPLE: ").upper(), ask("AC true/false: ")
    eff = ask("Effective date YYYY-MM-DD: ")
    command_room_change(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid, rt, ac, eff, "MANUAL")
    save_data()

def add_waitlist():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r:
        print("Resident not found."); return
    if not any(e["resident_id"] == rid and e["status"] == "WAITING" for e in DATA["waitlist"]):
        DATA["waitlist"].append({"resident_id": rid, "request_date": r.get("request_date", date.today().isoformat()), "status": "WAITING", "offer_bed": None, "offer_at": None, "deadline": None})
    r["status"] = "waitlisted"
    save_data(); print("Waitlist entry saved.")

def confirm_waitlist():
    rid = ask("Resident ID: ")
    e = next((x for x in DATA["waitlist"] if x["resident_id"] == rid and x["status"] == "OFFERED"), None)
    if not e:
        print("No current offer."); return
    command_confirm_allocation(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid, "MANUAL")
    save_data()

def move_out():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r or not r.get("bed_id"):
        print("Resident not allocated."); return
    d = ask("Move-out date YYYY-MM-DD: ")
    command_move_out(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid, d, "MANUAL")
    save_data()

def occupancy_report():
    for room_id, room in sorted(DATA["rooms"].items()):
        bed_list = [ (bid, b) for bid, b in DATA["beds"].items() if b["room_id"] == room_id]
        print(f"{room_id} {room['room_type']} {sum(bool(b.get('resident_id')) for _,b in bed_list)}/{len(bed_list)}")
        for bid, b in bed_list:
            print(" ", bid, b.get("resident_id") or "EMPTY")

def resident_ledger():
    rid = ask("Resident ID: ")
    r = DATA["residents"].get(rid)
    if not r:
        print("Resident not found."); return
    print(f"Ledger {rid} {r.get('name')}")
    for b in DATA["bills"].values():
        if b["resident_id"] == rid:
            print(b["month"], b["total"], b.get("paid", 0), b.get("balance", 0))

def view_bills():
    for b in DATA["bills"].values():
        print(b["resident_id"], b["month"], b["total"], b.get("paid", 0), b.get("balance", 0))

def menu():
    print("""
================ PG MANAGEMENT SYSTEM ================
 1. Register property
 2. Register room and beds
 3. Register resident
 4. Allocate bed
 5. Move resident in
 6. Change meal plan
 7. Manage add-ons
 8. Record absence
 9. Record electricity reading
10. Generate monthly bill
11. Record bill payment
12. Change resident room
13. Add resident to waitlist
14. Confirm waitlist offer
15. Move resident out
16. Occupancy report
17. Resident ledger
18. View all bills
19. Run college CSV/commands simulation
 0. Exit
""")

ACTIONS = {
    1: register_property, 2: register_room, 3: register_resident, 4: allocate_bed,
    5: move_in, 6: change_meal, 7: manage_addons, 8: record_absence,
    9: record_electricity, 10: generate_bill, 11: pay_bill, 12: change_room,
    13: add_waitlist, 14: confirm_waitlist, 15: move_out, 16: occupancy_report,
    17: resident_ledger, 18: view_bills, 19: run_commands_file
}

if __name__ == "__main__":
    print("PG Management System | Team T015 | PS-107")
    print("Data file:", DATA_FILE)
    while True:
        menu()
        try:
            choice = int(ask("Choose command: "))
        except ValueError:
            print("Please enter a number."); continue
        if choice == 0:
            save_data()
            print("Saved. Goodbye!")
            break
        action = ACTIONS.get(choice)
        if action:
            try:
                action()
            except Exception as exc:
                print("Operation failed:", exc)
        else:
            print("Invalid option.")
        save_data()
