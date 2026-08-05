# ACC-006 — Public Seller Profiles

**Status:** Implemented locally  
**Milestone:** M8  
**Last updated:** 2026-08-04

## Problem and scope

Buyers need a trustworthy, staff-reviewed way to learn about a seller without
exposing private account data. This accounts-domain slice adds immutable public
seller identifiers and moderation of a biography, avatar, and external social
links. Public routes and listing-page attribution are included in this slice.

## Non-goals

- No changes to seller display-name attribution, phone-verification policy,
  messaging, ratings, or seller subscriptions.

## Actors and permissions

- Authenticated active sellers update their private display name/phone and submit
  public profile content.
- Staff with the `accounts.change_sellerprofilerevision` permission (or a
  superuser) approve or reject pending revisions through Django admin.
- Public consumers may only use a later accounts selector that returns the
  profile's currently approved revision.

## Behavior and state

Each `SellerProfile` has an immutable UUID `public_id`. `display_name` remains
the existing public listing attribution and is never part of a revision.

Each submission creates one `SellerProfileRevision` in `pending` state with an
optional avatar, `bio`, `website_url`, `facebook_url`, `instagram_url`, `x_url`,
`linkedin_url`, and `youtube_url`. All links are optional but, when supplied,
must use HTTPS. Avatar input accepts JPEG, PNG, or WebP up to 10 MB.

A staff review records the reviewer, note, and review time. Approval changes the
revision to `approved` and atomically updates the profile's nullable
`current_approved_revision` pointer. Rejection changes only that revision to
`rejected`; the prior approved content, if any, stays public. A revision can be
reviewed exactly once through the service.

## Data, security, and privacy

The profile pointer is a singular foreign key, so each profile has at most one
current approved revision; it is nullable before first approval. The review
service locks the revision and profile, authorizes the reviewer, and accepts
only pending-to-approved or pending-to-rejected transitions. Admin exposes
revision content read-only and uses service-backed review actions.

`/sellers/<uuid>/` renders an active seller's safe profile and
`/sellers/<uuid>/avatar/` serves only the current approved avatar. Public
listing cards/details link to that stable profile URL. The profile page includes
only active public listings and seller-profile-only sold listings still inside
the accepted 30-day retention window; it never exposes private listing rows,
email, phone, verification state, or pending/rejected revisions.

## Migrations, rollout, and rollback

Apply the additive accounts migration before enabling any future public route.
It adds nullable `current_approved_revision`, an immutable UUID identifier, and
the revision table/index; existing profiles need no backfill. Roll back by
disabling the private submission/admin behavior and use a forward migration for
any correction, retaining submitted and reviewed moderation history.

## Tests and acceptance criteria

- Profiles receive unique immutable-format UUID public IDs.
- Sellers can submit private-profile changes and a pending public revision.
- HTTP and malformed external links are rejected; HTTPS links are accepted.
- Approved revisions update the current pointer and record reviewer/note/time.
- Rejected revisions preserve the existing current approved pointer.
- Non-staff and repeated review attempts fail.
