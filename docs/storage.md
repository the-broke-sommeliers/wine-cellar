# Storage

## Overview

The **Storage** system represents how bottles are organized physically — on racks, shelves, or in bins.  
There are two main types of storage in the Wine Cellar app:

1. Unstructured (Unlimited Shelf) 
2. Structured (Grid Shelf with Rows & Columns)

---

## Shelf Concepts

A **Shelf** (or rack) is a container for bottles. It may be either:

- **Unstructured** — a freeform space with no limits on capacity  
- **Structured** — a grid with fixed rows and columns

### Core Entities

| Entity | Description |
|---------|--------------|
| **Shelf / Rack** | Container for bottles |
| **Mode** | `unstructured` or `grid` |
| **Rows / Columns** | Grid dimensions (if structured) |
| **Slot / Cell** | Individual position in a grid shelf |
| **Bottle** | A stored instance of a wine in a given location |

---

## 1. Unstructured / Unlimited Shelf
Unstructured shelves act like bins, crates or a fridge — you can add as many bottles as you like without worrying about coordinates.

### Characteristics

- No defined **rows** or **columns**  
- Effectively **unlimited capacity**  
- Perfect for bulk or casual storage  

### Example: “Bulk Shelf”

**Shelf A** (mode: `unstructured`)

| Wine | Row | Column |
|------|-----------|-------|
| Château Margaux 2015 |  |  |
| Penfolds Grange 2014 | | |

---

## 2. Structured / Grid Shelf (Rows × Columns)

Structured shelves define a clear grid — each bottle sits in a specific slot (row and column).  
This is perfect for users who want to know exactly where each bottle is stored.

### Characteristics

- Fixed number of **rows** and **columns**  
- Each **slot** holds exactly one bottle  
- Prevents overfilling or duplicates  
- Makes locating a bottle easy

### Example: “Main Rack”

**Kitchen Rack** (mode: `structured`, 4 rows × 5 columns)

| Wine | Row | Column |
|------|-----|--------|
| Château Margaux 2015 | 1 | 1 |
| Château Margaux 2015 | 1 | 2 |
| Dom Pérignon 2012 | 1 | 3 |
| Penfolds Grange 2014 | 2 | 1 |

