#!/usr/bin/env python3
"""Validate qemu-img JSON before using an image as an immutable backing file."""
import json
import sys


def validate(info):
    if not isinstance(info, dict):
        raise ValueError('qemu-img info must be an object')
    if info.get('format') != 'qcow2':
        raise ValueError('expected QCOW2 format')
    if info.get('virtual-size') != 8 * 1024**3:
        raise ValueError('expected an 8 GiB virtual disk')
    if any(key in info for key in ('backing-filename', 'full-backing-filename', 'data-file')):
        raise ValueError('external backing/data files are forbidden')
    data = info.get('format-specific', {}).get('data', {})
    if info.get('encrypted') or data.get('encrypt') or data.get('data-file'):
        raise ValueError('encrypted or external-data images are unsupported')
    if info.get('dirty-flag') or data.get('corrupt'):
        raise ValueError('dirty/corrupt image')


if __name__ == '__main__':
    try:
        validate(json.load(sys.stdin))
    except (ValueError, TypeError, AttributeError) as error:
        sys.exit(str(error))
