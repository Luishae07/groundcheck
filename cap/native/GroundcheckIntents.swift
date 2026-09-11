import AppIntents
import Foundation

// Lets Siri/Shortcuts fetch the nearest station's current reading directly
// — no need to open the app UI at all. Runs a plain URLSession fetch
// against the same tunnel-url.txt + internal-API pattern every other
// Groundcheck client uses.
@available(iOS 16.0, *)
struct GetCurrentReadingIntent: AppIntent {
    static var title: LocalizedStringResource = "Get Ground Temperature"
    static var description = IntentDescription("Fetches the current reading from the nearest Groundcheck station.")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let tunnelFileURL = URL(string: "https://luishae07.github.io/groundcheck/tunnel-url.txt")!
        let (tunnelData, _) = try await URLSession.shared.data(from: tunnelFileURL)
        guard let base = String(data: tunnelData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
              !base.isEmpty else {
            throw GroundcheckIntentError.noData
        }

        let dataURL = URL(string: base + "/apiinternel/dont/json/microsftwindowssucks/data")!
        let (data, _) = try await URLSession.shared.data(from: dataURL)

        struct Reading: Decodable {
            let id: String
            let temp: Double
            let alt: Double
        }
        let readings = try JSONDecoder().decode([Reading].self, from: data)
        guard let first = readings.first else {
            throw GroundcheckIntentError.noData
        }

        let text = "\(first.temp.rounded())° at station \(first.id), \(Int(first.alt))m altitude"
        return .result(value: text, dialog: IntentDialog(stringLiteral: text))
    }
}

@available(iOS 16.0, *)
enum GroundcheckIntentError: Error, CustomLocalizedStringResourceConvertible {
    case noData
    var localizedStringResource: LocalizedStringResource {
        "Couldn't reach Groundcheck right now."
    }
}

@available(iOS 16.0, *)
struct GroundcheckShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: GetCurrentReadingIntent(),
            phrases: [
                "Get the ground temperature from \(.applicationName)",
                "Check \(.applicationName)"
            ],
            shortTitle: "Ground Temperature",
            systemImageName: "thermometer"
        )
    }
}
