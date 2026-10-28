use std::process::{Command, Stdio};

fn run(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_vpsctl"))
        .args(args)
        .stdin(Stdio::null())
        .output()
        .unwrap()
}

#[test]
fn help_and_version_are_standalone() {
    for args in [["--help"], ["--version"]] {
        let output = run(&args);
        assert!(output.status.success());
        assert!(String::from_utf8_lossy(&output.stdout).contains("vpsctl"));
    }
}

#[test]
fn redirected_no_arguments_fails_promptly_and_usefully() {
    let output = run(&[]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains("status --json"));
}

#[test]
fn json_commands_have_schema_and_no_terminal_formatting() {
    for name in ["status", "info", "doctor", "security"] {
        let output = run(&[name, "--json"]);
        assert!([Some(0), Some(1), Some(2)].contains(&output.status.code()));
        assert!(!output.stdout.contains(&0x1b));
        let value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(value["schema_version"], 1);
        assert!(output.stderr.is_empty(), "{name}: {:?}", output.stderr);
        if name == "status" {
            assert!(value.get("memory_total_bytes").is_some());
            assert!(value.get("uptime_seconds").is_some());
        }
        if name == "doctor" || name == "security" {
            for check in value["checks"].as_array().unwrap() {
                assert!(
                    ["ok", "warning", "fail", "unknown"]
                        .contains(&check["level"].as_str().unwrap())
                );
            }
        }
    }
}

#[test]
fn invalid_commands_do_not_launch_tui() {
    assert_eq!(run(&["mutate"]).status.code(), Some(2));
}
