// TenSeiAi Rust client (std-only, no crates).
// cargo would not even be needed:  rustc tensei_client.rs && ./tensei_client "hello"
use std::io::{Read, Write};
use std::net::TcpStream;

fn http(method: &str, path: &str, body: &str) -> String {
    let mut s = TcpStream::connect(("127.0.0.1", 8765)).expect("TenSeiAi not running on :8765");
    let req = format!(
        "{} {} HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        method, path, body.len(), body);
    s.write_all(req.as_bytes()).unwrap();
    let mut out = Vec::new();
    s.read_to_end(&mut out).unwrap();
    String::from_utf8_lossy(&out).into_owned()
}

fn json_str(s: &str, key: &str) -> Option<String> {
    let needle = format!("\"{}\": \"", key);
    let start = s.find(&needle)? + needle.len();
    let rest = &s[start..];
    let mut out = String::new();
    let mut chars = rest.chars();
    while let Some(c) = chars.next() {
        match c {
            '"' => break,
            '\\' => {
                if let Some(n) = chars.next() {
                    out.push(n);
                }
            }
            _ => out.push(c),
        }
    }
    Some(out)
}

fn main() {
    let q = std::env::args().skip(1).collect::<Vec<_>>().join(" ");
    let q = if q.is_empty() { "hello".to_string() } else { q };
    let esc = q.replace('\\', "\\\\").replace('"', "\\\"");
    let job = http("POST", "/api/ask", &format!("{{\"q\": \"{}\"}}", esc));
    let id = json_str(&job, "id").expect("could not start job");
    for _ in 0..600 {
        let j = http("GET", &format!("/api/job?id={}", id), "");
        if j.contains("\"status\": \"done\"") {
            println!("{}", json_str(&j, "answer").unwrap_or_default());
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(500));
    }
    eprintln!("(timeout)");
}
