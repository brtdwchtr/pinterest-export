"""CLI entry point for pinterest-export."""

import click
from rich.console import Console
from rich.live import Live

from pinterest_export.url_parser import parse_board_url
from pinterest_export.scraper import scrape_board_sync


console = Console()


@click.command()
@click.argument("url")
@click.option("--limit", "-l", default=None, type=int, help="Max pins to scrape")
def main(url: str, limit: int | None):
    """Scrape a Pinterest board."""
    try:
        parsed = parse_board_url(url)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    console.print(f"[green]Board:[/green] {parsed['canonical']}")
    console.print(f"[dim]User: {parsed['username']} | Board: {parsed['boardname']}[/dim]")
    console.print()

    with console.status("Scraping pins..."):
        pins = scrape_board_sync(parsed["canonical"], limit=limit)

    console.print(f"\n[bold green]Done![/bold green] Found [bold]{len(pins)}[/bold] pins.")
    for pin in pins[:5]:
        console.print(f"  • {pin.id}: {pin.title[:60] or '(no title)'}")
    if len(pins) > 5:
        console.print(f"  ... and {len(pins) - 5} more")
