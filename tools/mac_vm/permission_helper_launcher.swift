// Trusted VM lifecycle utility, never exposed as a model tool.
import AppKit
import CryptoKit
import Darwin

let appPath = "/Users/mvpagent/CUAgentDriverDiagnostic-67d334cd04207faff101955e0b2b1b5fd1cc4f25251d9a0a75a4708f063b6beb/CuaDriverPointGuard.app"
let executable = appPath + "/Contents/MacOS/cua-driver-pointguard"
let identifier = "com.trycua.driver.pointguard"
let expectedHash = "ce14200a07e0c80d73230ff599d69310864911eb2e79c51303e4941c5d8e179c"

func finish(_ result: String, _ reason: String, _ extra: [String: Any] = [:], code: Int32) -> Never {
    var payload = extra
    payload["result"] = result
    payload["reason"] = reason
    let data = try! JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
    exit(code)
}

guard CommandLine.arguments.count == 3,
      CommandLine.arguments[1] == "--result-file" else {
    finish("REJECTED", "EXPECTED_RESULT_FILE_ARGUMENT", code: 2)
}
let resultURL = URL(fileURLWithPath: CommandLine.arguments[2]).standardizedFileURL
let temp = FileManager.default.temporaryDirectory.resolvingSymlinksInPath().standardizedFileURL
var info = stat()
guard resultURL.deletingLastPathComponent().resolvingSymlinksInPath() == temp,
      resultURL.lastPathComponent.hasPrefix("cua-driver-permissions-"),
      resultURL.pathExtension == "json",
      lstat(resultURL.path, &info) == 0,
      (info.st_mode & S_IFMT) == S_IFREG,
      (info.st_mode & 0o777) == 0o600,
      info.st_uid == getuid(), info.st_nlink == 1, info.st_size == 0 else {
    finish("REJECTED", "UNSAFE_RESULT_FILE", code: 2)
}
let appURL = URL(fileURLWithPath: appPath)
guard appURL.resolvingSymlinksInPath().path == appPath,
      URL(fileURLWithPath: executable).resolvingSymlinksInPath().path == executable,
      Bundle(url: appURL)?.bundleIdentifier == identifier,
      let binary = try? Data(contentsOf: URL(fileURLWithPath: executable)),
      SHA256.hash(data: binary).map({ String(format: "%02x", $0) }).joined() == expectedHash else {
    finish("REJECTED", "APP_IDENTITY_MISMATCH", code: 2)
}
guard NSRunningApplication.runningApplications(withBundleIdentifier: identifier).isEmpty else {
    finish("REJECTED", "EXISTING_HELPER_INSTANCE", code: 2)
}
let configuration = NSWorkspace.OpenConfiguration()
configuration.createsNewApplicationInstance = true
configuration.allowsRunningApplicationSubstitution = false
configuration.activates = false
configuration.addsToRecentItems = false
configuration.promptsUserIfNeeded = false
configuration.environment = ["CUA_DRIVER_RS_TELEMETRY_ENABLED": "false"]
configuration.arguments = ["__permissions-host-request", "--result-file", resultURL.path, "--probe-direct-capture"]
// Timeout never means the launched process stopped. The supervisor owns cleanup.
DispatchQueue.main.asyncAfter(deadline: .now() + 60) {
    finish("UNKNOWN", "LAUNCH_CALLBACK_TIMEOUT", code: 3)
}
NSWorkspace.shared.openApplication(at: appURL, configuration: configuration) { application, error in
    guard error == nil, let application = application else {
        finish("UNKNOWN", "LAUNCH_CALLBACK_FAILED", code: 3)
    }
    let identity: [String: Any] = [
        "pid": application.processIdentifier,
        "bundleIdentifier": application.bundleIdentifier ?? "",
        "executablePath": application.executableURL?.path ?? "",
        "resultFile": resultURL.path,
        "source": "NSWorkspace.openApplication",
    ]
    guard application.processIdentifier > 0,
          application.bundleIdentifier == identifier,
          application.executableURL?.path == executable else {
        finish("UNKNOWN", "LAUNCHED_IDENTITY_MISMATCH", identity, code: 3)
    }
    finish("LAUNCHED", "OS_CALLBACK_IDENTITY", identity, code: 0)
}
RunLoop.main.run()
