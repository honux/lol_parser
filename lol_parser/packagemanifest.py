import io
import requests
import os.path
import urllib.parse
import zlib
from collections import defaultdict

_session = requests.Session()
CHUNK_SIZE = 1024
REQUESTS_TIMEOUT = 30

class PackageManifestFile(object):
    # PS: Some claim that the "ukn" is type, but there is no doc on what it belongs to. Also, on almost all the cases it is 0, so it does not look like the file type.
    def __init__(self, full_file_path, offset, size, ukn):
        self.full_file_path = full_file_path
        self.path, self.real_name = os.path.split(self.full_file_path)
        self.name = self.real_name.replace(".compressed", "")
        self.compressed = self.real_name.endswith(".compressed")
        self.offset = offset
        self.size = size
        self.ukn = ukn

    def download(self, base_url, out_file=None, out_dir=None):
        url = urllib.parse.urljoin(base_url, self.full_file_path.lstrip("/"))
        out_file_path = os.path.join(out_dir or self.path, out_file or self.name)
        os.makedirs(out_dir or self.path, exist_ok=True)

        r = _session.get(url, stream=True, timeout=REQUESTS_TIMEOUT)

        decoder = None
        if self.compressed:
            decoder = zlib.decompressobj(zlib.MAX_WBITS) # Zlib

        with open(out_file_path, 'wb') as out_file:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue

                if decoder:
                    chunk = decoder.decompress(chunk)

                out_file.write(chunk)
        return out_file_path

    def extract(self, buff, directory):
        buff.seek(self.offset, io.SEEK_SET)
        out_file_path = os.path.join(directory, self.name)

        decoder = None
        if self.compressed:
            decoder = zlib.decompressobj(zlib.MAX_WBITS) # Zlib

        with io.open(out_file_path, "wb") as out_file:
            data_left = self.compressed_file_size if self.compressed else self.file_size
            while True:
                if data_left <= 0:
                    break

                data_size = min(CHUNK_SIZE, data_left)
                data_left -= data_size
                data = buff.read(data_size)

                if decoder:
                    data = decoder.decompress(data)

                out_file.write(data)
        return out_file_path

    def content(self, base_url=None, buff=None):
        data = None
        if base_url:
            url = urllib.parse.urljoin(base_url, self.full_file_path.lstrip("/"))
            data = _session.get(url).content
        elif buff:
            data = buff.read(self.compressed_file_size if self.compressed else self.file_size)
        else:
            raise AttributeError("You should provide base_url or buff at least.")

        if self.compressed:
            return zlib.decompress(data, zlib.MAX_WBITS)
        return data


class PackageManifest(object):
    def __init__(self, data):
        self.files = []
        self.files_by_containing_file = defaultdict(list)
        self._parse_manifest(data)

    def download_all(self, base_url, out_dir=None):
        for f in self.files:
            f.download(base_url, out_dir=out_dir)

    def download_bin(self):
        # http://l3cdn.riotgames.com/releases/live/projects/league_client/releases/0.0.0.105/packages/files/BIN_0x00000000
        raise NotImplementedError("We didn't implement this feature yet")

    def _parse_manifest(self, data):
        entries = data.split("\r\n")

        if not entries[0].startswith("PKG"):
            raise NotImplementedError("The format of the package manifest is unknown.")

        for line in entries[1:]:
            if not line:
                continue

            file_path, containing_file, containing_file_offset, file_size, unknown = line.split(",")
            pmf = PackageManifestFile(
                file_path,
                containing_file_offset,
                file_size,
                unknown,
            )
            self.files.append(pmf)
            self.files_by_containing_file[containing_file].append(pmf)

    @staticmethod
    def from_live(base_url, project_name, project_version):
        url = urllib.parse.urljoin(base_url, "projects/{}/releases/{}/packages/files/packagemanifest".format(project_name, project_version))
        r = _session.get(url)
        return PackageManifest(r.text)
