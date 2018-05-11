import ast
import numpy as np

def walk_data_structure(d, fn, path=None):
    path = path or []

    _d = fn(d, path)
    if id(d) != id(_d):
        return _d

    if isinstance(d, dict):
        d = d.copy()
        for k in d:
            v = d[k]
            d[k] = walk_data_structure(v, fn, path + [k])

        return d

    elif isinstance(d, (list, tuple)):
        d = d.copy()
        for i, v in enumerate(d):
            d[i] = walk_data_structure(v, fn, path + [i])

        return d

    else:
        return fn(d, path)

def to_python_type(data):
    def _to_native(v, path):
        if isinstance(v, np.ndarray):
            v = v.tolist()
        elif type(v).__module__ == 'numpy':
            v = v.item()

        return v

    data = walk_data_structure(data, _to_native)

    return data

def liteval(x):
    try:
        x = ast.literal_eval(x)
    except Exception:
        pass

    return x

def get_loggable_params(kwargs):
    _kwargs = {}

    for k, v in kwargs.items():
        if not isinstance(v, (int, float, np.number, str)):
            continue

        if isinstance(v, str) and len(v) > 250:
            continue

        _kwargs[k] = v

    return _kwargs
