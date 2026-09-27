import SwiftUI

struct RootView: View {
    @State private var splashDone = false

    var h5URL: String {
        Bundle.main.infoDictionary?["H5BaseURL"] as? String ?? "about:blank"
    }

    var body: some View {
        ZStack {
            if splashDone {
                WebView(urlString: h5URL)
                    .ignoresSafeArea()
                    .transition(.opacity)
            } else {
                SplashView {
                    withAnimation(.easeIn(duration: 0.3)) {
                        splashDone = true
                    }
                }
                .transition(.opacity)
            }
        }
    }
}
