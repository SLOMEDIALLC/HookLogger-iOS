import SwiftUI
import WebKit

struct RootView: View {
    @State private var splashDone  = false
    @State private var webReady    = false

    // WKWebView 提前创建，splash 期间就在后台加载 H5
    @StateObject private var webStore = WebStore()

    var body: some View {
        ZStack {
            // H5 始终在底层渲染（splash 期间在后台静默加载）
            WebView(store: webStore)
                .ignoresSafeArea()
                .opacity(splashDone ? 1 : 0)

            // Splash 覆盖在上面，10秒后淡出
            if !splashDone {
                SplashView {
                    withAnimation(.easeIn(duration: 0.4)) {
                        splashDone = true
                    }
                }
                .transition(.opacity)
            }
        }
        .onAppear {
            // 触发 H5 加载（WebStore 在 @StateObject 初始化时已创建 WKWebView）
            webStore.load(appURL)
        }
    }

    var appURL: String {
        let raw = Bundle.main.infoDictionary?["H5BaseURL"] as? String ?? "about:blank"
        if raw.hasPrefix("http") { return raw }
        return "https://" + raw
    }
}

// 持有 WKWebView 实例，保证 splash 期间就在加载
class WebStore: NSObject, ObservableObject, WKNavigationDelegate {
    private static let pool = WKProcessPool()   // 独立进程池

    let webView: WKWebView

    override init() {
        let config = WKWebViewConfiguration()
        config.processPool = WebStore.pool       // SDWebuiopser hook 不到
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        webView = WKWebView(frame: .zero, configuration: config)
        super.init()
        webView.navigationDelegate = self
        webView.scrollView.bounces = false
    }

    func load(_ urlStr: String) {
        guard let url = URL(string: urlStr) else { return }
        var req = URLRequest(url: url)
        req.timeoutInterval = 30
        webView.load(req)
    }

    // 加载失败 3 秒后重试
    func webView(_ wv: WKWebView, didFailProvisionalNavigation _: WKNavigation!, withError _: Error) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            wv.reload()
        }
    }
}
