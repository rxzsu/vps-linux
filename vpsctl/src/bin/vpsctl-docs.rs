//! Generate the distribution documentation payload: man page and shell completions.
//! Invoked by scripts/package-deb.sh; the output is packaged, never installed directly.
use anyhow::{Context, Result};
use clap::{CommandFactory, Parser};
use std::path::PathBuf;
use vpsctl::cli::Cli;

#[derive(Parser)]
struct Args {
    /// Directory that receives vpsctl.1, vpsctl.bash and _vpsctl.
    output: PathBuf,
}

fn main() -> Result<()> {
    let args = Args::parse();
    std::fs::create_dir_all(&args.output).context("create documentation output directory")?;
    let command = Cli::command();
    clap_mangen::Man::new(command).render(
        &mut std::fs::File::create(args.output.join("vpsctl.1")).context("create man page")?,
    )?;
    for (shell, file) in [
        (clap_complete::Shell::Bash, "vpsctl.bash"),
        (clap_complete::Shell::Zsh, "_vpsctl"),
    ] {
        clap_complete::generate(
            shell,
            &mut Cli::command(),
            "vpsctl",
            &mut std::fs::File::create(args.output.join(file))
                .with_context(|| format!("create {file}"))?,
        );
    }
    Ok(())
}
