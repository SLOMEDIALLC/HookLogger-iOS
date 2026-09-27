import SwiftUI
import WebKit

struct WebView: UIViewRepresentable {
    let urlString: String

    // 独立进程池 —— SDWebuiopser hook 不到这里的网络
    private static let isolatedPool = WKProcessPool()

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.processPool = WebView.isolatedPool      // 关键：独立网络
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.scrollView.bounces = false
        webView.scrollView.showsVerticalScrollIndicator = false
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.1, green: 0.12, blue: 0.18, alpha: 1)
        webView.navigationDelegate = context.coordinator
        load(webView)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator() }

    private func load(_ webView: WKWebView) {
        guard !urlString.isEmpty, let url = URL(string: urlString) else { return }
        var req = URLRequest(url: url)
        req.timeoutInterval = 30
        webView.load(req)
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        func webView(_ webView: WKWebView,
                     didFailProvisionalNavigation nav: WKNavigation!,
                     withError error: Error) {
            // 加载失败后 3 秒重试
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                webView.reload()
            }
        }
    }
}
