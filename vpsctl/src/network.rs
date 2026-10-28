//! Local network observations; outbound requests require explicit --online.
use crate::{
    Check, Level,
    system::{check, probe},
};
use serde::{Deserialize, Serialize};
use std::net::IpAddr;

#[derive(Debug, Deserialize, Serialize)]
pub struct Address {
    pub family: String,
    pub local: IpAddr,
    pub prefixlen: u8,
}
#[derive(Debug, Deserialize, Serialize)]
pub struct Interface {
    pub ifname: String,
    pub operstate: Option<String>,
    pub addr_info: Vec<Address>,
}
#[derive(Debug, Serialize)]
pub struct Network {
    pub schema_version: u32,
    pub interfaces: Option<Vec<Interface>>,
    pub note: &'static str,
}

pub fn parse_interfaces(text: &str) -> Option<Vec<Interface>> {
    let interfaces: Vec<Interface> = serde_json::from_str(text).ok()?;
    for interface in &interfaces {
        if interface.ifname.is_empty() || interface.ifname.len() > 64 {
            return None;
        }
        for addr in &interface.addr_info {
            if !matches!(
                (addr.family.as_str(), addr.local),
                ("inet", IpAddr::V4(_)) | ("inet6", IpAddr::V6(_))
            ) || addr.prefixlen > if addr.local.is_ipv4() { 32 } else { 128 }
            {
                return None;
            }
        }
    }
    Some(interfaces)
}

pub fn network() -> Network {
    Network {
        schema_version: 1,
        interfaces: probe("/usr/sbin/ip", &["-j", "address", "show"])
            .and_then(|s| parse_interfaces(&s)),
        note: "Local addresses only; no outbound traffic. Link state does not prove connectivity.",
    }
}

pub fn valid_hostname(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 253
        && name.split('.').all(|part| {
            !part.is_empty()
                && part.len() <= 63
                && !part.starts_with('-')
                && !part.ends_with('-')
                && part.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-')
        })
}

pub fn online_checks(name: &str) -> Vec<Check> {
    // Validate again at the service boundary; CLI and future TUI share this API.
    if !valid_hostname(name) {
        return vec![check(
            "dns_resolution",
            Level::Unknown,
            "Invalid DNS name; no request sent",
        )];
    }
    let resolved = probe("/usr/bin/getent", &["ahosts", name]);
    let dns = resolved.as_deref().is_some_and(|s| {
        s.lines().any(|line| {
            line.split_whitespace()
                .next()
                .is_some_and(|v| v.parse::<IpAddr>().is_ok())
        })
    });
    let https = probe(
        "/usr/bin/curl",
        &[
            "-q",
            "--head",
            "--proto",
            "=https",
            "--max-time",
            "3",
            "--connect-timeout",
            "2",
            "--silent",
            "--show-error",
            "--fail",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code}",
            "https://deb.debian.org/",
        ],
    );
    let https_ok = https
        .as_deref()
        .and_then(|s| s.parse::<u16>().ok())
        .is_some_and(|n| (200..400).contains(&n));
    vec![
        check(
            "dns_resolution",
            if dns { Level::Ok } else { Level::Unknown },
            if dns {
                "System NSS resolver returned an IP address (may come from hosts/cache as well as DNS)"
            } else {
                "Resolution failed or helper unavailable; DNS health unverified"
            },
        ),
        check(
            "https_connectivity",
            if https_ok { Level::Ok } else { Level::Unknown },
            if https_ok {
                "HTTPS HEAD to deb.debian.org succeeded with certificate verification; configured proxy may be used"
            } else {
                "HTTPS probe failed or curl unavailable; external connectivity unverified"
            },
        ),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn interface_data_is_typed_and_validated() {
        let data = r#"[{"ifname":"eth0","operstate":"UP","addr_info":[{"family":"inet","local":"192.0.2.1","prefixlen":24}],"secret":"omitted"}]"#;
        let parsed = parse_interfaces(data).unwrap();
        assert_eq!(parsed[0].addr_info[0].local.to_string(), "192.0.2.1");
        assert!(!serde_json::to_string(&parsed).unwrap().contains("secret"));
        assert!(parse_interfaces(&data.replace("24", "64")).is_none());
        assert!(parse_interfaces(&data.replace("inet\"", "inet6\"")).is_none());
        assert!(parse_interfaces("{}").is_none());
    }
    #[test]
    fn hostnames_cannot_inject_options_or_context_fields() {
        for host in ["deb.debian.org", "localhost", "example-1.com"] {
            assert!(valid_hostname(host));
        }
        for host in [
            "",
            "-option",
            "a,b",
            "a\nb",
            "user@host",
            "https://host",
            "a..b",
            "a.",
        ] {
            assert!(!valid_hostname(host));
        }
        assert!(!valid_hostname(&"a".repeat(254)));
        assert_eq!(online_checks("-option")[0].level, Level::Unknown);
    }
}
