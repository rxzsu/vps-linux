use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::net::IpAddr;
use std::{
    io::{self, IsTerminal, Write},
    process::ExitCode,
};
use vpsctl::{network, security, system, tui};

#[derive(Parser)]
#[command(
    version,
    about = "Read-only VPS Linux control center",
    long_about = "Read-only VPS Linux control center. No command modifies the system or elevates privileges."
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Action>,
}

#[derive(Subcommand)]
enum Action {
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

fn dns_name(value: &str) -> std::result::Result<String, String> {
    if network::valid_hostname(value) {
        Ok(value.to_owned())
    } else {
        Err("Expected an ASCII hostname without options, URLs or context separators".into())
    }
}

fn run() -> Result<u8> {
    let cli = Cli::parse();
    let (value, json, code) = match cli.command {
        None => {
            if !io::stdin().is_terminal() || !io::stdout().is_terminal() {
                anyhow::bail!(
                    "TUI requires interactive stdin and stdout. Use 'vpsctl status --json' or 'vpsctl --help'."
                );
            }
            tui::run()?;
            return Ok(0);
        }
        Some(Action::Status { json }) => (serde_json::to_value(system::status())?, json, 0),
        Some(Action::Info { json }) => (serde_json::to_value(system::info())?, json, 0),
        Some(Action::Network { json }) => (serde_json::to_value(network::network())?, json, 0),
        Some(Action::Doctor {
            json,
            online,
            dns_name,
        }) => {
            let mut report = system::doctor();
            if online {
                report.checks.extend(network::online_checks(&dns_name));
            }
            let code = report.exit_code();
            (serde_json::to_value(report)?, json, code)
        }
        Some(Action::Security {
            json,
            ssh_user,
            ssh_address,
            ssh_host,
            ssh_local_address,
            ssh_local_port,
        }) => {
            let context =
                if let (Some(user), Some(address), Some(host), Some(local_address), Some(port)) = (
                    ssh_user,
                    ssh_address,
                    ssh_host,
                    ssh_local_address,
                    ssh_local_port,
                ) {
                    Some(security::SshContext::new(
                        user,
                        address,
                        host,
                        local_address,
                        port,
                    )?)
                } else {
                    None
                };
            let report = security::security(context.as_ref());
            let code = report.exit_code();
            (serde_json::to_value(report)?, json, code)
        }
    };
    let text = if json {
        serde_json::to_string_pretty(&value)?
    } else {
        tui::plain(&value)
    };
    writeln!(io::stdout().lock(), "{text}").context("write output")?;
    Ok(code)
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => ExitCode::from(code),
        Err(error) => {
            eprintln!("vpsctl: {error:#}");
            ExitCode::from(2)
        }
    }
}
