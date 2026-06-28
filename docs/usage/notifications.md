# Notifications

Wine Cellar can send you automatic email reminders so you don't miss the right moment to open a bottle.

## Drink-By Reminders

Every wine has an optional **drink-by date** that records when the wine should ideally be consumed. Two automated reminders are sent based on this date:

| Reminder | Trigger |
|----------|---------|
| **14-day warning** | Sent when a wine's drink-by date is exactly 14 days away and the wine is still in stock |
| **Opened-bottle reminder** | Sent when an opened bottle's drink-by date is today |

## Setting a Drink-By Date

A drink-by date can be set in two ways:

- Directly on the **wine record** via the edit form
- When **opening a bottle** — choose "drink within N days" and Wine Cellar calculates the date for that specific bottle

## Prerequisites

Notifications require:

1. **Email configured** — SMTP settings must be set in your environment (see [Deployment](../setup/deployment.md#email-setup))
2. **Notifications enabled** — each user can toggle notifications on or off in their account settings (`/user/settings/`)
