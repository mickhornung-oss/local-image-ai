const vscode = require("vscode");

let panelRef = null;

function getHtml() {
  return `<!DOCTYPE html>
  <html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      body { font-family: sans-serif; padding: 16px; color: #1f2937; background: #f7faf8; }
      h2 { margin-top: 0; }
      textarea, select { width: 100%; box-sizing: border-box; margin-bottom: 12px; border: 1px solid #c9d8cf; border-radius: 8px; padding: 10px; background: white; }
      textarea { min-height: 110px; resize: vertical; }
      button { border: 0; background: #2f6f4f; color: white; padding: 10px 14px; border-radius: 8px; cursor: pointer; }
      .muted { color: #5f6f67; font-size: 12px; margin-bottom: 12px; }
      .card { background: white; border: 1px solid #d8e3dc; border-radius: 10px; padding: 12px; margin-top: 14px; }
      pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
    </style>
  </head>
  <body>
    <h2>Code KI V1</h2>
    <div class="muted">Lokale Python-KI fuer enge Arbeitsauftraege. Keine automatische Code-Uebernahme.</div>
    <label>Modus</label>
    <select id="mode">
      <option value="python_task">Python-Aufgabe</option>
      <option value="rewrite">Ueberarbeiten</option>
      <option value="explain">Erklaeren</option>
    </select>
    <label>Arbeitsauftrag</label>
    <textarea id="prompt" placeholder="Was soll die lokale KI mit dem aktuellen Python-Kontext tun?"></textarea>
    <label>Optionaler Fehler / Traceback</label>
    <textarea id="traceback" placeholder="Optional: Traceback oder Fehlermeldung einfuegen."></textarea>
    <button id="run">Ausfuehren</button>
    <div id="status" class="muted"></div>
    <div class="card">
      <strong>Kontext</strong>
      <pre id="context">Noch kein Lauf.</pre>
    </div>
    <div class="card">
      <strong>Antwort</strong>
      <pre id="result">Noch keine Antwort.</pre>
    </div>
    <script>
      const vscode = acquireVsCodeApi();
      document.getElementById("run").addEventListener("click", () => {
        vscode.postMessage({
          type: "run",
          mode: document.getElementById("mode").value,
          prompt: document.getElementById("prompt").value,
          traceback: document.getElementById("traceback").value
        });
        document.getElementById("status").textContent = "Laeuft...";
      });
      window.addEventListener("message", (event) => {
        const message = event.data;
        if (message.type === "result") {
          document.getElementById("status").textContent = message.ok ? "Antwort empfangen." : "Fehler.";
          document.getElementById("context").textContent = message.context;
          document.getElementById("result").textContent = message.result;
        }
      });
    </script>
  </body>
  </html>`;
}

async function callBackend(payload) {
  const config = vscode.workspace.getConfiguration("codeKI");
  const serverUrl = config.get("serverUrl", "http://127.0.0.1:8787");
  const response = await fetch(`${serverUrl}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail || data;
    throw new Error(`${detail.blocker || "backend_error"}: ${detail.message || "Unbekannter Fehler"}`);
  }
  return data;
}

function collectEditorContext() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return {
      current_file_path: null,
      current_file_text: null,
      selected_text: null,
      workspace_root: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || null
    };
  }
  const document = editor.document;
  const selection = editor.selection && !editor.selection.isEmpty
    ? document.getText(editor.selection)
    : null;
  return {
    current_file_path: document.uri.fsPath,
    current_file_text: document.getText(),
    selected_text: selection,
    workspace_root: vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath || null
  };
}

function activate(context) {
  const disposable = vscode.commands.registerCommand("codeKI.openAssistant", () => {
    if (panelRef) {
      panelRef.reveal(vscode.ViewColumn.Beside);
      return;
    }
    panelRef = vscode.window.createWebviewPanel("codeKI", "Code KI V1", vscode.ViewColumn.Beside, {
      enableScripts: true,
      retainContextWhenHidden: true
    });
    panelRef.webview.html = getHtml();
    panelRef.onDidDispose(() => {
      panelRef = null;
    });
    panelRef.webview.onDidReceiveMessage(async (message) => {
      if (message.type !== "run") {
        return;
      }
      const editorContext = collectEditorContext();
      const payload = {
        prompt: String(message.prompt || "").trim(),
        mode: message.mode || "python_task",
        traceback_text: String(message.traceback || "").trim() || null,
        ...editorContext
      };
      const contextText = [
        `Datei: ${payload.current_file_path || "keine aktive Datei"}`,
        `Workspace: ${payload.workspace_root || "kein Workspace"}`,
        `Markierung: ${payload.selected_text ? payload.selected_text.length + " Zeichen" : "keine"}`,
        `Traceback: ${payload.traceback_text ? payload.traceback_text.length + " Zeichen" : "keiner"}`
      ].join("\n");
      try {
        const result = await callBackend(payload);
        panelRef.webview.postMessage({
          type: "result",
          ok: true,
          context: contextText,
          result: result.answer
        });
      } catch (error) {
        panelRef.webview.postMessage({
          type: "result",
          ok: false,
          context: contextText,
          result: String(error && error.message ? error.message : error)
        });
      }
    });
  });

  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = { activate, deactivate };
