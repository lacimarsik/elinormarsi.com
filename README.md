# elinormarsi.com

Website proposals for the singer and songwriter Elinor Marsi. Everything here is static
HTML and CSS with images, and there is no build step. Fonts load from Google Fonts. Nothing
is deployed yet. The production domain will be `www.elinormarsi.cz` (see `HANDOVER.md`).

The current state, the open decisions and the next steps are in **[HANDOVER.md](HANDOVER.md)**.

## Layout

| Path | What it is |
| --- | --- |
| `index.html` | The chooser page the client opens first. It shows one card per proposal with a preview, plus a link to the font page. |
| `proposals/01-drevo-a-erb/`, `-v2/`, `-v3/` | Proposal 1, "Dřevo a erb": a carved wooden plank with the crest over the forest photo. |
| `proposals/02-hluboky-les/`, `-v2/`, `-v3/` | Proposal 2, "Hluboký les": a dark cinematic forest with a Celtic tree of life. |
| `proposals/03-kniha-pohadek/` | Proposal 3, "Kniha pohádek": an illuminated storybook. The client did not choose it. |
| `proposals/fonty/` | A specimen page of candidate fonts for the name "Elinor Marsi". |
| `assets/` | Shared images. `assets/v3/` holds the layered v3 hero art, `assets/previews/` the chooser thumbnails. |
| `assets/CREDITS.md` | The source and licence of every third-party image and font. |
| `resources/` | The client's original material from the previous website effort: logo, texts and backgrounds. |
| `tools/hero-v3/build_layers.py` | Rebuilds the proposal 1 v3 hero layers (plank, forest photo) from `assets/forest-header.jpg`. |

Each page is self-contained: its CSS and JS are inline in its `index.html`.

## Preview

```sh
python3 -m http.server 8766    # from the repo root, then open http://127.0.0.1:8766/
```

Any free port works. Do a hard refresh (Cmd+Shift+R) after an image changes, because the
browser keeps serving the cached copy.

## Checks

There is no test suite or linter. Before a PR, open every changed page at 1440×900,
1920×1080 and 390×844 and check:

- the browser console has no errors;
- nothing scrolls sideways at 390 px;
- Czech diacritics (ř ě č ů ž Ř Ě) render in every font used.

Use Playwright for the 390 px check. Headless Chrome's `--window-size` will not go below
500 px.

## Rebuilding the proposal 1 hero

```sh
python3 tools/hero-v3/build_layers.py                # plank from a Lanczos 2x upscale
python3 tools/hero-v3/build_layers.py STRIP.png 4    # plank from a sharper 4x upscale of header rows 0-299
```

It needs numpy, scipy and Pillow. The committed plank comes from a Real-ESRGAN strip:
`realesrgan-ncnn-vulkan` with the `realesrgan-x4plus` model, run on rows 0–331 of
`forest-header.jpg` and cropped to 7680×1200.
