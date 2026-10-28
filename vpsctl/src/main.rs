use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::{
    io::{self, IsTerminal, Write},
    process::ExitCode,
};
use vpsctl::{system, tui};

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
    },
    /// Inspect default-context SSH policy and security service observations.
    Security {
        #[arg(long)]
        json: bool,
    },
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
        Some(Action::Doctor { json }) => {
            let report = system::doctor();
            let code = report.exit_code();
            (serde_json::to_value(report)?, json, code)
        }
        Some(Action::Security { json }) => {
            let report = system::security();
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
