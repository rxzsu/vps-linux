#!/usr/bin/env python3
"""Reject a package with a glibc floor newer than Debian 13's glibc 2.41."""
import re
import subprocess
import sys


def compatible(dependencies):
    matches = re.findall(r'libc6\s*\(>=\s*([^\s)]+)\)', dependencies)
    return len(matches) == 1 and subprocess.run(
        ['dpkg', '--compare-versions', matches[0], 'le', '2.41'],
        capture_output=True, check=False,
    ).returncode == 0


if __name__ == '__main__':
    if len(sys.argv) != 2 or not compatible(sys.argv[1]):
        sys.exit('Package ABI is unknown or newer than Debian 13; build with a Debian 13-compatible sysroot/toolchain.')
