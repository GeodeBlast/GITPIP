
import urllib.request as ur

class UnknownPackages(ModuleNotFoundError):
    def __init__(self, package, *packages, gitUsers : tuple[str]|None=[]):
        msg = f"Package{'s'*(bool(packages))} {', '.join(map(repr, (package,)+packages))} not found."
        sources = []
        sources.append("PyPi")
        if gitUsers:
            sources.append(f"Github users {tuple(gitUsers)}")
        msg += " Looked up on: " + ", ".join(sources)
        super().__init__(msg)

def urlExists(url):
    try:
        with ur.urlopen(url) as response:
            if response.status < 400:
                return True
            raise ur.HTTPError("", "", "", "", "")
    except ur.HTTPError:
        return False

def isOnPYPI(arg):
        return urlExists(f"https://pypi.org/project/{arg}/")

class GitUserbase:

    users : tuple[str]
    def __init__(self, users):
        self.users = users
    
    def findOnGit(self, arg):
        
        for user in self.users:
            if urlExists(link := f"http://github.com/{user}/{arg}"):
                return link
        return None