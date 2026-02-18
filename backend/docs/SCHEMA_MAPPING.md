# Schema Mapping: Placeholder Tables and SD_IoT Collections (CSE Senior Design, Budderfly)

This document describes the MongoDB database used by the backend and how it relates to the placeholder API. The backend expects two logical tables (`restaurant_lights` and `light_history`). The database **SD_IoT** contains five collections that implement this contract and support the lighting control system.

## Overview

The MongoDB database is named **SD_IoT** and contains five collections. The API uses an integer `restaurant_id` (1–5) that maps to devices via the `legacyId` field. Light state is read from and written to the **Devices** collection; event history is stored in the **light_history** collection. The remaining collections (**Schedules**, **Time_Data**, **users**) support the system but are not required to satisfy the two-table placeholder shape.

## 1. `Devices` Collection

Stores restaurant/device information with light control fields:

- `_id`: string (e.g., `"ESP32_MCD_DARIEN_001"`)
- `restaurant`: string
- `restaurantId`: string (e.g., `"mcd_1234"`)
- `location`: string
- `address`, `contact`, `device`, `status`: objects
- `scheduleId`: ObjectId (references Schedules collection)
- `createdAt`, `updatedAt`: ISO dates
- `ownerEmail`: string (references users collection)
- `lightState`: `"on"` / `"off"` (added for light control)
- `brightness`: 0–100 integer
- `scheduleOn`: `"HH:MM"` or null
- `scheduleOff`: `"HH:MM"` or null
- `lastUpdated`: ISO timestamp
- `legacyId`: integer (1–5, maps API `restaurant_id` to this device)

## 2. `light_history` Collection

Logs every light action:

- `_id`: ObjectId
- `restaurantId`: string (e.g., `"mcd_1234"`)
- `deviceId`: string (matches `Devices._id`)
- `action`: string (`"toggle_on"`, `"toggle_off"`, `"schedule_set"`)
- `timestamp`: ISO string
- `legacyId`: integer (matches the device’s `legacyId`)

## 3. `Schedules` Collection

Stores detailed schedule rules (unchanged):

- `_id`: ObjectId
- `deviceId`: string
- `restaurant`: string
- `restaurantId`: string
- `name`: string
- `enabled`: boolean
- `rules`: array of day/time objects
- `createdBy`, `createdAt`, `updatedAt`

## 4. `Time_Data` Collection

Time-series sensor readings (unchanged):

- `timestamp`: ISODate
- `metadata`: { `deviceId`, `restaurant`, `restaurantId`, `location` }
- `measurements`: { `V`, `I`, `P`, `uptime` }

## 5. `users` Collection

User accounts (unchanged):

- `_id`: email string
- `email`: string
- `name`: string
- `password`: hashed
- `role`: string
- `restaurants`: array of device `_id`s
- `createdAt`, `updatedAt`

## Key Mapping for the Backend

- The API uses integer `restaurant_id` (1–5) → maps to `Devices.legacyId`
- Light state comes from `Devices.lightState`, `brightness`, `scheduleOn`, `scheduleOff`, and `lastUpdated`
- History comes from the `light_history` collection
- Schedules can be derived from `Devices.scheduleOn` / `scheduleOff` or the `Schedules` collection

## Placeholder Tables (What the API Expects)

The existing API contract is defined in terms of two logical tables:

**restaurant_lights** (one row per restaurant/device): `restaurant_id`, `state`, `brightness`, `schedule_on`, `schedule_off`, `last_updated`. Implemented from the **Devices** collection (and optionally **Schedules** when schedule is not stored on the device).

**light_history** (events): `id`, `restaurant_id`, `action`, `timestamp`. Implemented as the **light_history** collection. The backend writes toggle and schedule events here and reads from it for the history endpoint.

## Code Reference

The five collections are defined in **`app.models.collections`** (and re-exported from `app.models`): `DeviceDocument`, `ScheduleDocument`, `TimeDataDocument`, `UserDocument`, `LightHistoryDocument`. Collection names are in `CollectionNames`. When `MONGODB_URI` is set in the backend `.env`, the application uses `MongoLightRepository` and the SD_IoT database; otherwise it uses SQLite.

---

*Designed and maintained by the CSE team, University of Connecticut. Project sponsored by Budderfly.*
