# Wine

## Overview

A **Wine** record acts as the blueprint for a specific label. It captures the core details (vintage, vineyard, etc.) that define what is in the bottle.

### Concept

| Concept | Description |
|----------|--------------|
| **Wine** | Blueprint of a particular wine |
| **Bottle** | An individual unit of wine, tracked by its specific location in your cellar. |

A single Wine record may have many bottles stored across different shelves or racks.

### Example

You might have:

- **Wine**: Alde Gott Sasbacher Limburg Riesling 2021
- 12 **Bottles** entries linked to it, each with a defined storage location.

This separation allows you to:

- Keep clean records of your cellar contents  
- Manage bottles individually  
- Track vintages, tasting notes, and inventory history

---

## Adding Wines

Wines can be added in two ways from the **Add Wine** page:

- **Manual entry** — a guided 5-step wizard covering basic info, details, region, sourcing, and notes/images. You can move forward and back between steps without losing data.
- **AI label scan** — upload a photo of the front and/or back label; an LLM extracts the name, vintage, country, grapes, region, and other fields and pre-fills the form for review before saving. Requires `AI_MODEL` and `AI_API_KEY` to be configured (see [Deployment](../setup/deployment.md#ai-setup)).

**Barcode scanning** is available from the navbar. Scanning a barcode takes you directly to the wine's detail page if it already exists in your cellar, or pre-fills the barcode in the creation form if it doesn't.

## Browsing and Filtering

The wine list supports filtering by type, country, vintage range, rating, and more. Results can be sorted by name, vintage, drink-by date, or price.

Wines with a geographic location set can also be viewed on an interactive **map** (`/wines/map`).

## Ratings and Tasting Notes

Each wine record can store:

- A numeric **rating** from 0 to 10
- A free-text **comment** for tasting notes or any other remarks

## Related Topics

- [Storage](storage.md): Organizing bottles within your cellar.
- [Notifications](notifications.md): Drink-by reminders.
