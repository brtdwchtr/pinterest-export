# pinterest-export

**Scrape any public Pinterest board from the command line.**  
Exports structured JSON, LLM-ready Markdown, and optionally caches all images locally — with a beautiful Rich progress UI.

```
$ pinterest-export https://www.pinterest.com/designmilk/packaging/

──────────────── pinterest-export ────────────────
  Board : designmilk/packaging
  URL   : https://www.pinterest.com/designmilk/packaging/

⏳ Scraping board…  42 pins found so far
✓ Scraped 87 pins.

⠸ Downloading images…  ████████░░  67/87  77%  00:12
✓ Downloaded 85 / 87 images.

┌─ Export Summary ──────────────────────────────┐
│ Board          │ designmilk/packaging          │
│ Pins scraped   │ 87                            │
│ Images cached  │ 85                            │
│ board.json     │ ./pinterest-export-output/... │
│ board.md       │ ./pinterest-export-output/... │
└───────────────────────────────────────────────┘
```

## Install

```bash
pip install pinterest-export
playwright install chromium
```

## Usage

```bash
# Scrape and export JSON + Markdown
pinterest-export https://www.pinterest.com/username/boardname

# Custom output directory
pinterest-export https://www.pinterest.com/username/boardname --output-dir ./my-research

# Also download all images
pinterest-export https://www.pinterest.com/username/boardname --cache-images

# Add Gemini Vision analysis per pin
pinterest-export https://www.pinterest.com/username/boardname --vision

# Increase Gemini analysis parallelism
pinterest-export https://www.pinterest.com/username/boardname --vision --vision-concurrency 10

# Scrape only (no files written)
pinterest-export https://www.pinterest.com/username/boardname --no-export

# Limit to first N pins
pinterest-export https://www.pinterest.com/username/boardname --limit 50
```

## Output formats

### `board.json`
Structured metadata for every pin:
```json
{
  "board": "username/boardname",
  "url": "https://www.pinterest.com/...",
  "scraped_at": "2026-03-03T04:22:00Z",
  "pin_count": 87,
  "pins": [
    {
      "id": "123456789",
      "title": "Minimal packaging concept",
      "description": "Clean kraft paper with letterpress...",
      "link": "https://www.pinterest.com/pin/...",
      "image_url": "https://i.pinimg.com/...",
      "board_url": "https://www.pinterest.com/username/boardname/"
    }
  ]
}
```

### `board.md`
LLM-optimised Markdown — ready to paste into Claude, GPT, or any AI tool as context for design research, mood board analysis, or trend detection.

### Cached images
When `--cache-images` is set, all pin images are downloaded to a local cache directory and referenced by their Pinterest image ID. Subsequent exports reuse cached images.

### Vision metadata
When `--vision` is enabled (with `GEMINI_API_KEY` or `GOOGLE_API_KEY` set), each pin is enriched with:
- `vision_description`
- `vision_tags`
- `vision_colors`
- `vision_style`
- `vision_mood`

## Features

- Scrapes public Pinterest boards via Playwright (handles infinite scroll)
- Rich live progress UI: real-time pin count + image download progress bar
- JSON export with full structured metadata
- Markdown export optimised for LLM context windows
- Optional Gemini Flash (`gemini-2.0-flash`) analysis per pin
- Local image cache with concurrent downloads
- `--limit` flag for controlled scrapes
- `--no-export` flag for dry runs / in-memory use

## Roadmap

- [#6](https://github.com/brtdwchtr/pinterest-export/issues/6) Theme clustering across boards
- [#7](https://github.com/brtdwchtr/pinterest-export/issues/7) HTML gallery generator
- [#11](https://github.com/brtdwchtr/pinterest-export/issues/11) Config file support (`.pinterest-export.toml`)
- [#12](https://github.com/brtdwchtr/pinterest-export/issues/12) Watch mode / incremental exports

## Development

```bash
git clone https://github.com/brtdwchtr/pinterest-export
cd pinterest-export
uv sync
playwright install chromium
uv run pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT
