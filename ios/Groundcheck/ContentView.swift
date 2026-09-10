import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var readings: [Reading] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    var newestReading: Reading? {
        readings.max(by: { $0.parsedTime < $1.parsedTime })
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            readings = try await NetworkService.fetchReadings()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct ContentView: View {
    @StateObject private var state = AppState()

    var body: some View {
        TabView {
            TodayView(state: state)
                .tabItem { Label("Today", systemImage: "sun.max") }

            MapScreenView(state: state)
                .tabItem { Label("Map", systemImage: "map") }

            StationsView(state: state)
                .tabItem { Label("Stations", systemImage: "mappin.circle") }

            AccountView()
                .tabItem { Label("Account", systemImage: "person.circle") }
        }
        .task { await state.load() }
    }
}
