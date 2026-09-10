import SwiftUI

struct StationsView: View {
    @ObservedObject var state: AppState

    private var uniqueStations: [Reading] {
        var seen = Set<String>()
        var result: [Reading] = []
        for reading in state.readings.sorted(by: { $0.parsedTime > $1.parsedTime }) {
            if !seen.contains(reading.id) {
                seen.insert(reading.id)
                result.append(reading)
            }
        }
        return result
    }

    var body: some View {
        NavigationStack {
            List(uniqueStations) { reading in
                HStack {
                    VStack(alignment: .leading) {
                        Text(reading.id).font(.headline)
                        Text(reading.parsedTime, style: .relative)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(String(format: "%.1f°", reading.temp))
                        .font(.headline)
                }
            }
            .navigationTitle("Stations")
            .overlay {
                if uniqueStations.isEmpty && !state.isLoading {
                    ContentUnavailableView("No stations", systemImage: "mappin.slash")
                }
            }
        }
    }
}
