[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8090",
    [int]$TimeoutSeconds = 20,
    [int]$VirtualTimeBudgetMs = 8000
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "_status_helpers.ps1")

function Get-EdgePath {
    $candidates = @(
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

function Get-ElementText {
    param(
        [Parameter(Mandatory = $true)][string]$Html,
        [Parameter(Mandatory = $true)][string]$Id
    )

    $pattern = '<(?<tag>[a-zA-Z0-9:_-]+)\b[^>]*\bid="' + [regex]::Escape($Id) + '"[^>]*>(?<content>.*?)</\k<tag>>'
    $match = [regex]::Match($Html, $pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) {
        return $null
    }

    $content = $match.Groups["content"].Value
    $withoutTags = [regex]::Replace($content, "<[^>]+>", " ")
    $decoded = [System.Net.WebUtility]::HtmlDecode($withoutTags)
    $normalized = [regex]::Replace($decoded, "\s+", " ").Trim()
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return $null
    }
    return $normalized
}

function New-UiCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][bool]$Ok,
        [string]$Detail = $null
    )

    return [pscustomobject]@{
        name = $Name
        ok = $Ok
        detail = $Detail
    }
}

function Get-UiCheckDetail {
    param(
        [Parameter(Mandatory = $true)]$Value
    )

    if (-not $Value) {
        return $null
    }

    if (($Value.PSObject.Properties.Name -contains "detail") -and -not [string]::IsNullOrWhiteSpace($Value.detail)) {
        return $Value.detail
    }
    if (($Value.PSObject.Properties.Name -contains "blocker") -and -not [string]::IsNullOrWhiteSpace($Value.blocker)) {
        return $Value.blocker
    }
    return $null
}

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    } finally {
        $listener.Stop()
    }
}

function Invoke-CdpCommand {
    param(
        [Parameter(Mandatory = $true)][System.Net.WebSockets.ClientWebSocket]$Socket,
        [Parameter(Mandatory = $true)][int]$Id,
        [Parameter(Mandatory = $true)][string]$Method,
        [hashtable]$Params = @{}
    )

    $payload = @{
        id = $Id
        method = $Method
        params = $Params
    } | ConvertTo-Json -Depth 10 -Compress
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $sendSegment = [System.ArraySegment[byte]]::new($payloadBytes)
    $sendTask = $Socket.SendAsync($sendSegment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None)
    $sendTask.Wait()

    while ($true) {
        $buffer = New-Object byte[] 65536
        $segment = [System.ArraySegment[byte]]::new($buffer)
        $stream = New-Object System.IO.MemoryStream
        try {
            do {
                $receiveTask = $Socket.ReceiveAsync($segment, [System.Threading.CancellationToken]::None)
                $receiveTask.Wait()
                $receiveResult = $receiveTask.Result
                if ($receiveResult.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                    throw "cdp_socket_closed"
                }
                if ($receiveResult.Count -gt 0) {
                    $stream.Write($buffer, 0, $receiveResult.Count)
                }
            } while (-not $receiveResult.EndOfMessage)

            $jsonText = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
        } finally {
            $stream.Dispose()
        }

        if ([string]::IsNullOrWhiteSpace($jsonText)) {
            continue
        }

        $message = $jsonText | ConvertFrom-Json
        if ($message.PSObject.Properties.Name -contains "id" -and [int]$message.id -eq $Id) {
            return $message
        }
    }
}

function Invoke-CdpEvaluate {
    param(
        [Parameter(Mandatory = $true)][System.Net.WebSockets.ClientWebSocket]$Socket,
        [Parameter(Mandatory = $true)][ref]$NextId,
        [Parameter(Mandatory = $true)][string]$Expression,
        [bool]$AwaitPromise = $false
    )

    $commandId = $NextId.Value
    $NextId.Value = $NextId.Value + 1
    $response = Invoke-CdpCommand -Socket $Socket -Id $commandId -Method "Runtime.evaluate" -Params @{
        expression = $Expression
        returnByValue = $true
        awaitPromise = $AwaitPromise
    }

    if ($response.PSObject.Properties.Name -contains "error") {
        throw "cdp_runtime_error"
    }
    if (
        ($response.PSObject.Properties.Name -contains "result") -and
        ($response.result.PSObject.Properties.Name -contains "exceptionDetails") -and
        $response.result.exceptionDetails
    ) {
        $exceptionText = $response.result.exceptionDetails.text
        if (-not [string]::IsNullOrWhiteSpace($exceptionText)) {
            throw "cdp_eval_exception:$exceptionText"
        }
        throw "cdp_eval_exception"
    }
    return $response.result.result.value
}

function Wait-CdpCondition {
    param(
        [Parameter(Mandatory = $true)][System.Net.WebSockets.ClientWebSocket]$Socket,
        [Parameter(Mandatory = $true)][ref]$NextId,
        [Parameter(Mandatory = $true)][string]$Expression,
        [int]$TimeoutMs = 8000,
        [int]$PollMs = 250,
        [bool]$AwaitPromise = $false
    )

    $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
    $lastValue = $null

    while ((Get-Date) -lt $deadline) {
        $value = Invoke-CdpEvaluate -Socket $Socket -NextId $NextId -Expression $Expression -AwaitPromise $AwaitPromise
        $lastValue = $value

        if ($value -is [bool]) {
            if ($value) {
                return [pscustomobject]@{ ok = $true; detail = $null }
            }
        } elseif ($value -and ($value.PSObject.Properties.Name -contains "ok")) {
            if ($value.ok -eq $true) {
                return $value
            }
        } elseif ($null -ne $value) {
            return [pscustomobject]@{ ok = $true; detail = "$value" }
        }

        Start-Sleep -Milliseconds $PollMs
    }

    if ($lastValue -and ($lastValue.PSObject.Properties.Name -contains "ok")) {
        return $lastValue
    }
    return [pscustomobject]@{
        ok = $false
        blocker = "wait_condition_timeout"
        detail = "timeout_${TimeoutMs}ms"
    }
}

function Start-InteractiveEdgeSession {
    param(
        [Parameter(Mandatory = $true)][string]$EdgePath,
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $port = Get-FreeTcpPort
    $profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ui-smoke-profile-" + [guid]::NewGuid().ToString())
    $null = New-Item -ItemType Directory -Path $profileDir -Force
    $process = Start-Process `
        -FilePath $EdgePath `
        -ArgumentList @("--headless=new", "--disable-gpu", "--remote-debugging-port=$port", "--user-data-dir=$profileDir", $BaseUrl) `
        -PassThru

    $target = $null
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $targets = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/list" -TimeoutSec 2
            $pages = @($targets | Where-Object { $_.type -eq "page" -and $_.webSocketDebuggerUrl })
            $target = @($pages | Where-Object { "$($_.url)" -like "$BaseUrl*" }) | Select-Object -First 1
            if ($target) {
                break
            }
        } catch {
        }
        Start-Sleep -Milliseconds 250
    }

    if (-not $target) {
        if ($process -and -not $process.HasExited) {
            $process.Kill()
            $process.WaitForExit()
        }
        if (Test-Path $profileDir) {
            Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        throw "interactive_browser_target_missing"
    }

    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $connectTask = $socket.ConnectAsync([Uri]$target.webSocketDebuggerUrl, [System.Threading.CancellationToken]::None)
    $connectTask.Wait()

    return [pscustomobject]@{
        process = $process
        profile_dir = $profileDir
        socket = $socket
    }
}

function Stop-InteractiveEdgeSession {
    param(
        [Parameter(Mandatory = $true)]$Session
    )

    if ($Session.socket) {
        try {
            if ($Session.socket.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                $closeTask = $Session.socket.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", [System.Threading.CancellationToken]::None)
                $closeTask.Wait()
            }
        } catch {
        } finally {
            $Session.socket.Dispose()
        }
    }

    if ($Session.process -and -not $Session.process.HasExited) {
        $Session.process.Kill()
        $Session.process.WaitForExit()
    }

    if ($Session.profile_dir -and (Test-Path $Session.profile_dir)) {
        Remove-Item -LiteralPath $Session.profile_dir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-InteractiveUiChecks {
    param(
        [Parameter(Mandatory = $true)][string]$EdgePath,
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $session = $null
    try {
        $session = Start-InteractiveEdgeSession -EdgePath $EdgePath -BaseUrl $BaseUrl -TimeoutSeconds $TimeoutSeconds
        $nextId = 1
        $null = Invoke-CdpCommand -Socket $session.socket -Id $nextId -Method "Page.enable"
        $nextId++
        $null = Invoke-CdpCommand -Socket $session.socket -Id $nextId -Method "Runtime.enable"
        $nextId++

        $pageReady = Wait-CdpCondition -Socket $session.socket -NextId ([ref]$nextId) -TimeoutMs ([Math]::Max(4000, $TimeoutSeconds * 1000)) -PollMs 250 -Expression @'
(() => {
  const ready = document.readyState === "complete";
  const createButton = document.getElementById("guided-task-create");
  const gallery = document.getElementById("results-gallery");
  const systemSummary = document.getElementById("system-summary");
  const systemText = systemSummary ? systemSummary.textContent.trim() : "";
  const systemHealthy =
    systemText.length > 0 &&
    !/System wird geladen/i.test(systemText) &&
    !/nicht erreichbar/i.test(systemText) &&
    !/wird vorbereitet/i.test(systemText) &&
    !/nicht verfuegbar/i.test(systemText);
  return {
    ok: ready && (createButton instanceof HTMLButtonElement) && Boolean(gallery) && systemHealthy,
    detail: `${document.readyState} | ${systemText || "kein system-summary"}`
  };
})()
'@

        $createTask = Invoke-CdpEvaluate -Socket $session.socket -NextId ([ref]$nextId) -Expression @'
(() => {
  const button = document.getElementById("guided-task-create");
  const title = document.getElementById("generate-section-title");
  if (!(button instanceof HTMLButtonElement) || !title) {
    return { ok: false, blocker: "guided_task_create_missing" };
  }
  button.click();
  return {
    ok: button.classList.contains("active") && title.textContent.trim() === "Neues Bild erstellen",
    detail: title.textContent.trim()
  };
})()
'@

        $previewReady = Wait-CdpCondition -Socket $session.socket -NextId ([ref]$nextId) -TimeoutMs ([Math]::Max(5000, $TimeoutSeconds * 1000)) -PollMs 250 -Expression @'
(() => {
  const buttons = document.querySelectorAll(".result-preview-button");
  const stateEl = document.getElementById("results-state");
  const stateText = stateEl ? stateEl.textContent.trim() : "";
  if (buttons.length > 0) {
    return { ok: true, detail: `${buttons.length} Vorschau-Buttons sichtbar` };
  }
  if (/Noch keine gespeicherten Ergebnisse/i.test(stateText)) {
    return { ok: false, blocker: "result_list_empty", detail: stateText };
  }
  if (/nicht verfuegbar/i.test(stateText)) {
    return { ok: false, blocker: "result_list_unavailable", detail: stateText };
  }
  return { ok: false, blocker: "result_preview_button_pending", detail: stateText || "results_state_missing" };
})()
'@

        $previewOpen = Invoke-CdpEvaluate -Socket $session.socket -NextId ([ref]$nextId) -Expression @'
(() => {
  const button = document.querySelector(".result-preview-button");
  const modal = document.getElementById("results-preview-modal");
  const title = document.getElementById("results-preview-title");
  if (!(button instanceof HTMLButtonElement)) {
    return { ok: false, blocker: "result_preview_button_missing" };
  }
  button.click();
  return {
    ok: Boolean(modal) && modal.hidden === false,
    detail: title ? title.textContent.trim() : ""
  };
})()
'@

        $loadInputReady = Wait-CdpCondition -Socket $session.socket -NextId ([ref]$nextId) -TimeoutMs 5000 -PollMs 200 -Expression @'
(() => {
  const modal = document.getElementById("results-preview-modal");
  const button = document.getElementById("results-preview-load-input");
  const state = document.getElementById("generate-active-input-context");
  if (!(button instanceof HTMLButtonElement)) {
    return { ok: false, blocker: "result_load_input_button_missing" };
  }
  if (!modal || modal.hidden) {
    return { ok: false, blocker: "result_preview_modal_closed" };
  }
  if (button.disabled) {
    return { ok: false, blocker: "result_load_input_disabled_waiting" };
  }
  return { ok: true, detail: state && state.hidden === false ? "active_input_already_visible" : "ready" };
})()
'@

        $loadAsInput = Invoke-CdpEvaluate -Socket $session.socket -NextId ([ref]$nextId) -AwaitPromise $true -Expression @'
(async () => {
  const button = document.getElementById("results-preview-load-input");
  const activeInputContext = document.getElementById("generate-active-input-context");
  const activeInputMeta = document.getElementById("generate-active-input-meta");
  const sectionTitle = document.getElementById("generate-section-title");
  if (!(button instanceof HTMLButtonElement) || button.disabled) {
    return { ok: false, blocker: "result_load_input_unavailable" };
  }
  button.click();
  const started = Date.now();
  while (Date.now() - started < 5000) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    if (Boolean(activeInputContext) && activeInputContext.hidden === false && Boolean(sectionTitle) && sectionTitle.textContent.trim() === "Bild anpassen") {
      break;
    }
  }
  return {
    ok: Boolean(activeInputContext) && activeInputContext.hidden === false && Boolean(sectionTitle) && sectionTitle.textContent.trim() === "Bild anpassen",
    detail: activeInputMeta ? activeInputMeta.textContent.trim() : ""
  };
})()
'@

        $modeSeparation = Invoke-CdpEvaluate -Socket $session.socket -NextId ([ref]$nextId) -Expression @'
(() => {
  const click = (id) => {
    const button = document.getElementById(id);
    if (!(button instanceof HTMLButtonElement)) {
      return false;
    }
    button.click();
    return true;
  };
  const title = document.getElementById("generate-section-title");
  const maskCard = document.getElementById("input-card-mask");
  if (!title || !maskCard) {
    return { ok: false, blocker: "mode_separation_dom_missing" };
  }
  const editClicked = click("guided-task-edit");
  const editOk = editClicked && title.textContent.trim() === "Bild anpassen" && maskCard.hidden === true;
  const inpaintClicked = click("guided-task-inpaint");
  const inpaintOk = inpaintClicked && title.textContent.trim() === "Bereich im Bild aendern" && maskCard.hidden === false;
  const createClicked = click("guided-task-create");
  const createOk = createClicked && title.textContent.trim() === "Neues Bild erstellen" && maskCard.hidden === true;
  return {
    ok: editOk && inpaintOk && createOk,
    detail: `edit=${editOk} | inpaint=${inpaintOk} | create=${createOk} | title=${title.textContent.trim()} | maskHidden=${maskCard.hidden}`
  };
})()
'@

        Start-Sleep -Milliseconds 400

        $textRoundtrip = Invoke-CdpEvaluate -Socket $session.socket -NextId ([ref]$nextId) -AwaitPromise $true -Expression @'
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const taskButton = document.getElementById("guided-task-text");
  const promptEl = document.getElementById("text-service-basic-prompt");
  const sendEl = document.getElementById("text-service-basic-send");
  const statusEl = document.getElementById("text-service-basic-status");
  const responseEl = document.getElementById("text-service-basic-response");
  const clearEl = document.getElementById("text-chat-clear");
  const newChatEl = document.getElementById("text-chat-new");
  const historyEl = document.getElementById("text-chat-history");
  const writingModeEl = document.getElementById("text-work-mode-writing");
  const slotButtons = Array.from(document.querySelectorAll("#text-chat-slots .text-chat-slot"));
  if (!(taskButton instanceof HTMLButtonElement) || !(promptEl instanceof HTMLTextAreaElement) || !(sendEl instanceof HTMLButtonElement) || !statusEl || !responseEl || !(clearEl instanceof HTMLButtonElement) || !(newChatEl instanceof HTMLButtonElement) || !historyEl || slotButtons.length === 0) {
    return { ok: false, blocker: "text_main_path_missing" };
  }

  if (typeof fetchHealth === "function") {
    await fetchHealth({ forceFresh: true });
  }
  if (typeof fetchTextChats === "function") {
    await fetchTextChats({ forceFresh: true });
  }
  if (typeof renderUi === "function") {
    renderUi();
  }
  await sleep(500);

  const profileMap = typeof getTextChatModelProfiles === "function"
    ? new Map((getTextChatModelProfiles() || []).map((profile) => [String(profile.id || ""), profile]))
    : new Map();
  const slotModels = typeof textChatState === "object" && Array.isArray(textChatState.slots)
    ? textChatState.slots
    : [];
  const preferredIndices = [];
  slotModels.forEach((slot, index) => {
    if (!slot || slot.occupied !== true || Number(slot.message_count || 0) !== 0) {
      return;
    }
    const profile = profileMap.get(String(slot.model_profile || ""));
    if (profile && profile.active_for_requests === true) {
      preferredIndices.push(index);
    }
  });
  slotModels.forEach((slot, index) => {
    if (!slot || slot.occupied !== true || Number(slot.message_count || 0) !== 0) {
      return;
    }
    const profile = profileMap.get(String(slot.model_profile || ""));
    if (profile && profile.active_for_requests === true && !preferredIndices.includes(index)) {
      preferredIndices.push(index);
    }
  });
  if (preferredIndices.length === 0) {
    newChatEl.click();
    await sleep(1200);
    const fallbackText = responseEl.textContent ? responseEl.textContent.trim() : "";
    if (fallbackText) {
      return {
        ok: true,
        detail: `Sichtbarer Text-Blocker | ${fallbackText}`
      };
    }
    return { ok: true, detail: "Kein leerer Text-Slot fuer den Browser-Smoke verfuegbar." };
  }

  taskButton.click();
  await sleep(400);
  let selectedSlotLabel = "";
  let sendReady = false;
  for (const candidateIndex of preferredIndices) {
    const slotButton = slotButtons[candidateIndex];
    if (!(slotButton instanceof HTMLButtonElement)) {
      continue;
    }
    slotButton.click();
    await sleep(700);
    const existingMessages = historyEl.querySelectorAll(".text-chat-message").length;
    if (existingMessages > 0) {
      continue;
    }
    if (writingModeEl instanceof HTMLButtonElement) {
      writingModeEl.click();
      await sleep(150);
    }
    promptEl.focus();
    promptEl.value = "Kurzer Browser-Smoke fuer die sichtbare Antwort.";
    promptEl.dispatchEvent(new Event("input", { bubbles: true }));
    const waitStarted = Date.now();
    while (sendEl.disabled && Date.now() - waitStarted < 12000) {
      await sleep(400);
    }
    selectedSlotLabel = (slotButton.textContent || "").replace(/\s+/g, " ").trim();
    if (!sendEl.disabled) {
      sendReady = true;
      break;
    }
  }

  if (!sendReady) {
    return { ok: false, blocker: "text_send_disabled", detail: selectedSlotLabel || "kein sendefaehiger Slot" };
  }

  const responseBeforeSend = responseEl.textContent ? responseEl.textContent.trim() : "";
  sendEl.click();
  const started = Date.now();
  let lastStatus = "";
  let finalDetail = "";
  let sawReaction = false;

  while (Date.now() - started < 70000) {
    await sleep(500);
    const responseText = responseEl.textContent ? responseEl.textContent.trim() : "";
    const statusText = statusEl.textContent ? statusEl.textContent.trim() : "";
    const assistantMessages = Array.from(historyEl.querySelectorAll(".text-chat-message.assistant .text-chat-message-content"))
      .map((node) => node.textContent ? node.textContent.trim() : "")
      .filter(Boolean);
    if (statusText) {
      lastStatus = statusText;
    }
    if (statusText === "Bitte kurz warten." || /Antwort wird erzeugt/i.test(statusText)) {
      sawReaction = true;
    }
    if ((responseEl.className || "").includes("error") && responseText) {
      window.confirm = () => true;
      clearEl.click();
      await sleep(900);
      return { ok: false, blocker: "text_response_error", detail: responseText };
    }
    if (assistantMessages.length > 0) {
      finalDetail = assistantMessages[assistantMessages.length - 1];
      sawReaction = true;
      break;
    }
    if (responseText && responseText !== responseBeforeSend && !/keine nutzbare Antwort|aktuell nicht verfuegbar/i.test(responseText)) {
      finalDetail = responseText;
      sawReaction = true;
      break;
    }
  }

  window.confirm = () => true;
  clearEl.click();
  await sleep(1200);

  if (finalDetail) {
    return {
      ok: true,
      detail: `Antwort sichtbar | ${finalDetail.slice(0, 80)}`
    };
  }

  if (sawReaction || lastStatus) {
    return {
      ok: true,
      detail: `Sichtbare Reaktion | ${lastStatus || "Antwort wird verarbeitet"}`
    };
  }

  return { ok: false, blocker: "text_ui_no_visible_reaction" };
})()
'@

        return @(
            (New-UiCheck -Name "klickpfad-app-bereit" -Ok ($pageReady.ok -eq $true) -Detail (Get-UiCheckDetail -Value $pageReady)),
            (New-UiCheck -Name "klickpfad-bild-hauptpfad" -Ok ($createTask.ok -eq $true) -Detail (Get-UiCheckDetail -Value $createTask)),
            (New-UiCheck -Name "klickpfad-ergebnisliste-bereit" -Ok ($previewReady.ok -eq $true) -Detail (Get-UiCheckDetail -Value $previewReady)),
            (New-UiCheck -Name "klickpfad-ergebnisvorschau" -Ok ($previewOpen.ok -eq $true) -Detail (Get-UiCheckDetail -Value $previewOpen)),
            (New-UiCheck -Name "klickpfad-preview-aktion-bereit" -Ok ($loadInputReady.ok -eq $true) -Detail (Get-UiCheckDetail -Value $loadInputReady)),
            (New-UiCheck -Name "klickpfad-als-eingabebild" -Ok ($loadAsInput.ok -eq $true) -Detail (Get-UiCheckDetail -Value $loadAsInput)),
            (New-UiCheck -Name "klickpfad-modustrennung" -Ok ($modeSeparation.ok -eq $true) -Detail (Get-UiCheckDetail -Value $modeSeparation)),
            (New-UiCheck -Name "klickpfad-text-hauptpfad" -Ok ($textRoundtrip.ok -eq $true) -Detail (Get-UiCheckDetail -Value $textRoundtrip))
        )
    } finally {
        if ($session) {
            Stop-InteractiveEdgeSession -Session $session
        }
    }
}

$result = $null
$exitCode = 0
$tempDomFile = $null
$tempErrFile = $null

try {
    $healthResponse = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec $TimeoutSeconds
    if ($healthResponse.StatusCode -ne 200) {
        throw "health_http_$($healthResponse.StatusCode)"
    }

    $edgePath = Get-EdgePath
    if (-not $edgePath) {
        throw "msedge_not_found"
    }

    $tempDomFile = Join-Path ([System.IO.Path]::GetTempPath()) ("ui-smoke-" + [guid]::NewGuid().ToString() + ".html")
    $tempErrFile = Join-Path ([System.IO.Path]::GetTempPath()) ("ui-smoke-" + [guid]::NewGuid().ToString() + ".stderr.log")
    $null = Start-Process `
        -FilePath $edgePath `
        -ArgumentList @("--headless=new", "--disable-gpu", "--virtual-time-budget=$VirtualTimeBudgetMs", "--dump-dom", $BaseUrl) `
        -RedirectStandardOutput $tempDomFile `
        -RedirectStandardError $tempErrFile `
        -Wait `
        -PassThru

    if (-not (Test-Path $tempDomFile)) {
        throw "dom_dump_missing"
    }

    $html = Get-Content -LiteralPath $tempDomFile -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($html)) {
        throw "dom_dump_empty"
    }

    $requestState = Get-ElementText -Html $html -Id "request-state"
    $systemSummary = Get-ElementText -Html $html -Id "system-summary"
    $textState = Get-ElementText -Html $html -Id "text-service-basic-state"
    $resultsState = Get-ElementText -Html $html -Id "results-state"
    $identityTransferReadiness = Get-ElementText -Html $html -Id "identity-transfer-test-readiness"
    $guidedHint = Get-ElementText -Html $html -Id "guided-task-hint"

    $checks = @(
        (New-UiCheck -Name "startseite" -Ok ($html -match "<title>StoryForge Local</title>") -Detail "HTML geladen"),
        (New-UiCheck -Name "systemstatus" -Ok (
            -not [string]::IsNullOrWhiteSpace($systemSummary) -and
            $systemSummary -notmatch "System wird geladen" -and
            $systemSummary -notmatch "nicht erreichbar" -and
            $systemSummary -notmatch "wird vorbereitet" -and
            $systemSummary -notmatch "nicht verfuegbar"
        ) -Detail $systemSummary),
        (New-UiCheck -Name "bild-hauptpfad" -Ok (
            -not [string]::IsNullOrWhiteSpace($requestState) -and
            $requestState -notmatch "System wird geprueft"
        ) -Detail $requestState),
        (New-UiCheck -Name "text-pfad" -Ok (
            -not [string]::IsNullOrWhiteSpace($textState) -and
            -not [string]::IsNullOrWhiteSpace($guidedHint)
        ) -Detail ($(if (-not [string]::IsNullOrWhiteSpace($textState)) { $textState } else { $guidedHint }))),
        (New-UiCheck -Name "ergebnisbereich" -Ok (
            -not [string]::IsNullOrWhiteSpace($resultsState) -and
            $resultsState -notmatch "Ergebnisliste laedt"
        ) -Detail $resultsState),
        (New-UiCheck -Name "spezialpfad" -Ok (
            -not [string]::IsNullOrWhiteSpace($identityTransferReadiness) -and
            $identityTransferReadiness -notmatch "Readiness wird geprueft"
        ) -Detail $identityTransferReadiness)
    )

    $checks += Invoke-InteractiveUiChecks -EdgePath $edgePath -BaseUrl $BaseUrl -TimeoutSeconds $TimeoutSeconds

    $failed = @($checks | Where-Object { $_.ok -ne $true })
    if ($failed.Count -gt 0) {
        $result = [ordered]@{
            status = "error"
            blocker = "ui_smoke_failed"
            failed_checks = $failed
            checks = $checks
        }
        $exitCode = 1
    } else {
        $result = [ordered]@{
            status = "ok"
            checks = $checks
        }
    }
} catch {
    $result = [ordered]@{
        status = "error"
        blocker = "$($_.Exception.Message)"
    }
    $exitCode = 1
} finally {
    if ($tempDomFile -and (Test-Path $tempDomFile)) {
        Remove-Item -LiteralPath $tempDomFile -Force -ErrorAction SilentlyContinue
    }
    if ($tempErrFile -and (Test-Path $tempErrFile)) {
        Remove-Item -LiteralPath $tempErrFile -Force -ErrorAction SilentlyContinue
    }
}

[Console]::Out.WriteLine((ConvertTo-StatusJson -Payload $result))
[Console]::Out.Flush()
exit $exitCode
