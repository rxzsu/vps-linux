#!/usr/bin/env bash
# Run remotely on the grown instance. The overlay was created larger than the
# image's 8 GiB virtual disk, so cloud-init growpart must expand partition and
# filesystem. A disk that did not grow is a failure, not a skipped check.
set -Eeuo pipefail
minimum=$((9 * 1024 * 1024 * 1024))
root_source=$(findmnt -n -o SOURCE /)
[[ -b $root_source ]] || { echo "Root source is not a block device: $root_source" >&2; exit 1; }
partition_bytes=$(sudo -n blockdev --getsize64 "$root_source")
filesystem_bytes=$(findmnt -n -b -o SIZE /)
if (( partition_bytes < minimum )); then
    echo "Root partition was not grown: $partition_bytes bytes" >&2
    exit 1
fi
if (( filesystem_bytes < minimum )); then
    echo "Root filesystem was not grown: $filesystem_bytes bytes" >&2
    exit 1
fi
# The GPT backup header must have moved to the new end of the disk.
parent_name=$(lsblk -n -o PKNAME "$root_source")
[[ -n $parent_name ]] || { echo 'Could not determine the parent disk.' >&2; exit 1; }
disk_bytes=$(sudo -n blockdev --getsize64 "/dev/$parent_name")
if (( disk_bytes < minimum )); then
    echo "Virtual disk was not enlarged: $disk_bytes bytes" >&2
    exit 1
fi
printf 'Disk growth: disk=%s partition=%s filesystem=%s bytes\n' \
    "$disk_bytes" "$partition_bytes" "$filesystem_bytes"

sector_bytes=$(sudo -n blockdev --getss "/dev/$parent_name")
sudo -n /usr/bin/python3 - "/dev/$parent_name" "$disk_bytes" "$sector_bytes" <<'PY_GPT'
import struct, sys, zlib
path, size, sector = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
last_lba = size // sector - 1
with open(path, 'rb') as disk:
    headers = []
    for location in (1, last_lba):
        disk.seek(location * sector)
        header = bytearray(disk.read(sector))
        assert header[:8] == b'EFI PART', 'Missing GPT header at current disk boundary'
        length, crc = struct.unpack_from('<II', header, 12)
        assert 92 <= length <= sector, 'Invalid GPT header length'
        struct.pack_into('<I', header, 16, 0)
        assert zlib.crc32(header[:length]) == crc, 'GPT header CRC mismatch'
        current, alternate = struct.unpack_from('<QQ', header, 24)
        assert current == location, 'GPT header is at the wrong LBA'
        headers.append((current, alternate))
assert headers == [(1, last_lba), (last_lba, 1)], 'GPT backup was not relocated'
print('Primary and backup GPT headers/CRCs match the expanded disk boundaries')
PY_GPT
