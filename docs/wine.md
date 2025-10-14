# Wine

## Overview

A **Wine** represents a unique wine type or label — identified by key attributes like grapes, vintage, vinyard.  
Wines are *templates* for real bottles, which reference them when stored in the cellar.

### Wine vs Bottle

It’s important to distinguish between a **Wine** and a **Bottle**:

| Concept | Description |
|----------|--------------|
| **Wine** | Metadata about a particular label or type of wine |
| **Bottle** | A specific instance of a wine in your cellar inventory |

A single Wine record may have many bottles stored across different shelves or racks.

### Example

You might have:

- `Wine`: Château Margaux 2015  
- 12 `Bottle` entries linked to it, each with a defined storage location.

This separation allows you to:

- Keep clean records of your cellar contents  
- Manage bottles individually  
- Track vintages, tasting notes, and inventory history

---

### Related Topics
- [Storage](storage.md): How and where bottles are organized in your cellar

