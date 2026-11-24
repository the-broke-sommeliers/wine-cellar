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
- **AI scan** — upload a photo of the front and/or back label, or switch to **Menu / wine list** and upload a photo of a menu (optionally with a hint such as "2019 Barolo" to pick one entry). The LLM extracts the name, vintage, country, grapes, region, and other fields and pre-fills the form for review before saving. Requires `AI_MODEL` and `AI_API_KEY` to be configured (see [Deployment](../setup/deployment.md#ai-setup)).

**Barcode scanning** is available from the navbar. Scanning a barcode takes you directly to the wine's detail page if it already exists in your cellar, or pre-fills the barcode in the creation form if it doesn't.

## Browsing and Filtering

The wine list supports filtering by type, country, vintage range, rating, and more. Results can be sorted by name, vintage, drink-by date, or price.

On wide screens the list fits as many wines next to each other as there is room for. To cap that, set **Wines per Row** under **Settings** (1–5, or Automatic). Enable **Compact Wine List** to keep the cards at a compact size and center the list instead of using the full width.

Wines with a geographic location set can also be viewed on an interactive **map** (`/wines/map`).

## Ratings and Tasting Notes

Each vintage can store:

- A numeric **rating** from 0 to 10
- Your own **tasting notes**: how the wine looks, smells and tastes
- A free-text **comment** for any other remarks

The vintage section on the wine's detail page also has an **AI Tasting Notes** box, kept separate from your own notes. Use **Edit** to write or paste notes from an AI tool of your choice. If AI is configured (see [Deployment](../setup/deployment.md#ai-setup)), **Generate** lets the AI describe how the wine probably tastes, based on its details (grapes, region, vintage and so on); without AI configuration the button is disabled. Once notes exist, **Remove** deletes them so you can generate new ones.

The **My Tasting Notes** section lets you add multiple personal reviews to a wine. Each review contains a note, an optional score from 0 to 5, and an optional link to a vintage of that wine. Reviews show their creation date and can be deleted, but not edited. Deleting a vintage keeps its reviews and removes the vintage link.

## Food Pairings

Food pairings belong to the wine, not a single vintage, so they are shared by all its vintages and power the wine list's food pairing filter. The **Food Pairings** box on the wine's detail page works like the AI Tasting Notes box: with AI configured, **Generate** suggests a few dishes based on the wine's details, reusing names you already have where they fit, and adds them to the wine. **Edit** opens the wine's edit form at the food pairings field, and **Remove** clears the wine's pairings (the pairing names themselves stay available for other wines).

## Related Topics

- [Storage](storage.md): Organizing bottles within your cellar.
- [Notifications](notifications.md): Drink-by reminders.
