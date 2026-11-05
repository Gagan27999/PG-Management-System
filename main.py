
# ==========================================
# PG OCCUPANCY AND BILLING ENGINE
# Team ID: T015
# Problem Statement: PS-107
# ==========================================

# Display the project heading
print("=" * 50)
print("       PG OCCUPANCY AND BILLING ENGINE")
print("=" * 50)

# Display basic project information
print("Team ID: T015")
print("Project: Co-living PG Management System")
print("Language: Python")

# Display the current development stage
print("\nDAY 1: PROJECT INITIALIZATION")

# Display a success message
print("Project started successfully!")


# ==========================================
# STEP 2: MONTHLY RENT CARD
# ==========================================

# Store monthly rent for each bed
# True means AC and False means Non-AC

RENT_CARD = {
    ("single", True): 18000,
    ("single", False): 14000,

    ("double", True): 12000,
    ("double", False): 9500,

    ("triple", True): 9000,
    ("triple", False): 7000
}

# Display all available rent categories
print("\n========== MONTHLY RENT CARD ==========")

# Go through every room type and AC option
for (room_type, ac), rent in RENT_CARD.items():

    # Display whether the room has AC
    if ac:
        ac_status = "AC"
    else:
        ac_status = "Non-AC"

    # Display the room type and monthly rent
    print(room_type.title(), "-", ac_status, ": Rs.", rent)

print("=======================================")

# ==========================================
# STEP 3: PROPERTY REGISTRATION
# ==========================================

# Store all registered properties
properties = {}


def register_property(property_id, property_name, location):
    """
    Register a new PG property.
    """

    # Check whether the property ID already exists
    if property_id in properties:
        print("Error: Property ID already exists!")
        return False

    # Store the property information
    properties[property_id] = {
        "property_name": property_name,
        "location": location,
        "rooms": []
    }

    # Display registration success
    print("\nPROPERTY REGISTERED SUCCESSFULLY!")
    print("Property ID:", property_id)
    print("Property Name:", property_name)
    print("Location:", location)

    return True


# Register our first sample property
register_property(
    "PG001",
    "Bengaluru PG",
    "Bengaluru"
)


# Display all registered properties
print("\n========== REGISTERED PROPERTIES ==========")

for property_id, details in properties.items():

    # Display property details
    print("Property ID:", property_id)
    print("Property Name:", details["property_name"])
    print("Location:", details["location"])

print("===========================================")

# ==========================================
# STEP 4: ROOM REGISTRATION
# ==========================================

def register_room(property_id, room_id, room_type, ac, floor, gender):
    """
    Register a room inside an existing PG property.
    """

    # Check whether the property exists
    if property_id not in properties:
        print("Error: Property does not exist!")
        return False

    # Convert room type and gender to lowercase
    room_type = room_type.lower()
    gender = gender.lower()

    # Check whether the room type is valid
    if room_type not in ["single", "double", "triple"]:
        print("Error: Invalid room type!")
        return False

    # Check whether gender is valid
    if gender not in ["male", "female"]:
        print("Error: Invalid gender!")
        return False

    # Check whether the floor number is valid
    if not isinstance(floor, int) or floor < 0:
        print("Error: Invalid floor number!")
        return False

    # Check whether the AC value is valid
    if not isinstance(ac, bool):
        print("Error: AC must be True or False!")
        return False

    # Check for duplicate room IDs across all properties
    for property_data in properties.values():
        for existing_room in property_data["rooms"]:
            if existing_room["room_id"] == room_id:
                print("Error: Room ID already exists!")
                return False

    # Determine the number of beds based on room type
    if room_type == "single":
        number_of_beds = 1
    elif room_type == "double":
        number_of_beds = 2
    else:
        number_of_beds = 3

    # Generate unique bed IDs for this room
    beds = []

    for bed_number in range(1, number_of_beds + 1):
        bed_id = room_id + "-B" + str(bed_number)
        beds.append(bed_id)

    # Create the room information
    room = {
        "room_id": room_id,
        "room_type": room_type,
        "ac": ac,
        "floor": floor,
        "gender": gender,
        "beds": beds,
        "occupants": []
    }

    # Add the room to the selected property
    properties[property_id]["rooms"].append(room)

    print("\nROOM REGISTERED SUCCESSFULLY!")
    print("Room ID:", room_id)
    print("Room Type:", room_type)
    print("AC:", ac)
    print("Floor:", floor)
    print("Gender:", gender)
    print("Beds:", beds)

    return True


# Register our first sample rooms
register_room("PG001", "R101", "double", True, 1, "male")
register_room("PG001", "R102", "triple", False, 2, "male")
register_room("PG001", "R103", "single", True, 0, "female")

# ==========================================
# STEP 5: PROPERTY AND ROOM REPORT
# ==========================================

def show_property_report():
    """
    Display all registered properties, rooms and beds.
    """

    print("\n")
    print("=" * 50)
    print("             PROPERTY REPORT")
    print("=" * 50)

    # Go through every registered property
    for property_id, property_data in properties.items():

        print("\nProperty ID:", property_id)
        print("Property Name:", property_data["property_name"])
        print("Location:", property_data["location"])

        # Store the total number of beds in this property
        total_beds = 0

        print("\n----------- ROOM DETAILS -----------")

        # Display every room in the property
        for room in property_data["rooms"]:

            # Calculate the rent using room type and AC status
            rent_key = (room["room_type"], room["ac"])
            monthly_rent = RENT_CARD[rent_key]

            # Display AC status in readable format
            if room["ac"]:
                ac_status = "AC"
            else:
                ac_status = "Non-AC"

            print("\nRoom ID:", room["room_id"])
            print("Room Type:", room["room_type"])
            print("Condition:", ac_status)
            print("Floor:", room["floor"])
            print("Gender:", room["gender"])
            print("Monthly Rent Per Bed: Rs.", monthly_rent)

            # Count the beds in this room
            total_beds += len(room["beds"])

            # Display all beds
            for bed in room["beds"]:
                print("   Bed:", bed, "| AVAILABLE")

        # Display property totals
        print("\n----------- PROPERTY SUMMARY -----------")
        print("Total Rooms:", len(property_data["rooms"]))
        print("Total Beds:", total_beds)

        print("=" * 50)


# Generate the property report
show_property_report()

# ==========================================
# STEP 6: RESIDENT REGISTRATION
# ==========================================

# Store all registered residents
residents = {}


def register_resident(resident_id, name, gender,
                      preferred_room_type, prefers_ac):
    """
    Register a new resident in the PG system.
    """

    # Check whether the resident ID already exists
    if resident_id in residents:
        print("Error: Resident ID already exists!")
        return False

    # Convert gender and room type to lowercase
    gender = gender.lower()
    preferred_room_type = preferred_room_type.lower()

    # Validate resident gender
    if gender not in ["male", "female"]:
        print("Error: Gender must be male or female!")
        return False

    # Validate preferred room type
    if preferred_room_type not in ["single", "double", "triple"]:
        print("Error: Invalid room type!")
        return False

    # Validate AC preference
    if not isinstance(prefers_ac, bool):
        print("Error: AC preference must be True or False!")
        return False

    # Store the resident's information
    residents[resident_id] = {
        "name": name,
        "gender": gender,
        "preferred_room_type": preferred_room_type,
        "prefers_ac": prefers_ac
    }

    # Display registration confirmation
    print("\nRESIDENT REGISTERED SUCCESSFULLY!")
    print("Resident ID:", resident_id)
    print("Name:", name)
    print("Gender:", gender)
    print("Preferred Room:", preferred_room_type)
    print("AC Preference:", prefers_ac)

    return True


# Register our first sample resident
register_resident(
    "P001",
    "Rahul",
    "male",
    "double",
    True
)


# Register our second sample resident
register_resident(
    "P002",
    "Arjun",
    "male",
    "triple",
    False
)


# Register our third sample resident
register_resident(
    "P003",
    "Priya",
    "female",
    "single",
    True
)

# ==========================================
# STEP 7: AUTOMATIC BED ALLOCATION
# ==========================================

# Store each resident's allocated bed
allocations = {}


def allocate_bed(resident_id):
    """
    Automatically find and allocate the best available bed.
    """

    # Check whether the resident is registered
    if resident_id not in residents:
        print("Error: Resident does not exist!")
        return False

    # Prevent a resident from getting multiple beds
    if resident_id in allocations:
        print("Error: Resident already has a bed!")
        return False

    # Get the resident's information
    resident = residents[resident_id]

    # Store all possible available beds
    candidates = []

    # Examine every registered property
    for property_data in properties.values():

        # Examine every room in the property
        for room in property_data["rooms"]:

            # RULE 1: Gender must match
            if room["gender"] != resident["gender"]:
                continue

            # Examine every bed in the room
            for bed_id in room["beds"]:

                # Skip beds that are already allocated
                if bed_id in allocations.values():
                    continue

                # RULE 2: Match preferred room type
                room_type_mismatch = (
                    room["room_type"]
                    != resident["preferred_room_type"]
                )

                # RULE 3: Match AC preference
                ac_mismatch = (
                    room["ac"] != resident["prefers_ac"]
                )

                # RULE 4: Prefer the lowest floor
                floor = room["floor"]

                # RULE 5: Prefer rooms with more occupants
                occupants_count = len(room["occupants"])

                # RULE 6: Use the lowest bed ID for ties
                sort_key = (
                    room_type_mismatch,
                    ac_mismatch,
                    floor,
                    -occupants_count,
                    bed_id
                )

                # Add this bed to the candidate list
                candidates.append(
                    (sort_key, room, bed_id)
                )

    # Check whether any suitable bed is available
    if not candidates:
        print("No suitable bed available for", resident["name"])
        return False

    # Sort all candidates according to business rules
    candidates.sort(key=lambda item: item[0])

    # Select the best available bed
    best_candidate = candidates[0]

    selected_room = best_candidate[1]
    selected_bed = best_candidate[2]

    # Save the allocation
    allocations[resident_id] = selected_bed

    # Add the resident to the room's occupant list
    selected_room["occupants"].append(resident_id)

    # Calculate the monthly rent
    rent_key = (selected_room["room_type"], selected_room["ac"])
    monthly_rent = RENT_CARD[rent_key]

    # Display allocation details
    print("\n========== BED ALLOCATED ==========")
    print("Resident:", resident["name"])
    print("Resident ID:", resident_id)
    print("Room:", selected_room["room_id"])
    print("Bed:", selected_bed)
    print("Monthly Rent: Rs.", monthly_rent)
    print("===================================")

    return True


# Allocate beds to our three sample residents
allocate_bed("P001")
allocate_bed("P002")
allocate_bed("P003")
