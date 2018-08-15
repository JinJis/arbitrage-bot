target = []
a = [{"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}]
b = [{"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}]
c = [{"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}, {"new": 1, "rev": 2}]

target.extend(a)
target.extend(b)
target.extend(c)

print(target)