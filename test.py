import copy

origin = {"a": 1, "b": 3, "c": {}}
copied = origin
deep = copy.deepcopy(origin)

copied["c"]["tester"] = 10
print(copied)
print(origin)
