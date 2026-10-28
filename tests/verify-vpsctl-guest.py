#!/usr/bin/env python3
"""Read-only acceptance inside each disposable guest, including after reboot."""
import json
import fcntl
import struct
import os
from pathlib import Path
import pty
import select
import subprocess
import termios
import time

image_version = Path('/usr/share/vps-linux/version').read_text().strip()
if tuple(map(int, image_version.removesuffix('-dev').split('.'))) < (0, 4):
    print('vpsctl acceptance: skipped for legacy image')
    raise SystemExit(0)


def run(*args, privileged=False):
    command = (['sudo', '-n'] if privileged else []) + ['/usr/bin/vpsctl', *args]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    assert result.returncode in (0, 1, 2), (args, result.returncode)
    assert not result.stderr, (args, result.stderr)
    value = json.loads(result.stdout)
    assert value['schema_version'] == 1
    return value


package_version = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'vpsctl'], text=True)
assert subprocess.check_output(['/usr/bin/vpsctl', '--version'], text=True).strip() == f'vpsctl {package_version}'
info = run('info', '--json')
assert info['vps_linux_version'] == image_version
assert info['utility_package_source_commit'] == subprocess.check_output(['dpkg-query', '-W', '-f=${X-Vpsctl-Source-Commit}', 'vpsctl'], text=True)
status = run('status', '--json')
assert status['memory_total_bytes'] > 0 and status['logical_cpus'] >= 1
assert status['root_total_bytes'] > 0
assert run('network', '--json')['interfaces']
for privileged in (False, True):
    security = run('security', '--json', privileged=privileged)
    checks = {c['id']: c['level'] for c in security['checks']}
    for key in ('upgrade_origins', 'automatic_reboot', 'periodic_security_updates'):
        assert checks[key] == 'ok', (key, checks)
    if privileged:
        for key in ('passwordauthentication', 'kbdinteractiveauthentication', 'permitrootlogin', 'pubkeyauthentication'):
            assert checks[key] == 'ok', (key, checks)
assert not any(c['level'] == 'fail' for c in run('doctor', '--json')['checks'])
plain = subprocess.run(['/usr/bin/vpsctl'], stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
assert plain.returncode == 2 and b'status --json' in plain.stderr
# Exercise terminal ownership as the ordinary SSH user, never with sudo.
master, slave = pty.openpty()
original = termios.tcgetattr(slave)
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
process = subprocess.Popen(['/usr/bin/vpsctl'], stdin=slave, stdout=slave, stderr=slave,
                           env={**os.environ, 'TERM': 'xterm'})
try:
    deadline = time.monotonic() + 20
    output = bytearray()
    while b'hostname' not in output and time.monotonic() < deadline:
        if select.select([master], [], [], 0.2)[0]:
            output.extend(os.read(master, 65536))
    assert b'hostname' in output, 'TUI did not render'
    os.write(master, b'q')
    assert process.wait(timeout=10) == 0
    assert termios.tcgetattr(slave) == original, 'TUI left terminal settings changed'
finally:
    if process.poll() is None:
        process.kill()
        process.wait()
    os.close(master)
    os.close(slave)
print(f'vpsctl {package_version}: installed package, JSON, security policy, offline doctor and TUI passed')
