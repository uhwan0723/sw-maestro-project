import SwiftUI
import ComposeApp

@main
struct iOSApp: App {
    init() {
        // local.properties 역할 — 실제 서버 주소로 교체할 것
        let baseUrl = "http://localhost:8080/"
        MainViewControllerKt.startKoinIos(baseUrl: baseUrl)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}