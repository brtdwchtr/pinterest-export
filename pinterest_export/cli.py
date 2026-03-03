"""CLI entry point for pinterest-export."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text

from pinterest_export.exporter import export_json, export_markdown
from pinterest_export.image_cache import download_pins
from pinterest_export.scraper import scrape_board_sync
from pinterest_export.url_parser import parse_board_url

console = Console()


def _make_scrape_status(pin_count: int, label: str = "Scraping board…") -> Text:
    """Build a status line for the live scraping display."""
    t = Text()
    t.append("⏳ ", style="yellow")
    t.append(label, style="bold")
    if pin_count:
        t.append(f"  {pin_count} pins found so far", style="dim")
    return t


@click.command()
@click.argument("url")
@click.option("--limit", "-l", default=None, type=int, help="Max pins to scrape.")
@click.option(
    "--output-dir", "-o",
    default=None,
    type=click.Path(),
    help="Directory to write board.json and board.md (default: ./pinterest-export-output).",
)
@click.option(
    "--cache-images",
    is_flag=True,
    default=False,
    help="Download and cache all pin images locally.",
)
@click.option(
    "--no-export",
    is_flag=True,
    default=False,
    help="Skip JSON/Markdown export — just scrape and display a summary.",
)
def main(url: str, limit: int | None, output_dir: str | None, cache_images: bool, no_export: bool):
    """Scrape a Pinterest board and export pin data.

    URL is the Pinterest board URL (e.g. https://www.pinterest.com/user/boardname/).

    Outputs board.json (structured metadata) and board.md (LLM-optimised Markdown)
    to OUTPUT_DIR.  Use --cache-images to also download pin images locally.
    """
    # ── Parse URL ────────────────────────────────────────────────────────────
    try:
        parsed = parse_board_url(url)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    canonical = parsed["canonical"]
    board_slug = f"{parsed['username']}/{parsed['boardname']}"

    console.rule(f"[bold magenta]pinterest-export[/bold magenta]")
    console.print(f"  Board : [cyan]{board_slug}[/cyan]")
    console.print(f"  URL   : [dim]{canonical}[/dim]")
    if limit:
        console.print(f"  Limit : [dim]{limit} pins[/dim]")
    console.print()

    # ── Scrape ───────────────────────────────────────────────────────────────
    pin_count_ref = [0]

    with Live(console=console, refresh_per_second=4) as live:
        def on_pin_found(count: int) -> None:
            pin_count_ref[0] = count
            live.update(_make_scrape_status(count))

        live.update(_make_scrape_status(0))
        pins = scrape_board_sync(canonical, limit=limit, on_pin_found=on_pin_found)

    console.print(f"[bold green]✓[/bold green] Scraped [bold]{len(pins)}[/bold] pins.\n")

    if not pins:
        console.print("[yellow]No pins found — check the URL and try again.[/yellow]")
        raise SystemExit(0)

    # ── Download images (optional) ────────────────────────────────────────────
    image_paths: dict[str, Path] = {}
    if cache_images:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading images…", total=len(pins))
            completed = [0]

            async def _download_with_progress() -> dict[str, Path]:
                from pinterest_export.image_cache import _download_one, DEFAULT_CACHE_DIR, DEFAULT_RATE_LIMIT, MAX_CONCURRENCY
                import asyncio
                import httpx

                cache_dir = DEFAULT_CACHE_DIR
                cache_dir.mkdir(parents=True, exist_ok=True)
                sem = asyncio.Semaphore(MAX_CONCURRENCY)
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.pinterest.com/",
                }
                results: dict[str, Path] = {}

                async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                    async def _one(pin):
                        pin_id, path = await _download_one(client, sem, pin, cache_dir, DEFAULT_RATE_LIMIT)
                        if path:
                            results[pin_id] = path
                        progress.advance(task)

                    await asyncio.gather(*[_one(p) for p in pins])

                return results

            image_paths = asyncio.run(_download_with_progress())

        downloaded = len(image_paths)
        console.print(
            f"[bold green]✓[/bold green] Downloaded [bold]{downloaded}[/bold] / "
            f"{len(pins)} images.\n"
        )

    # ── Export ────────────────────────────────────────────────────────────────
    out_dir: Path | None = None
    json_path: Path | None = None
    md_path: Path | None = None

    if not no_export:
        out_dir = Path(output_dir) if output_dir else Path.cwd() / "pinterest-export-output"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "board.json"
        md_path = out_dir / "board.md"

        with console.status("Writing exports…"):
            export_json(pins, canonical, json_path, image_paths=image_paths or None)
            export_markdown(pins, canonical, md_path, image_paths=image_paths or None)

        console.print(f"[bold green]✓[/bold green] Exports written to [bold]{out_dir}[/bold]\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    table = Table(title="Export Summary", show_header=True, header_style="bold magenta")
    table.add_column("", style="dim", width=20)
    table.add_column("Value", style="bold")

    table.add_row("Board", board_slug)
    table.add_row("Pins scraped", str(len(pins)))

    if cache_images:
        table.add_row("Images cached", str(len(image_paths)))

    if json_path:
        table.add_row("board.json", str(json_path))
    if md_path:
        table.add_row("board.md", str(md_path))

    # Show a few sample pins
    table.add_row("", "")
    table.add_row("[dim]Sample pins[/dim]", "")
    for pin in pins[:3]:
        label = (pin.title or "(no title)")[:55]
        table.add_row(f"  #{pin.id}", label)
    if len(pins) > 3:
        table.add_row("  …", f"and {len(pins) - 3} more")

    console.print(table)
