use crate::{network, security, system};
use anyhow::Result;
use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind, KeyModifiers},
    execute,
    terminal::{EnterAlternateScreen, LeaveAlternateScreen, disable_raw_mode, enable_raw_mode},
};
use ratatui::{
    Terminal,
    backend::CrosstermBackend,
    layout::{Constraint, Layout},
    style::{Color, Style},
    widgets::{Block, Borders, Paragraph, Tabs, Wrap},
};
use serde_json::Value;
use std::{io, time::Duration};

// Render only public observations; control characters from the host cannot
// become terminal escape sequences. JSON mode keeps standard JSON escaping.
fn clean(text: &str) -> String {
    text.chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect()
}

pub fn plain(value: &Value) -> String {
    if let Some(checks) = value.get("checks").and_then(Value::as_array) {
        return checks
            .iter()
            .map(|c| {
                format!(
                    "[{}] {}: {}",
                    clean(c["level"].as_str().unwrap_or("unknown")),
                    clean(c["id"].as_str().unwrap_or("unknown")),
                    clean(c["summary"].as_str().unwrap_or("unavailable"))
                )
            })
            .collect::<Vec<_>>()
            .join("\n");
    }
    value
        .as_object()
        .map(|o| {
            o.iter()
                .map(|(k, v)| {
                    let text = match v {
                        Value::Null => "unavailable".to_owned(),
                        Value::String(s) => clean(s),
                        _ => clean(&v.to_string()),
                    };
                    format!("{k}: {text}")
                })
                .collect::<Vec<_>>()
                .join("\n")
        })
        .unwrap_or_default()
}

fn section(index: usize) -> Result<String> {
    let value = match index {
        0 => serde_json::to_value(system::status())?,
        1 => serde_json::to_value(system::info())?,
        2 => serde_json::to_value(system::doctor())?,
        3 => serde_json::to_value(security::security(None))?,
        _ => serde_json::to_value(network::network())?,
    };
    Ok(plain(&value))
}

struct Restore;
impl Drop for Restore {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen, crossterm::cursor::Show);
    }
}

pub fn run() -> Result<()> {
    // Collect before entering raw mode. Guard covers failures and unwinding.
    let mut content = section(0)?;
    enable_raw_mode()?;
    let _restore = Restore;
    execute!(io::stdout(), EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(io::stdout()))?;
    let mut selected = 0;
    let mut scroll = 0u16;
    loop {
        terminal.draw(|frame| {
            let areas = Layout::vertical([Constraint::Length(3), Constraint::Min(1), Constraint::Length(3)]).split(frame.area());
            frame.render_widget(Tabs::new(["Status", "Info", "Doctor", "Security", "Network"]).select(selected).highlight_style(Style::default().fg(Color::Cyan)).block(Block::default().title("vpsctl 0.4.0 · read-only").borders(Borders::ALL)), areas[0]);
            frame.render_widget(Paragraph::new(content.as_str()).wrap(Wrap { trim: false }).scroll((scroll, 0)).block(Block::default().borders(Borders::ALL)), areas[1]);
            frame.render_widget(Paragraph::new("←/→ Tab: sections · ↑/↓: scroll · r: refresh · q/Esc/Ctrl-C: quit\nUnknown means unverified. Probes may take a few seconds.").block(Block::default().borders(Borders::TOP)), areas[2]);
        })?;
        if !event::poll(Duration::from_millis(200))? {
            continue;
        }
        if let Event::Key(key) = event::read()? {
            if key.kind != KeyEventKind::Press {
                continue;
            }
            if matches!(key.code, KeyCode::Char('q') | KeyCode::Esc)
                || (key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL))
            {
                break;
            }
            let mut refresh = false;
            match key.code {
                KeyCode::Right | KeyCode::Tab => {
                    selected = (selected + 1) % 5;
                    scroll = 0;
                    refresh = true;
                }
                KeyCode::Left | KeyCode::BackTab => {
                    selected = (selected + 4) % 5;
                    scroll = 0;
                    refresh = true;
                }
                KeyCode::Down => scroll = scroll.saturating_add(1),
                KeyCode::Up => scroll = scroll.saturating_sub(1),
                KeyCode::Char('r') => refresh = true,
                _ => {}
            }
            if refresh {
                content = section(selected)
                    .unwrap_or_else(|e| format!("Observation failed: {}", clean(&e.to_string())));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn host_control_sequences_are_not_rendered() {
        let text = plain(&serde_json::json!({"hostname": "evil\u{1b}[31m\nname", "memory": null}));
        assert!(!text.contains('\u{1b}'));
        assert!(text.contains("unavailable"));
    }
}
