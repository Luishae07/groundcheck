import Foundation

enum NetworkService {
    // Public rate-limited endpoint via the current live tunnel — same
    // pattern every other Groundcheck client uses; update when the tunnel
    // restarts (see current_tunnel_url.txt in the repo).
    static let dataURL = URL(string: "https://senate-armed-detector-farmers.trycloudflare.com/api/data")!

    static func fetchReadings() async throws -> [Reading] {
        let (data, _) = try await URLSession.shared.data(from: dataURL)
        return try JSONDecoder().decode([Reading].self, from: data)
    }
}
