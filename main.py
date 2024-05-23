from markdownify import markdownify as md

import requests
import mdv

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
        print(pages)

        for key in pages:
            if pages[key]['pageid'] == -1:
                print("No results found.")
                return
            result = WikiResult(key, pages[key]['title'], pages[key]['description'])
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

def printHtml(content: str):
    markdown = md(content)
    with open("output.md", "w") as f:
        f.write(markdown)
    formatted = mdv.main(markdown)
    print(formatted)
    
def query(q):
    search = WikiSearch()
    search.search(q)
    
    sorted = enumerate(search.get_results())
    
    for i, result in sorted:
        print(str(i) + ". " + str(result))
        
    index = input("Enter the index of the article you want to read: ")
    print("Opening article " + str(index))
    pageid = search.get_results()[int(index)].pageid
    
    wiki_page = WikiPage(pageid)
    wiki_page.fetch_content()
    printHtml(wiki_page.get_content())
    
    
    
    

if __name__ == "__main__":
    print_usage()
    type = input("Enter the type of action you want to perform: ")
    if type == "q":
        param = input("Enter the query: ")
        print("Searching for " + param)
        query(param)
        