import SwiftUI

struct AccountView: View {
    @AppStorage("groundcheck_nickname") private var nickname: String = ""
    @AppStorage("groundcheck_token") private var token: String = ""
    @State private var draftNickname: String = ""

    var body: some View {
        NavigationStack {
            Form {
                if nickname.isEmpty {
                    Section("Save a nickname on this device") {
                        TextField("Your nickname", text: $draftNickname)
                        Button("Save on this device") {
                            nickname = draftNickname
                            token = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
                        }
                        .disabled(draftNickname.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                } else {
                    Section {
                        LabeledContent("Nickname", value: nickname)
                        LabeledContent("Local token", value: token)
                    }
                    Section {
                        Button("Forget this device", role: .destructive) {
                            nickname = ""
                            token = ""
                            draftNickname = ""
                        }
                    }
                }
            }
            .navigationTitle("Account")
        }
    }
}
