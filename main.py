from markdownify import markdownify as md
from wikipedia import wikipedia as wiki
from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown

import replicate
import requests
import mdv
import re

load_dotenv()

console = Console()

class WikiResult:
    def __init__(self, pageid, title, description):
        self.pageid = pageid
        self.title = title
        self.description = description
        
    def __str__(self):
        return self.title + " - " + self.description

class WikiSearch:
    def __init__(self):
        self.results = []
        
    def search(self, q):
        data = {
            "action": "query",
            "prop": "info|description",
            "format": "json",
            "titles": q
        }
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=data)
        json_data = resp.json()

        pages = json_data["query"]["pages"]

        for key in pages:
            if pages[key]['pageid'] == -1:
                console.print("[red bold]No results found.", style="red bold")
                return
            page = pages[key]
            description = page.get("description", "")
            result = WikiResult(key, page['title'], description)
            self.results.append(result)
            
    def print_results(self):
        for result in self.results:
            print(result)
            
    def get_results(self) -> [WikiResult]:
        return self.results

class WikiPage:
    def __init__(self, pageid):
        self.pageid = pageid
        self.content = ""
        
    def fetch_content(self):
        data = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "pageids": self.pageid
        }
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=data)
        json_data = resp.json()
        self.content = json_data["query"]["pages"][str(self.pageid)]["extract"]
        
    def print_content(self):
        print(self.content)
        
    def get_content(self):
        return self.content

def print_usage():
    print("WikiSearch: A simple search engine for Wikipedia.")
    print("Usage: ")
    print("q: Search for an article.")

def summarize(content: str) -> str:
    result = replicate.run(
        'meta/meta-llama-3-70b-instruct',
        input={
            'prompt': "Summarize the following in 300 words: " + content,
        })
    res = ''
    for item in result:
        res += item
    return res

def remove_empty_headings(text):
  pattern_to_remove = re.compile(r'##(.*)\n\n\n')
  return pattern_to_remove.sub('', text)


def printHtml(content: str):
    markdown = remove_empty_headings(md(content).strip())
    with open("output.md", "w") as f:
        f.write(markdown)
    formatted = mdv.main(markdown, tab_length=8).replace('0m\n', '0m\n\n\n')
    with open("formatted.md", "w") as f:
        f.write(formatted)
    markdown = Markdown(formatted)
    console.print(markdown)

def query(q):
    search = wiki.search(q)
    for i, result in enumerate(search):
        rprint(str(i) + ". " + str(result))
        
    index = input("Enter the index of the article you want to read: ")
    print("Opening article " + str(index))
    
    wiki_page = wiki.page(search[int(index)])
    content = wiki_page.get_content().replace("= ", "# ")
    while content.find("=#") != -1:
        content = content.replace("=#", "##")
    
    while content.find(" =") != -1:
        content = content.replace(" =", " ")
    printHtml("# " + wiki_page.title + "\n\n" + content)
    


if __name__ == "__main__":
    print_usage()
    type = input("Enter the type of action you want to perform: ")
    if type == "q":
        param = input("Enter the query: ")
        print("Searching for " + param)
        query(param)
        