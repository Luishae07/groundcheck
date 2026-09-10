import Foundation

struct Reading: Codable, Identifiable {
    let id: String
    let time: String
    let temp: Double
    let alt: Double
    let pressure: Double?
    let humidity: Double?
    let lat: Double
    let lon: Double
    let source: [String]?
    let tsunix: Int?

    enum CodingKeys: String, CodingKey {
        case id, time, temp, alt, pressure, humidity, lat, lon, source, tsunix
    }

    var parsedTime: Date {
        let formatter = ISO8601DateFormatter()
        return formatter.date(from: time) ?? Date(timeIntervalSince1970: TimeInterval(tsunix ?? 0))
    }
}
