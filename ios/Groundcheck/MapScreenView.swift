import SwiftUI
import MapKit

struct MapScreenView: View {
    @ObservedObject var state: AppState
    @State private var cameraPosition: MapCameraPosition = .region(
        MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 51.5, longitude: 10.5),
            span: MKCoordinateSpan(latitudeDelta: 12, longitudeDelta: 12)
        )
    )

    private var recentReadings: [Reading] {
        let cutoff = Date().addingTimeInterval(-7 * 24 * 3600)
        return state.readings.filter { $0.parsedTime >= cutoff }
    }

    var body: some View {
        NavigationStack {
            Map(position: $cameraPosition) {
                ForEach(recentReadings) { reading in
                    Annotation(reading.id, coordinate: CLLocationCoordinate2D(latitude: reading.lat, longitude: reading.lon)) {
                        Circle()
                            .fill(colorForTemp(reading.temp))
                            .frame(width: 12, height: 12)
                            .overlay(Circle().stroke(.white, lineWidth: 2))
                    }
                }
            }
            .navigationTitle("Station Map")
        }
    }

    private func colorForTemp(_ t: Double) -> Color {
        if t < 3 { return Color(red: 0.23, green: 0.51, blue: 0.77) }
        if t < 7 { return Color(red: 0.18, green: 0.62, blue: 0.44) }
        if t < 11 { return Color(red: 0.79, green: 0.60, blue: 0.18) }
        return Color(red: 0.75, green: 0.35, blue: 0.24)
    }
}
