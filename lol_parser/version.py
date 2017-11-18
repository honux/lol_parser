
class Version(object):
    def __init__(self, raw_string):
        tmp = raw_string.split(".")
        self.parts = [int(s) for s in tmp if s]

    def format(self, parts_count):
        p_size = len(self.parts)
        if parts_count < p_size:
            self.parts = self.parts[0:parts_count]
        elif parts_count > p_size:
            for _ in range(parts_count-p_size):
                self.parts.append(0)

        return self

    def __str__(self):
        return ".".join(str(x) for x in self.parts)

    def __repr__(self):
        return "%s(%s)" % (self.__class__, str(self))

    def __lt__(self, other):
        if not other:
            return False

        p1_size = len(self.parts)
        p2_size = len(other.parts)

        for idx in range(max(p1_size, p2_size)):
            v1 = 0 if idx >= p1_size else self.parts[idx]
            v2 = 0 if idx >= p2_size else other.parts[idx]

            if v1 < v2:
                return True

        return False

    def __le__(self, other):
        if not other:
            return False

        p1_size = len(self.parts)
        p2_size = len(other.parts)
        max_size = max(p1_size, p2_size)
        equal = True

        for idx in range(max_size):
            v1 = 0 if idx >= p1_size else self.parts[idx]
            v2 = 0 if idx >= p2_size else other.parts[idx]

            if v1 < v2:
                return True

            if v1 != v2:
                equal = False

        if equal:
            return True

        return False

    def __eq__(self, other):
        if not other:
            return False

        p1_size = len(self.parts)
        p2_size = len(other.parts)

        for idx in range(max(p1_size, p2_size)):
            v1 = 0 if idx >= p1_size else self.parts[idx]
            v2 = 0 if idx >= p2_size else other.parts[idx]

            if v1 != v2:
                return False

        return True

    def __gt__(self, other):
        return other and (other < self)

    def __ge__(self, other):
        return other and (other <= self)

    def __ne__(self, other):
        return other and not (self == other)


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
