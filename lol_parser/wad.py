import hashlib
import io
import os
import os.path
import struct
import zlib
import xxhash
import zstd # https://github.com/indygreg/python-zstandard
from pprint import pprint

CHUNK_SIZE = 1024

class WadFileHeader(object):
    def __init__(self, hashed_file_name, offset, compressed_file_size, file_size, compressed, extra_args):
        self.hashed_file_name = hashed_file_name
        self.offset = offset
        self.compressed_file_size = compressed_file_size
        self.file_size = file_size
        self.compressed = compressed
        self.extra = extra_args

    def extract(self, directory, buff):
        buff.seek(self.offset, io.SEEK_SET)

        decoder = None
        if self.compressed:
            magic = buff.peek(2)[:2]
            if magic == b"\x1f\x8b": # GZIP Magic
                decoder = zlib.decompressobj(zlib.MAX_WBITS|16)
            elif magic == b"\x28\xb5": # ZSTD Magic
                decoder = zstd.ZstdDecompressor().decompressobj()
            else:
                raise NotImplementedError("A decompressor for magic {} is not implemented.".format(magic))

        hasher = None
        expected_hash = ""
        if "sha256" in self.extra:
            hasher = hashlib.sha256()
            expected_hash = self.extra["sha256"]

        file_name = os.path.join(directory, self.hashed_file_name)
        with io.open(file_name, "wb") as out_file:
            data_left = self.compressed_file_size if self.compressed else self.file_size
            while True:
                if data_left <= 0:
                    break

                data_size = min(CHUNK_SIZE, data_left)
                data_left -= data_size
                data = buff.read(data_size)

                # Future note to self: Hash *before* decompressing
                if hasher:
                    hasher.update(data)

                if decoder:
                    data = decoder.decompress(data)

                out_file.write(data)

        if hasher:
            calculed_hash = int.from_bytes(hasher.digest()[0:8], byteorder='little')
            if expected_hash != calculed_hash:
                print("WARNING: Expected hash '{}', calculed hash '{}'. \nDetails:\n{}".format(hex(expected_hash), hex(calculed_hash), pprint(vars(self))))

    def content(self, buff):
        buff.seek(self.offset, io.SEEK_SET)

        if self.compressed:
            data = buff.read(self.compressed_file_size)
            magic = buff.peek(2)[:2]
            if magic == b"\x1f\x8b": # GZIP Magic
                return zlib.decompress(data, zlib.MAX_WBITS|16)
            elif magic == b"\x28\xb5": # ZSTD Magic
                return zstd.ZstdDecompressor().decompress(data)
            else:
                raise NotImplementedError("A decompressor for magic {} is not implemented.".format(magic))

        return buff.read(self.file_size)


class WadFile(object):
    def __init__(self, file_path):
        self.path = file_path
        self.file_headers = {}
        self.version = 0
        self._load_headers()

    def extract_file(self, hashed_file_name, directory):
        os.makedirs(directory, exist_ok=True)
        hashed_file_name = hashed_file_name.lower()
        if hashed_file_name not in self.file_headers:
            print("The file {} is not known on this WAD.".format(hashed_file_name))
        else:
            with io.open(self.path, "rb") as buff:
                self.file_headers[hashed_file_name].extract(directory, buff)

    def extract_all(self, directory):
        os.makedirs(directory, exist_ok=True)
        with io.open(self.path, "rb") as buff:
            for file_header in self.file_headers.values():
                file_header.extract(directory, buff)

    def _load_headers(self):
        # https://docs.python.org/3/library/struct.html#format-characters
        with io.open(self.path, "rb") as buff:
            ukn, ukn = struct.unpack("cc", buff.read(2)) # int16
            version_major, version_minor = struct.unpack("BB", buff.read(2)) # int8

            files_count = 0
            if version_major == 1:
                self.file_headers = _parse_wad_v1(buff)
            elif version_major == 2:
                self.file_headers = _parse_wad_v2(buff)
            elif version_major == 3:
                self.file_headers = _parse_wad_v3(buff)
            else:
                raise NotImplementedError("A parser for wad version {} is not implemented.".format(version_major))

            self.version = version_major

    @staticmethod
    def hash(string, directory=None):
        hashed_name = xxhash.xxh64(string.lower(), seed=0).hexdigest()
        hashed_name = ensure_16_digits(hashed_name)

        if directory:
            return os.path.join(directory, hashed_name)
        return hashed_name

def _parse_wad_v1(buff):
    entry_header_offset, entry_header_cell_size, files_count = struct.unpack("<HHI", buff.read(8))

    wad_file_struct = struct.Struct("<QIIII")
    file_headers = {}
    for _ in range(files_count):
        path_hash, offset, compressed_file_size, file_size, compressed = wad_file_struct.unpack(buff.read(wad_file_struct.size))

        hashed_file_name = hex(path_hash)[2:]
        hashed_file_name = ensure_16_digits(hashed_file_name)

        file_headers[hashed_file_name] = WadFileHeader(
            hashed_file_name,
            offset,
            compressed_file_size,
            file_size,
            compressed,
            {}
        )

    return file_headers

def _parse_wad_v2(buff):
    ECDSA_length = struct.unpack("<B", buff.read(1))[0]
    ECDSA = struct.unpack("<{}b".format(ECDSA_length), buff.read(ECDSA_length))
    if (83-ECDSA_length) > 0: # Padding
        buff.read(83-ECDSA_length)

    files_checksum, entry_header_offset, entry_header_cell_size, files_count = struct.unpack("<QHHI", buff.read(16))

    wad_file_struct = struct.Struct("<QIIIBBBBQ")
    file_headers = {}
    for _ in range(files_count):
        path_hash, offset, compressed_file_size, file_size, compressed, duplicate, ukn1, ukn2, sha256 = wad_file_struct.unpack(buff.read(wad_file_struct.size))

        hashed_file_name = hex(path_hash)[2:]
        hashed_file_name = ensure_16_digits(hashed_file_name)

        file_headers[hashed_file_name] = WadFileHeader(
            hashed_file_name,
            offset,
            compressed_file_size,
            file_size,
            compressed,
            {
                "duplicate":    duplicate,
                "ukn1":         ukn1,
                "ukn2":         ukn2,
                "sha256":       sha256,
            }
        )

    return file_headers

def _parse_wad_v3(buff):
    ECDSA = struct.unpack("<256b", buff.read(256))

    files_checksum, files_count = struct.unpack("<QI", buff.read(12))

    wad_file_struct = struct.Struct("<QIIIBBBBQ")
    file_headers = {}
    for _ in range(files_count):
        path_hash, offset, compressed_file_size, file_size, compressed, duplicate, ukn1, ukn2, sha256 = wad_file_struct.unpack(buff.read(wad_file_struct.size))

        hashed_file_name = hex(path_hash)[2:]
        hashed_file_name = ensure_16_digits(hashed_file_name)

        file_headers[hashed_file_name] = WadFileHeader(
            hashed_file_name,
            offset,
            compressed_file_size,
            file_size,
            compressed,
            {
                "duplicate":    duplicate,
                "ukn1":         ukn1,
                "ukn2":         ukn2,
                "sha256":       sha256,
            }
        )

    return file_headers

def ensure_16_digits(string):
    if len(string) < 16:
        string = ("0000000000000000" + string)[-16:].lower()
    return string
