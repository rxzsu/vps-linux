#!/usr/bin/env python3
"""Exercise the actual TUI in a Linux PTY, including termios restoration."""
import fcntl
import os
import pathlib
import pty
import select
import struct
import subprocess
import termios
import time
import unittest

BINARY = pathlib.Path(__file__).resolve().parents[1] / 'target/debug/vpsctl'


class Terminal(unittest.TestCase):
    def exercise(self, quit_key):
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 100, 0, 0))
        process = subprocess.Popen([str(BINARY)], stdin=slave, stdout=slave, stderr=slave,
                                   env={**os.environ, 'TERM': 'xterm-256color'})
        output = bytearray()
        def wait_for(token):
            deadline = time.monotonic() + 10
            while token not in output and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    output.extend(os.read(master, 65536))
            self.assertIn(token, output)
        try:
            wait_for(b'hostname')
            os.write(master, b'\t')
            wait_for(b'utility_version')
            os.write(master, b'r')
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            os.write(master, quit_key)
            self.assertEqual(process.wait(timeout=10), 0)
            self.assertEqual(termios.tcgetattr(slave), original)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)

    def test_navigation_refresh_resize_and_quit(self):
        self.exercise(b'q')

    def test_control_c_restores_terminal(self):
        self.exercise(b'\x03')


if __name__ == '__main__':
    unittest.main()
