# Design: shared cellars (multi-user households)

*Design doc — not yet implemented. Written 2026-09-25.*

## TL;DR — findings

- **New first-class `Cellar` model** owns all wine/stock data; `user` stops being the scoping key. Every user still gets exactly one personal `Cellar` auto-created at signup, so existing single-user behavior is the unchanged default.
- **No personal-vs-shared distinction as a field** — a cellar is "shared" purely because it has ≥2 members. Users can belong to multiple cellars (personal + any shared ones) and must always belong to ≥1.
- **Sharing is real, symmetric, indefinite ownership** — not "temporary visibility while invited." Once a `CellarMembership` exists, both members have full read/write on that cellar's data until membership is revoked.
- **No automatic merging of existing wines.** A user's pre-existing personal wines stay in their personal cellar when they join a shared one. Moving data over is an explicit, opt-in, whole-`Wine`-at-a-time action, not a bulk/background merge.
- **Duplicates are handled by reusing existing dedup logic** (`_find_matching_wine`, barcode match), rescoped from per-user to per-cellar — the same "is this wine already known?" check that already runs for AI label-scan and barcode-scan today.
- **No separate "merge mode" setting.** The setting-free default (separate cellars + explicit move/copy) *is* the control; the only real per-request state is which cellar is currently "active" (a lightweight cellar switcher, session-based).
- **Departing/removed members don't take their data with them** — content belongs to the cellar, not the person. `user` is repurposed to `created_by` (nullable, SET_NULL) for historical attribution only.
- **Two roles are enough**: owner (manage membership, delete/rename cellar) and member (full CRUD on contents). No Django Group/Permission framework — matches the app's existing ad-hoc row-level-check style.
- **Biggest implementation cost isn't the sharing logic itself — it's the mechanical rescoping** of ~14 models' unique constraints and ~30 duplicated `.filter(user=request.user)` call sites from `user` to `cellar`. This is real but low-risk, since it can land as its own centralizing/de-duplicating PR before the sharing feature.

---

## 1. Current state (why this needs a real data-model change)

- Stock Django `User` model, `django-allauth` for login, no custom user model, `ENABLE_SIGNUPS=False` by default (closed signup).
- No Group/permission framework anywhere — every view does manual `.filter(user=request.user)` / `get_object_or_404(..., user=request.user)`.
- Abstract `UserContentModel` (`wine_cellar/apps/wine/models.py:19-25`: `user` FK CASCADE nullable, `created`, `modified`) is subclassed by essentially everything: lookup vocab (`Size`, `Grape`, `Region`, `Appellation`, `Vineyard`, `FoodPairing`, `Attribute`, `Source` — each `UniqueConstraint(["name", ..., "user"])`), `Wine` (`UniqueConstraint(["name","wine_type","size","country","user"])`, and redundantly redeclares its own `user` FK at `models.py:185`), `Vintage` (`FK(Wine, related_name="vintages")`, `UniqueConstraint(["wine","year","user"])`, holds `barcode`), and in `storage/models.py`: `Storage` (the shelf/rack grid), `StorageItem` (`FK(storage)`, `FK(vintage)`, `row`/`column`, constraint scoped to `storage` not `user` — already fine), `StorageItemEvent` (audit log), `StorageLabel`. `WineImage` has its own separate `user` FK (`SET_NULL`).
- No `Cellar` model exists at all — "cellar" today is purely informal: "everything `request.user` owns."
- Existing precedent worth reusing: `Q(user=None) | Q(user=user)` already appears **twice**, independently copy-pasted, as a "global, shared-by-everyone" fallback for lookup vocab — `wine/forms.py:183-201` (`_limit_user_querysets`) and `wine/filters.py:125-141` (`WineFilter.__init__`, plus a plain `Storage.objects.filter(user=request.user)` at `:139-141`).
- Existing dedup logic to reuse, not reinvent: `_find_matching_wine()` (`wine/views.py:907-938`) derives its match fields *dynamically from the `Wine.Meta` unique constraint itself* (`_unique_wine_constraint_fields`, `:907-916`), so rescoping the constraint from `user`→`cellar` requires **no field-list changes** to this helper — only its `user=user` filter argument becomes `cellar=cellar`. Barcode match (`WineScannedView`, `views.py:588-589,607-609`) is a second, independent dedup path (`Vintage.objects.filter(barcode=barcode, wine__user=...)`) that needs the same swap. Note: `Vintage.barcode` has **no DB uniqueness constraint** today — barcode collisions are a UX nicety to warn about, not an integrity concern.
- `tasks.py` reminders (`drink_by_reminder` / `opened_bottle_reminder`, `:65-102`) both iterate `User.objects...exclude(user_settings__notifications=False)` and email one recipient per row — a hardcoded 1-owner-1-recipient assumption that needs to become "iterate cellars, fan out to members with notifications enabled."
- `storage/signals.py:8-16` auto-creates one default `Storage` on user signup — the template for auto-creating one personal `Cellar` per user, extended to a 3-step chain (`Cellar` → `CellarMembership(owner)` → default `Storage`).

## 2. Proposed data model

New app `wine_cellar/apps/cellar/`, following the repo's per-app convention (`models.py`/`views.py`/`admin.py`/`forms.py`):

```python
class Cellar(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class CellarMembership(models.Model):
    cellar = models.ForeignKey(Cellar, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="cellar_memberships")
    role = models.CharField(choices=[("owner", "Owner"), ("member", "Member")])
    joined = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("cellar", "user")

class CellarInvitation(models.Model):
    cellar = models.ForeignKey(Cellar, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    token = models.CharField(max_length=64, unique=True)  # secrets.token_urlsafe, not a sequential/guessable id
    status = models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"),
                                        ("expired", "Expired"), ("revoked", "Revoked")])
    created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, related_name="+")
```

**`UserContentModel` change** (`wine/models.py:19-25`): add `cellar = FK(Cellar, CASCADE)` as the new scoping/ownership key; rename the existing `user` field to `created_by` (nullable, `SET_NULL`) — kept purely for audit/history, no longer drives scoping or uniqueness. Renaming (vs. keeping the name `user` with new meaning) costs touching every `.user` reference, but the app is already touching every one of those call sites to add `cellar` — better to not leave a permanently misleading field name.

- All 8 lookup-vocab models' `UniqueConstraint`s: `user` → `cellar`.
- `Wine.Meta` constraint (`:398-404`): `user` → `cellar`; also delete the redundant `Wine.user` redeclaration at `models.py:185` (dead weight once the abstract field covers it).
- `Vintage.Meta` constraint (`:529-535`): `user` → `cellar`.
- `WineImage`: gets its **own** `cellar` FK (not just transitively via `vintage.wine.cellar`) — needed because `user_directory_path` (`wine/utils.py:23-25`) builds the upload path from `instance.user.pk`, and once `user`/`created_by` is nullable (a departed member), that path function would break on already-uploaded files. Keying the path off `cellar_id` instead avoids the crash and stops leaking "which household member uploaded this" into storage paths.
- `Storage`, `StorageItem`, `StorageItemEvent`, `StorageLabel`: inherit `cellar` scoping via `UserContentModel` like everything else. `StorageItem`'s existing constraint (scoped to `storage`, not `user`, `:138-146`) needs **no change** — it's transitively cellar-scoped once `Storage` is.
- Global/shared lookup-vocab rows: extend the existing `user=None` convention to `cellar=None` in the same two places it already lives (`forms.py:200`, `filters.py:137`) — same-sized diff as doing it later, no reason to defer.

## 3. Sharing semantics (the actual questions asked)

**Are known wines merged between users when sharing?** No, not automatically, ever. A `Cellar`'s contents belong to the cellar, not to an individual. When two people share a cellar, they're both full members of *one* set of data from the start (for a newly created shared cellar) — there's nothing to merge. The "merge" question only arises when someone wants to fold their **pre-existing personal cellar** into a shared one; that is always an explicit, user-initiated action per `Wine` (moving a `Wine` moves all its `Vintage`s and `StorageItem`s with it — v1 does not support splitting a `Wine` across cellars), and it runs the existing `_find_matching_wine` dedup check scoped to the destination cellar so it can offer "merge stock into this existing match" instead of creating a duplicate.

**Does the invited user only see the other's wines while invited, or is it persistent?** Persistent and symmetric. Accepting an invite creates a `CellarMembership` — the same kind of row the inviter has. There is no "guest mode" or reduced/temporary visibility; both members have identical read/write access to that cellar for as long as the membership exists. Removing a member deletes their `CellarMembership` (access revoked immediately) but leaves their contributed data in the cellar, attributed to them via `created_by` (`SET_NULL`) for history.

**Is there a setting to control the behavior?** No dedicated "merge mode" toggle — the model itself (separate cellars, explicit per-item move) *is* the control, and it's simpler and safer than a global switch that could silently combine two people's data. The one piece of real per-request state is **which cellar is currently active** — a small cellar-switcher (session var + nav dropdown), needed because a user may belong to more than one cellar (their personal one + any shared ones). Users always belong to ≥1 cellar; an empty personal cellar can be deleted once another exists to fall back to.

**What happens with duplicates?** Three existing mechanisms, all rescoped from per-user to per-cellar rather than reinvented: (1) the `UniqueConstraint`s on `Wine`/`Vintage`/lookup-vocab already prevent exact-match duplicates within one cellar; (2) `_find_matching_wine` (case-insensitive name/type/size/country match) already backs the AI label-scan "is this wine already known?" flow and is reused for both routine adds and cellar-move merges; (3) barcode-scan matching is reused the same way. None of this is new logic — it's the same dedup the app already has, just re-pointed at `cellar` instead of `user`.

**Which grape/region/vineyard suggestions show up when creating a wine in a shared cellar — mine, theirs, or both?** Neither specifically — lookup vocab follows the same rule as everything else: scoped to the *active cellar*, not to whichever member is looking. `_limit_user_querysets` (`forms.py:183-201`) becomes `Q(cellar=None) | Q(cellar=active_cellar)`, so autosuggest shows the global baseline plus whatever's already been created *inside that specific cellar* by either member. It does not pull in rows from either member's own personal cellar. This falls straight out of the no-auto-merge principle, but has a real day-one wrinkle: a brand-new shared cellar starts with an empty vocab list even if both members had rich personal lists elsewhere, so the first several wines added will feel repetitive re-creating common grapes/regions. See the "copy my lookup vocab" nicety in §7.

## 4. Roles & invitation flow

- **Owner**: rename/delete the cellar, invite/remove members, transfer ownership. **Member**: full CRUD on cellar contents, cannot manage membership. No finer-grained permissions (e.g. hiding specific notes from a partner) — explicitly out of scope for v1, called out here so it isn't silently scope-crept in later.
- If the sole owner leaves/is removed from a 2-person cellar, the other member is auto-promoted to owner rather than leaving the cellar ownerless (a state the owner-only invite/remove UI couldn't otherwise recover from).
- Invite by email (`CellarInvitation`): owner sends an invite; existing users get a notification/accept link, non-users get a signup link. Since public signup is closed by default (`ENABLE_SIGNUPS=False`, gated in `user/signup_adapter.py:6-9`), the invite token must explicitly bypass that gate **only** for the invited email — `is_open_for_signup` extended to accept a valid pending-invite token, and the accepted signup must verify the signed-up email matches the invited email (not just "any signup with a valid token"). Token must be unguessable (`secrets.token_urlsafe`, not sequential) and expire (`expires_at`).
- `request.cellar` (session-based active cellar) must be **re-validated against current membership on every request**, not just at switch time — otherwise a just-removed member keeps a stale session pointer into a cellar they no longer belong to.
- Cellar with zero remaining members (last member removed/account deleted) is deleted via a `post_delete` signal on `CellarMembership`, mirroring the existing signal-driven auto-create pattern in `storage/signals.py`.

## 5. Reminders / notifications

`drink_by_reminder` and `opened_bottle_reminder` (`wine/tasks.py:65-102`) move from iterating `User.objects` to iterating `Cellar.objects`, querying cellar-scoped `Vintage`/`StorageItem` data once per cellar, then fanning out one email per member who still has `UserSettings.notifications` enabled (`user/models.py:20`) — the notification-preference check just moves from the outer loop to the inner per-member loop, no new preference model needed.

## 6. Migration path (mechanical, low-risk but wide)

1. Add `Cellar`, `CellarMembership`, `CellarInvitation` models/migration.
2. Data migration: one `Cellar` + one `CellarMembership(role="owner")` per existing `User`.
3. Add nullable `cellar` FK to every `UserContentModel` subclass + `WineImage`.
4. Data migration: backfill `cellar_id` from each row's owning user's personal cellar (built in step 2).
5. Make `cellar` non-nullable; drop/recreate all `UniqueConstraint`s (`user`→`cellar`); rename `user`→`created_by`, relax to nullable/`SET_NULL`.
6. Confirm `manage.py makemigrations --dry-run --check` is clean (per `CLAUDE.md` CI expectations) before merging.

**Touch points beyond models** (rescoping, not new logic): `wine/views.py` (~9 sites: `:64,70,78,499,573,629,889,933,1057`), `storage/views.py` (~11 sites), `wine/forms.py:183-201`, `wine/filters.py:125-145`, `wine/tasks.py:65-102`, `storage/signals.py:8-16`, `wine/admin.py` + `storage/admin.py` (add cellar-facing fields — `storage/admin.py` currently exposes no ownership field at all), `user/signup_adapter.py:6-9`, `wine/utils.py:23-25`. Recommend landing a **centralizing middleware/mixin** (`request.cellar`, resolved once, replacing all of the above ad-hoc `.filter(user=request.user)` calls and de-duplicating the two independently copy-pasted `Q(user=None) | Q(user=...))` implementations) as its own preparatory PR before the sharing feature lands — it's a net code-quality improvement independent of sharing, and de-risks the bigger migration.

## 7. Deliberately deferred / out of scope for v1

- Fine-grained per-item privacy within a shared cellar (e.g. hiding a note from a partner).
- Splitting a single `Wine` across cellars during a move (moves are always whole-`Wine`-subtree).
- Self-service account deletion (doesn't exist today either — this design only specifies the *intended* behavior — `SET_NULL` on `created_by`, membership removed, cellar deleted only once its last member is gone — for whenever such a view is built).
- Full data export / right-to-erasure semantics for shared, multi-contributor data (documented as a future constraint: erasure of a shared cellar's contributed rows isn't supported, only PII erasure via `created_by` `SET_NULL`).
- Cellar switcher UX beyond a flat list (search/pagination) — most users will have exactly 2 cellars (personal + 1 shared).
- **Nice to have, not required for v1**: a "copy my lookup vocab into this cellar" action, offered at cellar-creation/invite-accept time, that copies a joining member's personal `Grape`/`Region`/`Vineyard`/etc. rows into the target cellar (deduped by name, same logic as the wine-move merge check). Addresses the day-one-empty-vocab wrinkle from §3 without weakening the no-auto-merge principle, since it stays an explicit, opt-in action scoped to lookup vocab only — never wines/stock.

## 8. Extension: decoupling shared wine records from personal stock

A related but distinct ask: share the *wine catalog* (records, ratings, tasting notes, "including future modifications") between users while keeping physical *stock* personal — e.g. a couple rates and tracks wines together, but each keeps their own bottles in their own storage. This turns out to need no new schema: the existing design never forced `Wine.cellar` to equal the `cellar` of the `Storage` holding stock against it — both independently inherit their own `cellar` FK from `UserContentModel`. That coupling was only ever assumed at the UI/session ("one active cellar") layer described in §4, not enforced by the data model. "Share the catalog, keep stock personal" is simply the case where a `Wine`'s `cellar` (shared) differs from the `cellar` of the `Storage` a member places stock in (their own personal one, untouched).

What this actually requires:

1. **A new authorization rule on `StorageItem` creation.** Today nothing checks this, because same-cellar was assumed. Adding a bottle must require membership in *both* `storage.cellar` (allowed to place stock there) *and* `vintage.wine.cellar` (allowed to reference that wine record) — these can now be different cellars.
2. **A multi-cellar-aware wine/vintage picker for the "add stock" flow.** Instead of scoping to a single active cellar, the stock-add search becomes `Vintage.objects.filter(wine__cellar__in=<all cellars the user belongs to>)`, so a member can log a bottle of a jointly-tracked wine even though the stock itself goes into their own personal storage.
3. **The single "active cellar" concept (§4) splits into two independent selections**: which cellar's *catalog* you're browsing/adding wines to, versus which of your *storages* new stock physically goes into. These coincide in the common "share everything" case, so the UI can keep one picker by default and only surface the second when they diverge. (See §9 for why this doesn't actually need a second navbar switcher.)
4. **Nothing new needed for "including future modifications."** A shared `Vintage` is one database row, not a copy — any member editing its rating, tasting note, or drink-by date changes it for every member with catalog access, exactly per the "real shared ownership, not a snapshot" principle already established in §3.
5. **Generalizes to more than two users for free** — `Cellar`/`CellarMembership` was never hardcoded to a pair.

This reframes the two sharing modes as the same primitive used two ways: **"fully shared cellar"** (the original ask, §1-§6) is a couple's `Wine` records *and* `Storage` both pointing at the same shared `Cellar`. **"Shared catalog, personal stock"** (this extension) is `Wine` records pointing at a shared `Cellar` while each member's `Storage` stays pointed at their own personal `Cellar`, exactly as it is today.

**Gap worth flagging, not solving now**: this mode makes it more likely someone wants *personal* opinions on a *jointly* tracked wine (e.g. differing ratings) — but `Vintage.rating`/`comment` are single shared fields, so today the catalog can't hold two different ratings for the same vintage. Supporting that would need a separate overlay model, e.g. `VintageRating(vintage, user, rating, note)`, layered on top later. Likely the next question once this ships, not required for what's being asked now.

## 9. UX: a single navbar cellar switcher, not two

§8 point 3 raises the risk of needing two separate pickers (catalog context vs. stock destination) once wine-cellar and storage-cellar diverge. In practice one navbar-level switcher is enough, because a second control the app already has can absorb the other axis.

- **The navbar switcher sets one thing: the active cellar** (session var, re-validated against current membership every request per §4). It drives the default target for **new** `Wine` records, the default filter for the wine list/browse view, and lookup-vocab autosuggest scope (§3).
- **Stock doesn't need a second switcher.** The stock-add flow already has a `Storage` picker (`storage_picker_payload`, `storage/views.py`), and every `Storage` belongs to exactly one cellar. Widening that picker's queryset from "active cellar's storages" to "all storages across every cellar the user belongs to" — grouped/labeled by cellar name once there's more than one — gives the cellar choice for free through a control that already exists and is already the more natural axis to pick on ("Kitchen Fridge" vs. "My Shelf" is a more meaningful choice than "Cellar A" vs. "Cellar B"). §8 point 2's cross-cellar vintage search feeds the same form.
- **Adding a wine while a member of multiple wine-catalog cellars** (e.g. one shared with a partner, a separate one with a wine-tasting club): a new `Wine` defaults to whichever cellar is currently active via the navbar switcher — the same pattern as a workspace/org switcher in Notion or GitHub determining where new content lands by default. An optional inline cellar selector on the "New Wine" form (defaulting to active, shown only once the user belongs to >1 cellar) lets someone add to a non-active cellar without a full context switch first — a convenience, not a requirement.
- **Duplicate detection stays cellar-scoped, not merged across cellars.** `_find_matching_wine` runs against whichever cellar a `Wine` is being created in. A "Barolo 2018" existing separately in a partner-cellar and a wine-club-cellar is not a duplicate — cellar boundaries exist specifically to keep those catalogs separate, so no cross-cellar dedup should trigger.
