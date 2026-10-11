//! Copy into the pinned upstream cua-driver/tests directory; hermetic CLI test.
//! No real daemon, desktop runtime, model, input, or permission changes.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixListener;
use std::process::{Command, Stdio};
use std::sync::{Arc, atomic::{AtomicBool, Ordering}};
use std::time::{Duration, Instant};

fn run(response: Value) -> (std::process::Output, Vec<Value>) {
    let directory = tempfile::tempdir().unwrap();
    let socket = directory.path().join("driver.sock");
    let listener = UnixListener::bind(&socket).unwrap();
    listener.set_nonblocking(true).unwrap();
    let done = Arc::new(AtomicBool::new(false));
    let server_done = done.clone();
    let server = std::thread::spawn(move || {
        let mut requests = Vec::new();
        let deadline = Instant::now() + Duration::from_secs(25);
        while !server_done.load(Ordering::SeqCst) && Instant::now() < deadline {
            let (mut stream, _) = match listener.accept() {
                Ok(value) => value,
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    std::thread::sleep(Duration::from_millis(5));
                    continue;
                }
                Err(e) => panic!("accept: {e}"),
            };
            stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
            let mut line = String::new();
            BufReader::new(stream.try_clone().unwrap()).read_line(&mut line).unwrap();
            if line.is_empty() { continue; } // CLI socket-listening probe.
            let request: Value = serde_json::from_str(&line).unwrap();
            let reply = match request["method"].as_str() {
                Some("list") => json!({"ok":true,"result":{"tools":[]}}),
                Some("metadata") => json!({"ok":true,"result":cua_driver_core::daemon::current_daemon_metadata()}),
                Some("call") => json!({"ok":true,"result":response}),
                Some("session_end") => json!({"ok":true,"result":{}}),
                _ => json!({"ok":false,"error":"unexpected test request"}),
            };
            requests.push(request);
            writeln!(stream,"{reply}").unwrap();
        }
        requests
    });
    let mut child = Command::new(env!("CARGO_BIN_EXE_cua-driver"))
        .args(["--socket",socket.to_str().unwrap(),"click",r#"{"session":"cli-error-test","pid":10,"window_id":20,"x":1,"y":1}"#])
        .env("CUA_DRIVER_RS_HOME",directory.path())
        .env("CUA_DRIVER_TELEMETRY_HOME",directory.path())
        .env("CUA_DRIVER_RS_TELEMETRY_ENABLED","0")
        .env("CUA_DRIVER_CLI_TELEMETRY_CHILD","1")
        .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped())
        .spawn().unwrap();
    let deadline = Instant::now() + Duration::from_secs(20);
    let mut timeout = false;
    while child.try_wait().unwrap().is_none() {
        if Instant::now() >= deadline { child.kill().unwrap(); timeout=true; break; }
        std::thread::sleep(Duration::from_millis(10));
    }
    let output=child.wait_with_output().unwrap();
    done.store(true,Ordering::SeqCst);
    let requests=server.join().unwrap();
    assert!(!timeout,"CLI timed out");
    assert_eq!(requests.iter().filter(|r|r["method"]=="call").count(),1,"requests={requests:?}, output={output:?}");
    assert_eq!(requests.iter().map(|r|r["method"].as_str().unwrap()).collect::<Vec<_>>(),
        vec!["list","metadata","session_end","call"],"probe and metadata SDK cleanup precede the one action");
    assert_eq!(requests[3]["name"],"click");
    (output,requests)
}

#[test]
fn cli_preserves_failure_details_without_changing_stdout_exit_or_dispatch() {
    let long_cause = "文".repeat(1000);
    for cause in ["exact target window did not become focused", "", "中文 failure", long_cause.as_str()] {
        let code=json!({"code":"foreground_unavailable"});
        let (out,_)=run(json!({"isError":true,"structuredContent":code,
            "content":[{"type":"text","text":cause}]}));
        assert_eq!(out.status.code(),Some(1));
        assert_eq!(serde_json::from_slice::<Value>(&out.stdout).unwrap(),code);
        assert_eq!(String::from_utf8(out.stderr).unwrap(),format!("{cause}\n"));
    }
    let (out,_)=run(json!({"isError":true,"structuredContent":{"code":"failure"},"content":[]}));
    assert_eq!(out.status.code(),Some(1));
    assert!(out.stderr.is_empty());
    let (out,_)=run(json!({"isError":true,"content":[{"type":"text","text":"text-only"}]}));
    assert_eq!(out.status.code(),Some(1));
    assert_eq!(out.stdout,b"text-only\n");
    assert!(out.stderr.is_empty());
    let (out,_)=run(json!({"isError":false,"structuredContent":{"ok":true},
        "content":[{"type":"text","text":"success detail"}]}));
    assert_eq!(out.status.code(),Some(0));
    assert_eq!(serde_json::from_slice::<Value>(&out.stdout).unwrap(),json!({"ok":true}));
    assert!(out.stderr.is_empty());
}
