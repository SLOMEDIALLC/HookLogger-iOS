import SwiftUI
import WebKit

// WebView 直接复用 WebStore 里已创建的 WKWebView（splash 期间就在加载）
struct WebView: UIViewRepresentable {
    @ObservedObject var store: WebStore

    func makeUIView(context: Context) -> WKWebView {
        store.webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
