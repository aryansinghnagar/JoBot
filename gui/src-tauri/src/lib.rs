// The desktop shell is intentionally thin: it hosts the React frontend and
// exposes no privileged commands of its own. All sidecar interaction happens
// over the stdio JSON-RPC bridge implemented in JS (gui/src/lib/tauriTransport.js).
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}