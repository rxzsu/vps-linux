use anyhow::{Context, Result};
use clap::Parser;
use std::{
    io::{self, IsTerminal, Write},
    process::ExitCode,
};
use vpsctl::cli::{Action, Cli};
use vpsctl::{network, security, system, tui};

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
