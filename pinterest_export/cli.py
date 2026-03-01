"""CLI entry point."""
import click

@click.command()
@click.argument("board_url")
@click.option("--output", "-o", default="./output", help="Output directory")
@click.option("--limit", "-n", default=None, type=int, help="Max pins to scrape")
@click.option("--no-ai", is_flag=True, help="Skip AI analysis")
def main(board_url, output, limit, no_ai):
    """Scrape a Pinterest board and generate an HTML gallery."""
    click.echo(f"Scraping {board_url} → {output}")
    click.echo("⚠️  Not implemented yet. See GitHub issues for roadmap.")

if __name__ == "__main__":
    main()
