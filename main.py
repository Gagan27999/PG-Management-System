# ============================================================
# PG OCCUPANCY AND BILLING ENGINE
# Team ID: T015 | Problem Statement: PS-107
# Days 1 and 2: Setup, allocation, move-in/out, room change,
# absence tracking and waitlist
# ============================================================

from datetime import datetime, timedelta
import calendar


# ============================================================
# DAY 1 - STEP 1: PROJECT DETAILS AND RENT CARD
# ============================================================

print("=" * 60)
print("             PG OCCUPANCY AND BILLING ENGINE")
print("=" * 60)
print("Team ID: T015")
print("Project: Co-living PG Management System")
print("Language: Python")
print("Development: Day 1 and Day 2")
print("=" * 60)

# Monthly rent charged for each bed.
# True means AC; False means Non-AC.
RENT_CARD = {
    ("single", True): 18000,
    ("single", False): 14000,
    ("double", True): 12000,
    ("double", False): 9500,
    ("triple", True): 9000,
    ("triple", False): 7000
}

print("\n========== MONTHLY RENT CARD ==========")
for (room_type, ac), rent in RENT_CARD.items():
    ac_status = "AC" if ac else "Non-AC"
    print(room_type.title(), "-", ac_status, ": Rs.", rent)
print("=======================================")


# ============================================================
# DAY 1 - STEP 2: DATA STORAGE
# ============================================================

# These dictionaries/lists store the project's information.
properties = {}
residents = {}
allocations = {}
stay_records = {}
waitlist = []


# ============================================================
# DAY 1 - STEP 3: PROPERTY REGISTRATION
# ============================================================

def register_property(property_id, property_name, location):
    """Register a PG property."""

    if property_id in properties:
        print("Error: Property ID already exists!")
        return False

    properties[property_id] = {
        "property_name": property_name,
        "location": location,
        "rooms": []
    }

    print("\nPROPERTY REGISTERED:", property_id, "-", property_name)
    return True


# ============================================================
# DAY 1 - STEP 4: ROOM AND BED REGISTRATION
# ============================================================

def register_room(property_id, room_id, room_type, ac, floor, gender):
    """Register a room and automatically create its beds."""

    if property_id not in properties:
        print("Error: Property does not exist!")
        return False

    room_type = room_type.lower()
    gender = gender.lower()

    if room_type not in ["single", "double", "triple"]:
        print("Error: Room type must be single, double or triple!")
        return False

    if gender not in ["male", "female"]:
        print("Error: Gender must be male or female!")
        return False

    if not isinstance(ac, bool):
        print("Error: AC must be True or False!")
        return False

    if not isinstance(floor, int) or floor < 0:
        print("Error: Floor must be zero or a positive number!")
        return False

    # Room IDs must be unique throughout the PG system.
    for property_data in properties.values():
        for room in property_data["rooms"]:
            if room["room_id"] == room_id:
                print("Error: Room ID already exists!")
                return False

    # A single room has 1 bed, double has 2 and triple has 3.
    number_of_beds = {
        "single": 1,
        "double": 2,
        "triple": 3
    }[room_type]

    beds = []
    for number in range(1, number_of_beds + 1):
        beds.append(room_id + "-B" + str(number))

    room = {
        "room_id": room_id,
        "room_type": room_type,
        "ac": ac,
        "floor": floor,
        "gender": gender,
        "beds": beds,
        "occupants": []
    }

    properties[property_id]["rooms"].append(room)

    print("\nROOM REGISTERED:", room_id, "| Beds:", ", ".join(beds))
    return True


# ============================================================
# DAY 1 - STEP 5: RESIDENT REGISTRATION
# ============================================================

def register_resident(resident_id, name, gender,
                      preferred_room_type, prefers_ac):
    """Register a resident and store their room preferences."""

    if resident_id in residents:
        print("Error: Resident ID already exists!")
        return False

    gender = gender.lower()
    preferred_room_type = preferred_room_type.lower()

    if gender not in ["male", "female"]:
        print("Error: Gender must be male or female!")
        return False

    if preferred_room_type not in ["single", "double", "triple"]:
        print("Error: Invalid preferred room type!")
        return False

    if not isinstance(prefers_ac, bool):
        print("Error: AC preference must be True or False!")
        return False

    residents[resident_id] = {
        "name": name,
        "gender": gender,
        "preferred_room_type": preferred_room_type,
        "prefers_ac": prefers_ac
    }

    print("\nRESIDENT REGISTERED:", resident_id, "-", name)
    return True


# ============================================================
# DAY 1 - STEP 6: FIND ROOM USING BED ID
# ============================================================

def find_room_by_bed(bed_id):
    """Return the room that contains the given bed ID."""

    if bed_id is None:
        return None

    for property_data in properties.values():
        for room in property_data["rooms"]:
            if bed_id in room["beds"]:
                return room

    return None


def find_resident_room(resident_id):
    """Find the room currently allocated to a resident."""

    bed_id = allocations.get(resident_id)
    return find_room_by_bed(bed_id)


# ============================================================
# DAY 1 - STEP 7: AUTOMATIC BED ALLOCATION
# ============================================================

def allocate_bed(resident_id):
    """
    Allocate the best available bed using these rules:
    gender -> room type -> AC -> lowest floor ->
    fill partly occupied rooms -> lowest bed ID.
    """

    if resident_id not in residents:
        print("Error: Resident does not exist!")
        return False

    if resident_id in allocations:
        print("Error: Resident already has a bed!")
        return False

    resident = residents[resident_id]
    candidates = []

    for property_data in properties.values():
        for room in property_data["rooms"]:

            # Gender must match.
            if room["gender"] != resident["gender"]:
                continue

            for bed_id in room["beds"]:

                # Ignore beds already allocated to another resident.
                if bed_id in allocations.values():
                    continue

                # False (match) sorts before True (mismatch).
                sort_key = (
                    room["room_type"] != resident["preferred_room_type"],
                    room["ac"] != resident["prefers_ac"],
                    room["floor"],
                    -len(room["occupants"]),
                    bed_id
                )

                candidates.append((sort_key, room, bed_id))

    if not candidates:
        print("No suitable bed available for", resident["name"])
        return False

    candidates.sort(key=lambda item: item[0])
    selected_room = candidates[0][1]
    selected_bed = candidates[0][2]

    allocations[resident_id] = selected_bed
    selected_room["occupants"].append(resident_id)

    rent_key = (selected_room["room_type"], selected_room["ac"])
    monthly_rent = RENT_CARD[rent_key]

    print("\n========== BED ALLOCATED ==========")
    print("Resident:", resident["name"])
    print("Resident ID:", resident_id)
    print("Room:", selected_room["room_id"])
    print("Bed:", selected_bed)
    print("Monthly Rent: Rs.", monthly_rent)
    print("===================================")

    return True


# ============================================================
# DAY 1 - STEP 8: PROPERTY AND OCCUPANCY REPORT
# ============================================================

def show_property_report():
    """Display each room, bed, occupant and availability."""

    print("\n" + "=" * 60)
    print("                    PROPERTY REPORT")
    print("=" * 60)

    for property_id, property_data in properties.items():
        print("\nProperty:", property_id, "-", property_data["property_name"])
        print("Location:", property_data["location"])

        total_beds = 0
        occupied_beds = 0

        for room in property_data["rooms"]:
            rent = RENT_CARD[(room["room_type"], room["ac"])]
            ac_text = "AC" if room["ac"] else "Non-AC"

            print("\nRoom:", room["room_id"],
                  "|", room["room_type"],
                  "|", ac_text,
                  "| Floor:", room["floor"],
                  "| Gender:", room["gender"],
                  "| Rent per bed: Rs.", rent)

            for bed_id in room["beds"]:
                total_beds += 1
                occupant_name = None

                for resident_id, allocated_bed in allocations.items():
                    if allocated_bed == bed_id:
                        occupant_name = residents[resident_id]["name"]
                        break

                if occupant_name:
                    occupied_beds += 1
                    print("  ", bed_id, "| OCCUPIED by", occupant_name)
                else:
                    print("  ", bed_id, "| AVAILABLE")

        print("\nTotal beds:", total_beds)
        print("Occupied beds:", occupied_beds)
        print("Available beds:", total_beds - occupied_beds)

    print("=" * 60)


# ============================================================
# DAY 2 - STEP 1: MOVE-IN AND SECURITY DEPOSIT
# ============================================================

def complete_move_in(resident_id, move_in_date):
    """Record move-in date and collect a two-month rent deposit."""

    if resident_id not in residents:
        print("Error: Resident does not exist!")
        return False

    if resident_id not in allocations:
        print("Error: Resident has no allocated bed!")
        return False

    if resident_id in stay_records:
        print("Error: Move-in already recorded!")
        return False

    try:
        move_in = datetime.strptime(move_in_date, "%d-%m-%Y").date()
    except ValueError:
        print("Error: Enter date in DD-MM-YYYY format!")
        return False

    room = find_resident_room(resident_id)
    if room is None:
        print("Error: Allocated room not found!")
        return False

    monthly_rent = RENT_CARD[(room["room_type"], room["ac"])]
    deposit = monthly_rent * 2

    stay_records[resident_id] = {
        "move_in_date": move_in,
        "monthly_rent": monthly_rent,
        "security_deposit": deposit,
        "status": "ACTIVE",
        "last_room_change": None,
        "room_changes": 0,
        "absences": [],
        "pending_deposit_adjustment": 0,
        "pending_room_change_fee": 0,
        "room_change_history": []
    }

    print("\n========== MOVE-IN COMPLETED ==========")
    print("Resident:", residents[resident_id]["name"])
    print("Move-in Date:", move_in.strftime("%d-%m-%Y"))
    print("Monthly Rent: Rs.", monthly_rent)
    print("Security Deposit: Rs.", deposit)
    print("Status: ACTIVE")
    print("=======================================")
    return True


# ============================================================
# DAY 2 - STEP 2: RESIDENT MOVE-OUT AND SETTLEMENT
# ============================================================

def complete_move_out(resident_id, notice_date, move_out_date,
                      pending_dues=0, damages=0):
    """
    Settle the resident's deposit during move-out.
    A full 30-day notice allows unused current-month rent refund.
    """

    if resident_id not in stay_records:
        print("Error: No stay record found!")
        return False

    stay = stay_records[resident_id]

    if stay["status"] != "ACTIVE":
        print("Error: Resident has already moved out!")
        return False

    try:
        notice = datetime.strptime(notice_date, "%d-%m-%Y").date()
        move_out = datetime.strptime(move_out_date, "%d-%m-%Y").date()
    except ValueError:
        print("Error: Enter dates in DD-MM-YYYY format!")
        return False

    move_in = stay["move_in_date"]

    if notice < move_in or move_out < notice:
        print("Error: Invalid notice or move-out date!")
        return False

    if pending_dues < 0 or damages < 0:
        print("Error: Charges cannot be negative!")
        return False

    notice_days = (move_out - notice).days
    notice_shortfall = max(0, 30 - notice_days)

    monthly_rent = stay["monthly_rent"]
    notice_charge = round(monthly_rent / 30 * notice_shortfall)

    # Calculate completed calendar months of stay.
    months_stayed = (
        (move_out.year - move_in.year) * 12
        + move_out.month - move_in.month
    )
    if move_out.day < move_in.day:
        months_stayed -= 1

    cleaning_charge = 1000 if months_stayed < 3 else 0

    unused_rent_refund = 0
    if notice_days >= 30:
        days_in_month = calendar.monthrange(
            move_out.year, move_out.month
        )[1]
        unused_days = days_in_month - move_out.day
        unused_rent_refund = round(
            monthly_rent * unused_days / days_in_month
        )

    total_deductions = (
        notice_charge + pending_dues + damages + cleaning_charge
    )

    total_settlement = (
        stay["security_deposit"]
        + unused_rent_refund
        - total_deductions
    )

    final_refund = max(0, total_settlement)
    additional_due = max(0, -total_settlement)

    # Release the resident's bed.
    room = find_resident_room(resident_id)
    if room and resident_id in room["occupants"]:
        room["occupants"].remove(resident_id)

    allocations.pop(resident_id, None)

    stay["status"] = "MOVED OUT"
    stay["move_out_date"] = move_out
    stay["notice_date"] = notice
    stay["notice_days"] = notice_days
    stay["notice_charge"] = notice_charge
    stay["cleaning_charge"] = cleaning_charge
    stay["unused_rent_refund"] = unused_rent_refund
    stay["pending_dues"] = pending_dues
    stay["damages"] = damages
    stay["refund_amount"] = final_refund
    stay["remaining_amount_due"] = additional_due

    print("\n========== MOVE-OUT SETTLEMENT ==========")
    print("Resident:", residents[resident_id]["name"])
    print("Move-out Date:", move_out.strftime("%d-%m-%Y"))
    print("Notice Days:", notice_days)
    print("Notice Charge: Rs.", notice_charge)
    print("Cleaning Charge: Rs.", cleaning_charge)
    print("Pending Dues: Rs.", pending_dues)
    print("Damages: Rs.", damages)
    print("Unused Rent Refund: Rs.", unused_rent_refund)
    print("Security Deposit: Rs.", stay["security_deposit"])
    print("-----------------------------------------")
    print("Final Refund: Rs.", final_refund)
    print("Additional Amount Due: Rs.", additional_due)
    print("Status: MOVED OUT")
    print("=========================================")

    # Offer the newly vacant bed to someone on the waitlist.
    process_waitlist()
    return True


# ============================================================
# DAY 2 - STEP 3: ROOM CHANGE AND DEPOSIT ADJUSTMENT
# ============================================================

def change_resident_room(resident_id, new_bed_id, change_date):
    """Move an active resident to another available compatible bed."""

    if resident_id not in stay_records:
        print("Error: Resident stay record not found!")
        return False

    stay = stay_records[resident_id]
    if stay["status"] != "ACTIVE":
        print("Error: Resident is not active!")
        return False

    try:
        date_object = datetime.strptime(change_date, "%d-%m-%Y").date()
    except ValueError:
        print("Error: Use DD-MM-YYYY format!")
        return False

    if date_object < stay["move_in_date"]:
        print("Error: Room change cannot be before move-in!")
        return False

    old_bed = allocations.get(resident_id)
    old_room = find_room_by_bed(old_bed)
    new_room = find_room_by_bed(new_bed_id)

    if old_room is None or new_room is None:
        print("Error: Old or new room not found!")
        return False

    if old_bed == new_bed_id:
        print("Error: Resident is already using this bed!")
        return False

    if new_bed_id in allocations.values():
        print("Error: New bed is already occupied!")
        return False

    if new_room["gender"] != residents[resident_id]["gender"]:
        print("Error: Gender does not match the new room!")
        return False

    old_rent = RENT_CARD[(old_room["room_type"], old_room["ac"])]
    new_rent = RENT_CARD[(new_room["room_type"], new_room["ac"])]

    # First room change is free. Another change within 6 months costs Rs. 1000.
    last_change = stay["last_room_change"]
    change_fee = 0
    if last_change is not None:
        if (date_object - last_change).days < 183:
            change_fee = 1000

    old_deposit = stay["security_deposit"]
    new_deposit = new_rent * 2
    deposit_difference = new_deposit - old_deposit

    # Release old bed and occupy the new bed.
    if resident_id in old_room["occupants"]:
        old_room["occupants"].remove(resident_id)

    new_room["occupants"].append(resident_id)
    allocations[resident_id] = new_bed_id

    # Update the resident's current rent and deposit.
    stay["monthly_rent"] = new_rent
    stay["security_deposit"] = new_deposit
    stay["last_room_change"] = date_object
    stay["room_changes"] += 1

    # Save adjustments for the billing engine on Day 3.
    stay["pending_deposit_adjustment"] += deposit_difference
    stay["pending_room_change_fee"] += change_fee

    # Save history so Day 3 can calculate the change-date rent correctly.
    stay["room_change_history"].append({
        "date": date_object,
        "old_rent": old_rent,
        "new_rent": new_rent,
        "rent_for_change_date": max(old_rent, new_rent)
    })

    print("\n========== ROOM CHANGE COMPLETED ==========")
    print("Resident:", residents[resident_id]["name"])
    print("Old Bed:", old_bed)
    print("New Bed:", new_bed_id)
    print("New Monthly Rent: Rs.", new_rent)
    print("New Security Deposit: Rs.", new_deposit)
    print("Deposit Adjustment: Rs.", deposit_difference)
    print("Room Change Fee: Rs.", change_fee)
    print("============================================")

    # The old bed may now be available to a waiting resident.
    process_waitlist()
    return True


# ============================================================
# DAY 2 - STEP 4: ABSENCE TRACKING
# ============================================================

def record_absence(resident_id, start_date, end_date, notified=True):
    """Record absence dates and whether the PG was informed beforehand."""

    if resident_id not in stay_records:
        print("Error: Resident stay record not found!")
        return False

    stay = stay_records[resident_id]
    if stay["status"] != "ACTIVE":
        print("Error: Resident is not active!")
        return False

    try:
        start = datetime.strptime(start_date, "%d-%m-%Y").date()
        end = datetime.strptime(end_date, "%d-%m-%Y").date()
    except ValueError:
        print("Error: Use DD-MM-YYYY format!")
        return False

    if start < stay["move_in_date"] or end < start:
        print("Error: Invalid absence dates!")
        return False

    if not isinstance(notified, bool):
        print("Error: notified must be True or False!")
        return False

    # Add one because both start and end dates count as absent days.
    absent_days = (end - start).days + 1

    stay["absences"].append({
        "start_date": start,
        "end_date": end,
        "days": absent_days,
        "notified": notified,
        "meal_credit_eligible": notified and absent_days >= 5
    })

    print("\n========== ABSENCE RECORDED ==========")
    print("Resident:", residents[resident_id]["name"])
    print("Start:", start.strftime("%d-%m-%Y"))
    print("End:", end.strftime("%d-%m-%Y"))
    print("Absent Days:", absent_days)
    print("Prior Notice:", "YES" if notified else "NO")
    print("Meal Credit Eligible:",
          "YES" if notified and absent_days >= 5 else "NO")
    print("======================================")
    return True


# ============================================================
# DAY 2 - STEP 5: WAITLIST AND AUTOMATIC BED OFFER
# ============================================================

def process_waitlist():
    """
    Offer available beds to waiting residents.
    ANY preference has priority over SPECIFIC preference.
    """

    current_time = datetime.now()

    # Expire offers that were not confirmed within 48 hours.
    for item in waitlist:
        if item["status"] == "OFFERED":
            if current_time > item["confirmation_deadline"]:
                # Release the offered bed if it is still allocated.
                resident_id = item["resident_id"]
                bed_id = allocations.get(resident_id)

                if bed_id is not None:
                    room = find_room_by_bed(bed_id)
                    if room and resident_id in room["occupants"]:
                        room["occupants"].remove(resident_id)
                    allocations.pop(resident_id, None)

                item["status"] = "WAITING"
                item["request_date"] = current_time.date()
                item.pop("offered_bed", None)
                item.pop("confirmation_deadline", None)
                print("Waitlist offer expired for:", resident_id)

    # Sort waiting residents: ANY first, then earliest request date.
    waiting = [item for item in waitlist if item["status"] == "WAITING"]
    waiting.sort(key=lambda item: (
        0 if item["preference"] == "ANY" else 1,
        item["request_date"],
        item["request_time"]
    ))

    for item in waiting:
        resident_id = item["resident_id"]

        if resident_id in allocations:
            continue

        # allocate_bed applies gender, room and AC matching rules.
        if allocate_bed(resident_id):
            item["status"] = "OFFERED"
            item["offered_bed"] = allocations[resident_id]
            item["confirmation_deadline"] = (
                current_time + timedelta(hours=48)
            )
            print("WAITLIST OFFER: Confirm within 48 hours.")


def add_to_waitlist(resident_id, preference="SPECIFIC"):
    """Add a registered resident to the waiting list."""

    if resident_id not in residents:
        print("Error: Register the resident first!")
        return False

    if resident_id in allocations:
        print("Error: Resident already has a bed!")
        return False

    if any(item["resident_id"] == resident_id for item in waitlist):
        print("Error: Resident is already on the waitlist!")
        return False

    preference = preference.upper()
    if preference not in ["ANY", "SPECIFIC"]:
        print("Error: Preference must be ANY or SPECIFIC!")
        return False

    now = datetime.now()
    waitlist.append({
        "resident_id": resident_id,
        "preference": preference,
        "request_date": now.date(),
        "request_time": now,
        "status": "WAITING"
    })

    print("\nAdded to waitlist:", residents[resident_id]["name"])
    process_waitlist()
    return True


def confirm_waitlist_offer(resident_id):
    """Confirm a bed offer before the 48-hour deadline."""

    item = None
    for entry in waitlist:
        if entry["resident_id"] == resident_id:
            item = entry
            break

    if item is None or item["status"] != "OFFERED":
        print("Error: No active bed offer found!")
        return False

    if datetime.now() > item["confirmation_deadline"]:
        print("Error: The 48-hour offer has expired!")
        process_waitlist()
        return False

    item["status"] = "CONFIRMED"

    print("Waitlist offer confirmed for:",
          residents[resident_id]["name"])
    return True


def show_waitlist():
    """Display all residents currently on the waitlist."""

    print("\n========== WAITLIST ==========")

    if not waitlist:
        print("Waitlist is empty.")
    else:
        for item in waitlist:
            name = residents[item["resident_id"]]["name"]
            print(
                item["resident_id"], "|", name,
                "| Preference:", item["preference"],
                "| Status:", item["status"]
            )

    print("==============================")


# ============================================================
# DAY 2 - STEP 6: RESIDENT LEDGER AND OCCUPANCY REPORT
# ============================================================

def show_resident_ledger():
    """Display each resident's current stay and allocation details."""

    print("\n========== RESIDENT LEDGER ==========")

    for resident_id, resident in residents.items():
        bed_id = allocations.get(resident_id)
        stay = stay_records.get(resident_id)

        print("\nResident ID:", resident_id)
        print("Name:", resident["name"])
        print("Allocated Bed:", bed_id if bed_id else "No bed")

        if stay:
            print("Status:", stay["status"])
            print("Move-in Date:", stay["move_in_date"].strftime("%d-%m-%Y"))
            print("Monthly Rent: Rs.", stay["monthly_rent"])
            print("Security Deposit: Rs.", stay["security_deposit"])
        else:
            print("Status: NOT MOVED IN")

    print("=====================================")


# ============================================================
# DAY 1 AND DAY 2 - SAMPLE DATA
# ============================================================

# Register one sample PG property.
register_property("PG001", "Bengaluru PG", "Bengaluru")

# Register sample rooms.
register_room("PG001", "R101", "double", True, 1, "male")
register_room("PG001", "R102", "triple", False, 2, "male")
register_room("PG001", "R103", "single", True, 0, "female")

# Register sample residents.
register_resident("P001", "Rahul", "male", "double", True)
register_resident("P002", "Arjun", "male", "triple", False)
register_resident("P003", "Priya", "female", "single", True)

# Allocate beds using the automatic allocation rules.
allocate_bed("P001")
allocate_bed("P002")
allocate_bed("P003")

# Record move-in dates and security deposits.
complete_move_in("P001", "01-11-2026")
complete_move_in("P002", "03-11-2026")
complete_move_in("P003", "05-11-2026")

# Display the final Day 1 and Day 2 sample reports.
show_property_report()
show_resident_ledger()

print("\nDAY 1 AND DAY 2 INITIALIZATION COMPLETED SUCCESSFULLY!")
