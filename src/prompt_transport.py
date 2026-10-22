"""Lossless JSON transport for repeated card keys/strings, not clinical filtering."""
from collections import Counter
import string


def pack(cards):
    keys, texts, shapes = Counter(), Counter(), Counter()

    def count(value):
        if isinstance(value, dict):
            shapes[tuple(value)] += 1
            for key, item in value.items():
                keys[key] += 1
                count(item)
        elif isinstance(value, list):
            for item in value:
                count(item)
        elif isinstance(value, str):
            texts[value] += 1

    count(cards)
    alphabet = string.ascii_letters
    names = sorted(key for key, n in keys.items() if len(key) > 5 and n >= 3)
    key_codes = {key: alphabet[i] if i < len(alphabet) else 'k'+str(i)
                 for i, key in enumerate(names)}
    # Reserve aliases so that a canonical short key cannot collide with one.
    key_codes = {key: code for key, code in key_codes.items() if code not in keys}
    values = sorted(text for text, n in texts.items() if (len(text) >= 24 and n >= 2) or (len(text) >= 10 and n >= 3))
    text_codes = {text: i for i, text in enumerate(values)}
    rows = sorted(shape for shape, n in shapes.items() if len(shape) >= 4 and n >= 3)
    row_codes = {shape: i for i, shape in enumerate(rows)}

    used_keys = set()
    def encode(value):
        if isinstance(value, dict):
            if tuple(value) in row_codes:
                return ['@o', row_codes[tuple(value)], *[encode(item) for item in value.values()]]
            used_keys.update(key for key in value if key in key_codes)
            return {key_codes.get(key, key): encode(item) for key, item in value.items()}
        if isinstance(value, list):
            return [encode(item) for item in value]
        if isinstance(value, str) and value in text_codes:
            return '@'+str(text_codes[value])
        return value

    encoded = encode(cards)
    return {'key_legend': {code: key for key, code in key_codes.items() if key in used_keys}, 'row_columns': rows,
            'string_table': values, 'cards': encoded}


def unpack(packed):
    """Verification utility: reconstruct every supplied card field exactly."""
    def decode(value):
        if isinstance(value, str) and value.startswith('@') and value[1:].isdigit():
            return packed['string_table'][int(value[1:])]
        if isinstance(value, dict):
            if set(value) == {'@'}:
                return packed['string_table'][value['@']]
            return {packed['key_legend'].get(key, key): decode(item) for key, item in value.items()}
        if isinstance(value, list):
            if len(value) >= 2 and value[0] == '@o':
                return dict(zip(packed['row_columns'][value[1]], [decode(item) for item in value[2:]], strict=True))
            return [decode(item) for item in value]
        return value
    return decode(packed['cards'])
