import SwiftUI

struct SplashView: View {
    let onFinish: () -> Void

    @State private var progress: CGFloat = 0
    @State private var pct: Int = 0

    private var appName: String {
        Bundle.main.infoDictionary?["CFBundleDisplayName"] as? String ??
        Bundle.main.infoDictionary?["CFBundleName"] as? String ?? "App"
    }

    var body: some View {
        ZStack {
            bgColor.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // Logo
                Group {
                    if let img = UIImage(named: "AppLogo") {
                        Image(uiImage: img)
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                    } else {
                        Image(systemName: "bolt.circle.fill")
                            .resizable()
                            .foregroundColor(.cyan)
                    }
                }
                .frame(width: 110, height: 110)
                .clipShape(Circle())
                .overlay(Circle().stroke(Color.cyan.opacity(0.4), lineWidth: 2))
                .shadow(color: .cyan.opacity(0.3), radius: 20)

                Spacer().frame(height: 28)

                Text(appName)
                    .font(.system(size: 26, weight: .bold))
                    .foregroundColor(.white)

                Spacer()

                // Progress bar
                VStack(spacing: 10) {
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 3)
                                .fill(Color.white.opacity(0.15))
                                .frame(height: 4)
                            RoundedRectangle(cornerRadius: 3)
                                .fill(LinearGradient(
                                    colors: [Color(red:0.2,green:0.9,blue:0.8),
                                             Color(red:0.5,green:0.3,blue:0.9)],
                                    startPoint: .leading, endPoint: .trailing))
                                .frame(width: geo.size.width * progress, height: 4)
                                .animation(.linear(duration: 0.05), value: progress)
                        }
                    }
                    .frame(height: 4)
                    .padding(.horizontal, 48)

                    HStack {
                        Text("正在加载资源...")
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.5))
                        Spacer()
                        Text("\(pct)%")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.white.opacity(0.5))
                    }
                    .padding(.horizontal, 48)
                }
                .padding(.bottom, 60)
            }
        }
        .onAppear { startProgress() }
    }

    private var bgColor: Color {
        let info = Bundle.main.infoDictionary ?? [:]
        let r = (info["SplashBgR"] as? Int ?? 26)
        let g = (info["SplashBgG"] as? Int ?? 30)
        let b = (info["SplashBgB"] as? Int ?? 46)
        return Color(red: Double(r)/255, green: Double(g)/255, blue: Double(b)/255)
    }

    private func startProgress() {
        let dur = Bundle.main.infoDictionary?["SplashDuration"] as? Double ?? 10.0
        let total = dur
        let steps = 100
        let interval = total / Double(steps)
        var step = 0

        Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { t in
            step += 1
            let raw = Double(step) / Double(steps)
            // ease-out curve
            progress = CGFloat(1 - pow(1 - raw, 3))
            pct = min(step, 100)

            if step >= steps {
                t.invalidate()
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                    onFinish()
                }
            }
        }
    }
}
