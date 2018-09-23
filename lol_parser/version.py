
class Version(object):
    def __init__(self, raw_string):
        self.raw = raw_string
        self.parts = tuple(int(x) for x in self.raw.split("."))

    def format(self, parts_count):
        p_size = len(self.parts)
        if parts_count < p_size:
            self.parts = self.parts[0:parts_count]
        elif parts_count > p_size:
            for _ in range(parts_count-p_size):
                self.parts.append(0)

        return self

    def __str__(self):
        return self.raw

    def __repr__(self):
        return "{}({!r})".format(self.__class__, self.raw)

    def __lt__(self, other):
        return other and (self.parts < other.parts)

    def __le__(self, other):
        return other and (self.parts <= other.parts)

    def __eq__(self, other):
        if isinstance(other, Version):
            return self.raw == other.raw
        elif isinstance(other, str):
            return self.raw == other
        elif isinstance(other, tuple) or isinstance(other, list):
            return self.parts == other
        elif isinstance(other, int):
            return self.parts == tuple(other,)
        return False

    def __gt__(self, other):
        return other and (self.parts > other.parts)

    def __ge__(self, other):
        return other and (self.parts >= other.parts)

    def __ne__(self, other):
        return other and (self.parts != other.parts)


'''
    TEST
from version import Version
v1 = Version("1.1.1")
v2 = Version("1.1.2")

assert(not (v1 > v1))
assert(v1 >= v1)
assert(not(v1 < v1))
assert(v1 <= v1)
assert(v1 == v1)
assert(not(v1 != v1))

assert(not (v1 > v2))
assert(not (v1 >= v2))
assert(v1 < v2)
assert(v1 <= v2)
assert(not (v1 == v2))
assert(v1 != v2)

assert(v2 > v1)
assert(v2 >= v1)
assert(not (v2 < v1))
assert(not (v2 <= v1))
assert(not (v2 == v1))
assert(v2 != v1)

v3 = Version("1.1.1.0")
v4 = Version("1.1")

assert(not (v1 > v3))
assert(v1 >= v3)
assert(not(v1 < v3))
assert(v1 <= v3)
assert(v1 == v3)
assert(not(v1 != v3))

assert(v3 > v4)
assert(v3 >= v4)
assert(not (v3 < v4))
assert(not (v3 <= v4))
assert(not (v3 == v4))
assert(v3 != v4)
'''
