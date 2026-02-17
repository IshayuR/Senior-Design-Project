# Schema mapping: your 4 collections → placeholder (restaurant_lights + light_history)

The existing backend expects a **placeholder** shape: two logical tables (`restaurant_lights` and `light_history`) with integer `restaurant_id`. Your data lives in four MongoDB collections. This doc describes how they map so the app can use your schema without changing the API.

**Your collections in code:** The four MongoDB collections and the placeholder-compat `light_history` are defined one-to-one in **`app.models.collections`** (and re-exported from `app.models`): `DeviceDocument`, `ScheduleDocument`, `TimeDataDocument`, `UserDocument`, `LightHistoryDocument`. Field names and metadata there match the document examples for each collection. Collection names are in `CollectionNames`.

---

## Placeholder shape (what the API expects)

### restaurant_lights (one row per “restaurant” / light)

| Placeholder field | Type   | Description |
|------------------|--------|-------------|
| `restaurant_id`  | int    | Identifies which restaurant/device. |
| `state`          | "on" / "off" | Light on or off. |
| `brightness`     | 0–100  | Light brightness. |
| `schedule_on`    | "HH:MM" or null | Scheduled on time (24h). |
| `schedule_off`   | "HH:MM" or null | Scheduled off time (24h). |
| `last_updated`   | ISO datetime | Last change. |

### light_history (events)

| Placeholder field | Type   | Description |
|------------------|--------|-------------|
| `id`             | int    | Unique event id. |
| `restaurant_id`  | int    | Which restaurant. |
| `action`         | string | e.g. "toggle_on", "schedule_set_20:00_02:00". |
| `timestamp`      | ISO datetime | When it happened. |

---

## How your 4 collections map into that

### 1. `restaurant_id` (int) ↔ which device

- The API uses **integer** `restaurant_id` (e.g. `1`, `2`).
- Your data uses **string** IDs: `Devices._id`, `Devices.restaurantId`.

**Mapping options:**

- **Option A (recommended):** Add an optional field on each device document:
  - `legacyRestaurantId: 1` (or 2, 3, …) so one integer maps to one device.
- **Option B:** If that field is missing, the code falls back to **position**: first device (by `_id`) = 1, second = 2, etc. Order can change if you add/remove devices.

So: **Devices** is the source for “one row per restaurant/light”; `restaurant_id` in the API is either `legacyRestaurantId` or that position.

### 2. `restaurant_lights` fields from your collections

| Placeholder field | Source in your schema | Notes |
|-------------------|------------------------|--------|
| `restaurant_id`   | See above (Devices + optional `legacyRestaurantId`). | Int used in API. |
| `state`           | **Devices** – optional `lightState`: `"on"` \| `"off"`. | Not in your original Devices; we add it for placeholder compatibility. Default `"off"` if missing. |
| `brightness`      | **Devices** – optional `brightness`: 0–100. | Same; add for compatibility. Default `0` if missing. |
| `schedule_on`     | **Devices** – optional `scheduleOn`: `"HH:MM"` **or** **Schedules** – first rule’s `startHour` → `"HH:00"`. | Prefer Device field; else derive from linked Schedule. |
| `schedule_off`    | **Devices** – optional `scheduleOff`: `"HH:MM"` **or** **Schedules** – first rule’s `endHour` → `"HH:00"`. | Same. |
| `last_updated`    | **Devices** – `updatedAt` or `status.lastSeen`. | Use existing datetime; keep in ISO form for API. |

So: **Devices** is the main source. Adding optional `lightState`, `brightness`, `scheduleOn`, `scheduleOff` keeps the placeholder contract; if you prefer not to change Devices, the code can default state/brightness and derive schedule from **Schedules** when possible.

### 3. **Schedules** (for schedule_on / schedule_off when not on Device)

- Link: **Devices** has `scheduleId` → **Schedules._id** (or match by `deviceId`).
- One schedule can have many **rules** (days, startHour, endHour, action).
- **Conversion:** Use the **first rule** (or first “ON” rule):  
  `startHour` → `schedule_on = f"{startHour:02d}:00"`,  
  `endHour` → `schedule_off = f"{endHour:02d}:00"`.  
- If you **set** schedule via the API (e.g. “20:00” / “02:00”), the implementation can either update that rule in **Schedules** or store only on **Devices** in `scheduleOn` / `scheduleOff` (simpler).

### 4. **Time_Data**

- Telemetry (V, I, P, uptime, etc.), not toggle events.
- **Not used** for the placeholder’s `light_history` (which is for actions like “toggle_on”, “schedule_set_…”). So no direct mapping from Time_Data to `light_history`.

### 5. **light_history** (placeholder events)

- Your schema doesn’t have an equivalent “event log” for light toggles/schedule changes.
- **Conversion:** Add a **fifth collection**, e.g. **light_history**, with documents like:
  - `restaurant_id` (int, same mapping as above),
  - `action` (string),
  - `timestamp` (datetime or ISO string).
- The backend will **write** here on toggle/schedule and **read** here for history. So the placeholder “table” is implemented as this collection.

### 6. **users**

- No direct mapping to `restaurant_lights` or `light_history`. Use for auth / “who changed what” later if you want.

---

## Summary

| Placeholder concept      | Implemented from your schema |
|-------------------------|------------------------------|
| One “light” per restaurant | One **Device** per restaurant; `restaurant_id` = `legacyRestaurantId` or 1-based index. |
| state, brightness       | Optional fields on **Devices** (or defaults). |
| schedule_on / schedule_off | Optional on **Devices** and/or from **Schedules** first rule. |
| last_updated            | **Devices** `lastUpdated` (last light-state change) or `updatedAt` / `status.lastSeen`. |
| light_history           | **light_history** collection: `restaurantId`, `deviceId`, `action`, `timestamp`, `legacyId`. |

So: **convert** by (1) using **Devices** (and optionally **Schedules**) to fill the logical `restaurant_lights` row, (2) adding optional fields on Devices and one **light_history** collection so the existing API keeps working without changing your four main collections’ structure for anything else.

---

## What to add in MongoDB so the backend can use your schema

1. **On each Device document (per Database Schema Report):**
   - `legacyId` or `legacyRestaurantId`: integer (e.g. `1`, `2`) so the API's `restaurantId` maps to this device. The repo checks `legacyId` first, then `legacyRestaurantId`, then 1-based index by `_id`.
   - `lightState`: `"on"` or `"off"` (default `"off"`).
   - `brightness`: 0–100 (default `0`).
   - `scheduleOn`, `scheduleOff`: `"HH:MM"` 24h or null.
   - `lastUpdated`: ISO string of the last light-state change (set by the backend on update).

2. **Collection `light_history`**
   - Documents: `restaurantId` (string, e.g. `"mcd_1234"`), `deviceId` (string, optional), `action` (e.g. `"toggle_on"`, `"toggle_off"`, `"schedule_set_20:00_02:00"`), `timestamp` (ISO string), `legacyId` (int, for API filter/response).
   - The backend inserts these on toggle/schedule and reads for the history endpoint.

3. **Backend config**
   - In backend `.env`: `MONGODB_URI=mongodb+srv://...` (and optionally `MONGODB_DB_NAME=SD_IoT`).
   - With `MONGODB_URI` set, the app uses `MongoLightRepository` and your four collections (plus `light_history`); without it, it keeps using SQLite.
