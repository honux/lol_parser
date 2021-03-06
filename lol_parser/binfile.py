import io
import os
import struct
from enum import Enum
import json

with io.open(os.path.join(os.path.dirname(__file__), "binfile.hashes.txt")) as hashes_file:
    hashes = (l.strip().split(' ', 1) for l in hashes_file)
    binfile_hashes = {str(int(h, 16)): s for h, s in hashes}


class BinFileFieldHashType(Enum):
    VECTOR3_UINT8   = 0
    BOOL            = 1
    INT8            = 2
    UINT8           = 3
    INT16           = 4
    UINT16          = 5
    INT32           = 6
    UINT32          = 7
    INT64           = 8
    UINT64          = 9
    FLOAT           = 10
    VECTOR2_FLOAT   = 11
    VECTOR3_FLOAT   = 12
    VECTOR4_FLOAT   = 13
    MATRIX_4X4      = 14
    RGBA            = 15
    STRING          = 16
    HASH            = 17
    FIELD_LIST      = 18
    STRUCT          = 19
    EMBEDDED        = 20
    HASH_LINK       = 21
    ARRAY           = 22
    MAP             = 23
    PADDING         = 24


# Bin files are pretty much a structured json file
class BinFile(object):
    def __init__(self, file_path=None, buffer=None):
        self._buffer = buffer
        self.path = file_path
        self.version = 0
        self.associated_files = []
        self.entries = {}

        if self.path != None:
            self._buffer = io.open(self.path, "rb")

        self._load_headers()

        if self.path != None:
            self._buffer.close()


    def _read(self, byte_format):
        byte_length = struct.calcsize(byte_format)
        return struct.unpack(byte_format, self._buffer.read(byte_length))


    def _load_headers(self):
            magic = self._buffer.read(4)
            if magic != b"PROP":
                raise NotImplementedError("A parser for Bin with magic '{}' is not implemented.".format(magic))

            version = self._read("<I")[0]

            if version not in [1, 2]:
                raise NotImplementedError("A parser for Bin version {} is not implemented.".format(version))
            
            if version == 2:
                self._parse_associated_files()

            self._parse_v1()
        

    def _parse_associated_files(self):
        strings_count = self._read("<I")[0]
        for _ in range(strings_count):
            string = self._parseField(BinFileFieldHashType.STRING)
            self.associated_files.append(string)


    def _parse_v1(self):
        entries_count = self._read("<I")[0]
        entries_types = []
        
        for _ in range(entries_count):
            entry_type = self._read("<I")[0]
            entries_types.append(entry_type)
        
        for entry_type in entries_types:
            strct = self._parseField(BinFileFieldHashType.STRUCT)
            strct["_hash"], strct["_data_size"] = strct["_data_size"], strct["_hash"]
            if entry_type not in self.entries:
                self.entries[entry_type] = []
            self.entries[entry_type].append(strct)
    

    def _parseFieldHeader(self):
        # Hash, Type
        return self._read("<IB")


    def _parseField(self, field_type):
        if isinstance(field_type, int):
            field_type = BinFileFieldHashType(field_type)
        
        if field_type == BinFileFieldHashType.VECTOR3_UINT8:
            return self._read("<3H")

        elif field_type == BinFileFieldHashType.BOOL:
            return self._read("<?")[0]

        elif field_type == BinFileFieldHashType.INT8:
            return self._read("<b")[0]

        elif field_type == BinFileFieldHashType.UINT8:
            return self._read("<B")[0]

        elif field_type == BinFileFieldHashType.INT16:
            return self._read("<h")[0]

        elif field_type == BinFileFieldHashType.UINT16:
            return self._read("<H")[0]

        elif field_type == BinFileFieldHashType.INT32:
            return self._read("<i")[0]

        elif field_type == BinFileFieldHashType.UINT32:
            return self._read("<I")[0]

        elif field_type == BinFileFieldHashType.INT64:
            return self._read("<q")[0]

        elif field_type == BinFileFieldHashType.UINT64:
            return self._read("<Q")[0]

        elif field_type == BinFileFieldHashType.FLOAT:
            return self._read("<f")[0]

        elif field_type == BinFileFieldHashType.VECTOR2_FLOAT:
            return self._read("<2f")

        elif field_type == BinFileFieldHashType.VECTOR3_FLOAT:
            return self._read("<3f")

        elif field_type == BinFileFieldHashType.VECTOR4_FLOAT:
            return self._read("<4f")

        elif field_type == BinFileFieldHashType.MATRIX_4X4:
            return self._read("<16f")

        elif field_type == BinFileFieldHashType.RGBA:
            return self._read("<4B")

        elif field_type == BinFileFieldHashType.STRING:
            string_length = self._read("<H")[0]
            return self._buffer.read(string_length).decode('utf-8')

        elif field_type == BinFileFieldHashType.HASH:
            hashed_val = str(self._read("<I")[0])
            return binfile_hashes.get(hashed_val, hashed_val)

        elif field_type == BinFileFieldHashType.FIELD_LIST:
            container_field_type, unknown, container_size = self._read("<BII")
            lst = []
            for _ in range(container_size):
                lst.append(self._parseField(container_field_type))
            return lst

        elif field_type == BinFileFieldHashType.STRUCT:
            struct_hash = self._read("<I")[0]
            data_size, struct_entries_count = self._read("<IH")
            strct = {"_hash": struct_hash, "_data_size": data_size, "_type": 0}

            for _ in range(struct_entries_count):
                key, entry_type = self._parseFieldHeader()
                if key in strct:
                    print("WARNING: Replacing key {} in the struct field.".format(key))
                strct[key] = self._parseField(entry_type)
            return strct
        
        elif field_type == BinFileFieldHashType.EMBEDDED:
            struct_hash = self._read("<I")[0]
            data_size, entries_count = self._read("<IH")
            strct = {"_hash": struct_hash, "_data_size": data_size, "_type": 1}

            for _ in range(entries_count):
                key, entry_type = self._parseFieldHeader()
                if key in strct:
                    print("WARNING: Replacing key {} in the embedded field.".format(key))
                strct[key] = self._parseField(entry_type)
            return strct
        
        elif field_type == BinFileFieldHashType.HASH_LINK:
            return self._read("<L")[0]

        elif field_type == BinFileFieldHashType.ARRAY:
            array_element_type, array_size = self._read("<BB")
            lst = []
            for _ in range(array_size):
                lst.append(self._parseField(array_element_type))
            return lst

        elif field_type == BinFileFieldHashType.MAP:
            key_type, value_type, unknown, map_size = self._read("<BBLL")
            strct = {}
            for _ in range(map_size):
                key = self._parseField(key_type)
                value = self._parseField(value_type)
                if key in strct:
                    print("WARNING: Replacing key {} in the map.".format(key))
                strct[key] = value
            return strct

        elif field_type == BinFileFieldHashType.PADDING:
            return self._read("<B")[0]

        else:
            raise NotImplementedError("A parser for a BinFileField with type '{}' is not implemented.".format(field_type))

    
    # Translate all known "keys hashes" to strings, returns the hash when unknown
    def translate(self):
        return BinFile._translateEntry(self.entries)


    @staticmethod
    def _translateEntry(entry):
        if isinstance(entry, dict):
            tmp = {}
            for k, v in entry.items():
                new_key = binfile_hashes.get(str(k), k)
                tmp[new_key] = BinFile._translateEntry(v)
            return tmp
        elif isinstance(entry, list):
            tmp = []
            for v in entry:
                tmp.append(BinFile._translateEntry(v))
            return tmp
        else:
            return entry


    @staticmethod
    def hash(s):
        h = 0x811c9dc5
        for b in s.encode('ascii').lower():
            h = ((h ^ b) * 0x01000193) % 0x100000000
        return h
