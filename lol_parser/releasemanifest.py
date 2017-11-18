import io
import struct

# http://l3cdn.riotgames.com/releases/live/projects/{project_name}/releases/{version}/releasemanifest

class ReleaseManifestDirectory(object):
    def __init__(self, name, sub_directories, files):
        self.name = name
        self.sub_directories = sub_directories
        self.files = files

    def __repr__(self):
        return str(self)

    def __str__(self):
        if self.sub_directories and self.files:
            return "Directory {}\nSubdirs: {}\n Files: {}\n".format(self.name, ",".join(str(d) for d in self.sub_directories), ",".join(str(f) for f in self.files))
        elif self.files:
            return "Directory {}\n Files: {}\n".format(self.name, ",".join(str(f) for f in self.files))
        return "Directory {}\nSubdirs: {}\n".format(self.name, ",".join(str(d) for d in self.sub_directories))


class ReleaseManifestFile(object):
    # According to https://github.com/LoL-Fantome/Fantome.Libraries.League, ukn1+file_type+ukn2+ukn3 (int64) is the date value.
    def __init__(self, name, version, hash_checksum, flags, size, compressed_size, ukn1, file_type, ukn2, ukn3):
        self.name             = name
        self.version          = version
        self.hash_checksum    = hash_checksum
        self.flags            = flags
        self.size             = size
        self.compressed_size  = compressed_size
        self.ukn1             = ukn1
        self.file_type        = file_type
        self.ukn2             = ukn2
        self.ukn3             = ukn3

        # Known Flags:
        # 0x01 :  Managedfiles dir (?)
        # 0x02 :  Archived/Filearchives dir (?)
        # 0x04 :  (?) #
        # 0x10 :  Compressed
        # lol_air_client: all 0
        # lol_air_client_config_euw: all 0
        # lol_launcher: all & 4
        # lol_game_client: all & 4
        # lol_game_client_en_gb: all 5

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "<File {}>".format(self.name)

class ReleaseManifest(object):
    def __init__(self, file_path):
        self.path = file_path
        self.files = []
        self.directories = []
        self.strings = []

        self._parse_manifest()

    def _parse_manifest(self):
        unparsed_directories = []
        unparsed_files = []

        with io.open(self.path, "rb") as manifest_file:
            buff = io.BufferedReader(manifest_file)

            magic = struct.unpack("<4s", buff.read(4))[0] # b"RLSM"
            self.type, self.entries = struct.unpack("<II", buff.read(8))

            v4, v3, v2, v1 = struct.unpack("<4B", buff.read(4))
            self.version = "{}.{}.{}.{}".format(v1, v2, v3, v4)

            directories_count = struct.unpack("<I", buff.read(4))[0]
            directory_struct = struct.Struct("<IIIII")
            for _ in range(directories_count):
                name_index, sub_directories_start_index, sub_directories_count, files_start_index, files_count = directory_struct.unpack(buff.read(directory_struct.size))
                unparsed_directories.append({
                    "name_index": name_index,
                    "sub_directories_start_index": sub_directories_start_index,
                    "sub_directories_count": sub_directories_count,
                    "files_start_index": files_start_index,
                    "files_count": files_count,
                })

            files_count = struct.unpack("<I", buff.read(4))[0]
            file_struct = struct.Struct("<IIQQIIIIHBB")
            for _ in range(files_count):
                name_index, version, hash_checksum_1, hash_checksum_2, flags, size, compressed_size, ukn1, file_type, ukn2, ukn3 = file_struct.unpack(buff.read(file_struct.size))
                unparsed_files.append({
                    "name_index":       name_index,
                    "version":          version,
                    "hash_checksum":    hex(hash_checksum_1) + hex(hash_checksum_2)[2:],
                    "flags":            flags,
                    "size":             size,
                    "compressed_size":  compressed_size,
                    "ukn1":             ukn1,
                    "file_type":        file_type,
                    "ukn2":             ukn2,
                    "ukn3":             ukn3,
                })

            strings_count, string_size = struct.unpack("<II", buff.read(8))
            character_struct = struct.Struct("B")
            for _ in range(strings_count):
                chars = []
                while True:
                    c = character_struct.unpack(buff.read(character_struct.size))[0]
                    if not c:
                        break
                    chars.append(chr(c))

                self.strings.append("".join(chars))

            for data in unparsed_files:
                self.files.append(
                    ReleaseManifestFile(
                        name = self.strings[data["name_index"]],
                        version = data["version"],
                        hash_checksum = data["hash_checksum"],
                        flags = data["flags"],
                        size = data["size"],
                        compressed_size = data["compressed_size"],
                        ukn1 = data["ukn1"],
                        file_type = data["file_type"],
                        ukn2 = data["ukn2"],
                        ukn3 = data["ukn3"],
                    )
                )

            for data in unparsed_directories:
                self.directories.append(
                    ReleaseManifestDirectory(
                        name = self.strings[data["name_index"]],
                        sub_directories = [],
                        files = [self.files[idx] for idx in range(data["files_count"])]
                    )
                )

            for (idx, directory) in enumerate(self.directories):
                data = unparsed_directories[idx]
                for directory_offset in range(data["sub_directories_count"]):
                    directory.sub_directories.append(self.directories[data["sub_directories_start_index"]+directory_offset])
