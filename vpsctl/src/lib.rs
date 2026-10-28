//! Shared, read-only Linux observations. Missing evidence stays unknown.
pub mod network;
pub mod security;
pub mod system;
pub mod tui;

use serde::Serialize;

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Level {
    Ok,
    Warning,
    Fail,
    Unknown,
}

#[derive(Debug, Serialize)]
pub struct Check {
    pub id: &'static str,
    pub level: Level,
    pub summary: String,
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub schema_version: u32,
    pub section: &'static str,
    pub checks: Vec<Check>,
}

impl Report {
    pub fn exit_code(&self) -> u8 {
        if self.checks.iter().any(|c| c.level == Level::Fail) {
            1
        } else if self.checks.iter().any(|c| c.level != Level::Ok) {
            2
        } else {
            0
        }
    }
}

pub fn classify_unit(state: Option<&str>) -> Level {
    match state.map(str::trim) {
        Some("active") => Level::Ok,
        Some("failed") => Level::Fail,
        Some("inactive" | "activating" | "deactivating" | "reloading") => Level::Warning,
        _ => Level::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn missing_and_transitional_services_are_not_healthy() {
        assert_eq!(classify_unit(None), Level::Unknown);
        assert_eq!(classify_unit(Some("garbage")), Level::Unknown);
        assert_eq!(classify_unit(Some("activating")), Level::Warning);
        assert_eq!(classify_unit(Some("failed")), Level::Fail);
        assert_eq!(classify_unit(Some("active\n")), Level::Ok);
    }
    #[test]
    fn failure_takes_precedence_over_unknown() {
        let mut report = Report {
            schema_version: 1,
            section: "test",
            checks: vec![],
        };
        assert_eq!(report.exit_code(), 0);
        report.checks.push(Check {
            id: "a",
            level: Level::Unknown,
            summary: String::new(),
        });
        assert_eq!(report.exit_code(), 2);
        report.checks.push(Check {
            id: "b",
            level: Level::Fail,
            summary: String::new(),
        });
        assert_eq!(report.exit_code(), 1);
    }
}
