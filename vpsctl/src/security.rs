//! Context-specific SSH observations and conservative effective APT checks.
use crate::{
    Check, Level, Report,
    network::valid_hostname,
    system::{self, check, probe},
};
use anyhow::{Result, ensure};
use std::net::IpAddr;

pub struct SshContext {
    user: String,
    address: IpAddr,
    host: String,
    local_address: IpAddr,
    local_port: u16,
}
impl SshContext {
    pub fn new(
        user: String,
        address: IpAddr,
        host: String,
        local_address: IpAddr,
        local_port: u16,
    ) -> Result<Self> {
        ensure!(
            !user.is_empty()
                && user.len() <= 64
                && user
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"._-".contains(&c)),
            "Invalid SSH user"
        );
        ensure!(valid_hostname(&host), "Invalid SSH peer hostname");
        ensure!(local_port > 0, "SSH local port must be nonzero");
        Ok(Self {
            user,
            address,
            host,
            local_address,
            local_port,
        })
    }
    fn argument(&self) -> String {
        format!(
            "user={},addr={},host={},laddr={},lport={}",
            self.user, self.address, self.host, self.local_address, self.local_port
        )
    }
}

pub fn apt_policy(text: Option<&str>) -> Vec<Check> {
    let Some(text) = text else {
        return vec![check(
            "upgrade_policy",
            Level::Unknown,
            "Effective APT configuration unavailable",
        )];
    };
    let mut origins = Vec::new();
    let mut allowed = Vec::new();
    let mut reboot = None;
    let mut periodic = None;
    let mut malformed = false;
    for line in text.lines() {
        let Some((key, raw)) = line.split_once(' ') else {
            malformed = true;
            continue;
        };
        if !matches!(
            key,
            "Unattended-Upgrade::Origins-Pattern::"
                | "Unattended-Upgrade::Allowed-Origins::"
                | "Unattended-Upgrade::Automatic-Reboot"
                | "APT::Periodic::Unattended-Upgrade"
        ) {
            continue;
        }
        let Some(value) = raw.strip_prefix('"').and_then(|v| v.strip_suffix("\";")) else {
            malformed = true;
            continue;
        };
        if value.contains(['"', '\\']) {
            malformed = true;
            continue;
        }
        match key {
            "Unattended-Upgrade::Origins-Pattern::" => origins.push(value),
            "Unattended-Upgrade::Allowed-Origins::" => allowed.push(value),
            "Unattended-Upgrade::Automatic-Reboot" => reboot = Some(value),
            "APT::Periodic::Unattended-Upgrade" => periodic = Some(value),
            _ => {}
        }
    }
    // Do not claim security-only for arbitrary APT matching expressions.
    let security = "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
    let level = if malformed {
        Level::Unknown
    } else if origins == [security] && allowed.is_empty() {
        Level::Ok
    } else {
        Level::Warning
    };
    vec![
        check(
            "upgrade_origins",
            level,
            match level {
                Level::Ok => {
                    "Effective APT origins match VPS Linux security-only policy; package freshness not checked"
                }
                Level::Warning => {
                    "Effective APT origins do not match the exact VPS Linux security-only policy"
                }
                _ => "Effective APT origin data malformed or incomplete",
            },
        ),
        check(
            "automatic_reboot",
            match reboot {
                Some("false" | "0" | "no") => Level::Ok,
                Some("true" | "1" | "yes") => Level::Warning,
                _ => Level::Unknown,
            },
            match reboot {
                Some("false" | "0" | "no") => "Automatic reboots explicitly disabled",
                Some("true" | "1" | "yes") => "Automatic reboots enabled",
                _ => "Automatic reboot setting not verified",
            },
        ),
        check(
            "periodic_security_updates",
            if periodic == Some("1") {
                Level::Ok
            } else {
                Level::Unknown
            },
            "Daily unattended upgrade schedule; does not certify successful installation",
        ),
    ]
}

pub fn security(context: Option<&SshContext>) -> Report {
    let ssh = match context {
        Some(context) => probe("/usr/sbin/sshd", &["-T", "-C", &context.argument()]),
        None => probe("/usr/sbin/sshd", &["-T"]),
    };
    let mut checks = system::ssh_policy(ssh.as_deref());
    if context.is_some() {
        for check in &mut checks {
            check.summary = check
                .summary
                .replace("default-context", "specified connection context");
        }
        checks.push(check("ssh_match_context", if ssh.is_some() { Level::Ok } else { Level::Unknown }, "Supplied user, peer address/hostname, local address/port only; other connections are not assessed"));
    } else {
        checks.push(check("ssh_match_context", Level::Unknown, "Per-user/address Match policies are not evaluated; default-context checks do not cover every SSH login"));
    }
    // List rules read-only, never dump firewall addresses/rules into the report.
    let nft = probe("/usr/sbin/nft", &["-j", "list", "ruleset"])
        .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok());
    checks.push(check(
        "firewall",
        Level::Unknown,
        if nft.is_some() {
            "nftables readable; effective ingress policy not evaluated"
        } else {
            "Firewall policy unavailable (permissions, missing nft or unsupported backend)"
        },
    ));
    for timer in ["apt-daily.timer", "apt-daily-upgrade.timer"] {
        let state = probe(
            "/usr/bin/systemctl",
            &["show", "--property=ActiveState", "--value", timer],
        );
        checks.push(check(
            timer,
            crate::classify_unit(state.as_deref()),
            "Timer activity checked independently; does not certify installed package freshness",
        ));
    }
    checks.extend(apt_policy(
        probe("/usr/bin/apt-config", &["dump"]).as_deref(),
    ));
    Report {
        schema_version: 1,
        section: "security",
        checks,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn apt_policy_rejects_extra_origins_and_reports_reboot() {
        let data = "Unattended-Upgrade::Origins-Pattern:: \"origin=Debian,codename=${distro_codename}-security,label=Debian-Security\";\nUnattended-Upgrade::Automatic-Reboot \"false\";\nAPT::Periodic::Unattended-Upgrade \"1\";";
        assert!(apt_policy(Some(data)).iter().all(|c| c.level == Level::Ok));
        assert_eq!(
            apt_policy(Some(&format!(
                "{data}\nUnattended-Upgrade::Allowed-Origins:: \"Debian:stable\";"
            )))[0]
                .level,
            Level::Warning
        );
        assert_eq!(
            apt_policy(Some(&data.replace("false", "true")))[1].level,
            Level::Warning
        );
        assert_eq!(apt_policy(None)[0].level, Level::Unknown);
        assert_eq!(apt_policy(Some("broken"))[0].level, Level::Unknown);
    }
    #[test]
    fn context_is_structured_and_cannot_inject_fields() {
        let ip = "192.0.2.1".parse().unwrap();
        assert!(SshContext::new("root,addr=bad".into(), ip, "host".into(), ip, 22).is_err());
        assert!(SshContext::new("debian".into(), ip, "host,addr=bad".into(), ip, 22).is_err());
        assert!(SshContext::new("debian".into(), ip, "host".into(), ip, 0).is_err());
        assert_eq!(
            SshContext::new("debian".into(), ip, "host".into(), ip, 22)
                .unwrap()
                .argument(),
            "user=debian,addr=192.0.2.1,host=host,laddr=192.0.2.1,lport=22"
        );
    }
}
