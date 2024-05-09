
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
    def __init__(self, packages : tuple[str]|str, gitUsers : list[str]|None=[], locals : list[str]|None=[], pypi=True):

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
        if locals:
            sources.extend(map(repr, locals))
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

from PseudoPathy import PathGroup

class LocalRepositories(PathGroup):
    
    def __init__(self, paths : tuple[str]):
        super().__init__(*paths, purpose="r")
    
    def find(self, package : str):
        
        match len(results := self.findall(path=package)):
            case 0:
                return None
            case 1:
                return results[0]
            case _ as size:
                msg = "Packages were found in multiple sources:\n" + \
                    "\n".join(map(lambda x:f"{x[1]:<70}[{x[0]+1:^8}]", enumerate(results))) + \
                    "\nSelect py entering the # of the desired package source: "
                # Not a digit or outside the range
                while not (userString := input(msg).strip()).isdigit() or not (choice := int(userString)-1) in range(size):
                    pass
                return results[choice]

class GitUserbase:

    users : tuple[str]
    def __init__(self, users : tuple[str]|list[str]):
        
        self.users = tuple(users)
    
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

def mainCLI():
    
    import sys, os
    from shutil import which, rmtree

    from argparse import ArgumentParser, SUPPRESS
    from appdirs import user_config_dir, user_data_dir
    
    from collections import OrderedDict

    def applyArgsTemplate(parser : ArgumentParser, users=False, packages=False):
        if packages is True:
            parser.add_argument("packages", metavar="PACKAGE", nargs="+", default=[])
        if users is True:
            parser.add_argument("-u", "--user", "--users", dest="users", metavar="USER", nargs="+", action="extend", default=[])
            parser.add_argument("-l", dest="locals", metavar="LOCAL", action="store_const", const=[], default=None)
            parser.add_argument("--local", "--locals", dest="locals", metavar="LOCALS", nargs="*", default=None)

    __package__ = "GITPIP"
    __version__ = "1.0"

    if len(sys.argv) < 2:
        sys.argv += ["--help"]
    
    configDir = user_config_dir(__package__)
    dataDir = user_data_dir(__package__)

    os.makedirs(configDir, exist_ok=True)
    os.makedirs(dataDir, exist_ok=True)

    userFilename = os.path.join(configDir, "users.txt")
    localFilename = os.path.join(configDir, "locals.txt")

    if not os.path.exists(userFilename): open(userFilename, "w").close()
    if not os.path.exists(localFilename): open(localFilename, "w").close()

    parser = ArgumentParser(prog="GITPIP")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    modes = parser.add_subparsers(title="Modes", metavar="")
    for name, *aliases in [["install"], ["update", "upgrade", "reinstall"], ["remove", "uninstall"]]:
        modes.add_parser(name, aliases=aliases, argument_default=SUPPRESS, help=f"{name.capitalize()} packages")
    modes.add_parser("users", help=f"Add/remove github users")
    modes.add_parser("locals", help=f"Add/remove local source directories.")

    applyArgsTemplate(modes.choices["install"], users=True, packages=True)
    applyArgsTemplate(modes.choices["update"],  users=True, packages=True)
    applyArgsTemplate(modes.choices["remove"],              packages=True)

    modes.choices["users"].add_argument("--add", metavar="Add", nargs="*", default=[])
    modes.choices["users"].add_argument("--remove", dest="rm", metavar="Remove", nargs="*", default=[])

    modes.choices["locals"].add_argument("--add", metavar="Add", nargs="*", default=[])
    modes.choices["locals"].add_argument("--remove", dest="rm", metavar="Remove", nargs="*", default=[])

    modes.choices["install"].add_argument("--debug", action="store_true")
    modes.choices["update"].add_argument("--debug", action="store_true")
    modes.choices["remove"].add_argument("--debug", action="store_true")
    modes.choices["users"].add_argument("--debug", action="store_true")
    modes.choices["locals"].add_argument("--debug", action="store_true")
    
    args = parser.parse_args(sys.argv[1:])

    if os.name == "nt":
        exe = ["py", "-m", "pip"]
    elif which("pip") is not None:
        exe = ["pip"]
    elif which("pip3") is not None:
        exe = ["pip3"]
    else:
        print("Can't find a command for pip. Please install pip or create a proper alias for pip (E.g: 'pip' or 'pip3')")
        exit(1)
        
    mode = sys.argv[1].lower()
    try:
        match mode:
            case "update" | "upgrade" | "reinstall":
                com = ["install", "--force-reinstall", "--no-deps", "--cache-dir", repr(dataDir)]
                if args.locals is not None:
                    com.append("-e")
                    locals = LocalRepositories(map(str.strip, filter(None, open(localFilename, "r").readlines()+args.locals)))
                    packs = OrderedDict([(package, locals.find(package)) for package in args.packages])
                    if None in packs.values():
                        raise UnknownPackages(tuple(filter(lambda name: packs[name] is None, packs)), locals=locals._roots, pypi=False)
                else:
                    users = GitUserbase(map(str.strip, filter(None, open(userFilename, "r").readlines()+args.users)))
                    packs = OrderedDict(zip(args.packages, map(users.find, args.packages)))
                    if None in packs.values():
                        raise UnknownPackages(tuple(filter(lambda name: packs[name] is None, packs)), gitUsers=users.users)
                os.system(" ".join(exe+com+list(packs.values())))
                if args.locals is not None:
                    for pack in packs.values():
                        rmtree(pack / (os.path.split(pack)[1]+".egg-info"), ignore_errors=True)
                        rmtree(pack / os.path.split(pack)[1] / "__pycache__", ignore_errors=True)

            case "remove" | "uninstall":
                com = ["uninstall"]
                packs = args.packages
                os.system(" ".join(exe+com+packs))

            case "install":
                com = ["install", "--cache-dir", repr(dataDir)]
                if args.locals is not None:
                    com.append("-e")
                    locals = LocalRepositories(map(str.strip, filter(None, open(localFilename, "r").readlines()+args.locals)))
                    packs = OrderedDict([(package, locals.find(package)) for package in args.packages])
                    if None in packs.values():
                        raise UnknownPackages(tuple(filter(lambda name: packs[name] is None, packs)), locals=locals._roots, pypi=False)
                else:
                    users = GitUserbase(map(str.strip, filter(None, open(userFilename, "r").readlines()+args.users)))
                    packs = OrderedDict(zip(args.packages, map(users.find, args.packages)))
                    if None in packs.values():
                        raise UnknownPackages(tuple(filter(lambda name: packs[name] is None, packs)), gitUsers=users.users)
                os.system(" ".join(exe+com+list(packs.values())))
                if args.locals is not None:
                    for pack in packs.values():
                        rmtree(pack / (os.path.split(pack)[1]+".egg-info"), ignore_errors=True)
                        rmtree(pack / os.path.split(pack)[1] / "__pycache__", ignore_errors=True)

            case "users":
                users = set(map(str.strip, filter(None, open(userFilename, "r").readlines())))
                if args.rm or args.add:
                    users.difference_update(args.rm)
                    users.update(args.add)
                    open(userFilename, "w").write("\n".join(users))
                users = list(users)
                for i in range(0, len(users), 3):
                    print(" ".join(map("{:<19}".format, users[i:i+3])))

            case "locals":
                locals = set(map(str.strip, filter(None, open(localFilename, "r").readlines())))
                if args.rm or args.add:
                    locals.difference_update(args.rm)
                    locals.update(args.add)
                    open(localFilename, "w").write("\n".join(locals))
                locals = list(locals)
                for i in range(0, len(locals), 3):
                    print(" ".join(map("{:<19}".format, locals[i:i+3])))

            case _:
                print(f"Unknown mode {mode!r}")
    except Exception as e:
        if args.debug:
            raise e
        else:
            print(e)
            exit(1)