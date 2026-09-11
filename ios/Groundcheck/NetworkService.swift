import Foundation

enum NetworkService {
    // tunnel-url.txt on GitHub Pages always holds the current live tunnel
    // hostname (the tunnel restarts with a new random URL periodically) —
    // fetch it fresh each time instead of hardcoding a URL that goes stale.
    static let tunnelURLFile = URL(string: "https://luishae07.github.io/groundcheck/tunnel-url.txt")!

    static func currentTunnelURL() async throws -> String {
        let (data, _) = try await URLSession.shared.data(from: tunnelURLFile)
        guard let text = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
              !text.isEmpty else {
            throw URLError(.cannotParseResponse)
        }
        return text
    }

    static func fetchReadings() async throws -> [Reading] {
        let base = try await currentTunnelURL()
        guard let dataURL = URL(string: base + "/api/data") else {
            throw URLError(.badURL)
        }
        let (data, _) = try await URLSession.shared.data(from: dataURL)
        return try JSONDecoder().decode([Reading].self, from: data)
    }
}
