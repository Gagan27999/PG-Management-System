# PS-107 – Co-living PG Occupancy, Bed Allocation and Monthly Billing with Meal Plans Engine — Sample Data Pack
Prepared by 10 SECONDS for Team T015.

## Files
| File | What it holds | Rows |
|---|---|---|
| properties.csv | Properties | 3 |
| rooms.csv | Rooms with type/AC/floor/gender | 30 |
| beds.csv | Beds (60) per room | 60 |
| residents.csv | Residents with preferences and starting meal plan / add-ons | 50 |
| meter_readings.csv | Monthly electricity per room (4 months) | 120 |
| commands.txt | 120+ onboarding/move/absence/meal/payment events + 4 BILL_RUN | 117 |

## Column reference
Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 = 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. Row counts in the Files table exclude the header row (and comment lines in command files).

### properties.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| property_id | string | PG-NN |  | PK |
| property_name | string |  |  |  |
| city | string |  |  |  |
| floors | integer |  |  |  |

### rooms.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| room_id | string | PG-NN-RNNN |  | PK |
| property_id | string |  | properties.property_id |  |
| room_type | string |  | SINGLE/DOUBLE/TRIPLE |  |
| ac | boolean |  | true/false |  |
| floor | integer |  | 1-3 |  |
| gender | string |  | M/F | room gender |
| bed_count | integer |  | 1-3 |  |

### beds.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| bed_id | string | room_id-BN |  | PK |
| room_id | string |  | rooms.room_id |  |
| bed_no | integer |  |  |  |

### residents.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| resident_id | string | RES-NNN |  | PK |
| resident_name | string |  |  |  |
| gender | string |  | M/F |  |
| mobile | string | 10 digits |  |  |
| request_date | date | YYYY-MM-DD |  | waitlist ordering key |
| preferred_property_id | string |  | properties.property_id | allocation is within this property |
| preferred_room_type | string |  | SINGLE/DOUBLE/TRIPLE |  |
| preferred_ac | boolean |  | true/false |  |
| any_room_flag | boolean |  | true/false | ANY: accepts any room type |
| meal_plan | string |  | NONE/BREAKFAST/TWO_MEALS/FULL | plan from move-in |
| addons | list | semicolon-separated | LAUNDRY/PARKING_2W/PARKING_CAR/NONE | from move-in |

### meter_readings.csv
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| room_id | string |  | rooms.room_id |  |
| month | string | YYYY-MM |  |  |
| units | integer | kWh |  |  |
| amount | money | Rs |  | room electricity bill to split |

### commands.txt
| Column | Type | Units/format | Allowed values | Notes |
|---|---|---|---|---|
| line | text | COMMAND/args | see below |  |

## Command file format
`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands MUST be processed in file order (top to bottom). Lines starting with `#` are comments and blank lines are ignored. Argument order per command:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| ONBOARD | ts/resident_id/move_in_date | allocate a bed (or waitlist) and move in |
| CONFIRM_ALLOCATION | ts/resident_id | waitlist head confirms an auto-allocated bed |
| MOVE_OUT_NOTICE | ts/resident_id/move_out_date | notice |
| MOVE_OUT | ts/resident_id/date | vacate |
| ROOM_CHANGE | ts/resident_id/room_type/ac/effective_date | request a room change |
| ABSENCE | ts/resident_id/from_date/to_date/notified | inclusive dates; notified true/false |
| MEAL_PLAN | ts/resident_id/plan | effective next day |
| ADDON | ts/resident_id/addon/action | action ADD/REMOVE, effective this month |
| GUEST_STAY | ts/resident_id/nights | extra guest nights |
| PAYMENT | ts/resident_id/bill_month | full payment of that month's bill on ts |
| BILL_RUN | ts/month | generate bills for month YYYY-MM |

## Planted scenarios
Every edge case from the brief is planted at a known location, followed by extra traps. Line numbers refer to `commands.txt` counting from line 1 including comment lines.
- **Move-in on the 31st of a month** — RES-008 ONBOARD with move_in_date 2026-08-31 (line 54): August pro-rata 1/31; September is a full month.
- **Absence of exactly 5 days with notice** — RES-009 ABSENCE 2026-09-10 → 2026-09-14 with notice (line 56) = exactly 5 consecutive days → meal credit 50% per day; a 4-day absence at line 87 and an un-notified 8-day absence at line 100 earn nothing.
- **Meal plan change on the last day of the month** — RES-010 MEAL_PLAN FULL on 2026-09-30 (line 85) → effective 2026-10-01; September billed entirely at the old plan.
- **Electricity split among 3 occupants with one absent for the whole month** — RES-001/002/003 are the only PG-01 male TRIPLE non-AC requests and fill PG-01-R103 (RES-003 at line 10); RES-003 is on notified absence for all of October (line 82) → October electricity of PG-01-R103 splits between two occupants, residue to the longest-tenured.
- **Room change on the day of move-in** — RES-011 ONBOARD 2026-08-12 (line 33) then ROOM_CHANGE effective the same day (line 35); day-of-change rent at the higher of the two rooms; second change within 6 months at line 90 costs Rs 1,000.
- **Late fee reaching the cap on day 22** — RES-012 pays the September bill on 2026-09-22 (line 81): 15 days late × Rs 100 = 1500.00 = cap exactly.
- **Waitlist head failing to confirm at exactly 48 h** — PG-03 has two female SINGLE AC beds (R101, R303) taken by RES-004/005; RES-006 waitlisted (line 13) ahead of RES-007 (line 17) by request_date; RES-004 vacates 2026-09-20 09:00:00 (line 77) → RES-006 auto-allocated; CONFIRM_ALLOCATION by RES-006 at 2026-09-22 09:00:00 (line 79) is exactly 48 h after the vacancy (boundary: confirm 'within 48 h'); RES-007's confirm at line 80 is valid only if RES-006 dropped to the tail.
- **Move-out notice given 30 days before the 1st of a month** — RES-013 MOVE_OUT_NOTICE on 2026-10-02 for 2026-11-01 (line 89) = 30 days → no shortfall; move-out on the 1st means the November rent billed in advance is fully refundable.
- Trap — RES-014 guest stays 2 + 2 nights in September (second at line 76) exceed the 3-night monthly cap.
- Trap — RES-010 gives 10 days' notice (line 93): 20-day shortfall charged; stay < 3 months → Rs 1,000 cleaning.
- Trap — RES-012 is late twice in 3 months (lines 81, 104) → ROOM_CHANGE at line 110 must be refused (90-day block).
- Trap — duplicate ONBOARD of RES-009 at line 20 (reject); this line is deliberately out of timestamp order with its neighbour — process in file order.
- Bill runs at lines 55, 86, 106, 119.

## What is NOT in this pack
Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation
Produce the following CSV files (header row, same conventions as above, rows in the order stated). Column names are case-sensitive.

### `allocations.csv`
One row per ONBOARD/CONFIRM_ALLOCATION/ROOM_CHANGE line in file order; status ALLOCATED/WAITLISTED/REJECTED/CHANGED; bed_id NONE when waitlisted.

Columns, in order: `line_no`, `resident_id`, `status`, `bed_id`, `message`

### `occupancy.csv`
After each BILL_RUN: every bed with its occupant on the last day of the month (resident_id EMPTY if vacant), ordered by bed_id.

Columns, in order: `month`, `bed_id`, `resident_id`

### `bills.csv`
One row per resident billed in the month, ordered by resident_id.

Columns, in order: `month`, `resident_id`, `rent`, `meal_plan`, `addons`, `electricity`, `late_fee`, `adjustments`, `total`

### `ledger.csv`
Final ledger per resident after the last BILL_RUN, ordered by resident_id.

Columns, in order: `resident_id`, `deposit_held`, `total_billed`, `total_paid`, `balance`

## Notes and assumptions
- Rent is billed on the 1st for the month ahead; the move-in month is pro-rated by remaining days.
- Late fee for a month's bill is computed up to the PAYMENT date (or the next BILL_RUN if unpaid) and added to the next bill.
- Deposit = 2 × the monthly rent of the allocated bed, billed on the first bill.
