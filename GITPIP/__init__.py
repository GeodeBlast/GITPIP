
import urllib.request as ur

class URL(str): pass
    
class PyPiURL(URL):
    
    package : str
    def __new__(cls, *, package):
        obj = super().__new__(cls, f"https://pypi.org/project/{package}/")
        obj.package = package
        return obj

class GitURL(URL):
    
    user : str
    package : str
    def __new__(cls, *, user, package):
        obj = super().__new__(cls, f"https://github.com/{user}/{package}")
        obj.user = user
        obj.package = package
        return obj

class UnknownPackages(ModuleNotFoundError):
    def __init__(self, packages : tuple[str]|str, gitUsers : tuple[str]|None=[], pypi=True):

        if len(packages) == 0:
            msg = "Package not found."
        elif isinstance(packages, str):
            msg = f"Package {packages} not found."
        elif len(packages) == 1:
            msg = f"Package {packages[0]} not found."
        else:
            msg = f"Packages {', '.join(map(repr, packages))} not found."
        
        sources = ["PyPi"] if pypi is True else []
        if gitUsers:
            sources.append( f"Github users {tuple(gitUsers)}")
        sourced = " Looked up on: " + ", ".join(sources)
        
        super().__init__(msg + sourced)

class PackageSourceConfliction(ModuleNotFoundError):
    def __init__(self, sources):
        super().__init__("Package was found on multiple sources:\n" + "\n".join(sources))

def urlExists(url : str):
    try:
        with ur.urlopen(url) as response:
            if response.status < 400:
                return True
            raise ur.HTTPError("", "", "", "", "")
    except ur.HTTPError:
        return False

def isOnPyPi(package):
        return urlExists(f"https://pypi.org/project/{package}/")

class GitUserbase:

    users : tuple[str]
    def __init__(self, users : tuple[str]|list[str]):
        
        self.users = users
    
    def findOnGit(self, package):
        
        return list(filter(urlExists, map(lambda user : GitURL(user=user, package=package), self.users)))
    
    def findOnPyPi(self, package):
        
        return url if urlExists(url := PyPiURL(package=package)) else None
    
    def __getitem__(self, package):
        
        match len(results := self.get(package)):
            case 0:
                raise UnknownPackages(package, gitUsers=self.users)
            case 1:
                return results[0]
            case _:
                raise PackageSourceConfliction(results)
    
    def get(self, package) -> tuple[str]:
        
        return tuple(filter(lambda source : source is not None, [self.findOnPyPi(package)] + self.findOnGit(package)))
    
    def find(self, package):
        """For `pip install`"""
        match len(results := self.get(package)):
            case 0:
                return None
            case 1:
                return results[0].package if isinstance(results[0], PyPiURL) else f"git+{results[0]}"
            case _ as size:
                msg = "Packages were found on multiple sources:\n" + \
                    "\n".join(map(lambda x:f"{x[1]:<70}[{x[0]+1:^8}]", enumerate(results))) + \
                    "\nSelect py entering the # of the desired package source: "
                # Not a digit or outside the range
                while not (userString := input(msg).strip()).isdigit() or not (choice := int(userString)-1) in range(size):
                    pass
                return results[choice].package if isinstance(results[choice], PyPiURL) else f"git+{results[choice]}"