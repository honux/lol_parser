import io
import requests

from .version import Version

# Simple wrapper for the readline method on python, removing the "\r\n"
def _read_line(buff):
    return buff.readline().rstrip()

class SolutionManifestProject(object):
    def __init__(self, name, version, ukn_1, ukn_2):
        self.name = name
        self.version = version
        self.ukn_1 = ukn_1
        self.ukn_2 = ukn_2

class SolutionManifest(object):
    def __init__(self, buff):
        self.projects_available = {}
        self.languages_requirements = {}
        self.version = ""

        self.sln_project_name = ""
        self.sln_version = ""

        self._parse_solution_manifest(buff)

    def _parse_solution_manifest(self, buff):
        if not isinstance(buff, io.IOBase):
            buff = io.StringIO(buff)

        magic = _read_line(buff)
        if magic != "RADS Solution Manifest":
            raise NotImplementedError("The format of the solution manifest is unknown")

        self.version = Version(_read_line(buff))
        self.sln_project_name = _read_line(buff)
        self.sln_version = Version(_read_line(buff))

        projects_count = int(_read_line(buff))
        for _ in range(projects_count):
            project_name = _read_line(buff)
            project_version = _read_line(buff)
            ukn_1 = _read_line(buff)
            ukn_2 = _read_line(buff)
            self.projects_available[project_name.lower()] = SolutionManifestProject(project_name, project_version, ukn_1, ukn_2)

        language_requirements_count = int(_read_line(buff))
        for _ in range(language_requirements_count):
            language = _read_line(buff)
            ukn_1 = _read_line(buff)
            project_requirement_count = int(_read_line(buff)) # Not sure about this

            self.languages_requirements[language] = []
            for _ in range(project_requirement_count):
                project_name = _read_line(buff).lower()
                self.languages_requirements[language].append(self.projects_available[project_name])

    @staticmethod
    def available_versions():
        r = requests.get("http://l3cdn.riotgames.com/releases/live/solutions/league_client_sln/releases/releaselisting")
        return [Version(v) for v in r.text.split("\n") if v]

    @staticmethod
    def latest_version():
        return SolutionManifest.available_versions()[0]

    @staticmethod
    def from_live(version):
        r = requests.get("http://l3cdn.riotgames.com/releases/live/solutions/league_client_sln/releases/{}/solutionmanifest".format(version))
        return SolutionManifest(r.text)
