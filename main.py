from typing import List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from wikipedia import wikipedia as wiki
import mdv
import requests
import re
import replicate
from dotenv import load_dotenv
import os
from pathlib import Path
import aiohttp
import asyncio

load_dotenv()

APP_DIR = Path.cwd() / 'wiki_search'
APP_DIR.mkdir(exist_ok=True)

console = Console(theme=Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
    "heading": "purple bold",
}))

app = typer.Typer(pretty_exceptions_enable=False)


class WikiResult:
    def __init__(self, pageid: str, title: str, description: str, content: Optional[str] = None, summary: Optional[str] = None):
        self.pageid = pageid
        self.title = title
        self.description = description
        self.summary: Optional[str] = summary
        self.content: Optional[str] = content


class WikiSearch:
    def __init__(self):
        self.results: List[WikiResult] = []
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search(self, query: str) -> bool:
        params = {
            "action": "query",
            "prop": "info|description",
            "format": "json",
            "titles": query,
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": 10
        }

        try:
            status = console.status("[info]Searching Wikipedia...[/info]")
            status.start()

            try:
                async with self.session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        raise requests.RequestException(f"Status code: {response.status}")
                    data = await response.json()
            finally:
                status.stop()

            if "query" not in data or "pages" not in data["query"]:
                console.print(Panel("[error]No results found[/error]", title="Search Error"))
                return False

            # Parse search results
            self.results = [
                WikiResult(
                    str(page["pageid"]),
                    page["title"],
                    page.get("description", "No description available")
                )
                for page in data["query"]["pages"].values()
            ]
            return True

        except Exception as e:
            console.print(Panel(f"[error]{str(e)}[/error]", title="Error"))
            return False

    def display_results(self):
        table = Table(title="Search Results", show_header=True, header_style="bold magenta")
        table.add_column("Index", style="cyan", width=6)
        table.add_column("Title", style="green")
        table.add_column("Description", style="yellow")

        for i, result in enumerate(self.results):
            table.add_row(str(i), result.title, result.description)

        console.print(Panel(table, border_style="green"))


async def summarize(content: str) -> str:
    if not os.getenv("REPLICATE_API_TOKEN"):
        return "Missing API token for summary generation"
    try:
        with console.status("[info]Generating summary...[/info]"):
            return ''.join(replicate.run(
                'meta/meta-llama-3-70b-instruct',
                input={'prompt': f"Summarize in 300 words, no other output {content}"}
            ))
    except Exception as e:
        return f"Summary generation failed: {str(e)}"


@app.command()
def run_search(
    query: str = typer.Option(..., "--query", "-q", help="Search term"),
):
    asyncio.run(search(query))


def remove_empty_headings(text):
  pattern_to_remove = re.compile(r'##(.*)\n\n\n')
  return pattern_to_remove.sub('', text)


async def search(query: str):
    async with WikiSearch() as wiki_search:
        if not await wiki_search.search(query):
            raise typer.Exit(code=1)

        wiki_search.display_results()

        while True:
            index = Prompt.ask("Enter article index to read (or 'q' to quit)", default="0")
            if index.lower() == 'q':
                break

            try:
                result = wiki_search.results[int(index)]
                page = wiki.page(result.title)
                content = page.content.replace("= ", "# ")
                while content.find("=#") != -1:
                    content = content.replace("=#", "##")

                while content.find(" =") != -1:
                    content = content.replace(" =", " ")

                content = f"# {result.title}\n\n\n" + remove_empty_headings(content)
                result.content = content

                content = mdv.main(content, tab_length=8).replace('0m\n', '0m\n\n\n')

                md_content = Markdown(content)

                while True:
                    # Clear the screen before showing content
                    console.clear()

                    console.print(Panel(f"[heading]{result.title}[/heading]"))

                    with console.pager():
                        console.print(md_content)

                    console.print(Panel(
                        "[info]s: Summary | n: New search | q: Quit[/info]"
                    ))

                    action = Prompt.ask("Action", choices=["s", "n", "q"], default="q")

                    if action == "q":
                        exit()
                    elif action == "s":
                        if not result.summary:
                            result.summary = await summarize(result.content)
                        console.clear()
                        console.print(Panel(result.summary, title="Summary"))

                        Prompt.ask("Press Enter to continue")
                    elif action == "n":
                        break

            except Exception as e:
                console.print(f"[error]{str(e)}[/error]")
                if not Confirm.ask("Try another article?"):
                    break

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[warning]Operation cancelled[/warning]")
    except Exception as e:
        console.print(f"[error]{str(e)}[/error]")