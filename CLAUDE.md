# elinormarsi.com: agent notes

Static website proposals for the singer Elinor Marsi, with no build step. Read
`README.md` (layout, preview, checks) and `HANDOVER.md` (state, open items, ground
rules) before any work.

- **Branches.** Work in a git worktree on a short kebab-case branch from `origin/main`.
  Open a draft PR. Merge and deploy only when the owner says so.
- **Commit identity.** Before committing, check `git config user.name` and `user.email`.
  The repo lives under the owner's personal GitHub account, so never commit under an
  employer's email.
- **Artwork.** Never draw it from SVG shapes. Use real images, and record their licence in
  `assets/CREDITS.md` (see `HANDOVER.md`).
- **Versions.** Every design round gets a new version folder linked from `index.html`,
  and older versions stay.
- **Verifying a change.** Screenshot it at 1440×900, 1920×1080 and 390×844, with zero
  console errors and no sideways scroll on mobile.
- **Privacy.** The repo is public: no client contact details, private correspondence,
  credentials or `.env` files.
