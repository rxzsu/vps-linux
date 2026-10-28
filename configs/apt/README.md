# Debian Trixie public archive keys

`debian-trixie.asc` contains public keys only, exported from the Debian-installed `debian-archive-keyring` package version `2025.1`. Sources were its `debian-archive-trixie-{automatic,security-automatic,stable}.pgp` keyrings. The export was made with an isolated empty GnuPG home and explicit keyring paths; no user keyrings or private keys were accessed.

Primary fingerprints:

- Archive automatic: `04B54C3CDCA79751B16BC6B5225629DF75B188BD`
- Security archive: `5E04A1E3223A19A20706E20F9904613D4CCE68C6`
- Stable release: `41587F7DB8C774BCCF131416762F67A0B2C39DE4`

Authoritative reference: https://ftp-master.debian.org/keys.html

These public trust roots let Noble hosts bootstrap Trixie even if their packaged keyring predates Debian 13. `mmdebstrap`/APT must still verify repository signatures and package checksums. TLS verification remains enabled. The installed guest's `debian-archive-keyring` package manages subsequent APT trust.

Key rotation/revocation requires deliberate review against Debian's published announcements and fingerprints. Never disable signature verification or substitute an unreviewed key to work around an error. Keys are not package-version pins and do not make builds byte-reproducible.
