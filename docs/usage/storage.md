# Storage

## Overview

The **Storage** system represents how bottles are organized physically.

## Shelf Concepts

A **Shelf** (or rack) is a container for bottles. It may be either:

- **Unstructured** — a freeform space with no limits on capacity  
- **Structured** — a grid with fixed rows and columns


### Unstructured / Unlimited Shelf
Unstructured shelves act like bins, crates or a fridge — you can add as many bottles as you like without worrying about coordinates.

#### Characteristics

- No defined **rows** or **columns**  
- Effectively **unlimited capacity**  
- Perfect for bulk or casual storage  

#### Example

##### Fridge

| Wine | Row | Column |
|------|-----------|-------|
| Château Margaux 2015 |  |  |
| Penfolds Grange 2014 | | |

---

### Structured / Grid Shelf (Rows × Columns)

Structured shelves define a clear grid — each bottle sits in a specific slot (row and column).  
This is perfect for users who want to know exactly where each bottle is stored.

#### Characteristics

- Fixed number of **rows** and **columns**  
- Each **slot** holds exactly one bottle  
- Prevents overfilling or duplicates  
- Makes locating a bottle easy

#### Example: “Main Rack”

##### Kitchen Rack (2x3)

| Wine | Row | Column |
|------|-----|--------|
| Château Margaux 2015 | 1 | 1 |
| Château Margaux 2015 | 1 | 2 |
| Dom Pérignon 2012 | 1 | 3 |
| Penfolds Grange 2014 | 2 | 1 |

---

## Managing Bottles

### Adding a Bottle

From a wine's detail page, click **Add to storage** to place a bottle into a storage slot.

- Choose the target storage location
- For structured (grid) storages, pick a row and column from the available slots
- Optionally set a **per-bottle purchase price** that overrides the wine's default price for that individual bottle

### Bottle States

Each bottle in your cellar can be in one of four states:

| State | Description |
|-------|-------------|
| **Sealed** | In storage, not yet opened (default) |
| **Opened** | Has been opened but is still being tracked |
| **Consumed** | Opened and finished — moved to history |
| **Removed** | Taken out of storage without being opened — moved to history |

### Opening a Bottle

Use the **Open** action on a bottle to mark it as opened.

- Add an optional **note** (e.g. occasion, who you shared it with)
- Optionally set a **drink within N days** reminder — this calculates a drink-by date and triggers an automatic email when that date approaches

???+ Info
    See [Notifications](notifications.md) for details on how drink-by reminders work.

### Undo Opening

Made a mistake? Use the **Undo Open** action to revert a bottle back to sealed state. This clears the opening note and removes any drink-by date that was set.

### Consuming a Bottle

Use the **Consume** action to record that a bottle has been drunk. This marks it as both opened and removed from your active inventory in a single step. Consumed bottles appear in the [History](#history).

### Removing from Storage

Use the **Remove** action to take a bottle out of storage without marking it as consumed (e.g. you gave it away or it broke). Removed bottles appear in [History](#history) with a "removed" status.

### Repositioning Bottles

In the storage detail view, bottles in a structured grid can be repositioned by dragging and dropping them:

- Drag to an **empty slot** to move the bottle there
- Drag onto **another bottle** to swap their positions

### History

The **History** page (`/storage/history`) shows a paginated list of all bottles that have been consumed, removed, or are currently opened. For each entry you can see the wine, storage location, opening note, status, and the date of the last change.

