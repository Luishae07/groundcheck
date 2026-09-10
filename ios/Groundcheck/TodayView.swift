import SwiftUI

struct TodayView: View {
    @ObservedObject var state: AppState

    var body: some View {
        NavigationStack {
            ScrollView {
                if let reading = state.newestReading {
                    VStack(spacing: 12) {
                        Text("Station \(reading.id)")
                            .font(.headline)
                            .foregroundStyle(.secondary)

                        Text(String(format: "%.1f°", reading.temp))
                            .font(.system(size: 72, weight: .bold, design: .rounded))

                        HStack(spacing: 24) {
                            metric("Humidity", reading.humidity.map { "\(Int($0))%" } ?? "—")
                            metric("Pressure", reading.pressure.map { "\(Int($0)) hPa" } ?? "—")
                            metric("Altitude", "\(Int(reading.alt)) m")
                        }

                        Text(reading.parsedTime, style: .relative)
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
                    .padding()
                } else if state.isLoading {
                    ProgressView("Loading…")
                        .padding()
                } else if let error = state.errorMessage {
                    Text("Unable to load data: \(error)")
                        .foregroundStyle(.red)
                        .padding()
                }
            }
            .navigationTitle("Groundcheck")
            .refreshable { await state.load() }
        }
    }

    private func metric(_ label: String, _ value: String) -> some View {
        VStack {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline)
        }
    }
}
