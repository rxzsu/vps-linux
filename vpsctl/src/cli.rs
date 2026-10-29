//! Command-line surface shared by the binary and the documentation generator.
use crate::network;
use clap::{Parser, Subcommand};
use std::net::IpAddr;

#[derive(Parser)]
#[command(
    version,
    about = "Read-only VPS Linux control center",
    long_about = "Read-only VPS Linux control center. No command modifies the system or elevates privileges."
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Action>,
}

#[derive(Subcommand)]
pub enum Action {
    /// Show CPU, memory, root disk and uptime observations.
    Status {
        #[arg(long)]
        json: bool,
    },
    /// Identify this utility, operating system and VPS Linux image.
    Info {
        #[arg(long)]
        json: bool,
    },
    /// Check services, route, DNS configuration and time synchronization.
    Doctor {
        #[arg(long)]
        json: bool,
        /// Explicitly permit outbound NSS resolution and an HTTPS HEAD probe.
        #[arg(long)]
        online: bool,
        #[arg(long, default_value = "deb.debian.org", requires = "online", value_parser = dns_name)]
        dns_name: String,
    },
    /// List local interface addresses without sending network probes.
    Network {
        #[arg(long)]
        json: bool,
    },
    /// Inspect default-context SSH policy and security service observations.
    Security {
        #[arg(long)]
        json: bool,
        #[arg(long, requires_all = ["ssh_address", "ssh_host", "ssh_local_address", "ssh_local_port"])]
        ssh_user: Option<String>,
        #[arg(long, requires = "ssh_user")]
        ssh_address: Option<IpAddr>,
        #[arg(long, requires = "ssh_user", value_parser = dns_name)]
        ssh_host: Option<String>,
        #[arg(long, requires = "ssh_user")]
        ssh_local_address: Option<IpAddr>,
        #[arg(long, requires = "ssh_user", value_parser = clap::value_parser!(u16).range(1..))]
        ssh_local_port: Option<u16>,
    },
}

pub fn dns_name(value: &str) -> std::result::Result<String, String> {
    if network::valid_hostname(value) {
        Ok(value.to_owned())
    } else {
        Err("Expected an ASCII hostname without options, URLs or context separators".into())
    }
}
