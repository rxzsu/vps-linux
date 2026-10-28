use crate::{Check, Level, Report, classify_unit};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    fs,
    io::Read,
    path::Path,
    process::{Command, Stdio},
};

const LIMIT: u64 = 262_144;

// Never invoke a shell, search PATH, elevate privileges, or return raw stderr.
// GNU timeout also kills stuck helper processes; output is capped per stream.
pub(crate) fn probe(program: &str, args: &[&str]) -> Option<String> {
    let mut child = Command::new("/usr/bin/timeout")
        .args(["--kill-after=1s", "4s", program])
        .args(args)
        .env("LC_ALL", "C")
        .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
        .env_remove("DBUS_SYSTEM_BUS_ADDRESS")
        .env_remove("SYSTEMD_BUS_ADDRESS")
        .env_remove("APT_CONFIG")
        .env("SYSTEMD_PAGER", "")
        .env("SYSTEMD_COLORS", "0")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .ok()?;
    let errors = child.stderr.take()?;
    let errors = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        errors
            .take(LIMIT + 1)
            .read_to_end(&mut bytes)
            .map(|_| bytes)
    });
    let mut bytes = Vec::new();
    let result = child.stdout.take()?.take(LIMIT + 1).read_to_end(&mut bytes);
    if result.is_err() || bytes.len() as u64 > LIMIT {
        let _ = child.kill();
        let _ = child.wait();
        let _ = errors.join();
        return None;
    }
    let status = child.wait().ok()?;
    let errors = errors.join().ok()?.ok()?;
    // Warnings can mean incomplete configuration (notably apt-config).
    if !status.success() || !errors.is_empty() || bytes.len() as u64 > LIMIT {
        return None;
    }
    String::from_utf8(bytes).ok()
}

fn read(path: impl AsRef<Path>) -> Option<String> {
    let mut bytes = Vec::new();
    fs::File::open(path)
        .ok()?
        .take(LIMIT + 1)
        .read_to_end(&mut bytes)
        .ok()?;
    if bytes.len() as u64 > LIMIT {
        return None;
    }
    String::from_utf8(bytes).ok()
}

pub fn parse_os_release(text: &str) -> BTreeMap<String, String> {
    text.lines()
        .filter_map(|line| {
            let (key, value) = line.split_once('=')?;
            if !["ID", "VERSION_ID", "PRETTY_NAME"].contains(&key) {
                return None;
            }
            let value = value.trim();
            let value = if value.starts_with('"') && value.ends_with('"') && value.len() >= 2 {
                value[1..value.len() - 1]
                    .replace("\\\"", "\"")
                    .replace("\\\\", "\\")
            } else if value.starts_with('\'') && value.ends_with('\'') && value.len() >= 2 {
                value[1..value.len() - 1].to_owned()
            } else if value.contains(['"', '\'']) {
                return None;
            } else {
                value.to_owned()
            };
            Some((key.to_owned(), value))
        })
        .collect()
}

pub fn mem_bytes(text: &str, field: &str) -> Option<u64> {
    let line = text.lines().find(|l| l.starts_with(&format!("{field}:")))?;
    let mut parts = line.split_whitespace();
    parts.next()?;
    let number = parts.next()?.parse::<u64>().ok()?;
    if parts.next()? != "kB" {
        return None;
    }
    number.checked_mul(1024)
}

pub fn uptime(text: &str) -> Option<f64> {
    let value = text.split_whitespace().next()?.parse::<f64>().ok()?;
    (value.is_finite() && value >= 0.0).then_some(value)
}

pub fn cpu_count(text: &str) -> Option<usize> {
    let mut count = 0usize;
    let mut previous = None;
    for range in text.trim().split(',') {
        let (first, last) = range.split_once('-').unwrap_or((range, range));
        let first = first.parse::<usize>().ok()?;
        let last = last.parse::<usize>().ok()?;
        if last < first || previous.is_some_and(|p| first <= p) {
            return None;
        }
        count = count.checked_add(last.checked_sub(first)?.checked_add(1)?)?;
        previous = Some(last);
    }
    (count > 0).then_some(count)
}

#[derive(Debug, Serialize)]
pub struct Status {
    pub schema_version: u32,
    pub hostname: Option<String>,
    pub kernel: Option<String>,
    pub os: Option<String>,
    pub logical_cpus: Option<usize>,
    pub load_average: Option<[f64; 3]>,
    pub uptime_seconds: Option<f64>,
    pub memory_total_bytes: Option<u64>,
    pub memory_available_bytes: Option<u64>,
    pub root_total_bytes: Option<u64>,
    pub root_available_bytes: Option<u64>,
}

pub fn status() -> Status {
    let mem = read("/proc/meminfo").unwrap_or_default();
    let cpu = read("/sys/devices/system/cpu/online").and_then(|v| cpu_count(&v));
    let disk = probe("/usr/bin/df", &["-B1", "--output=size,avail", "/"]).and_then(|s| {
        let nums: Vec<u64> = s
            .split_whitespace()
            .skip(2)
            .filter_map(|v| v.parse().ok())
            .collect();
        (nums.len() == 2 && nums[1] <= nums[0]).then(|| (nums[0], nums[1]))
    });
    let load = read("/proc/loadavg").and_then(|v| {
        let n: Vec<f64> = v
            .split_whitespace()
            .take(3)
            .map(str::parse)
            .collect::<Result<_, _>>()
            .ok()?;
        (n.len() == 3 && n.iter().all(|v| v.is_finite() && *v >= 0.0)).then(|| [n[0], n[1], n[2]])
    });
    Status {
        schema_version: 1,
        hostname: read("/proc/sys/kernel/hostname").map(|s| s.trim().to_owned()),
        kernel: read("/proc/sys/kernel/osrelease").map(|s| s.trim().to_owned()),
        os: read("/etc/os-release").and_then(|s| parse_os_release(&s).remove("PRETTY_NAME")),
        logical_cpus: cpu,
        load_average: load,
        uptime_seconds: read("/proc/uptime").and_then(|s| uptime(&s)),
        memory_total_bytes: mem_bytes(&mem, "MemTotal"),
        memory_available_bytes: mem_bytes(&mem, "MemAvailable"),
        root_total_bytes: disk.map(|d| d.0),
        root_available_bytes: disk.map(|d| d.1),
    }
}

#[derive(Debug, Serialize)]
pub struct Info {
    pub schema_version: u32,
    pub utility_version: &'static str,
    pub utility_package_source_commit: Option<String>,
    pub vps_linux_version: Option<String>,
    pub os: BTreeMap<String, String>,
    pub architecture: &'static str,
    pub image_build_metadata: &'static str,
}

pub fn info() -> Info {
    let package_source = probe(
        "/usr/bin/dpkg-query",
        &["-W", "-f=${Version}\t${X-Vpsctl-Source-Commit}", "vpsctl"],
    )
    .and_then(|s| {
        let (version, commit) = s.split_once('\t')?;
        (version == env!("CARGO_PKG_VERSION")
            && commit.len() == 40
            && commit.bytes().all(|b| b.is_ascii_hexdigit()))
        .then(|| commit.to_owned())
    });
    Info {
        schema_version: 1,
        utility_version: env!("CARGO_PKG_VERSION"),
        utility_package_source_commit: package_source,
        vps_linux_version: read("/usr/share/vps-linux/version")
            .map(|s| s.trim().to_owned())
            .filter(|s| !s.is_empty()),
        os: read("/etc/os-release")
            .map(|s| parse_os_release(&s))
            .unwrap_or_default(),
        architecture: std::env::consts::ARCH,
        image_build_metadata: "Build commit/checksum are distributed in the image bundle; not inferred from the running guest.",
    }
}

pub(crate) fn check(id: &'static str, level: Level, summary: impl Into<String>) -> Check {
    Check {
        id,
        level,
        summary: summary.into(),
    }
}

pub fn doctor() -> Report {
    let mut checks = Vec::new();
    for unit in [
        "systemd-networkd.service",
        "systemd-resolved.service",
        "systemd-timesyncd.service",
        "docker.service",
        "qemu-guest-agent.service",
    ] {
        let state = probe(
            "/usr/bin/systemctl",
            &["show", "--property=ActiveState", "--value", unit],
        );
        checks.push(check(
            unit,
            classify_unit(state.as_deref()),
            state
                .map(|s| format!("Service state: {}", s.trim()))
                .unwrap_or("Service unavailable or not readable".into()),
        ));
    }
    let route = probe("/usr/sbin/ip", &["-j", "route", "show", "default"])
        .and_then(|s| serde_json::from_str::<Vec<serde_json::Value>>(&s).ok());
    checks.push(match route {
        Some(routes) if !routes.is_empty() => check(
            "default_route",
            Level::Ok,
            "IPv4 default route exists; external connectivity is not verified",
        ),
        Some(_) => check("default_route", Level::Warning, "No IPv4 default route"),
        None => check("default_route", Level::Unknown, "Route data unavailable"),
    });
    let dns = read("/etc/resolv.conf");
    checks.push(match dns {
        Some(s)
            if s.lines().any(|l| {
                let mut p = l.split_whitespace();
                p.next() == Some("nameserver")
                    && p.next()
                        .is_some_and(|v| v.parse::<std::net::IpAddr>().is_ok())
            }) =>
        {
            check(
                "dns_config",
                Level::Ok,
                "Resolver address configured; DNS resolution is not verified",
            )
        }
        Some(_) => check(
            "dns_config",
            Level::Warning,
            "No valid nameserver in resolv.conf",
        ),
        None => check(
            "dns_config",
            Level::Unknown,
            "Resolver configuration unavailable",
        ),
    });
    let sync = probe(
        "/usr/bin/timedatectl",
        &["show", "--property=NTPSynchronized", "--value"],
    );
    checks.push(match sync.as_deref().map(str::trim) {
        Some("yes") => check("ntp_sync", Level::Ok, "Clock synchronized"),
        Some("no") => check("ntp_sync", Level::Warning, "Clock is not synchronized"),
        _ => check(
            "ntp_sync",
            Level::Unknown,
            "Time synchronization not readable",
        ),
    });
    // Do not connect to the Docker socket: membership grants root-equivalent access.
    checks.push(check(
        "docker_api",
        Level::Unknown,
        "Docker service state checked; daemon API, containers and registry access not probed",
    ));
    Report {
        schema_version: 1,
        section: "doctor",
        checks,
    }
}

pub fn ssh_policy(text: Option<&str>) -> Vec<Check> {
    let expected = [
        ("passwordauthentication", "no"),
        ("kbdinteractiveauthentication", "no"),
        ("permitrootlogin", "no"),
        ("pubkeyauthentication", "yes"),
    ];
    expected
        .into_iter()
        .map(|(key, safe)| {
            let value = text.and_then(|s| {
                s.lines().find_map(|l| {
                    let (k, v) = l.split_once(' ')?;
                    (k == key).then_some(v.trim())
                })
            });
            match value {
                Some(v) if v == safe => {
                    check(key, Level::Ok, format!("sshd default-context {key}: {v}"))
                }
                Some("yes" | "no" | "prohibit-password" | "forced-commands-only") => check(
                    key,
                    Level::Fail,
                    format!("sshd default-context {key} differs from VPS Linux policy"),
                ),
                _ => check(
                    key,
                    Level::Unknown,
                    format!("sshd effective {key} unavailable (permissions or missing sshd)"),
                ),
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn missing_files_helpers_and_excess_output_are_unknown() {
        assert!(read("/proc/vpsctl-nonexistent-data").is_none());
        assert!(probe("/usr/bin/vpsctl-nonexistent-helper", &[]).is_none());
        assert!(probe("/usr/bin/head", &["-c", "262145", "/dev/zero"]).is_none());
    }
    #[test]
    fn parses_only_public_os_fields_without_execution() {
        let p = parse_os_release(
            "ID=debian\nPRETTY_NAME=\"Debian GNU/Linux 13\"\nSECRET=hidden\nVERSION_ID='13'\nBAD\n",
        );
        assert_eq!(p["ID"], "debian");
        assert_eq!(p["VERSION_ID"], "13");
        assert_eq!(p.len(), 3);
        assert!(!parse_os_release("ID=\"broken").contains_key("ID"));
    }
    #[test]
    fn cpu_ranges_reject_malformed_and_overlapping_data() {
        assert_eq!(cpu_count("0-3,8,10-11\n"), Some(7));
        for value in ["", "3-1", "0-3,2", "oops", "0-", "1,,2"] {
            assert_eq!(cpu_count(value), None);
        }
    }
    #[test]
    fn malformed_memory_is_unknown() {
        assert_eq!(mem_bytes("MemTotal: 1024 kB", "MemTotal"), Some(1_048_576));
        for value in [
            "",
            "MemTotal: nope kB",
            "MemTotal: 1 MB",
            "MemTotal: 18446744073709551615 kB",
        ] {
            assert_eq!(mem_bytes(value, "MemTotal"), None);
        }
    }
    #[test]
    fn malformed_uptime_is_unknown() {
        assert_eq!(uptime("12.5 50.0"), Some(12.5));
        for value in ["", "NaN", "inf", "-1", "invalid"] {
            assert_eq!(uptime(value), None);
        }
    }
    #[test]
    fn effective_ssh_policy_never_assumes_missing_values_safe() {
        assert!(ssh_policy(None).iter().all(|c| c.level == Level::Unknown));
        assert_eq!(
            ssh_policy(Some("passwordauthentication yes"))[0].level,
            Level::Fail
        );
        assert_eq!(
            ssh_policy(Some("passwordauthentication no"))[0].level,
            Level::Ok
        );
        assert_eq!(
            ssh_policy(Some("passwordauthentication nonsense"))[0].level,
            Level::Unknown
        );
    }
}
