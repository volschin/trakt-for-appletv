# https://python.plainenglish.io/a-better-python-named-tuple-6e239755e1b9
import operator
import uuid


def make_named_tuple_type(*member_names):
    name = f"Anonymous_{str(uuid.uuid4()).replace('-', '_')}"
    T = type(name, (tuple,), {})
    for i, k in enumerate(member_names):
        setattr(T, k, property(operator.itemgetter(i)))

    def new(cls, **kwargs):
        return tuple.__new__(T, (kwargs[k] for k in member_names))

    setattr(T, '__new__', new)

    def from_object(obj):
        return T(**{k: getattr(obj, k) for k in member_names})

    setattr(T, 'from_object', staticmethod(from_object))

    def to_dict(self):
        return {k: getattr(self, k) for k in member_names}

    setattr(T, 'to_dict', to_dict)

    def __str__(self):
        return str(self.to_dict())

    setattr(T, '__str__', __str__)
    return T


def make_named_tuple_instance(**kwargs):
    T = make_named_tuple_type(kwargs.keys())
    return T(**kwargs)
