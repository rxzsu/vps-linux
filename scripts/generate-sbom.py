#!/usr/bin/env python3
"""Generate SPDX 2.3 from a dpkg name/version[/architecture] TSV manifest."""
import argparse
import datetime
import json
import pathlib
from sbom import generate

parser = argparse.ArgumentParser()
parser.add_argument('manifest', type=pathlib.Path)
parser.add_argument('output', type=pathlib.Path)
parser.add_argument('--version', required=True)
parser.add_argument('--commit', required=True)
parser.add_argument('--created')
args = parser.parse_args()
try:
    document = generate(args.manifest.read_bytes(), args.version, args.commit,
                        args.created or datetime.datetime.now(datetime.timezone.utc).isoformat())
except (ValueError, UnicodeError) as error:
    parser.exit(1, str(error) + '\n')
args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')
print(f'Wrote {len(document["packages"])} packages to {args.output}')
