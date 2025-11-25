# TDB Database Schema Documentation

## Overview

The TDB (medication dispenser) database uses MySQL 8.0.42 hosted on AWS RDS in ap-southeast-2 region.

**Database Host**: `tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com`

This document describes the complete database schema, relationships, and data flow for the medication dispensing system.

---

## Entity Relationship Diagram (Text Description)

```
┌─────────────┐
│   users     │
└─────┬───────┘
      │ 1
      │ (parent_user_id)
      ↓ *
┌─────────────┐         ┌─────────────────────────┐
│ user_group  │ 1     * │ user_group_membership   │
└─────┬───────┘←────────┤ (many-to-many bridge)   │
      │ 1               └───────────┬─────────────┘
      │                             │ *
      │                             ↓ 1
      │                       ┌─────────────┐
      │                       │   users     │
      │                       └─────────────┘
      │ 1
      ├────→ * ┌─────────────┐
      │        │  machine    │
      │        └─────┬───────┘
      │              │ 1
      │              ↓ *
      │        ┌─────────────────┐
      │        │  machine_slot   │──→ medi_id
      │        └─────────────────┘
      │
      ↓ *
┌─────────────┐
│  medicine   │
└─────┬───────┘
      │
      ↓ (reference from schedule)
┌─────────────┐
│  schedule   │
└─────┬───────┘
      │
      ↓ (creates records in)
┌──────────────┐
│ dose_history │
└──────────────┘
```

---

## Table Schemas

### 1. `users` - User Accounts

Stores user authentication and RFID card mapping.

```sql
CREATE TABLE `users` (
  `user_id` varchar(50) NOT NULL,           -- Primary key, unique username
  `password` varchar(255) NOT NULL,         -- Bcrypt hashed password ($2b$10$...)
  `name` varchar(100) NOT NULL,             -- User's real name (Korean supported)
  `age` int DEFAULT NULL,                   -- User age
  `birthDate` date DEFAULT NULL,            -- Birth date
  `k_uid` varchar(45) DEFAULT NULL,         -- RFID card UID (e.g., "6CEFECBF")
  `took_today` int NOT NULL DEFAULT '0',    -- Boolean flag (0/1) for dose taken today
  `refresh_token` varchar(255) DEFAULT NULL,-- JWT refresh token
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Key Fields**:
- `k_uid`: RFID card unique identifier, used by dispenser to identify user
- `took_today`: Reset daily, set to 1 when user completes dose
- `refresh_token`: JWT token for mobile app authentication

**Sample Data**:
```
user_id    | name     | k_uid    | took_today
-----------|----------|----------|------------
test12     | 김경동   | 6CEFECBF | 1
subtest1   | 강현성   | NULL     | 0
```

---

### 2. `user_group` - Family Groups

Represents family units that share a dispenser.

```sql
CREATE TABLE `user_group` (
  `group_id` varchar(50) NOT NULL,          -- UUID primary key
  `group_name` varchar(100) DEFAULT NULL,   -- Display name for group
  `parent_user_id` varchar(50) DEFAULT NULL,-- Creator/owner of group
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `note` text,                              -- Usually "Auto-created family group"
  PRIMARY KEY (`group_id`),
  FOREIGN KEY (`parent_user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Sample Data**:
```
group_id                              | group_name   | parent_user_id
--------------------------------------|--------------|----------------
d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2 | 경동대학교   | test12
```

---

### 3. `user_group_membership` - Group Membership

Many-to-many relationship between users and groups with role assignment.

```sql
CREATE TABLE `user_group_membership` (
  `group_id` varchar(50) NOT NULL,
  `user_id` varchar(50) NOT NULL,
  `role` enum('parent','child') NOT NULL,   -- Parent = manager, Child = dependent
  `joined_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`group_id`,`user_id`),
  FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Roles**:
- **parent**: Can manage group, add/remove members, configure schedules
- **child**: Regular member who receives medications

**Sample Data**:
```
group_id                              | user_id  | role
--------------------------------------|----------|--------
d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2 | test12   | parent
d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2 | subtest1 | child
```

---

### 4. `machine` - Physical Dispensers

Represents physical Arduino-based dispenser devices.

```sql
CREATE TABLE `machine` (
  `machine_id` varchar(50) NOT NULL,        -- Unique hardware ID (e.g., MAC-based)
  `group_id` varchar(50) NOT NULL,          -- Which family owns this machine
  `note` text,
  PRIMARY KEY (`machine_id`),
  FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Sample Data**:
```
machine_id | group_id                              | note
-----------|---------------------------------------|------
F7F8F9AA   | d9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2 | NULL
```

---

### 5. `machine_slot` - Slot Assignments

Maps physical dispenser slots (1-3) to medications with inventory tracking.

```sql
CREATE TABLE `machine_slot` (
  `machine_id` varchar(50) NOT NULL,
  `slot_number` int NOT NULL,               -- Physical slot: 1, 2, or 3
  `medi_id` varchar(50) DEFAULT NULL,       -- Which medicine is loaded
  `total` int DEFAULT '0',                  -- Initial quantity loaded
  `remain` int DEFAULT '0',                 -- Current remaining quantity
  PRIMARY KEY (`machine_id`,`slot_number`),
  FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Important Notes**:
- Each machine has exactly 3 slots
- `remain` decrements on each successful dispense
- When `remain` reaches 0, slot needs refilling

**Sample Data**:
```
machine_id | slot_number | medi_id                  | total | remain
-----------|-------------|--------------------------|-------|--------
F7F8F9AA   | 1           | medicine_1762787136492   | 60    | 57
F7F8F9AA   | 2           | medicine_1762787587816   | 40    | 40
F7F8F9AA   | 3           | supplement_1762787919297 | 100   | 98
```

---

### 6. `medicine` - Medicine Catalog

Stores medication and supplement information.

```sql
CREATE TABLE `medicine` (
  `medi_id` varchar(50) NOT NULL,           -- Unique medicine ID
  `group_id` varchar(50) NOT NULL,          -- Which group can see this medicine
  `name` varchar(100) NOT NULL,             -- Medicine name (Korean supported)
  `warning` tinyint NOT NULL DEFAULT '0',   -- Warning level (0=safe, 1=caution, etc.)
  `start_date` date DEFAULT NULL,           -- Prescription start date
  `end_date` date DEFAULT NULL,             -- Prescription end date (NULL=ongoing)
  `target_users` json DEFAULT NULL,         -- JSON array of user_ids (e.g., ["test12"])
  `listed_only` tinyint(1) NOT NULL DEFAULT '1', -- 0=prescription, 1=supplement
  PRIMARY KEY (`medi_id`,`group_id`),
  UNIQUE KEY (`group_id`,`name`),
  FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Field Details**:
- `listed_only`:
  - `0` = Prescription medicine (requires medical oversight)
  - `1` = Over-the-counter supplement
- `target_users`: JSON array, empty `[]` means available to all group members
- `end_date`: NULL means no expiration (common for supplements)

**Sample Data**:
```
medi_id                    | name                        | warning | start_date | end_date   | target_users | listed_only
---------------------------|----------------------------|---------|------------|------------|--------------|-------------
medicine_1762787136492     | 아네모정                   | 0       | 2025-11-10 | 2025-12-10 | ["test12"]   | 0
medicine_1762787587816     | 엠코발캡슐(메코발라민)      | 0       | 2025-11-10 | 2025-12-10 | []           | 0
supplement_1762787919297   | 오메가3 골드               | 0       | 2025-11-10 | NULL       | NULL         | 1
```

---

### 7. `schedule` - Dosing Schedules

Defines when and how much medicine each user should take.

```sql
CREATE TABLE `schedule` (
  `schedule_id` varchar(50) NOT NULL,
  `user_id` varchar(50) NOT NULL,
  `group_id` varchar(50) NOT NULL,
  `medi_id` varchar(50) NOT NULL,
  `day_of_week` enum('mon','tue','wed','thu','fri','sat','sun') NOT NULL,
  `time_of_day` enum('morning','afternoon','evening') NOT NULL,
  `dose` int NOT NULL,                      -- Number of pills/doses
  PRIMARY KEY (`schedule_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Time Mapping**:
- `morning` → Carousel position 1
- `afternoon` → Carousel position 2
- `evening` → Carousel position 3

**Schedule Logic**:
- Multiple medicines can be scheduled for same user/day/time
- Pi client queries schedules daily based on current day_of_week
- Schedules determine which slot (time_of_day) to rotate to

**Sample Data** (user test12 has 50+ schedule entries):
```
schedule_id              | user_id | medi_id                  | day_of_week | time_of_day | dose
-------------------------|---------|--------------------------|-------------|-------------|------
schedule_1762787143374   | test12  | medicine_1762787136492   | mon         | morning     | 1
schedule_1762787143381   | test12  | medicine_1762787136492   | mon         | afternoon   | 1
schedule_1762787600199   | test12  | medicine_1762787587816   | tue         | morning     | 2
```

---

### 8. `dose_history` - Dispensing Records

Audit trail of all medication dispensing events.

```sql
CREATE TABLE `dose_history` (
  `history_id` varchar(50) NOT NULL,
  `user_id` varchar(50) NOT NULL,
  `group_id` varchar(50) NOT NULL,
  `medi_id` varchar(50) NOT NULL,
  `scheduled_dose` int NOT NULL,            -- Expected dose from schedule
  `actual_dose` int NOT NULL,               -- Actually dispensed amount
  `status` enum('completed','missed','partial') NOT NULL,
  `time_of_day` enum('morning','afternoon','evening') NOT NULL,
  `dispensed_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`history_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  FOREIGN KEY (`group_id`) REFERENCES `user_group` (`group_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Status Values**:
- `completed`: actual_dose == scheduled_dose
- `partial`: actual_dose < scheduled_dose (inventory shortage)
- `missed`: actual_dose == 0 (user didn't take medicine)

**Sample Data**:
```
history_id            | user_id | medi_id                  | scheduled_dose | actual_dose | status    | time_of_day | dispensed_at
----------------------|---------|--------------------------|----------------|-------------|-----------|-------------|-------------------
history_1762787331... | test12  | medicine_1762787136492   | 1              | 1           | completed | morning     | 2025-11-10 10:35:31
history_1762787331... | test12  | medicine_1762787587816   | 2              | 2           | completed | morning     | 2025-11-10 10:35:31
```

---

## Data Flow: RFID Scan to Dispensing

### 1. User Scans RFID Card
```
Arduino RFID Reader → Serial: RFID,6CEFECBF
                              ↓
                     Pi Client receives card UID
```

### 2. User Lookup
```python
# Pi client calls: GET /dispenser/resolve-uid?cardUid=6CEFECBF&machineId=F7F8F9AA

Server Query:
SELECT u.user_id, u.name, ugm.group_id, ugm.role
FROM users u
JOIN user_group_membership ugm ON u.user_id = ugm.user_id
WHERE u.k_uid = '6CEFECBF'

Result: { user_id: 'test12', name: '김경동', group_id: 'd9f5dc5b-...', role: 'parent' }
```

### 3. Schedule Query
```python
# Pi client calls: GET /dispenser/build-queue?userId=test12&groupId=d9f5dc5b-...&machineId=F7F8F9AA

Server Logic:
1. Get current day_of_week (e.g., 'mon')
2. Determine next time_of_day based on current time
   - Before 10 AM → 'morning'
   - 10 AM - 5 PM → 'afternoon'
   - After 5 PM → 'evening'

3. Query schedules:
SELECT s.medi_id, s.dose, s.time_of_day, ms.slot_number, ms.remain
FROM schedule s
JOIN medicine m ON s.medi_id = m.medi_id
JOIN machine_slot ms ON m.medi_id = ms.medi_id AND ms.machine_id = 'F7F8F9AA'
WHERE s.user_id = 'test12'
  AND s.group_id = 'd9f5dc5b-...'
  AND s.day_of_week = 'mon'
  AND s.time_of_day = 'morning'
  AND ms.remain > 0

Result: [
  { slot: 1, medi_id: 'medicine_1762787136492', dose: 1, time_of_day: 'morning' },
  { slot: 2, medi_id: 'medicine_1762787587816', dose: 2, time_of_day: 'morning' }
]
```

### 4. Carousel Positioning
```
time_of_day = 'morning' → Servo rotates carousel to position 1
time_of_day = 'afternoon' → Position 2
time_of_day = 'evening' → Position 3
```

### 5. Dispensing
```
For each item in queue:
  - Arduino receives: DISPENSE,<slot>,<dose>
  - Solenoid activates <dose> times
  - Pills fall into carousel cup
```

### 6. Update Database
```python
# Pi client calls: POST /dispenser/report-dispense

Server Updates:
1. Decrement machine_slot.remain for each dispensed medicine
UPDATE machine_slot
SET remain = remain - <actual_dose>
WHERE machine_id = 'F7F8F9AA' AND slot_number = <slot>

2. Insert dose_history records
INSERT INTO dose_history (history_id, user_id, group_id, medi_id, scheduled_dose, actual_dose, status, time_of_day)
VALUES (...)

3. Update users.took_today flag
UPDATE users SET took_today = 1 WHERE user_id = 'test12'
```

---

## Common Queries

### Get User's Today Schedule
```sql
SELECT
  s.medi_id,
  m.name AS medicine_name,
  s.time_of_day,
  s.dose,
  ms.slot_number,
  ms.remain AS available_quantity
FROM schedule s
JOIN medicine m ON s.medi_id = m.medi_id AND s.group_id = m.group_id
JOIN machine_slot ms ON m.medi_id = ms.medi_id
JOIN machine mc ON ms.machine_id = mc.machine_id
WHERE s.user_id = 'test12'
  AND s.group_id = 'd9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2'
  AND s.day_of_week = 'mon'
  AND mc.machine_id = 'F7F8F9AA'
  AND ms.remain > 0
ORDER BY s.time_of_day, ms.slot_number;
```

### Check Inventory Levels
```sql
SELECT
  ms.machine_id,
  ms.slot_number,
  m.name AS medicine_name,
  ms.total,
  ms.remain,
  ROUND((ms.remain / ms.total) * 100, 1) AS fill_percentage
FROM machine_slot ms
JOIN medicine m ON ms.medi_id = m.medi_id
WHERE ms.machine_id = 'F7F8F9AA'
ORDER BY ms.slot_number;
```

### Get User's Dose History (Last 7 Days)
```sql
SELECT
  dh.dispensed_at,
  m.name AS medicine_name,
  dh.scheduled_dose,
  dh.actual_dose,
  dh.status,
  dh.time_of_day
FROM dose_history dh
JOIN medicine m ON dh.medi_id = m.medi_id
WHERE dh.user_id = 'test12'
  AND dh.dispensed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY dh.dispensed_at DESC;
```

### Find Users Who Missed Doses Today
```sql
SELECT
  u.user_id,
  u.name,
  u.took_today,
  COUNT(s.schedule_id) AS scheduled_doses
FROM users u
JOIN user_group_membership ugm ON u.user_id = ugm.user_id
JOIN schedule s ON u.user_id = s.user_id
WHERE ugm.group_id = 'd9f5dc5b-68ef-4c7e-8a23-1a0c2ed553b2'
  AND s.day_of_week = LOWER(DATE_FORMAT(NOW(), '%a'))
  AND u.took_today = 0
GROUP BY u.user_id, u.name, u.took_today;
```

---

## Key Design Patterns

### 1. Multi-Tenancy via Groups
- All data scoped to `group_id`
- Users can belong to multiple groups (via `user_group_membership`)
- Dispensers assigned to single group
- Medicines catalog per group

### 2. Inventory Management
- `machine_slot` tracks real-time inventory
- `total` field records initial load
- `remain` decrements on dispense
- Server rejects dispense if `remain < dose`

### 3. Schedule Flexibility
- Weekly recurring schedules (not calendar dates)
- 3 daily time slots (morning/afternoon/evening)
- Supports multiple medicines per slot
- Can target specific users via `schedule.user_id`

### 4. Audit Trail
- All dispenses recorded in `dose_history`
- Tracks partial doses (inventory shortage)
- Tracks missed doses (user didn't collect)
- Timestamps for compliance reporting

### 5. RFID Mapping
- One-to-one: `users.k_uid` ↔ Physical RFID card
- Case-insensitive hex string (e.g., "6CEFECBF")
- Nullable (users can exist without cards)
- Used for instant user identification at dispenser

---

## Database Connection Details

**Production Database**:
```
Host: tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com
Database: tdb
Engine: MySQL 8.0.42
Region: ap-southeast-2 (Sydney)
Character Set: utf8mb4
Collation: utf8mb4_0900_ai_ci
```

**Connection String Example**:
```
mysql://user:password@tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com:3306/tdb
```

---

## Related Documentation

- **CLAUDE.md**: Complete project overview, setup, architecture
- **scripts/**: Python client that interfaces with this database via REST API
- **firmware/**: Arduino code that triggers dispensing events
- **TDB_Server**: NestJS backend that manages this database
