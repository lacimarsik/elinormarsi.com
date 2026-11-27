# Handover: elinormarsi.com

State as of 2026-11-27. From this date, development continues with the team that is in
direct contact with the client. The repo layout, preview and checks are in `README.md`.

## Where things stand

- **Proposals 1 and 2 continue, and proposal 3 is dropped.** The client reviewed the
  chooser on 2026-11-26.
- **Hero first.** She wants to settle the first screen (the hero) of proposals 1 and 2
  before going through the rest of each page in detail. So **v3 changes only the hero**.
  Everything below it is the same as v2.
- **v2 vs v1.** v2 fixed small problems in v1: hidden background text, the video gallery
  and the concert table on mobile. It also added the "Svět Elinor" section about her other
  crafts. v1 and v2 stay in the repo for comparison.
- **Placeholders.** Concert dates and the technical rider button are placeholders on every
  page.
- **Not deployed.** Nothing is published. The client reviews the pages from a local
  preview, or from screenshots sent by email.

### What v3 changed (PR #2, branch `hero-refresh`)

- **Proposal 1, "Dřevo a erb":** the hero is split into three layers in `assets/v3/`:
  - `hero-forest.jpg`, the forest photo;
  - `plank.webp`, with a PNG fallback;
  - `logo.png`.

  The plank is about 28–30% less tall than in v2. Measured at 1440×900, the crest tip
  went from about 214 to 152 px and the carved edge from about 211 to 151 px. The client
  asked for the plank "the same, only sharper", so it is rebuilt from a 4× Real-ESRGAN
  upscale of the original art.
- **Proposal 2, "Hluboký les":** a CC0 Celtic tree of life in gold outlines replaces the
  ring behind the title. The nav is no longer hidden under the back bar, and the eyebrow
  is set in Cormorant Garamond, because Uncial Antiqua broke "příroda".
- **Both v3 heroes:** the name is set in Cinzel Decorative with Cinzel's E. The client
  felt the Decorative E looked cut off.
- **Font page:** `proposals/fonty/` shows that option next to six OFL alternatives. Each
  one was checked for Czech by rendering it.
- **Chooser:** each card shows a preview of its proposal's latest version and opens that
  version.

PR #2 is a draft. Until it is merged, `main` has v2 only, so work from `hero-refresh` or
merge it first.

## Waiting on the client

1. **The plank for proposal 1.**
   - The client is preparing her own plank in Gemini.
   - Compare it side by side with the Real-ESRGAN plank now in v3, and let her pick.
   - A Gemini plank is new artwork with its own geometry, so `build_layers.py` can't use
     it (that script only accepts an upscale of the original header strip).
   - To use it:
     1. Cut it out of its flat background.
     2. Scale it to 3840 px wide.
     3. Save it as `assets/v3/plank.webp` plus `plank.png`.
     4. Re-check the nav position (`.plank-nav` `margin-top` in the page CSS) and the
        heights at 1440×900: at most 158 px to the crest tip and 140 px to the scallops.
2. **A new logo.**
   - The owner will send a transparent PNG at least 500 px tall, or an SVG.
   - It replaces `assets/v3/logo.png` as a single-file swap. Check its size on the plank
     afterwards.
3. **The name font.**
   - She picks one on the font page.
   - Apply it to the name in both heroes. Option 0 is in place for now.

## After the hero is settled

- Go through the rest of proposals 1 and 2 section by section with the client.
- Add the real concert dates and the rider.
- Choose hosting. The production domain is **`www.elinormarsi.cz`** (canonical),
  confirmed by the client on 2026-11-27. The bare `elinormarsi.cz` must 301-redirect to
  `www`. Before launch, search the pages for hard-coded `.com` references: canonical,
  `og:url`, links, and the `booking@elinormarsi.com` contact address. The repo keeps its
  `elinormarsi.com` name.

## Ground rules that came from the client and the owner

- **No artwork drawn from geometric SVG shapes or paths:** no hand-made wood, ivy or
  trees, because they come out looking geometric. Use real images instead:
  - an upscale of the existing art,
  - Gemini output from the client or the owner,
  - or a public-domain or CC0 image whose licence you checked on its own source page.
- **Record every third-party asset** (source, author, licence) in `assets/CREDITS.md`.
  Fonts must be OFL.
- **New round, new folder.** Copy the latest version (e.g. `v3` to `v4`) and don't edit
  the old one in place. Link the new version from the chooser so the client can compare.
- **Owner approval:**
  - Ask the owner before installing software on the Mac.
  - PRs here have been merged only on the owner's say-so, and the owner decides when
    anything is deployed.
- **Browser dialogs:** never use `window.confirm`, `alert` or `prompt`. Use an in-page
  dialog.
- **Page copy:** Czech. Keep repo docs, commits and PRs in English.
