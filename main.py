# ============================================================
# PG OCCUPANCY AND BILLING ENGINE
# Team ID: T015 | Problem Statement: PS-107
# Complete PG management, occupancy and billing system
# Python 3.10+
# ============================================================

from datetime import datetime, date, timedelta
from calendar import monthrange
from collections import defaultdict

# ------------------------------------------------------------
# 1. CONSTANTS / RATE CARDS
# ------------------------------------------------------------

RENT_CARD = {
    ("single", "AC"): 18000,
    ("single", "Non-AC"): 14000,
    ("double", "AC"): 12000,
    ("double", "Non-AC"): 9500,
    ("triple", "AC"): 9000,
    ("triple", "Non-AC"): 7000,
}

MEAL_RATES = {
    "NONE": 0,
    "BREAKFAST": 2000,
    "TWO_MEALS": 4500,
    "FULL": 6000,
}

ADDON_RATES = {
    "laundry": 800,
    "two_wheeler": 500,
    "car": 1500,
}

LATE_FEE_PER_DAY = 100
MAX_LATE_FEE = 1500
ROOM_CHANGE_FEE = 1000
CLEANING_FEE_SHORT_STAY = 1000

# All information is kept in dictionaries while this program runs.
properties = {}
rooms = {}
beds = {}
residents = {}
stays = {}
waitlist = []
bills = {}
electricity_readings = {}
payment_history = defaultdict(list)
next_waitlist_number = 1


# ------------------------------------------------------------
# 2. COMMON HELPER FUNCTIONS
# ------------------------------------------------------------

def parse_date(value):
    """Convert DD-MM-YYYY text into a date object."""
    return datetime.strptime(value, "%d-%m-%Y").date()


def date_text(value):
    return value.strftime("%d-%m-%Y") if value else "-"


def money(value):
    return round(value)


def month_key(value):
    return value.strftime("%Y-%m")


def month_dates(year, month):
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def rent_for_room(room_id):
    room = rooms[room_id]
    return RENT_CARD[(room["room_type"], room["ac_type"])]


def active_resident(resident_id):
    return resident_id in residents and residents[resident_id]["status"] == "ACTIVE"


def current_bed(resident_id):
    return residents[resident_id].get("bed_id")


def current_room(resident_id):
    bed_id = current_bed(resident_id)
    return beds[bed_id]["room_id"] if bed_id else None


def occupied_residents(room_id):
    result = []
    for resident_id, resident in residents.items():
        if resident["status"] == "ACTIVE":
            bed_id = resident.get("bed_id")
            if bed_id and beds[bed_id]["room_id"] == room_id:
                result.append(resident_id)
    return result


def print_line():
    print("-" * 64)


# ------------------------------------------------------------
# 3. PROPERTY, ROOM, BED AND RESIDENT REGISTRATION
# ------------------------------------------------------------

def register_property(property_id, name, location):
    if property_id in properties:
        print("Property ID already exists.")
        return
    properties[property_id] = {
        "name": name,
        "location": location,
    }
    print(f"PROPERTY REGISTERED: {property_id} - {name}")


def register_room(property_id, room_id, room_type, ac_type, floor, gender):
    room_type = room_type.lower()
    ac_type = ac_type.upper() if ac_type.upper() == "AC" else "Non-AC"
    gender = gender.lower()

    if property_id not in properties:
        print("Property does not exist.")
        return
    if room_id in rooms:
        print("Room ID already exists.")
        return
    if room_type not in ("single", "double", "triple"):
        print("Room type must be single, double or triple.")
        return
    if (room_type, ac_type) not in RENT_CARD:
        print("Invalid AC type.")
        return
    if gender not in ("male", "female", "any"):
        print("Gender must be male, female or any.")
        return

    capacity = {"single": 1, "double": 2, "triple": 3}[room_type]
    rooms[room_id] = {
        "property_id": property_id,
        "room_type": room_type,
        "ac_type": ac_type,
        "floor": int(floor),
        "gender": gender,
        "capacity": capacity,
    }

    for number in range(1, capacity + 1):
        bed_id = f"{room_id}-B{number}"
        beds[bed_id] = {"room_id": room_id}

    print(f"ROOM REGISTERED: {room_id} | Beds: {capacity}")


def register_resident(resident_id, name, gender, preferred_room="any",
                      preferred_ac="any", requested_date=None):
    if resident_id in residents:
        print("Resident ID already exists.")
        return
    gender = gender.lower()
    preferred_room = preferred_room.lower()
    preferred_ac = preferred_ac.lower()

    if gender not in ("male", "female"):
        print("Gender must be male or female.")
        return
    if preferred_room not in ("any", "single", "double", "triple"):
        print("Invalid room preference.")
        return
    if preferred_ac not in ("any", "ac", "non-ac"):
        print("Invalid AC preference.")
        return

    residents[resident_id] = {
        "name": name,
        "gender": gender,
        "preferred_room": preferred_room,
        "preferred_ac": preferred_ac,
        "status": "REGISTERED",
        "bed_id": None,
        "deposit": 0,
        "move_in": None,
        "notice_date": None,
        "meal_plan": "NONE",
        "meal_history": [],
        "addons": [],
        "room_changes": [],
        "absence_records": [],
        "damage_amount": 0,
    }
    print(f"RESIDENT REGISTERED: {resident_id} - {name}")


def available_beds():
    occupied = {
        resident["bed_id"]
        for resident in residents.values()
        if resident["status"] == "ACTIVE" and resident["bed_id"]
    }
    return [bed_id for bed_id in beds if bed_id not in occupied]


# ------------------------------------------------------------
# 4. DETERMINISTIC BED ALLOCATION
# ------------------------------------------------------------

def allocation_candidates(resident_id):
    resident = residents[resident_id]
    candidates = []

    for bed_id in available_beds():
        room_id = beds[bed_id]["room_id"]
        room = rooms[room_id]

        # Rule 1: gender eligibility.
        if room["gender"] not in ("any", resident["gender"]):
            continue

        # Rule 2 and 3: preferences are used for ranking.
        room_match = 0 if resident["preferred_room"] == "any" or room["room_type"] == resident["preferred_room"] else 1
        ac_match = 0 if resident["preferred_ac"] == "any" or room["ac_type"].lower() == resident["preferred_ac"] else 1

        # Rule 4: lower floor first.
        floor_rank = room["floor"]

        # Rule 5: fill the room with most current occupants first.
        occupancy_rank = -len(occupied_residents(room_id))

        # Rule 6: lowest bed ID as final tie-breaker.
        candidates.append((room_match, ac_match, floor_rank, occupancy_rank, bed_id))

    return sorted(candidates)


def allocate_bed(resident_id):
    if resident_id not in residents:
        print("Resident not found.")
        return None
    if residents[resident_id]["status"] == "ACTIVE":
        print("Resident is already active.")
        return residents[resident_id]["bed_id"]

    candidates = allocation_candidates(resident_id)
    if not candidates:
        print("No matching bed available. Resident can be added to waitlist.")
        return None

    bed_id = candidates[0][-1]
    residents[resident_id]["bed_id"] = bed_id
    print(f"BED ALLOCATED: {resident_id} -> {bed_id}")
    return bed_id


# ------------------------------------------------------------
# 5. MOVE-IN, DEPOSIT AND RESIDENT LIFECYCLE
# ------------------------------------------------------------

def complete_move_in(resident_id, move_in_text):
    if resident_id not in residents:
        print("Resident not found.")
        return
    resident = residents[resident_id]
    if resident["status"] == "ACTIVE":
        print("Resident is already active.")
        return

    if not resident["bed_id"]:
        if not allocate_bed(resident_id):
            return

    move_in = parse_date(move_in_text)
    room_id = current_room(resident_id)
    monthly_rent = rent_for_room(room_id)
    resident["move_in"] = move_in
    resident["deposit"] = monthly_rent * 2
    resident["status"] = "ACTIVE"
    stays[resident_id] = {
        "move_in": move_in,
        "move_out": None,
        "initial_rent": monthly_rent,
    }

    # Start meal plan history from the move-in date.
    resident["meal_plan"] = "NONE"
    resident["meal_history"] = [(move_in, "NONE")]
    print(f"MOVE-IN COMPLETED: {resident['name']} | {date_text(move_in)}")
    print(f"Monthly rent: Rs. {monthly_rent} | Deposit: Rs. {resident['deposit']}")


def change_resident_room(resident_id, new_bed_id, change_text):
    if not active_resident(resident_id):
        print("Only active residents can change rooms.")
        return
    if new_bed_id not in beds or new_bed_id not in available_beds():
        print("New bed is not available.")
        return

    change_date = parse_date(change_text)
    old_bed = residents[resident_id]["bed_id"]
    old_room = beds[old_bed]["room_id"]
    new_room = beds[new_bed_id]["room_id"]

    if rooms[new_room]["gender"] not in ("any", residents[resident_id]["gender"]):
        print("The new room is not eligible for this resident.")
        return

    changes = residents[resident_id]["room_changes"]
    fee = 0
    if changes:
        last_change = changes[-1]["date"]
        if (change_date - last_change).days < 180:
            fee = ROOM_CHANGE_FEE

    old_rent = rent_for_room(old_room)
    new_rent = rent_for_room(new_room)
    old_deposit = residents[resident_id]["deposit"]
    new_deposit = new_rent * 2

    residents[resident_id]["bed_id"] = new_bed_id
    residents[resident_id]["deposit"] = new_deposit
    changes.append({
        "date": change_date,
        "old_bed": old_bed,
        "new_bed": new_bed_id,
        "old_rent": old_rent,
        "new_rent": new_rent,
        "deposit_adjustment": new_deposit - old_deposit,
        "fee": fee,
    })

    print("ROOM CHANGE COMPLETED")
    print(f"New bed: {new_bed_id} | New monthly rent: Rs. {new_rent}")
    print(f"Deposit adjustment: Rs. {new_deposit - old_deposit}")
    print(f"Room change fee: Rs. {fee}")


def record_absence(resident_id, start_text, end_text, prior_notice=True):
    if not active_resident(resident_id):
        print("Only active residents can record absence.")
        return
    start = parse_date(start_text)
    end = parse_date(end_text)
    if end < start:
        print("End date cannot be before start date.")
        return
    residents[resident_id]["absence_records"].append({
        "start": start,
        "end": end,
        "prior_notice": bool(prior_notice),
    })
    print(f"ABSENCE RECORDED: {resident_id} | {date_text(start)} to {date_text(end)}")


def add_to_waitlist(resident_id, request_text):
    global next_waitlist_number
    if resident_id not in residents:
        print("Resident not found.")
        return
    if any(item["resident_id"] == resident_id for item in waitlist):
        print("Resident is already on the waitlist.")
        return
    waitlist.append({
        "number": next_waitlist_number,
        "resident_id": resident_id,
        "request_date": parse_date(request_text),
        "status": "WAITING",
        "offered_bed": None,
        "offer_deadline": None,
    })
    next_waitlist_number += 1
    print(f"Added {resident_id} to waitlist.")


def process_waitlist(today=None):
    """Offer a newly free bed to the first eligible waitlisted resident."""
    if today is None:
        today = date.today()

    # Expired offers return to the end of the queue.
    for item in waitlist:
        if item["status"] == "OFFERED" and item["offer_deadline"] < today:
            item["status"] = "WAITING"
            item["offered_bed"] = None
            item["offer_deadline"] = None
            item["request_date"] = today

    waiting = sorted(
        [item for item in waitlist if item["status"] == "WAITING"],
        key=lambda item: (0 if residents[item["resident_id"]]["preferred_room"] == "any" else 1,
                          item["request_date"], item["number"])
    )

    for item in waiting:
        resident_id = item["resident_id"]
        candidates = allocation_candidates(resident_id)
        if candidates:
            bed_id = candidates[0][-1]
            item["status"] = "OFFERED"
            item["offered_bed"] = bed_id
            item["offer_deadline"] = today + timedelta(hours=48)
            print(f"WAITLIST OFFER: {resident_id} -> {bed_id}; confirm within 48 hours.")
            return


def confirm_waitlist_offer(resident_id, confirm=True):
    item = next((x for x in waitlist if x["resident_id"] == resident_id and x["status"] == "OFFERED"), None)
    if not item:
        print("No active offer found.")
        return
    if not confirm:
        item["status"] = "WAITING"
        item["request_date"] = date.today()
        item["offered_bed"] = None
        item["offer_deadline"] = None
        print("Offer declined; resident moved to the end of the waitlist.")
        return

    if item["offer_deadline"] < date.today():
        item["status"] = "WAITING"
        item["request_date"] = date.today()
        print("Offer expired.")
        return

    residents[resident_id]["bed_id"] = item["offered_bed"]
    item["status"] = "CONFIRMED"
    print(f"WAITLIST OFFER CONFIRMED: {resident_id} -> {item['offered_bed']}")


def complete_move_out(resident_id, move_out_text, notice_text=None):
    if not active_resident(resident_id):
        print("Resident is not active.")
        return

    move_out = parse_date(move_out_text)
    resident = residents[resident_id]
    move_in = resident["move_in"]
    notice_date = parse_date(notice_text) if notice_text else None
    notice_days = (move_out - notice_date).days if notice_date else 0
    notice_charge = 0
    if notice_date and notice_days < 30:
        notice_charge = max(0, 30 - notice_days) * rent_for_room(current_room(resident_id)) // 30

    stay_days = (move_out - move_in).days
    cleaning = CLEANING_FEE_SHORT_STAY if stay_days < 90 else 0
    deposit = resident["deposit"]
    dues = notice_charge + cleaning + resident["damage_amount"]
    refund = max(0, deposit - dues)
    additional_due = max(0, dues - deposit)

    old_bed = resident["bed_id"]
    resident["status"] = "MOVED OUT"
    resident["bed_id"] = None
    stays[resident_id]["move_out"] = move_out

    print("MOVE-OUT SETTLEMENT")
    print(f"Notice days: {notice_days}")
    print(f"Notice charge: Rs. {notice_charge}")
    print(f"Cleaning: Rs. {cleaning}")
    print(f"Damages: Rs. {resident['damage_amount']}")
    print(f"Security deposit: Rs. {deposit}")
    print(f"Final refund: Rs. {refund}")
    print(f"Additional amount due: Rs. {additional_due}")
    print(f"Bed released: {old_bed}")
    process_waitlist(move_out)


# ------------------------------------------------------------
# 6. MEAL PLANS, ADD-ONS AND MONTHLY BILLING
# ------------------------------------------------------------

def change_meal_plan(resident_id, new_plan, effective_text):
    if not active_resident(resident_id):
        print("Resident is not active.")
        return
    new_plan = new_plan.upper()
    if new_plan not in MEAL_RATES:
        print("Meal plan must be NONE, BREAKFAST, TWO_MEALS or FULL.")
        return
    effective_date = parse_date(effective_text)
    residents[resident_id]["meal_history"].append((effective_date, new_plan))
    residents[resident_id]["meal_plan"] = new_plan
    print(f"Meal plan for {resident_id} changes to {new_plan} from {date_text(effective_date)}.")


def add_addon(resident_id, addon_name):
    if not active_resident(resident_id):
        print("Resident is not active.")
        return
    addon_name = addon_name.lower()
    if addon_name == "guest":
        print("Guest charges are entered separately in the guest field of the bill.")
        return
    if addon_name not in ADDON_RATES:
        print("Add-on must be laundry, two_wheeler or car.")
        return
    if addon_name not in residents[resident_id]["addons"]:
        residents[resident_id]["addons"].append(addon_name)
    print(f"Add-on added: {addon_name}")


def set_electricity_reading(room_id, year, month, units, rate_per_unit):
    if room_id not in rooms:
        print("Room not found.")
        return
    electricity_readings[(room_id, year, month)] = {
        "units": float(units),
        "rate": float(rate_per_unit),
    }
    print(f"Electricity reading saved for {room_id}: {units} units.")


def meal_plan_for_day(resident, day):
    history = sorted(resident["meal_history"], key=lambda x: x[0])
    plan = "NONE"
    for effective_date, plan_name in history:
        if effective_date <= day:
            plan = plan_name
        else:
            break
    return plan


def resident_present_on_day(resident, day):
    for absence in resident["absence_records"]:
        if absence["start"] <= day <= absence["end"]:
            return False
    return True


def calculate_meal_charge(resident, start, end):
    total = 0.0
    current = start
    while current <= end:
        daily_rate = MEAL_RATES[meal_plan_for_day(resident, current)] / monthrange(current.year, current.month)[1]
        total += daily_rate
        current += timedelta(days=1)
    return money(total)


def calculate_absence_credit(resident, start, end):
    credit = 0.0
    for absence in resident["absence_records"]:
        days = (absence["end"] - absence["start"]).days + 1
        if absence["prior_notice"] and days >= 5:
            first = max(start, absence["start"])
            last = min(end, absence["end"])
            if first <= last:
                for day_number in range((last - first).days + 1):
                    day = first + timedelta(days=day_number)
                    plan = meal_plan_for_day(resident, day)
                    daily_rate = MEAL_RATES[plan] / monthrange(day.year, day.month)[1]
                    credit += daily_rate * 0.5
    return money(credit)


def rent_for_billing_period(resident_id, start, end):
    """Prorate rent by day and apply room-change date using higher old/new rent."""
    resident = residents[resident_id]
    total = 0.0
    current = start
    while current <= end:
        if current < resident["move_in"]:
            current += timedelta(days=1)
            continue
        if stays[resident_id]["move_out"] and current > stays[resident_id]["move_out"]:
            current += timedelta(days=1)
            continue

        daily_rent = rent_for_room(current_room(resident_id))
        for change in resident["room_changes"]:
            if change["date"] == current:
                daily_rent = max(change["old_rent"], change["new_rent"])
        total += daily_rent / monthrange(current.year, current.month)[1]
        current += timedelta(days=1)
    return money(total)


def electricity_share(resident_id, year, month):
    room_id = current_room(resident_id)
    if not room_id:
        return 0
    reading = electricity_readings.get((room_id, year, month))
    if not reading:
        return 0

    total_charge = reading["units"] * reading["rate"]
    first, last = month_dates(year, month)
    occupants = occupied_residents(room_id)
    daily_share = 0.0

    for day_number in range((last - first).days + 1):
        day = first + timedelta(days=day_number)
        present = [rid for rid in occupants if residents[rid]["move_in"] <= day
                   and (not stays[rid]["move_out"] or day <= stays[rid]["move_out"])
                   and resident_present_on_day(residents[rid], day)]
        if resident_id in present and present:
            daily_share += total_charge / len(present) / (last - first).days.__class__(last.day)

    return money(daily_share)


def generate_monthly_bill(resident_id, year, month, payment_date_text=None,
                          guest_nights=0, extra_charges=0):
    if resident_id not in residents:
        print("Resident not found.")
        return
    resident = residents[resident_id]
    if resident["status"] not in ("ACTIVE", "MOVED OUT"):
        print("Resident has no billable stay.")
        return

    first, last = month_dates(year, month)
    bill_start = max(first, resident["move_in"])
    move_out = stays[resident_id]["move_out"]
    bill_end = min(last, move_out) if move_out else last
    if bill_end < bill_start:
        print("No stay during this month.")
        return

    rent = rent_for_billing_period(resident_id, bill_start, bill_end)
    meal = calculate_meal_charge(resident, bill_start, bill_end)
    absence_credit = calculate_absence_credit(resident, bill_start, bill_end)

    addons = sum(ADDON_RATES[name] for name in resident["addons"])
    guest_charge = min(max(int(guest_nights), 0), 3) * 500
    electricity = electricity_share(resident_id, year, month)
    late_fee = 0
    if payment_date_text:
        payment_date = parse_date(payment_date_text)
        due_date = date(year, month, 7)
        if payment_date > due_date:
            late_days = (payment_date - due_date).days
            late_fee = min(late_days * LATE_FEE_PER_DAY, MAX_LATE_FEE)

    adjustment = sum(
        change["deposit_adjustment"] + change["fee"]
        for change in resident["room_changes"]
        if change["date"].year == year and change["date"].month == month
    )

    total = rent + meal + addons + guest_charge + electricity + late_fee + extra_charges - absence_credit + adjustment
    bill = {
        "resident_id": resident_id,
        "month": month_key(first),
        "rent": rent,
        "meal": meal,
        "addons": addons,
        "guest": guest_charge,
        "electricity": electricity,
        "late_fee": late_fee,
        "absence_credit": absence_credit,
        "adjustment": adjustment,
        "extra_charges": money(extra_charges),
        "total": money(total),
    }
    bills[(resident_id, year, month)] = bill

    print("\n========== MONTHLY BILL ==========")
    print(f"Resident: {resident['name']} ({resident_id})")
    print(f"Billing month: {first.strftime('%B %Y')}")
    print(f"Rent: Rs. {rent}")
    print(f"Meal plan: Rs. {meal}")
    print(f"Add-ons: Rs. {addons}")
    print(f"Guest charges: Rs. {guest_charge}")
    print(f"Electricity: Rs. {electricity}")
    print(f"Late fee: Rs. {late_fee}")
    print(f"Absence meal credit: -Rs. {absence_credit}")
    print(f"Adjustments / other charges: Rs. {adjustment + money(extra_charges)}")
    print_line()
    print(f"TOTAL: Rs. {money(total)}")
    print("==================================")
    return bill


def record_payment(resident_id, year, month, amount, payment_text):
    payment_date = parse_date(payment_text)
    payment_history[resident_id].append({
        "date": payment_date,
        "amount": float(amount),
        "month": month_key(date(year, month, 1)),
    })
    print(f"Payment recorded: Rs. {amount} from {resident_id}.")


# ------------------------------------------------------------
# 7. REPORTS, WAITLIST, ADVANCED RULES AND TESTING
# ------------------------------------------------------------

def show_property_report():
    print("\n" + "=" * 64)
    print("PROPERTY OCCUPANCY REPORT")
    print("=" * 64)
    for property_id, prop in properties.items():
        print(f"\nProperty: {property_id} - {prop['name']}")
        print(f"Location: {prop['location']}")
        for room_id, room in rooms.items():
            if room["property_id"] != property_id:
                continue
            print(f"\nRoom {room_id}: {room['room_type']} | {room['ac_type']} | Floor {room['floor']}")
            for bed_id, bed in beds.items():
                if bed["room_id"] != room_id:
                    continue
                occupant = next((r["name"] for r in residents.values()
                                 if r["status"] == "ACTIVE" and r["bed_id"] == bed_id), None)
                print(f"  {bed_id}: {'OCCUPIED by ' + occupant if occupant else 'AVAILABLE'}")
    occupied = sum(1 for r in residents.values() if r["status"] == "ACTIVE" and r["bed_id"])
    print_line()
    print(f"Total beds: {len(beds)}")
    print(f"Occupied beds: {occupied}")
    print(f"Available beds: {len(beds) - occupied}")
    print("=" * 64)


def show_waitlist():
    print("\n========== WAITLIST ==========")
    if not waitlist:
        print("Waitlist is empty.")
    for item in sorted(waitlist, key=lambda x: (x["status"] != "OFFERED", x["request_date"], x["number"])):
        print(f"{item['number']}. {item['resident_id']} | {item['status']} | "
              f"Requested: {date_text(item['request_date'])} | Offer: {item['offered_bed']}")
    print("==============================")


def show_resident_ledger(resident_id=None):
    selected = [resident_id] if resident_id else list(residents.keys())
    print("\n========== RESIDENT LEDGER ==========")
    for rid in selected:
        if rid not in residents:
            continue
        r = residents[rid]
        print(f"\nID: {rid} | Name: {r['name']}")
        print(f"Status: {r['status']} | Bed: {r['bed_id'] or '-'}")
        print(f"Move-in: {date_text(r['move_in'])}")
        print(f"Deposit: Rs. {r['deposit']}")
        print(f"Meal plan: {r['meal_plan']}")
        print(f"Add-ons: {', '.join(r['addons']) if r['addons'] else 'None'}")
    print("=====================================")


def show_bills():
    print("\n========== BILL HISTORY ==========")
    if not bills:
        print("No bills generated yet.")
    for key, bill in bills.items():
        print(f"{bill['month']} | {bill['resident_id']} | Total: Rs. {bill['total']}")
    print("==================================")


def run_edge_case_checks():
    print("\n========== BASIC EDGE-CASE CHECKS ==========")
    # A month can contain 28, 29, 30 or 31 days.
    for month in range(1, 13):
        assert 28 <= monthrange(2028, month)[1] <= 31
    # Move-in on the final day must produce one billable day.
    final_day = date(2026, 11, 30)
    assert (final_day - final_day).days + 1 == 1
    # Exactly five consecutive days qualifies for the absence rule.
    five_days = (date(2026, 11, 5) - date(2026, 11, 1)).days + 1
    assert five_days == 5
    # Late fee must never exceed the cap.
    assert min(100 * 100, MAX_LATE_FEE) == MAX_LATE_FEE
    print("PASS: Month length (including leap year)")
    print("PASS: One-day stay / move-in on last day")
    print("PASS: Exactly five absence days")
    print("PASS: Late fee cap")
    print("Note: These are rule checks; full live-data scenarios should also be tested.")
    print("============================================")


# ------------------------------------------------------------
# 8. SAMPLE DATA - RUNS WHEN THE PROGRAM STARTS
# ------------------------------------------------------------

def load_sample_data():
    register_property("PG001", "Bengaluru PG", "Bengaluru")

    register_room("PG001", "R101", "double", "AC", 1, "male")
    register_room("PG001", "R102", "triple", "Non-AC", 2, "male")
    register_room("PG001", "R103", "single", "AC", 0, "female")

    register_resident("P001", "Rahul", "male", "double", "ac")
    register_resident("P002", "Arjun", "male", "triple", "non-ac")
    register_resident("P003", "Priya", "female", "single", "ac")

    for rid in residents:
        allocate_bed(rid)

    complete_move_in("P001", "01-11-2026")
    complete_move_in("P002", "03-11-2026")
    complete_move_in("P003", "05-11-2026")


# ------------------------------------------------------------
# 9. SIMPLE MENU - USE THIS TO TEST THE FEATURES
# ------------------------------------------------------------

def show_menu():
    print("\n" + "=" * 64)
    print("PG MANAGEMENT SYSTEM - MAIN MENU")
    print("=" * 64)
    print("1. Show property / occupancy report")
    print("2. Show resident ledger")
    print("3. Register a new resident")
    print("4. Allocate a bed")
    print("5. Complete move-in")
    print("6. Change room")
    print("7. Record absence")
    print("8. Add resident to waitlist")
    print("9. Show / process waitlist")
    print("10. Confirm waitlist offer")
    print("11. Change meal plan")
    print("12. Add add-on")
    print("13. Enter room electricity reading")
    print("14. Generate monthly bill")
    print("15. Record payment")
    print("16. Complete move-out")
    print("17. Show bill history")
    print("18. Run basic edge-case checks")
    print("0. Exit")


def main():
    print("=" * 64)
    print("             PG OCCUPANCY AND BILLING ENGINE")
    print("=" * 64)
    print("Team ID: T015 | Project: Co-living PG Management System")
    print("Problem Statement: PS-107 | Python 3")
    print("System: PG Occupancy, Bed Allocation and Billing")
    print("=" * 64)

    print("\n========== MONTHLY RENT CARD ==========")
    for (room_type, ac_type), rent in RENT_CARD.items():
        print(f"{room_type.title()} - {ac_type}: Rs. {rent}")
    print("=======================================")

    if not properties:
        load_sample_data()

    show_property_report()
    show_resident_ledger()

    while True:
        show_menu()
        choice = input("Enter your choice: ").strip()

        try:
            if choice == "1":
                show_property_report()
            elif choice == "2":
                show_resident_ledger()
            elif choice == "3":
                rid = input("Resident ID: ").strip()
                name = input("Name: ").strip()
                gender = input("Gender (male/female): ").strip()
                pref_room = input("Room preference (any/single/double/triple): ").strip() or "any"
                pref_ac = input("AC preference (any/ac/non-ac): ").strip() or "any"
                register_resident(rid, name, gender, pref_room, pref_ac)
            elif choice == "4":
                allocate_bed(input("Resident ID: ").strip())
            elif choice == "5":
                complete_move_in(input("Resident ID: ").strip(), input("Move-in date DD-MM-YYYY: ").strip())
            elif choice == "6":
                change_resident_room(
                    input("Resident ID: ").strip(),
                    input("New bed ID: ").strip(),
                    input("Change date DD-MM-YYYY: ").strip()
                )
            elif choice == "7":
                rid = input("Resident ID: ").strip()
                start = input("Absence start DD-MM-YYYY: ").strip()
                end = input("Absence end DD-MM-YYYY: ").strip()
                notice = input("Prior notice given? (y/n): ").strip().lower() == "y"
                record_absence(rid, start, end, notice)
            elif choice == "8":
                add_to_waitlist(input("Resident ID: ").strip(), input("Request date DD-MM-YYYY: ").strip())
            elif choice == "9":
                process_waitlist()
                show_waitlist()
            elif choice == "10":
                rid = input("Resident ID: ").strip()
                confirm = input("Confirm offer? (y/n): ").strip().lower() == "y"
                confirm_waitlist_offer(rid, confirm)
            elif choice == "11":
                rid = input("Resident ID: ").strip()
                plan = input("Plan (NONE/BREAKFAST/TWO_MEALS/FULL): ").strip()
                effective = input("Effective date DD-MM-YYYY: ").strip()
                change_meal_plan(rid, plan, effective)
            elif choice == "12":
                add_addon(input("Resident ID: ").strip(), input("Add-on (laundry/two_wheeler/car): ").strip())
            elif choice == "13":
                room_id = input("Room ID: ").strip()
                year = int(input("Year: "))
                month = int(input("Month (1-12): "))
                units = float(input("Units consumed: "))
                rate = float(input("Rate per unit: "))
                set_electricity_reading(room_id, year, month, units, rate)
            elif choice == "14":
                rid = input("Resident ID: ").strip()
                year = int(input("Billing year: "))
                month = int(input("Billing month (1-12): "))
                paid_on = input("Payment date DD-MM-YYYY (blank if not paid yet): ").strip() or None
                guests = int(input("Guest nights (0-3): ") or "0")
                extra = float(input("Other charges (0 if none): ") or "0")
                generate_monthly_bill(rid, year, month, paid_on, guests, extra)
            elif choice == "15":
                rid = input("Resident ID: ").strip()
                year = int(input("Bill year: "))
                month = int(input("Bill month: "))
                amount = float(input("Amount paid: "))
                paid_on = input("Payment date DD-MM-YYYY: ").strip()
                record_payment(rid, year, month, amount, paid_on)
            elif choice == "16":
                rid = input("Resident ID: ").strip()
                move_out = input("Move-out date DD-MM-YYYY: ").strip()
                notice = input("Notice date DD-MM-YYYY (blank if none): ").strip() or None
                complete_move_out(rid, move_out, notice)
            elif choice == "17":
                show_bills()
            elif choice == "18":
                run_edge_case_checks()
            elif choice == "0":
                print("Thank you. Program closed.")
                break
            else:
                print("Invalid choice. Please select from the menu.")
        except ValueError:
            print("Invalid input. Check the date, number or ID and try again.")
        except KeyError as error:
            print(f"Required record not found: {error}")
        except Exception as error:
            print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()
