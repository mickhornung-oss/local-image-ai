    const VALID_MODES = new Set(["auto", "sdxl", "placeholder"]);
    const VALID_UPLOAD_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp"]);
    const VALID_UPLOAD_MIME_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
    const HEALTH_POLL_INTERVAL_MS = 4000;
    const OFFLINE_FAILURE_THRESHOLD = 2;
    const TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH = 2000;
    const TEXT_RESPONSE_COPY_NOTICE_DURATION_MS = 1800;
    const SERVER_RENDER_STALE_MS = 300000;
    const SERVER_RENDER_FUTURE_SKEW_MS = 30000;
    const NEGATIVE_PROMPT_MAX_LENGTH = 2000;
    const DEFAULT_IMG2IMG_DENOISE = 0.25;
    const DEFAULT_INPAINT_DENOISE = 0.58;
    const DEFAULT_INPAINT_PERSON_NEGATIVE_PROMPT = "bad anatomy, bad proportions, deformed body, bad hands, extra fingers, deformed face, blurry";
    const MIN_IMG2IMG_DENOISE = 0.05;
    const MAX_IMG2IMG_DENOISE = 0.55;
    const MAX_INPAINT_DENOISE = 0.80;
    const TRANSIENT_BUSY_NOTICE_DURATION_MS = 4000;
    const TRANSIENT_CLIENT_PRECHECK_ERROR_DURATION_MS = 4000;
    const TRANSIENT_INFO_NOTICE_DURATION_MS = 4000;
    const MASK_EDITOR_DEFAULT_BRUSH = 28;
    const MASK_EDITOR_MIN_BRUSH = 8;
    const MASK_EDITOR_MAX_BRUSH = 96;
    const MULTI_REFERENCE_MAX_SLOTS = 3;
    const IDENTITY_TRANSFER_ROLE_CONFIG = [
      { role: "identity_head_reference", label: "Kopf-Referenzbild", required: true },
      { role: "target_body_image", label: "Zielbild", required: true },
      { role: "pose_reference", label: "Pose-Referenz", required: false },
      { role: "transfer_mask", label: "Transfer-Maske", required: false }
    ];
    const BASIC_IMAGE_TASK_IDS = ["create", "edit", "inpaint"];
    const RESULTS_FETCH_LIMIT = 20;
    const LAST_SUCCESS_STORAGE_KEY = "local-image-app:last-success";
    const INTERRUPTED_REQUEST_STORAGE_KEY = "local-image-app:interrupted-request";
    const SPEECH_USAGE_STORAGE_KEY = "storyforge:speech-usage:v1";
    const V7_VIEW_MODE_STORAGE_KEY = "local-image-app:v7:view-mode";
    const V7_BASIC_TASK_STORAGE_KEY = "local-image-app:v7:basic-task";
    const V11_BASIC_IMAGE_STYLE_STORAGE_KEY = "local-image-app:v11:basic-image-style";
    const V11_IDENTITY_SINGLE_IMAGE_STYLE_STORAGE_KEY = "local-image-app:v11:identity-single-image-style";
    const SPEECH_INPUT_FEEDBACK_DURATION_MS = 2200;
    const SPEECH_CAPTURE_MAX_MS = 60000;
    const SPEECH_STATUS_ENDPOINT = "/speech/status";
    const SPEECH_TRANSCRIBE_ENDPOINT = "/speech/transcribe";
    const SETTLED_REQUEST_HISTORY_LIMIT = 32;
    const INPUT_UPLOAD_ERROR_TYPES = new Set(["invalid_request", "invalid_upload", "upload_error"]);
    const BASIC_IMAGE_STYLE_CONFIG = {
      photo: {
        id: "photo",
        label: "Foto",
        hint: "passt fuer natuerliche Gesichter und realistische Szenen.",
        checkpoint_mode: "photo_standard"
      },
      anime: {
        id: "anime",
        label: "Anime",
        hint: "passt fuer stilisierte Anime-Bilder; Motiv und Komposition koennen freier interpretiert werden.",
        checkpoint_mode: "anime_standard"
      }
    };
    const V7_TASK_CONFIG = [
      {
        id: "text",
        label: "Schreiben",
        hint: "Text schreiben, ueberarbeiten und Bildprompts ableiten. Der Schreibbereich ist das Hauptarbeitsobjekt.",
        section_ids: ["section-text-service-basic"]
      },
      {
        id: "create",
        label: "Neues Bild erstellen",
        hint: "Beschreibe Motiv, Stil, Licht und Stimmung. Dieser Weg ist der normale Start fuer ein neues Bild.",
        section_ids: ["section-generate"]
      },
      {
        id: "edit",
        label: "Bild anpassen",
        hint: "Lade ein Bild und beschreibe eine leichte bis mittlere Aenderung am bestehenden Motiv.",
        section_ids: ["section-input-images", "section-generate"]
      },
      {
        id: "identity-single",
        label: "Sonderpfad: Neue Szene mit derselben Person",
        hint: "Aktuell nicht verlaesslich freigegeben. Gleiche Person in neuer Szene driftet auf diesem lokalen Stand noch zu stark.",
        section_ids: ["section-identity-reference"]
      },
      {
        id: "inpaint",
        label: "Bereich im Bild aendern",
        hint: "Markiere zuerst den Bereich und beschreibe nur dort die Aenderung. Dieser Weg ist fuer lokale Korrekturen gedacht.",
        section_ids: ["section-input-images", "section-generate"]
      }
    ];
    const V7_TASK_CONFIG_BY_ID = Object.fromEntries(
      V7_TASK_CONFIG.map((config) => [config.id, config])
    );
    const guidedModeBasicEl = document.getElementById("view-mode-basic");
    const guidedModeExpertEl = document.getElementById("view-mode-expert");
    const guidedModeStateEl = document.getElementById("guided-mode-state");
    const guidedTaskHintEl = document.getElementById("guided-task-hint");
    const guidedTaskAreaEl = document.getElementById("guided-task-area");
    const guidedOpenExpertEl = document.getElementById("guided-open-expert");
    const sectionBasicTaskFocusEl = document.getElementById("section-basic-task-focus");
    const basicTaskFocusTitleEl = document.getElementById("basic-task-focus-title");
    const basicTaskFocusHintEl = document.getElementById("basic-task-focus-hint");
    const basicTaskFocusNoteEl = document.getElementById("basic-task-focus-note");
    const basicTaskFocusExtraEl = document.getElementById("basic-task-focus-extra");
    const basicTaskFocusActionsEl = document.getElementById("basic-task-focus-actions");
    const basicTaskOpenExpertEl = document.getElementById("basic-task-open-expert");
    const basicTaskOpenExpertHintEl = document.getElementById("basic-task-open-expert-hint");
    const sectionExpertOverviewEl = document.getElementById("section-expert-overview");
    const guidedTaskButtonEls = Object.fromEntries(
      V7_TASK_CONFIG.map((config) => [
        config.id,
        document.getElementById(`guided-task-${config.id}`)
      ])
    );
    const sectionGenerateEl = document.getElementById("section-generate");
    const sectionTextServiceBasicEl = document.getElementById("section-text-service-basic");
    const sectionTextServiceTestEl = document.getElementById("section-text-service-test");
    const sectionInputImagesEl = document.getElementById("section-input-images");
    const sectionIdentityReferenceEl = document.getElementById("section-identity-reference");
    const sectionIdentityMultiReferenceEl = document.getElementById("section-identity-multi-reference");
    const sectionIdentityTransferEl = document.getElementById("section-identity-transfer");
    const sectionCurrentResultEl = document.getElementById("section-current-result");
    const sectionResultsEl = document.getElementById("section-results");
    const generateSectionTitleEl = document.getElementById("generate-section-title");
    const generateSectionHintEl = document.getElementById("generate-section-hint");
    const generateBasicGuideEl = document.getElementById("generate-basic-guide");
    const generateActiveInputContextEl = document.getElementById("generate-active-input-context");
    const generateActiveInputPreviewEl = document.getElementById("generate-active-input-preview");
    const generateActiveInputMetaEl = document.getElementById("generate-active-input-meta");
    const basicImageStyleSwitchEl = document.getElementById("basic-image-style-switch");
    const basicImageStyleHintEl = document.getElementById("basic-image-style-hint");
    const basicImageStylePhotoEl = document.getElementById("basic-image-style-photo");
    const basicImageStyleAnimeEl = document.getElementById("basic-image-style-anime");
    const textServiceBasicSectionTitleEl = document.getElementById("text-service-basic-section-title");
    const textServiceBasicSectionHintEl = document.getElementById("text-service-basic-section-hint");
    const textServiceBasicGuideEl = document.getElementById("text-service-basic-guide");
    const generateControlGridEl = document.getElementById("generate-control-grid");
    const generateControlModeEl = document.getElementById("generate-control-mode");
    const generateControlCheckpointEl = document.getElementById("generate-control-checkpoint");
    const generateControlInputToggleEl = document.getElementById("generate-control-input-toggle");
    const generateControlDenoiseEl = document.getElementById("generate-control-denoise");
    const generateControlInpaintToggleEl = document.getElementById("generate-control-inpaint-toggle");
    const inputImagesSectionTitleEl = document.getElementById("input-images-section-title");
    const inputImagesSectionHintEl = document.getElementById("input-images-section-hint");
    const inputImagesBasicGuideEl = document.getElementById("input-images-basic-guide");
    const inputCardSourceEl = document.getElementById("input-card-source");
    const inputCardMaskEl = document.getElementById("input-card-mask");
    const identityReferenceSectionTitleEl = document.getElementById("identity-reference-section-title");
    const identityReferenceSectionHintEl = document.getElementById("identity-reference-section-hint");
    const identityReferenceBasicGuideEl = document.getElementById("identity-reference-basic-guide");
    const identityReferenceCardTitleEl = document.getElementById("identity-reference-card-title");
    const identityReferenceCardCopyEl = document.getElementById("identity-reference-card-copy");
    const identityRunCardTitleEl = document.getElementById("identity-run-card-title");
    const identityRunCardCopyEl = document.getElementById("identity-run-card-copy");
    const identitySingleStyleSwitchEl = document.getElementById("identity-single-style-switch");
    const identitySingleStyleHintEl = document.getElementById("identity-single-style-hint");
    const identitySingleStylePhotoEl = document.getElementById("identity-single-style-photo");
    const identitySingleStyleAnimeEl = document.getElementById("identity-single-style-anime");
    const identityMultiSectionTitleEl = document.getElementById("identity-multi-section-title");
    const identityMultiSectionHintEl = document.getElementById("identity-multi-section-hint");
    const identityMultiBasicGuideEl = document.getElementById("identity-multi-basic-guide");
    const multiReferenceCardTitleEl = document.getElementById("multi-reference-card-title");
    const multiReferenceCardCopyEl = document.getElementById("multi-reference-card-copy");
    const multiReferenceSlotSelectLabelEl = document.getElementById("multi-reference-slot-select-label");
    const multiReferenceRunCardTitleEl = document.getElementById("multi-reference-run-card-title");
    const multiReferenceRunCardCopyEl = document.getElementById("multi-reference-run-card-copy");
    const multiReferenceRunOutputCopyEl = document.getElementById("multi-reference-run-output-copy");
    const identityTransferSectionTitleEl = document.getElementById("identity-transfer-section-title");
    const identityTransferSectionHintEl = document.getElementById("identity-transfer-section-hint");
    const identityTransferRolesSectionTitleEl = document.getElementById("identity-transfer-roles-section-title");
    const identityTransferRolesSectionHintEl = document.getElementById("identity-transfer-roles-section-hint");
    const identityTransferRolesBasicGuideEl = document.getElementById("identity-transfer-roles-basic-guide");
    const identityTransferTestSectionTitleEl = document.getElementById("identity-transfer-test-section-title");
    const identityTransferTestSectionHintEl = document.getElementById("identity-transfer-test-section-hint");
    const identityTransferTestBasicGuideEl = document.getElementById("identity-transfer-test-basic-guide");
    const identityTransferStatusCardTitleEl = document.getElementById("identity-transfer-status-card-title");
    const identityTransferRunCardTitleEl = document.getElementById("identity-transfer-run-card-title");
    const identityTransferRunCardCopyEl = document.getElementById("identity-transfer-run-card-copy");
    const inputFileEl = document.getElementById("input-file");
    const pasteTargetEl = document.getElementById("paste-target");
    const uploadImageEl = document.getElementById("upload-image");
    const resetInputImageEl = document.getElementById("reset-input-image");
    const uploadStateEl = document.getElementById("upload-state");
    const uploadHintEl = document.getElementById("upload-hint");
    const inputMetaEl = document.getElementById("input-meta");
    const inputPreviewEl = document.getElementById("input-preview");
    const maskFileEl = document.getElementById("mask-file");
    const uploadMaskEl = document.getElementById("upload-mask");
    const resetMaskImageEl = document.getElementById("reset-mask-image");
    const maskUploadStateEl = document.getElementById("mask-upload-state");
    const maskUploadHintEl = document.getElementById("mask-upload-hint");
    const maskMetaEl = document.getElementById("mask-meta");
    const maskPreviewEl = document.getElementById("mask-preview");
    const maskToolBrushEl = document.getElementById("mask-tool-brush");
    const maskToolEraserEl = document.getElementById("mask-tool-eraser");
    const maskBrushSizeEl = document.getElementById("mask-brush-size");
    const maskEditorEmptyEl = document.getElementById("mask-editor-empty");
    const maskEditorStageEl = document.getElementById("mask-editor-stage");
    const maskEditorSourceEl = document.getElementById("mask-editor-source");
    const maskEditorOverlayEl = document.getElementById("mask-editor-overlay");
    const maskEditorClearEl = document.getElementById("mask-editor-clear");
    const maskEditorSaveEl = document.getElementById("mask-editor-save");
    const maskEditorStateEl = document.getElementById("mask-editor-state");
    const identityReferenceFileEl = document.getElementById("identity-reference-file");
    const uploadIdentityReferenceEl = document.getElementById("upload-identity-reference");
    const resetIdentityReferenceEl = document.getElementById("reset-identity-reference");
    const identityReferenceStateEl = document.getElementById("identity-reference-state");
    const identityReferenceHintEl = document.getElementById("identity-reference-hint");
    const identityReferenceMetaEl = document.getElementById("identity-reference-meta");
    const identityReferencePreviewEl = document.getElementById("identity-reference-preview");
    const identityVerfuegbarkeitEl = document.getElementById("identity-readiness");
    const identityPromptEl = document.getElementById("identity-prompt");
    const identityGenerateEl = document.getElementById("identity-generate");
    const identityRunStateEl = document.getElementById("identity-run-state");
    const identityRunHintEl = document.getElementById("identity-run-hint");
    const identityProgressPanelEl = document.getElementById("identity-progress-panel");
    const identityProgressTitleEl = document.getElementById("identity-progress-title");
    const identityProgressMetaEl = document.getElementById("identity-progress-meta");
    const identityProgressStepsEl = document.getElementById("identity-progress-steps");
    const identityResultImageEl = document.getElementById("identity-result-image");
    const multiReferenceVerfuegbarkeitEl = document.getElementById("multi-reference-readiness");
    const multiReferenceFileEl = document.getElementById("multi-reference-file");
    const multiReferenceSlotSelectEl = document.getElementById("multi-reference-slot-select");
    const uploadMultiReferenceEl = document.getElementById("upload-multi-reference");
    const resetAllMultiReferenceEl = document.getElementById("reset-all-multi-reference");
    const multiReferenceStateEl = document.getElementById("multi-reference-state");
    const multiReferenceHintEl = document.getElementById("multi-reference-hint");
    const multiReferenceRuntimeVerfuegbarkeitEl = document.getElementById("multi-reference-runtime-readiness");
    const multiReferencePromptEl = document.getElementById("multi-reference-prompt");
    const multiReferenceGenerateEl = document.getElementById("multi-reference-generate");
    const multiReferenceRunStateEl = document.getElementById("multi-reference-run-state");
    const multiReferenceRunHintEl = document.getElementById("multi-reference-run-hint");
    const multiReferenceSlotStateEls = [
      null,
      document.getElementById("multi-reference-slot-state-1"),
      document.getElementById("multi-reference-slot-state-2"),
      document.getElementById("multi-reference-slot-state-3")
    ];
    const multiReferenceSlotMetaEls = [
      null,
      document.getElementById("multi-reference-slot-meta-1"),
      document.getElementById("multi-reference-slot-meta-2"),
      document.getElementById("multi-reference-slot-meta-3")
    ];
    const multiReferenceSlotPreviewEls = [
      null,
      document.getElementById("multi-reference-slot-preview-1"),
      document.getElementById("multi-reference-slot-preview-2"),
      document.getElementById("multi-reference-slot-preview-3")
    ];
    const resetMultiReferenceSlotEls = [
      null,
      document.getElementById("reset-multi-reference-slot-1"),
      document.getElementById("reset-multi-reference-slot-2"),
      document.getElementById("reset-multi-reference-slot-3")
    ];
    const identityTransferVerfuegbarkeitEl = document.getElementById("identity-transfer-readiness");
    const resetAllIdentityTransferEl = document.getElementById("reset-all-identity-transfer");
    const identityTransferStateEl = document.getElementById("identity-transfer-state");
    const identityTransferHintEl = document.getElementById("identity-transfer-hint");
    const identityTransferRoleViews = Object.fromEntries(
      IDENTITY_TRANSFER_ROLE_CONFIG.map((config) => [
        config.role,
        {
          ...config,
          fileEl: document.getElementById(`identity-transfer-file-${config.role}`),
          uploadEl: document.getElementById(`upload-identity-transfer-${config.role}`),
          resetEl: document.getElementById(`reset-identity-transfer-${config.role}`),
          stateEl: document.getElementById(`identity-transfer-role-state-${config.role}`),
          metaEl: document.getElementById(`identity-transfer-role-meta-${config.role}`),
          previewEl: document.getElementById(`identity-transfer-role-preview-${config.role}`)
        }
      ])
    );
    const identityTransferTestVerfuegbarkeitEl = document.getElementById("identity-transfer-test-readiness");
    const identityTransferTestHintEl = document.getElementById("identity-transfer-test-hint");
    const identityTransferPromptEl = document.getElementById("identity-transfer-prompt");
    const identityTransferGenerateEl = document.getElementById("identity-transfer-generate");
    const identityTransferMaskHybridGenerateEl = document.getElementById("identity-transfer-mask-hybrid-generate");
    const identityTransferRunStateEl = document.getElementById("identity-transfer-run-state");
    const identityTransferMaskHybridScopeEl = document.getElementById("identity-transfer-mask-hybrid-scope");
    const identityTransferMaskHybridLimitsEl = document.getElementById("identity-transfer-mask-hybrid-limits");
    const identityTransferRunHintEl = document.getElementById("identity-transfer-run-hint");
    const identityTransferResultImageEl = document.getElementById("identity-transfer-result-image");
    const identityTransferTestRoleViews = Object.fromEntries(
      IDENTITY_TRANSFER_ROLE_CONFIG.map((config) => [
        config.role,
        {
          ...config,
          stateEl: document.getElementById(`identity-transfer-test-role-state-${config.role}`),
          previewEl: document.getElementById(`identity-transfer-test-role-preview-${config.role}`)
        }
      ])
    );
    const promptEl = document.getElementById("prompt");
    const negativePromptEl = document.getElementById("negative-prompt");
    const negativePromptHintEl = document.getElementById("negative-prompt-hint");
    const standardNegativePromptRowEl = document.getElementById("standard-negative-prompt-row");
    const useStandardNegativePromptEl = document.getElementById("use-standard-negative-prompt");
    const standardNegativePromptCopyEl = document.getElementById("standard-negative-prompt-copy");
    const modeEl = document.getElementById("mode");
    const checkpointEl = document.getElementById("checkpoint");
    const useInputImageEl = document.getElementById("use-input-image");
    const denoiseStrengthEl = document.getElementById("denoise-strength");
    const useInpaintingEl = document.getElementById("use-inpainting");
    const generateEl = document.getElementById("generate");
    const requestStateEl = document.getElementById("request-state");
    const generateProgressPanelEl = document.getElementById("generate-progress-panel");
    const generateProgressTitleEl = document.getElementById("generate-progress-title");
    const generateProgressMetaEl = document.getElementById("generate-progress-meta");
    const generateProgressStepsEl = document.getElementById("generate-progress-steps");
    const actionFeedbackEl = document.getElementById("action-feedback");
    const systemSummaryEl = document.getElementById("system-summary");
    const textBodyEl = document.getElementById("text-body");
    const textBodyClearEl = document.getElementById("text-body-clear");
    const textBodySpeechTargetEl = document.getElementById("text-body-speech-target");
    const textBodyContextHintEl = document.getElementById("text-body-context-hint");
    const textBodyInsertEl = document.getElementById("text-body-insert");
    const textBodyReplaceEl = document.getElementById("text-body-replace");
    const textResponsePanelEl = document.getElementById("text-response-panel");
    const textToImageForwardEl = document.getElementById("text-to-image-forward");
    const textToImageGoEl = document.getElementById("text-to-image-go");
    const textServiceBasicPromptEl = document.getElementById("text-service-basic-prompt");
    const textServiceBasicSendEl = document.getElementById("text-service-basic-send");
    const textServiceBasicStateEl = document.getElementById("text-service-basic-state");
    const textServiceBasicStatusEl = document.getElementById("text-service-basic-status");
    const textServiceBasicResponseEl = document.getElementById("text-service-basic-response");
    const textServiceBasicApplyTargetEl = document.getElementById("text-service-basic-apply-target");
    const textServiceBasicApplyImagePromptEl = document.getElementById("text-service-basic-apply-image-prompt");
    const textServiceBasicApplyStateEl = document.getElementById("text-service-basic-apply-state");
    const textServiceBasicCopyEl = document.getElementById("text-service-basic-copy");
    const textServiceBasicCopyStateEl = document.getElementById("text-service-basic-copy-state");
    const textChatSlotStateEl = document.getElementById("text-chat-slot-state");
    const textChatSlotsEl = document.getElementById("text-chat-slots");
    const textChatActiveMetaEl = document.getElementById("text-chat-active-meta");
    const textChatSummaryEl = document.getElementById("text-chat-summary");
    const textChatHistoryEl = document.getElementById("text-chat-history");
    const textChatNewEl = document.getElementById("text-chat-new");
    const textChatRenameEl = document.getElementById("text-chat-rename");
    const textChatClearEl = document.getElementById("text-chat-clear");
    const textModelProfileGridEl = document.getElementById("text-model-profile-grid");
    const textModelProfileHintEl = document.getElementById("text-model-profile-hint");
    const textWorkModeWritingEl = document.getElementById("text-work-mode-writing");
    const textWorkModeRewriteEl = document.getElementById("text-work-mode-rewrite");
    const textWorkModeImageEl = document.getElementById("text-work-mode-image");
    const textWorkModeHintEl = document.getElementById("text-work-mode-hint");
    const textServicePromptEl = document.getElementById("text-service-prompt");
    const textServiceSendEl = document.getElementById("text-service-send");
    const textServiceTestStateEl = document.getElementById("text-service-test-state");
    const textServiceTestResponseEl = document.getElementById("text-service-test-response");
    const textServiceTestCopyEl = document.getElementById("text-service-test-copy");
    const textServiceTestCopyStateEl = document.getElementById("text-service-test-copy-state");
    const speechInputControllers = Object.fromEntries([
      {
        key: "text-body",
        fieldEl: textBodyEl,
        buttonEl: document.getElementById("text-body-speech-button"),
        feedbackEl: document.getElementById("text-body-speech-state"),
        resolveInsertMode: () => {
          if (!(textBodySpeechTargetEl instanceof HTMLSelectElement)) {
            return "append";
          }
          const value = textBodySpeechTargetEl.value;
          if (value === "replace") return "replace";
          if (value === "insert") return "insert";
          return "append";
        }
      },
      {
        key: "generate",
        fieldEl: promptEl,
        buttonEl: document.getElementById("prompt-speech-button"),
        feedbackEl: document.getElementById("prompt-speech-state")
      },
      {
        key: "text-basic",
        fieldEl: textServiceBasicPromptEl,
        buttonEl: document.getElementById("text-service-basic-prompt-speech-button"),
        feedbackEl: document.getElementById("text-service-basic-prompt-speech-state")
      },
      {
        key: "text-test",
        fieldEl: textServicePromptEl,
        buttonEl: document.getElementById("text-service-prompt-speech-button"),
        feedbackEl: document.getElementById("text-service-prompt-speech-state")
      },
      {
        key: "identity",
        fieldEl: identityPromptEl,
        buttonEl: document.getElementById("identity-prompt-speech-button"),
        feedbackEl: document.getElementById("identity-prompt-speech-state")
      },
      {
        key: "multi-reference",
        fieldEl: multiReferencePromptEl,
        buttonEl: document.getElementById("multi-reference-prompt-speech-button"),
        feedbackEl: document.getElementById("multi-reference-prompt-speech-state")
      },
      {
        key: "identity-transfer",
        fieldEl: identityTransferPromptEl,
        buttonEl: document.getElementById("identity-transfer-prompt-speech-button"),
        feedbackEl: document.getElementById("identity-transfer-prompt-speech-state"),
        resolveInsertMode: () => "insert"
      }
    ].map((controller) => [controller.key, controller]));
    const resultSummaryEl = document.getElementById("result-summary");
    const imageStateEl = document.getElementById("image-state");
    const imageEl = document.getElementById("image");
    const resultsStateEl = document.getElementById("results-state");
    const resultsStorageEl = document.getElementById("results-storage");
    const resultsGalleryEl = document.getElementById("results-gallery");
    const resultsRefreshEl = document.getElementById("results-refresh");
    const resultsExportStateEl = document.getElementById("results-export-state");
    const resultsDeleteStateEl = document.getElementById("results-delete-state");
    const resultsPreviewModalEl = document.getElementById("results-preview-modal");
    const resultsPreviewTitleEl = document.getElementById("results-preview-title");
    const resultsPreviewMetaEl = document.getElementById("results-preview-meta");
    const resultsPreviewImageEl = document.getElementById("results-preview-image");
    const resultsPreviewDownloadEl = document.getElementById("results-preview-download");
    const resultsPreviewLoadInputEl = document.getElementById("results-preview-load-input");
    const resultsPreviewDeleteEl = document.getElementById("results-preview-delete");
    const resultsPreviewPrevEl = document.getElementById("results-preview-prev");
    const resultsPreviewNextEl = document.getElementById("results-preview-next");
    const resultsPreviewCloseEl = document.getElementById("results-preview-close");
    const healthState = {
      payload: null,
      error: "health_pending",
      consecutiveFailures: 0
    };
    let currentV7ViewMode = "basic";
    let currentV7BasicTask = "text";
    let currentBasicImageStyle = "photo";
    let currentIdentitySingleImageStyle = "photo";
    const STANDARD_NEGATIVE_PROMPT_TEXT = "bad anatomy, bad proportions, deformed body, bad hands, extra fingers, deformed face, blurry";
    const basicTaskNegativePromptDrafts = {
      create: null,
      edit: null,
      inpaint: null
    };
    const basicTaskStandardNegativeEnabled = {
      create: true,
      edit: true,
      inpaint: true
    };
    const basicTaskNegativePromptAutoManaged = {
      create: false,
      edit: false,
      inpaint: false
    };
    let activeSpeechInputSession = null;
    let speechUsageState = {
      text_body_used: false
    };
    let speechStatusState = {
      checked: false,
      available: false,
      backend: null,
      message: "Lokaler Sprachpfad wird geprueft."
    };
    let speechStatusFetchPromise = null;
    let speechInputSessionCounter = 0;
    const speechInputFeedbackTimers = new Map();
    let currentRequest = null;
    let currentRequestCounter = 0;
    let healthPollTimer = null;
    let healthFetchPromise = null;
    let progressRenderTimer = null;
    let renderUiQueued = false;
    let requestNoticeTimer = null;
    let requestNoticeCounter = 0;
    let transientClientPrecheckError = null;
    let transientClientPrecheckErrorTimer = null;
    let transientClientPrecheckErrorCounter = 0;
    let transientRequestError = null;
    let transientRequestErrorTimer = null;
    let transientRequestErrorCounter = 0;
    let transientBusyNotice = null;
    let transientBusyNoticeTimer = null;
    let transientBusyNoticeCounter = 0;
    let lastResult = null;
    let lastSuccessfulResult = null;
    let requestNotice = null;
    let restoringLastSuccess = false;
    const settledClientRequestIdSet = new Set();
    const settledClientRequestIds = [];
    let imageTokenCounter = 0;
    let activeImageLoader = null;
    let activeImageContext = {
      token: null,
      output_file: null,
      display_url: null,
      request_id: null,
      mode: null,
      prompt_id: null,
      restored_from_storage: false,
      state: "none"
    };
    let displayedImage = {
      token: null,
      output_file: null,
      display_url: null,
      request_id: null
    };
    let selectedUploadFile = null;
    let currentUpload = null;
    let currentUploadCounter = 0;
    let inputUploadNotice = {
      state: "idle",
      text: "Bild fehlt noch",
      source_type: null,
      error_type: null,
      blocker: null
    };
    let inputPreviewTokenCounter = 0;
    let activeInputPreviewLoader = null;
    let activeInputImage = {
      token: null,
      image_id: null,
      source_type: null,
      original_name: null,
      stored_name: null,
      mime_type: null,
      size_bytes: null,
      width: null,
      height: null,
      preview_url: null,
      display_url: null,
      state: "none",
      restored_from_health: false
    };
    let displayedInputImage = {
      token: null,
      preview_url: null,
      display_url: null
    };
    let selectedMaskFile = null;
    let currentMaskUpload = null;
    let currentMaskUploadCounter = 0;
    let maskUploadNotice = {
      state: "idle",
      text: "Maske fehlt noch",
      source_type: "mask",
      error_type: null,
      blocker: null
    };
    let maskPreviewTokenCounter = 0;
    let activeMaskPreviewLoader = null;
    let activeMaskImage = {
      token: null,
      image_id: null,
      source_type: null,
      original_name: null,
      stored_name: null,
      mime_type: null,
      size_bytes: null,
      width: null,
      height: null,
      preview_url: null,
      display_url: null,
      state: "none",
      restored_from_health: false
    };
    let displayedMaskImage = {
      token: null,
      preview_url: null,
      display_url: null
    };
    let selectedIdentityReferenceFile = null;
    let currentIdentityReferenceUpload = null;
    let currentIdentityReferenceUploadCounter = 0;
    let identityReferenceUploadNotice = {
      state: "idle",
      text: "Keine Referenz geladen",
      source_type: "reference",
      error_type: null,
      blocker: null
    };
    let identityReferencePreviewTokenCounter = 0;
    let activeIdentityReferencePreviewLoader = null;
    let activeIdentityReferenceImage = {
      token: null,
      image_id: null,
      source_type: "reference",
      original_name: null,
      stored_name: null,
      mime_type: null,
      size_bytes: null,
      width: null,
      height: null,
      preview_url: null,
      display_url: null,
      state: "none",
      restored_from_health: false
    };
    let displayedIdentityReferenceImage = {
      token: null,
      preview_url: null,
      display_url: null
    };
    let identityVerfuegbarkeitState = {
      phase: "pending",
      payload: null,
      error: "identity_readiness_pending"
    };
    let identityVerfuegbarkeitFetchPromise = null;
    let currentIdentityRequest = null;
    let currentIdentityRequestCounter = 0;
    let identityResultPreviewTokenCounter = 0;
    let activeIdentityResultLoader = null;
    let activeIdentityResult = {
      token: null,
      result_id: null,
      output_file: null,
      display_url: null,
      request_id: null,
      prompt_id: null,
      state: "none",
      error_type: null,
      blocker: null
    };
    let selectedMultiReferenceFile = null;
    let multiReferenceStatusState = {
      phase: "pending",
      payload: null,
      error: "multi_reference_status_pending"
    };
    let multiReferenceStatusFetchPromise = null;
    let multiReferenceRuntimeState = {
      phase: "pending",
      payload: null,
      error: "multi_reference_readiness_pending"
    };
    let multiReferenceRuntimeFetchPromise = null;
    let currentMultiReferenceAction = null;
    let currentMultiReferenceActionCounter = 0;
    let currentMultiReferenceRequest = null;
    let currentMultiReferenceRequestCounter = 0;
    let multiReferenceNotice = {
      state: "idle",
      text: "Noch kein Multi-Reference-Bild geladen",
      error_type: null,
      blocker: null
    };
    const selectedIdentityTransferFiles = Object.fromEntries(
      IDENTITY_TRANSFER_ROLE_CONFIG.map((config) => [config.role, null])
    );
    let identityTransferStatusState = {
      phase: "pending",
      payload: null,
      error: "identity_transfer_status_pending"
    };
    let identityTransferStatusFetchPromise = null;
    let currentIdentityTransferAction = null;
    let currentIdentityTransferActionCounter = 0;
    let identityTransferNotice = {
      state: "idle",
      text: "Noch keine Standardpfad-Rolle geladen",
      error_type: null,
      blocker: null
    };
    let identityTransferRuntimeState = {
      phase: "pending",
      payload: null,
      error: "identity_transfer_readiness_pending"
    };
    let identityTransferRuntimeFetchPromise = null;
    let identityTransferMaskHybridRuntimeState = {
      phase: "pending",
      payload: null,
      error: "identity_transfer_mask_hybrid_readiness_pending"
    };
    let identityTransferMaskHybridRuntimeFetchPromise = null;
    let currentIdentityTransferRequest = null;
    let currentIdentityTransferRequestCounter = 0;
    let identityTransferResultPreviewTokenCounter = 0;
    let activeIdentityTransferResultLoader = null;
    let activeIdentityTransferResult = {
      token: null,
      result_id: null,
      output_file: null,
      display_url: null,
      request_id: null,
      prompt_id: null,
      state: "none",
      error_type: null,
      blocker: null,
      used_roles: [],
      pose_reference_present: false,
      pose_reference_used: false,
      transfer_mask_present: false,
      transfer_mask_used: false,
      identity_transfer_strategy: null
    };
    const maskEditorStorageCanvas = document.createElement("canvas");
    let maskEditorState = {
      source_image_id: null,
      source_preview_url: null,
      source_display_url: null,
      width: null,
      height: null,
      tool: "brush",
      brush_size: MASK_EDITOR_DEFAULT_BRUSH,
      has_painted: false,
      dirty: false,
      saving: false,
      status: "idle",
      message: "Lade zuerst ein Bild. Danach kannst du den Bereich markieren."
    };
    let maskEditorSourceTokenCounter = 0;
    let currentMaskEditorStroke = null;
    let resultsState = {
      items: [],
      loading: false,
      error: null,
      initialized: false,
      total_count: 0,
      limit: RESULTS_FETCH_LIMIT,
      storage: null
    };
    let resultsFetchCounter = 0;
    let activeResultsFetchToken = null;
    let resultExportCounter = 0;
    let activeResultExportToken = null;
    let resultsExportState = {
      phase: "idle",
      text: "Optional: Ergebnis in Exportordner kopieren.",
      result_id: null,
      export_url: null,
      export_file_name: null,
      exported_at: null,
      blocker: null
    };
    let resultDeleteCounter = 0;
    let activeResultDeleteToken = null;
    let resultsDeleteState = {
      phase: "idle",
      text: "Optional: Ergebnis aus Haupt-Output loeschen.",
      result_id: null,
      blocker: null
    };
    let resultsPreviewState = {
      open: false,
      result_id: null,
      mode: null,
      file_name: null,
      created_at: null,
      width: null,
      height: null,
      preview_url: null,
      download_url: null
    };
    let textServicePromptTestState = {
      phase: "idle",
      request_token: null,
      response_text: null,
      error: null,
      error_message: null,
      stub: null,
      service: null,
      model_status: null
    };
    let textServicePromptTestCounter = 0;
    let textServicePromptTestCopyNotice = {
      state: "idle",
      text: ""
    };
    let textServicePromptTestCopyNoticeTimeoutId = null;
    let textServiceBasicPromptState = {
      phase: "idle",
      request_token: null,
      response_text: null,
      error: null,
      error_message: null,
      stub: null,
      service: null,
      model_status: null
    };
    let textServiceBasicPromptCounter = 0;
    let textServiceBasicCopyNotice = {
      state: "idle",
      text: ""
    };
    let textServiceBasicCopyNoticeTimeoutId = null;
    let textServiceBasicApplyNotice = {
      state: "idle",
      text: ""
    };
    let textServiceBasicApplyNoticeTimeoutId = null;
    let textChatState = {
      phase: "idle",
      slots: [],
      active_slot_index: 1,
      active_chat: null,
      model_profiles: [],
      current_model_profile_id: "standard",
      model_switch_state: null,
      error: null
    };
    let textChatFetchPromise = null;
    let currentTextWorkMode = "writing";
    let textModelSwitchUiState = {
      phase: "idle",
      profile_id: null,
      message: ""
    };
    let sceneState = {
      scenes: [],
      active_scene_id: null,
      active_scene: null,
      phase: "idle",
      error: null
    };
    let sceneSaveState = {
      phase: "idle",
      message: ""
    };
    let sceneSaveTimer = null;
    let sceneListOpen = false;
    let sceneActionCounter = 0;
    let sceneResultsState = {
      scene_id: null,
      items: [],
      result_ids: [],
      missing_result_ids: [],
      total_result_count: 0,
      limit: 24,
      loading: false,
      error: null,
      initialized: false
    };
    let activeSceneResultsFetchToken = null;
    let sceneResultsFetchCounter = 0;
    let sceneExportState = {
      phase: "idle",
      text: "",
      export_url: null,
      export_file_name: null,
      export_json_url: null,
      export_json_file_name: null
    };
    let activeSceneExportToken = null;
    let sceneExportCounter = 0;

    const sceneNewEl = document.getElementById("scene-new");
    const sceneSaveEl = document.getElementById("scene-save");
    const sceneDeleteEl = document.getElementById("scene-delete");
    const sceneTitleEl = document.getElementById("scene-title");
    const sceneSaveStateEl = document.getElementById("scene-save-state");
    const sceneContextMetaEl = document.getElementById("scene-context-meta");
    const sceneListPanelEl = document.getElementById("scene-list-panel");
    const sceneListEl = document.getElementById("scene-list");
    const sceneToggleListEl = document.getElementById("scene-toggle-list");
    const sceneResultsPanelEl = document.getElementById("scene-results-panel");
    const sceneResultsStateEl = document.getElementById("scene-results-state");
    const sceneResultsGridEl = document.getElementById("scene-results-grid");
    const sceneResultsRefreshEl = document.getElementById("scene-results-refresh");
    const sceneExportEl = document.getElementById("scene-export");
    const sceneExportStateEl = document.getElementById("scene-export-state");
    const scenePanelRootEl = sceneResultsPanelEl ? sceneResultsPanelEl.closest(".scene-panel") : null;
    const textImageNegativePromptBlockEl = document.getElementById("text-image-negative-prompt-block");
    const textImageNegativePromptEl = document.getElementById("text-image-negative-prompt");
    const textImageNegativePromptHintEl = document.getElementById("text-image-negative-prompt-hint");

    function isClientRequestActive() {
      return Boolean(currentRequest);
    }

    function clearSpeechInputFeedback(key) {
      const controller = speechInputControllers[key];
      if (!controller) {
        return;
      }

      const timeoutId = speechInputFeedbackTimers.get(key);
      if (timeoutId) {
        window.clearTimeout(timeoutId);
        speechInputFeedbackTimers.delete(key);
      }

      controller.feedbackEl.textContent = "";
      controller.feedbackEl.className = "speech-input-feedback";
    }

    function setSpeechInputFeedback(key, state, text, options = {}) {
      const controller = speechInputControllers[key];
      if (!controller) {
        return;
      }

      clearSpeechInputFeedback(key);
      const normalizedText = isNonEmptyString(text) ? text.trim() : "";
      controller.feedbackEl.textContent = normalizedText;
      controller.feedbackEl.className = state === "error" ? "speech-input-feedback error" : "speech-input-feedback";

      if (!normalizedText || options.persistent === true) {
        return;
      }

      const timeoutId = window.setTimeout(() => {
        clearSpeechInputFeedback(key);
      }, SPEECH_INPUT_FEEDBACK_DURATION_MS);
      speechInputFeedbackTimers.set(key, timeoutId);
    }

    function setSpeechInputButtonState(key, listening) {
      const controller = speechInputControllers[key];
      if (!controller) {
        return;
      }

      controller.buttonEl.classList.toggle("listening", listening);
      controller.buttonEl.textContent = listening ? "Stop" : "Diktat";
      controller.buttonEl.setAttribute("aria-pressed", listening ? "true" : "false");
      if (listening) {
        controller.buttonEl.title = "Diktat stoppen";
        return;
      }
      if (!speechStatusState.checked) {
        controller.buttonEl.title = "Lokaler Sprachpfad wird geprueft";
        return;
      }
      controller.buttonEl.title = speechStatusState.available
        ? "Lokales Diktat starten"
        : speechStatusState.message;
    }

    function isSpeechInputFieldUnavailable(fieldEl) {
      return !fieldEl || fieldEl.disabled === true || Boolean(fieldEl.closest("[hidden]"));
    }

    function getSpeechInputInsertMode(controller) {
      if (!controller || typeof controller.resolveInsertMode !== "function") {
        return "insert";
      }
      const mode = controller.resolveInsertMode();
      return mode === "replace" || mode === "append" ? mode : "insert";
    }

    function insertSpeechTranscriptIntoField(fieldEl, transcript, options = {}) {
      const normalized = isNonEmptyString(transcript)
        ? transcript.trim().replace(/\s+/g, " ")
        : "";
      if (!normalized || !fieldEl) {
        return false;
      }

      const mode = options.mode === "replace" || options.mode === "append" ? options.mode : "insert";
      const currentValue = typeof fieldEl.value === "string" ? fieldEl.value : "";
      let nextValue = "";
      let caret = 0;

      if (mode === "replace") {
        nextValue = normalized;
        caret = nextValue.length;
      } else if (mode === "append") {
        const separator = currentValue && !/[\n\s]$/.test(currentValue) ? "\n" : "";
        nextValue = `${currentValue}${separator}${normalized}`;
        caret = nextValue.length;
      } else {
        const start = Number.isFinite(fieldEl.selectionStart) ? fieldEl.selectionStart : currentValue.length;
        const end = Number.isFinite(fieldEl.selectionEnd) ? fieldEl.selectionEnd : currentValue.length;
        const before = currentValue.slice(0, start);
        const after = currentValue.slice(end);
        const prefix = before && !/[\s\n]$/.test(before) ? " " : "";
        const suffix = after && !/^[\s\n]/.test(after) ? " " : "";
        const insertion = `${prefix}${normalized}${suffix}`;
        nextValue = `${before}${insertion}${after}`;
        caret = `${before}${insertion}`.length;
      }

      fieldEl.value = nextValue;
      fieldEl.focus();
      if (typeof fieldEl.setSelectionRange === "function") {
        fieldEl.setSelectionRange(caret, caret);
      }
      fieldEl.dispatchEvent(new Event("input", { bubbles: true }));
      fieldEl.dispatchEvent(new Event("change", { bubbles: true }));
      renderUi();
      return true;
    }

    function mapSpeechInputError(errorCode) {
      const normalized = isNonEmptyString(errorCode) ? errorCode.trim().toLowerCase() : "";
      const labels = {
        speech_backend_unavailable: "Lokale Transkription ist nicht verfuegbar",
        unsupported_audio_format: "Audioformat wird nicht unterstuetzt",
        audio_too_large: "Aufnahme ist zu lang",
        empty_audio: "Aufnahme war leer",
        empty_transcript: "Kein Text erkannt",
        speech_transcription_failed: "Transkription fehlgeschlagen",
        upload_read_failed: "Audio konnte nicht gelesen werden",
        permission_denied: "Mikrofonzugriff nicht erlaubt",
        media_recorder_unavailable: "Mikrofonaufnahme im Browser nicht verfuegbar",
        recording_start_failed: "Aufnahme konnte nicht gestartet werden",
        network_error: "Transkriptionsdienst nicht erreichbar"
      };
      return labels[normalized] || "Diktat fehlgeschlagen";
    }

    function stopSpeechMediaTracks(stream) {
      if (!stream || typeof stream.getTracks !== "function") {
        return;
      }
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (error) {
        }
      });
    }

    function stopActiveSpeechInput(options = {}) {
      const session = activeSpeechInputSession;
      if (!session) {
        return;
      }

      activeSpeechInputSession = null;
      session.stopped_manually = true;
      if (session.stopTimerId) {
        window.clearTimeout(session.stopTimerId);
        session.stopTimerId = null;
      }
      setSpeechInputButtonState(session.key, false);
      if (options.clear_feedback === true) {
        clearSpeechInputFeedback(session.key);
      } else if (isNonEmptyString(options.message)) {
        setSpeechInputFeedback(session.key, options.state === "error" ? "error" : "success", options.message, {
          persistent: options.persistent === true
        });
      }

      try {
        if (session.recorder && session.recorder.state !== "inactive") {
          session.recorder.stop();
        }
      } catch (error) {
        stopSpeechMediaTracks(session.stream);
      }
    }

    function resolveSpeechCaptureMimeType() {
      if (typeof window.MediaRecorder !== "function") {
        return "";
      }
      if (typeof window.MediaRecorder.isTypeSupported !== "function") {
        return "";
      }
      const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
      for (const candidate of candidates) {
        if (window.MediaRecorder.isTypeSupported(candidate)) {
          return candidate;
        }
      }
      return "";
    }

    async function fetchSpeechStatus(options = {}) {
      const forceFresh = options.forceFresh === true;
      if (speechStatusFetchPromise && !forceFresh) {
        return speechStatusFetchPromise;
      }
      if (speechStatusFetchPromise && forceFresh) {
        try {
          await speechStatusFetchPromise;
        } catch (error) {
        }
      }

      speechStatusFetchPromise = (async () => {
        try {
          const response = await fetch(SPEECH_STATUS_ENDPOINT, { cache: "no-store" });
          if (!response.ok) {
            throw new Error(`speech_status_http_${response.status}`);
          }
          const payload = await response.json();
          const available = payload?.available === true && payload?.ok === true;
          speechStatusState = {
            checked: true,
            available,
            backend: isNonEmptyString(payload?.backend) ? payload.backend.trim() : null,
            message: isNonEmptyString(payload?.message)
              ? payload.message.trim()
              : (available ? "Lokale Transkription bereit." : "Lokale Transkription nicht verfuegbar.")
          };
        } catch (error) {
          speechStatusState = {
            checked: true,
            available: false,
            backend: null,
            message: "Lokale Transkription ist nicht erreichbar."
          };
        } finally {
          speechStatusFetchPromise = null;
          renderUi();
        }
      })();

      return speechStatusFetchPromise;
    }

    async function transcribeSpeechRecording(key, controller, blob, token) {
      if (!(blob instanceof Blob) || blob.size <= 0) {
        setSpeechInputFeedback(key, "error", mapSpeechInputError("empty_audio"));
        return false;
      }
      setSpeechInputFeedback(key, "success", "Wird lokal transkribiert...", { persistent: true });
      const formData = new FormData();
      const fileName = blob.type && blob.type.includes("ogg") ? "speech-input.ogg" : "speech-input.webm";
      formData.append("audio", blob, fileName);
      formData.append("language", navigator.language || "de-DE");

      try {
        const response = await fetch(SPEECH_TRANSCRIBE_ENDPOINT, {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }
        if (!activeSpeechInputSession || activeSpeechInputSession.token !== token) {
          return false;
        }
        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const blocker = isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `speech_http_${response.status}`;
          setSpeechInputFeedback(key, "error", mapSpeechInputError(blocker));
          if (blocker === "speech_backend_unavailable") {
            void fetchSpeechStatus({ forceFresh: true });
          }
          return false;
        }
        const transcript = isNonEmptyString(payload.text) ? payload.text.trim() : "";
        const insertMode = getSpeechInputInsertMode(controller);
        const inserted = insertSpeechTranscriptIntoField(controller.fieldEl, transcript, { mode: insertMode });
        if (!inserted) {
          setSpeechInputFeedback(key, "error", mapSpeechInputError("empty_transcript"));
          return false;
        }
        if (key === "text-body") {
          markSpeechUsedForTextBody();
        }
        setSpeechInputFeedback(key, "success", "Text uebernommen");
        return true;
      } catch (error) {
        if (!activeSpeechInputSession || activeSpeechInputSession.token !== token) {
          return false;
        }
        setSpeechInputFeedback(key, "error", mapSpeechInputError("network_error"));
        return false;
      }
    }

    async function toggleSpeechInput(key) {
      const controller = speechInputControllers[key];
      if (!controller || isSpeechInputFieldUnavailable(controller.fieldEl)) {
        return;
      }

      if (activeSpeechInputSession && activeSpeechInputSession.key === key) {
        stopActiveSpeechInput({ message: "Diktat beendet" });
        return;
      }

      if (activeSpeechInputSession) {
        stopActiveSpeechInput({ clear_feedback: true });
      }

      if (!speechStatusState.checked) {
        await fetchSpeechStatus();
      }
      if (!speechStatusState.available) {
        setSpeechInputFeedback(key, "error", mapSpeechInputError("speech_backend_unavailable"));
        return;
      }

      if (!(navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") || typeof window.MediaRecorder !== "function") {
        setSpeechInputFeedback(key, "error", mapSpeechInputError("media_recorder_unavailable"));
        return;
      }

      let stream = null;
      let recorder = null;
      const token = `speech-input-${String(++speechInputSessionCounter).padStart(6, "0")}`;
      const chunks = [];
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = resolveSpeechCaptureMimeType();
        recorder = mimeType ? new window.MediaRecorder(stream, { mimeType }) : new window.MediaRecorder(stream);
      } catch (error) {
        stopSpeechMediaTracks(stream);
        const message = String(error?.name || "").toLowerCase().includes("notallowed")
          ? mapSpeechInputError("permission_denied")
          : mapSpeechInputError("recording_start_failed");
        setSpeechInputFeedback(key, "error", message);
        return;
      }

      const session = {
        key,
        token,
        stream,
        recorder,
        chunks,
        stopped_manually: false,
        stopTimerId: null
      };
      activeSpeechInputSession = session;

      recorder.ondataavailable = (event) => {
        if (!activeSpeechInputSession || activeSpeechInputSession.token !== token) {
          return;
        }
        if (event.data instanceof Blob && event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onerror = () => {
        if (activeSpeechInputSession && activeSpeechInputSession.token === token) {
          activeSpeechInputSession = null;
        }
        setSpeechInputButtonState(key, false);
        stopSpeechMediaTracks(stream);
        setSpeechInputFeedback(key, "error", mapSpeechInputError("recording_start_failed"));
      };

      recorder.onstop = async () => {
        if (!activeSpeechInputSession || activeSpeechInputSession.token !== token) {
          stopSpeechMediaTracks(stream);
          return;
        }
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        await transcribeSpeechRecording(key, controller, blob, token);
        if (activeSpeechInputSession && activeSpeechInputSession.token === token) {
          activeSpeechInputSession = null;
        }
        setSpeechInputButtonState(key, false);
        stopSpeechMediaTracks(stream);
      };

      setSpeechInputButtonState(key, true);
      setSpeechInputFeedback(key, "success", "Aufnahme laeuft...", { persistent: true });
      try {
        recorder.start();
        session.stopTimerId = window.setTimeout(() => {
          if (activeSpeechInputSession && activeSpeechInputSession.token === token) {
            stopActiveSpeechInput({ clear_feedback: true });
          }
        }, SPEECH_CAPTURE_MAX_MS);
      } catch (error) {
        activeSpeechInputSession = null;
        setSpeechInputButtonState(key, false);
        stopSpeechMediaTracks(stream);
        setSpeechInputFeedback(key, "error", mapSpeechInputError("recording_start_failed"));
      }
    }

    function syncSpeechInputControls() {
      for (const [key, controller] of Object.entries(speechInputControllers)) {
        if (!controller) {
          continue;
        }

        const active = Boolean(activeSpeechInputSession && activeSpeechInputSession.key === key);
        const disabled = isSpeechInputFieldUnavailable(controller.fieldEl);
        if (active && disabled) {
          stopActiveSpeechInput({ clear_feedback: true });
        }
        controller.buttonEl.disabled = disabled || !speechStatusState.available;
        setSpeechInputButtonState(key, Boolean(activeSpeechInputSession && activeSpeechInputSession.key === key));
      }

      const textBodyController = speechInputControllers["text-body"];
      if (!textBodyController || !textBodyController.feedbackEl) {
        return;
      }
      const isActive = Boolean(activeSpeechInputSession && activeSpeechInputSession.key === "text-body");
      if (isActive) {
        return;
      }
      if (!speechStatusState.available) {
        textBodyController.feedbackEl.textContent = "Lokales Diktat momentan nicht verfuegbar.";
        textBodyController.feedbackEl.className = "speech-input-feedback error";
        return;
      }
      if (!speechUsageState.text_body_used && !isNonEmptyString(textBodyController.feedbackEl.textContent)) {
        textBodyController.feedbackEl.textContent = "Noch kein Diktat genutzt.";
        textBodyController.feedbackEl.className = "speech-input-feedback";
      }
    }

    function queueUiRefresh() {
      if (renderUiQueued) {
        return;
      }

      renderUiQueued = true;
      window.setTimeout(() => {
        renderUiQueued = false;
        renderUi();
      }, 0);
    }

    function clearTransientInfoNotice(reason = null, expectedToken = null) {
      if (expectedToken && (!requestNotice || requestNotice.token !== expectedToken)) {
        return false;
      }

      if (requestNoticeTimer) {
        window.clearTimeout(requestNoticeTimer);
        requestNoticeTimer = null;
      }

      if (!requestNotice) {
        return false;
      }

      requestNotice = null;
      return true;
    }

    function clearTransientInfoNoticeIfStale(nowMs = Date.now()) {
      if (!requestNotice || requestNotice.level !== "info" || !Number.isFinite(requestNotice.expires_at_ms)) {
        return false;
      }

      if (requestNotice.expires_at_ms > nowMs) {
        return false;
      }

      return clearTransientInfoNotice("stale", requestNotice.token);
    }

    function hasMatchingTransientInfoState(currentState, nextState) {
      if (!currentState || !nextState) {
        return false;
      }

      return Boolean(
        currentState.level === nextState.level &&
        currentState.code === nextState.code &&
        currentState.message === nextState.message &&
        currentState.request_id === nextState.request_id &&
        currentState.mode === nextState.mode
      );
    }

    function setTransientInfoNotice(payload, options = {}) {
      const notice = buildRequestNotice(payload, "info");
      if (!notice) {
        return null;
      }

      const token = `info-${String(++requestNoticeCounter).padStart(6, "0")}`;
      const startedAtMs = Date.now();
      const noticeDurationMs = Number.isFinite(options.duration_ms) && options.duration_ms > 0
        ? options.duration_ms
        : TRANSIENT_INFO_NOTICE_DURATION_MS;

      const nextState = {
        ...notice,
        token,
        expires_at_ms: startedAtMs + noticeDurationMs
      };

      requestNotice = applyTransientChannelState(
        requestNotice,
        nextState,
        clearTransientInfoNotice,
        hasMatchingTransientInfoState
      );

      requestNoticeTimer = window.setTimeout(() => {
        if (!clearTransientInfoNotice("timeout", token)) {
          return;
        }
        queueUiRefresh();
      }, noticeDurationMs);

      return {
        ...requestNotice
      };
    }

    function deriveTransientInfoNoticeView() {
      if (!requestNotice || requestNotice.level !== "info") {
        return {
          active: false,
          text: "",
          request_id: null,
          code: null
        };
      }

      return {
        active: true,
        text: `${requestNotice.message || requestNotice.code || "Hinweis"}${requestNotice.request_id ? ` | ${requestNotice.request_id}` : ""}`,
        request_id: requestNotice.request_id ?? null,
        code: requestNotice.code ?? null
      };
    }

    function clearTransientClientPrecheckError(reason = null, expectedToken = null) {
      if (expectedToken && (!transientClientPrecheckError || transientClientPrecheckError.token !== expectedToken)) {
        return false;
      }

      if (transientClientPrecheckErrorTimer) {
        window.clearTimeout(transientClientPrecheckErrorTimer);
        transientClientPrecheckErrorTimer = null;
      }

      if (!transientClientPrecheckError) {
        return false;
      }

      transientClientPrecheckError = null;
      return true;
    }

    function clearTransientClientPrecheckErrorIfStale(nowMs = Date.now()) {
      if (!transientClientPrecheckError || !Number.isFinite(transientClientPrecheckError.expires_at_ms)) {
        return false;
      }

      if (transientClientPrecheckError.expires_at_ms > nowMs) {
        return false;
      }

      return clearTransientClientPrecheckError("stale", transientClientPrecheckError.token);
    }

    function hasMatchingTransientErrorState(currentState, nextState) {
      if (!currentState || !nextState) {
        return false;
      }

      return Boolean(
        currentState.error_type === nextState.error_type &&
        currentState.blocker === nextState.blocker &&
        currentState.request_id === nextState.request_id &&
        currentState.message === nextState.message
      );
    }

    function applyTransientChannelState(currentState, nextState, clearFn, matcherFn) {
      clearFn(
        matcherFn(currentState, nextState) ? "refresh" : "replace"
      );
      return nextState;
    }

    function setTransientClientPrecheckError(errorType, blocker, options = {}) {
      const token = `precheck-error-${String(++transientClientPrecheckErrorCounter).padStart(6, "0")}`;
      const startedAtMs = Date.now();
      const noticeDurationMs = Number.isFinite(options.duration_ms) && options.duration_ms > 0
        ? options.duration_ms
        : TRANSIENT_CLIENT_PRECHECK_ERROR_DURATION_MS;
      const normalizedErrorType = isNonEmptyString(errorType) ? errorType.trim() : "client_precheck";
      const normalizedBlocker = isNonEmptyString(blocker) ? blocker.trim() : "client_precheck_failed";
      const message = isNonEmptyString(options.message)
        ? options.message.trim()
        : (normalizedErrorType === "invalid_request"
          ? `${formatUiCause(normalizedBlocker)}`
          : `Vorabpruefung fehlgeschlagen | ${formatUiCause(normalizedBlocker)}`);

      const nextState = {
        token,
        error_type: normalizedErrorType,
        blocker: normalizedBlocker,
        request_id: options.request_id ?? null,
        message,
        created_at_utc: new Date(startedAtMs).toISOString(),
        expires_at_ms: startedAtMs + noticeDurationMs
      };

      transientClientPrecheckError = applyTransientChannelState(
        transientClientPrecheckError,
        nextState,
        clearTransientClientPrecheckError,
        hasMatchingTransientErrorState
      );

      transientClientPrecheckErrorTimer = window.setTimeout(() => {
        if (!clearTransientClientPrecheckError("timeout", token)) {
          return;
        }
        queueUiRefresh();
      }, noticeDurationMs);

      return {
        ...transientClientPrecheckError
      };
    }

    function deriveTransientClientPrecheckErrorView() {
      if (!transientClientPrecheckError) {
        return {
          active: false,
          text: "",
          request_id: null,
          error_type: null,
          blocker: null
        };
      }

      return {
        active: true,
        text: `${transientClientPrecheckError.message}${transientClientPrecheckError.request_id ? ` | ${transientClientPrecheckError.request_id}` : ""}`,
        request_id: transientClientPrecheckError.request_id,
        error_type: transientClientPrecheckError.error_type,
        blocker: transientClientPrecheckError.blocker
      };
    }

    function clearTransientRequestError(reason = null, expectedToken = null) {
      if (expectedToken && (!transientRequestError || transientRequestError.token !== expectedToken)) {
        return false;
      }

      if (transientRequestErrorTimer) {
        window.clearTimeout(transientRequestErrorTimer);
        transientRequestErrorTimer = null;
      }

      if (!transientRequestError) {
        return false;
      }

      transientRequestError = null;
      return true;
    }

    function clearTransientRequestErrorIfStale(nowMs = Date.now()) {
      if (!transientRequestError || !Number.isFinite(transientRequestError.expires_at_ms)) {
        return false;
      }

      if (transientRequestError.expires_at_ms > nowMs) {
        return false;
      }

      return clearTransientRequestError("stale", transientRequestError.token);
    }

    function setTransientRequestError(errorType, blocker, requestId, options = {}) {
      const token = `request-error-${String(++transientRequestErrorCounter).padStart(6, "0")}`;
      const startedAtMs = Date.now();
      const noticeDurationMs = Number.isFinite(options.duration_ms) && options.duration_ms > 0
        ? options.duration_ms
        : TRANSIENT_BUSY_NOTICE_DURATION_MS;
      const normalizedErrorType = isNonEmptyString(errorType) ? errorType.trim() : "api_error";
      const normalizedBlocker = isNonEmptyString(blocker) ? blocker.trim() : "request_failed";

      const nextState = {
        token,
        error_type: normalizedErrorType,
        blocker: normalizedBlocker,
        request_id: requestId ?? null,
        message: options.message ?? formatImageGenerationErrorMessage(normalizedBlocker, {
          fallback: "Aktion konnte gerade nicht abgeschlossen werden."
        }),
        created_at_utc: new Date(startedAtMs).toISOString(),
        expires_at_ms: startedAtMs + noticeDurationMs
      };

      transientRequestError = applyTransientChannelState(
        transientRequestError,
        nextState,
        clearTransientRequestError,
        hasMatchingTransientErrorState
      );

      transientRequestErrorTimer = window.setTimeout(() => {
        if (!clearTransientRequestError("timeout", token)) {
          return;
        }
        queueUiRefresh();
      }, noticeDurationMs);

      return {
        ...transientRequestError
      };
    }

    function deriveTransientRequestErrorView() {
      if (!transientRequestError) {
        return {
          active: false,
          text: "",
          request_id: null,
          error_type: null,
          blocker: null
        };
      }

      return {
        active: true,
        text: transientRequestError.message,
        request_id: transientRequestError.request_id,
        error_type: transientRequestError.error_type,
        blocker: transientRequestError.blocker
      };
    }

    function derivePrioritizedLocalFaultView() {
      const precheckNotice = deriveTransientClientPrecheckErrorView();
      if (precheckNotice.active) {
        return {
          active: true,
          channel: "client_precheck_error",
          text: precheckNotice.text,
          state: "error",
          request_id: precheckNotice.request_id,
          error_type: precheckNotice.error_type,
          blocker: precheckNotice.blocker
        };
      }

      const requestErrorNotice = deriveTransientRequestErrorView();
      if (requestErrorNotice.active) {
        return {
          active: true,
          channel: "request_error",
          text: requestErrorNotice.text,
          state: "error",
          request_id: requestErrorNotice.request_id,
          error_type: requestErrorNotice.error_type,
          blocker: requestErrorNotice.blocker
        };
      }

      const busyNotice = deriveTransientBusyNoticeView();
      if (busyNotice.active) {
        return {
          active: true,
          channel: "busy_notice",
          text: busyNotice.text,
          state: "error",
          request_id: busyNotice.request_id,
          error_type: busyNotice.error_type,
          blocker: busyNotice.blocker
        };
      }

      return {
        active: false,
        channel: null,
        text: "",
        state: "idle",
        request_id: null,
        error_type: null,
        blocker: null
      };
    }

    function clearTransientBusyNotice(reason = null, expectedToken = null) {
      if (expectedToken && (!transientBusyNotice || transientBusyNotice.token !== expectedToken)) {
        return false;
      }

      if (transientBusyNoticeTimer) {
        window.clearTimeout(transientBusyNoticeTimer);
        transientBusyNoticeTimer = null;
      }

      if (!transientBusyNotice) {
        return false;
      }

      transientBusyNotice = null;
      return true;
    }

    function clearTransientBusyNoticeIfStale(nowMs = Date.now()) {
      if (!transientBusyNotice || !Number.isFinite(transientBusyNotice.expires_at_ms)) {
        return false;
      }

      if (transientBusyNotice.expires_at_ms > nowMs) {
        return false;
      }

      return clearTransientBusyNotice("stale", transientBusyNotice.token);
    }

    function setTransientBusyNotice(payload, durationMs = TRANSIENT_BUSY_NOTICE_DURATION_MS) {
      const token = `busy-${String(++transientBusyNoticeCounter).padStart(6, "0")}`;
      const startedAtMs = Date.now();
      const noticeDurationMs = Number.isFinite(durationMs) && durationMs > 0
        ? durationMs
        : TRANSIENT_BUSY_NOTICE_DURATION_MS;

      const nextState = {
        token,
        error_type: "busy",
        blocker: payload?.blocker ?? "render_in_progress",
        request_id: payload?.request_id ?? null,
        message: "Gerade laeuft schon eine andere Bild-Erstellung. Bitte kurz warten.",
        created_at_utc: new Date(startedAtMs).toISOString(),
        expires_at_ms: startedAtMs + noticeDurationMs
      };

      transientBusyNotice = applyTransientChannelState(
        transientBusyNotice,
        nextState,
        clearTransientBusyNotice,
        hasMatchingTransientErrorState
      );

      transientBusyNoticeTimer = window.setTimeout(() => {
        if (!clearTransientBusyNotice("timeout", token)) {
          return;
        }
        queueUiRefresh();
      }, noticeDurationMs);

      return {
        ...transientBusyNotice
      };
    }

    function deriveTransientBusyNoticeView() {
      if (!transientBusyNotice) {
        return {
          active: false,
          text: "",
          request_id: null,
          error_type: null,
          blocker: null
        };
      }

      return {
        active: true,
        text: transientBusyNotice.message,
        request_id: transientBusyNotice.request_id,
        error_type: transientBusyNotice.error_type,
        blocker: transientBusyNotice.blocker
      };
    }

    function reconcileTransientLocalHintState(nowMs = Date.now()) {
      let changed = false;
      changed = clearTransientInfoNoticeIfStale(nowMs) || changed;
      changed = clearTransientClientPrecheckErrorIfStale(nowMs) || changed;
      changed = clearTransientRequestErrorIfStale(nowMs) || changed;
      changed = clearTransientBusyNoticeIfStale(nowMs) || changed;
      return changed;
    }

    function createEmptyInputImageState() {
      return {
        token: null,
        image_id: null,
        source_type: null,
        original_name: null,
        stored_name: null,
        mime_type: null,
        size_bytes: null,
        width: null,
        height: null,
        preview_url: null,
        display_url: null,
        state: "none",
        restored_from_health: false
      };
    }

    function createEmptyMaskImageState() {
      return {
        token: null,
        image_id: null,
        source_type: "mask",
        original_name: null,
        stored_name: null,
        mime_type: null,
        size_bytes: null,
        width: null,
        height: null,
        preview_url: null,
        display_url: null,
        state: "none",
        restored_from_health: false
      };
    }

    function createEmptyIdentityReferenceImageState() {
      return {
        token: null,
        image_id: null,
        source_type: "reference",
        original_name: null,
        stored_name: null,
        mime_type: null,
        size_bytes: null,
        width: null,
        height: null,
        preview_url: null,
        display_url: null,
        state: "none",
        restored_from_health: false
      };
    }

    function isCurrentMaskCompatibleWithSource() {
      if (!hasUsableInputImage() || !hasUsableMaskImage()) {
        return false;
      }

      return Boolean(
        Number.isFinite(activeInputImage.width) &&
        Number.isFinite(activeInputImage.height) &&
        Number.isFinite(activeMaskImage.width) &&
        Number.isFinite(activeMaskImage.height) &&
        activeInputImage.width === activeMaskImage.width &&
        activeInputImage.height === activeMaskImage.height
      );
    }

    function createEmptyMaskEditorState() {
      return {
        source_image_id: null,
        source_preview_url: null,
        source_display_url: null,
        width: null,
        height: null,
        tool: "brush",
        brush_size: MASK_EDITOR_DEFAULT_BRUSH,
        has_painted: false,
        dirty: false,
        saving: false,
        status: "idle",
        message: "Lade zuerst ein Bild. Danach kannst du den Bereich markieren."
      };
    }

    function normalizeMaskEditorBrushSize(value) {
      const numericValue = Number.parseFloat(String(value ?? "").trim());
      if (!Number.isFinite(numericValue)) {
        return MASK_EDITOR_DEFAULT_BRUSH;
      }
      return Math.min(MASK_EDITOR_MAX_BRUSH, Math.max(MASK_EDITOR_MIN_BRUSH, numericValue));
    }

    function setMaskEditorStatus(state, message) {
      maskEditorState = {
        ...maskEditorState,
        status: state,
        message: isNonEmptyString(message) ? message.trim() : ""
      };
    }

    function getMaskEditorMaskContext() {
      return maskEditorStorageCanvas.getContext("2d", { willReadFrequently: true });
    }

    function getMaskEditorOverlayContext() {
      return maskEditorOverlayEl.getContext("2d");
    }

    function resetMaskEditorBuffers(width, height) {
      const normalizedWidth = Math.max(1, Math.trunc(width || 1));
      const normalizedHeight = Math.max(1, Math.trunc(height || 1));
      maskEditorStorageCanvas.width = normalizedWidth;
      maskEditorStorageCanvas.height = normalizedHeight;
      maskEditorOverlayEl.width = normalizedWidth;
      maskEditorOverlayEl.height = normalizedHeight;

      const maskCtx = getMaskEditorMaskContext();
      const overlayCtx = getMaskEditorOverlayContext();
      maskCtx.globalCompositeOperation = "source-over";
      maskCtx.fillStyle = "#000000";
      maskCtx.fillRect(0, 0, normalizedWidth, normalizedHeight);
      overlayCtx.clearRect(0, 0, normalizedWidth, normalizedHeight);
    }

    function clearMaskEditorStroke() {
      if (currentMaskEditorStroke && Number.isInteger(currentMaskEditorStroke.pointer_id)) {
        try {
          maskEditorOverlayEl.releasePointerCapture(currentMaskEditorStroke.pointer_id);
        } catch (error) {
        }
      }
      currentMaskEditorStroke = null;
    }

    function hasMaskEditorSource() {
      return Boolean(
        hasUsableInputImage() &&
        isNonEmptyString(maskEditorState.source_image_id) &&
        maskEditorState.source_image_id === activeInputImage.image_id &&
        Number.isFinite(maskEditorState.width) &&
        Number.isFinite(maskEditorState.height)
      );
    }

    function maskEditorHasPaintedPixels() {
      if (!hasMaskEditorSource()) {
        return false;
      }

      const maskCtx = getMaskEditorMaskContext();
      const imageData = maskCtx.getImageData(0, 0, maskEditorStorageCanvas.width, maskEditorStorageCanvas.height).data;
      for (let index = 0; index < imageData.length; index += 4) {
        if (imageData[index] > 0 || imageData[index + 1] > 0 || imageData[index + 2] > 0) {
          return true;
        }
      }
      return false;
    }

    function updateMaskEditorPaintState() {
      maskEditorState = {
        ...maskEditorState,
        has_painted: maskEditorHasPaintedPixels()
      };
    }

    function clearMaskEditorDraft(options = {}) {
      clearMaskEditorStroke();
      if (Number.isFinite(maskEditorState.width) && Number.isFinite(maskEditorState.height)) {
        resetMaskEditorBuffers(maskEditorState.width, maskEditorState.height);
      } else {
        resetMaskEditorBuffers(1, 1);
      }
      maskEditorState = {
        ...maskEditorState,
        has_painted: false,
        dirty: false
      };
      setMaskEditorStatus("idle", options.message || "Noch kein Bereich markiert");
    }

    function clearMaskEditorSourceState(message = "Lade zuerst ein Bild. Danach kannst du den Bereich markieren.") {
      clearMaskEditorStroke();
      resetMaskEditorBuffers(1, 1);
      maskEditorSourceEl.removeAttribute("src");
      maskEditorStageEl.style.display = "none";
      maskEditorEmptyEl.style.display = "block";
      maskEditorEmptyEl.textContent = message;
      maskEditorState = {
        ...createEmptyMaskEditorState(),
        tool: maskEditorState.tool,
        brush_size: maskEditorState.brush_size
      };
    }

    function syncMaskEditorSourceFromInput() {
      if (!hasUsableInputImage() || !isNonEmptyString(activeInputImage.preview_url)) {
        if (!isNonEmptyString(maskEditorState.source_image_id)) {
          return;
        }
        clearMaskEditorSourceState();
        return;
      }

      const normalizedWidth = Number.isFinite(activeInputImage.width) ? Number(activeInputImage.width) : null;
      const normalizedHeight = Number.isFinite(activeInputImage.height) ? Number(activeInputImage.height) : null;
      if (!Number.isFinite(normalizedWidth) || !Number.isFinite(normalizedHeight)) {
        clearMaskEditorSourceState("Eingabebild hat keine gueltige Groesse.");
        return;
      }

      const sameSource = (
        maskEditorState.source_image_id === activeInputImage.image_id &&
        maskEditorState.source_preview_url === activeInputImage.preview_url &&
        maskEditorState.width === normalizedWidth &&
        maskEditorState.height === normalizedHeight
      );
      if (sameSource) {
        return;
      }

      const sourceToken = `mask-editor-source-${String(++maskEditorSourceTokenCounter).padStart(6, "0")}`;
      const sourceDisplayUrl = buildInputPreviewDisplayUrl(activeInputImage.preview_url, sourceToken);
      maskEditorSourceEl.src = sourceDisplayUrl;
      maskEditorStageEl.style.display = "block";
      maskEditorStageEl.style.aspectRatio = `${normalizedWidth} / ${normalizedHeight}`;
      maskEditorEmptyEl.style.display = "none";
      resetMaskEditorBuffers(normalizedWidth, normalizedHeight);
      maskEditorState = {
        ...createEmptyMaskEditorState(),
        source_image_id: activeInputImage.image_id,
        source_preview_url: activeInputImage.preview_url,
        source_display_url: sourceDisplayUrl,
        width: normalizedWidth,
        height: normalizedHeight,
        tool: maskEditorState.tool,
        brush_size: maskEditorState.brush_size,
        status: "idle",
        message: "Noch kein Bereich markiert"
      };
    }

    function hasUsableInputImage() {
      return activeInputImage.state !== "none" && isNonEmptyString(activeInputImage.image_id);
    }

    function hasUsableMaskImage() {
      return activeMaskImage.state !== "none" && isNonEmptyString(activeMaskImage.image_id);
    }

    function normalizeDenoiseStrength(value, maxValue = MAX_IMG2IMG_DENOISE) {
      const numericValue = Number.parseFloat(String(value ?? "").trim());
      if (!Number.isFinite(numericValue)) {
        return DEFAULT_IMG2IMG_DENOISE;
      }
      return Math.min(maxValue, Math.max(MIN_IMG2IMG_DENOISE, numericValue));
    }

    function getActiveDenoiseMax() {
      return shouldUseInpainting() ? MAX_INPAINT_DENOISE : MAX_IMG2IMG_DENOISE;
    }

    function shouldUseInputImage() {
      return hasUsableInputImage() && (useInputImageEl.checked === true || shouldUseInpainting());
    }

    function shouldUseInpainting() {
      return hasUsableInputImage() && isCurrentMaskCompatibleWithSource() && useInpaintingEl.checked === true;
    }

    function syncGenerateInputControls() {
      const hasInputImage = hasUsableInputImage();
      const hasMaskImage = isCurrentMaskCompatibleWithSource();
      const modeAllowsInputImage = modeEl.value !== "placeholder";
      const canUseInputImage = hasInputImage && modeAllowsInputImage;
      const canUseInpainting = hasInputImage && hasMaskImage && modeAllowsInputImage;
      
      // Task-aware disable logic: never disable a checkbox for its required task
      const isEditTask = isV7BasicModeActive() && currentV7BasicTask === "edit";
      const isInpaintTask = isV7BasicModeActive() && currentV7BasicTask === "inpaint";

      // Only disable input image checkbox if not available AND not required by edit task
      if (!canUseInputImage && !isEditTask) {
        useInputImageEl.checked = false;
      }
      // Only disable inpaint checkbox if not available AND not required by inpaint task
      if (!canUseInpainting && !isInpaintTask) {
        useInpaintingEl.checked = false;
      }
      // Ensure inpainting can't be true without input image
      if (useInpaintingEl.checked && !useInputImageEl.checked) {
        useInputImageEl.checked = true;
      }

      useInputImageEl.disabled = !canUseInputImage && !isEditTask;
      useInpaintingEl.disabled = !canUseInpainting && !isInpaintTask;
      const activeDenoiseMax = getActiveDenoiseMax();
      denoiseStrengthEl.max = activeDenoiseMax.toFixed(2);
      denoiseStrengthEl.value = normalizeDenoiseStrength(denoiseStrengthEl.value, activeDenoiseMax).toFixed(2);
      denoiseStrengthEl.disabled = !(shouldUseInputImage() || shouldUseInpainting());
    }

    function isSupportedUploadFile(file) {
      if (!(file instanceof File)) {
        return false;
      }

      const name = typeof file.name === "string" ? file.name.trim() : "";
      const extension = name.includes(".") ? `.${name.split(".").pop().toLowerCase()}` : "";
      const mimeType = typeof file.type === "string" ? file.type.trim().toLowerCase() : "";
      return VALID_UPLOAD_EXTENSIONS.has(extension) && (!mimeType || VALID_UPLOAD_MIME_TYPES.has(mimeType));
    }

    function inferUploadExtensionFromMimeType(mimeType) {
      const normalized = typeof mimeType === "string" ? mimeType.trim().toLowerCase() : "";
      if (normalized === "image/png") {
        return ".png";
      }
      if (normalized === "image/jpeg") {
        return ".jpg";
      }
      if (normalized === "image/webp") {
        return ".webp";
      }
      return null;
    }

    function makeClipboardFile(fileLike) {
      if (!(fileLike instanceof Blob)) {
        return null;
      }

      const mimeType = typeof fileLike.type === "string" ? fileLike.type.trim().toLowerCase() : "";
      const extension = inferUploadExtensionFromMimeType(mimeType);
      if (!extension) {
        return null;
      }

      const sourceBits = fileLike instanceof File ? [fileLike] : [fileLike];
      return new File(sourceBits, `clipboard${extension}`, { type: mimeType || "image/png" });
    }

    function extractClipboardImageFile(clipboardData) {
      if (!clipboardData || !clipboardData.items) {
        return null;
      }

      for (const item of clipboardData.items) {
        if (!item || item.kind !== "file" || !String(item.type || "").toLowerCase().startsWith("image/")) {
          continue;
        }
        const file = typeof item.getAsFile === "function" ? item.getAsFile() : null;
        const normalizedFile = makeClipboardFile(file);
        if (normalizedFile) {
          return normalizedFile;
        }
      }

      return null;
    }

    function buildInputPreviewDisplayUrl(url, token) {
      return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}-${encodeURIComponent(token)}`;
    }

    function showUploadPreview(previewEl, displayUrl) {
      if (!(previewEl instanceof HTMLImageElement) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      const panelEl = previewEl.closest(".upload-preview-panel");
      if (panelEl instanceof HTMLElement) {
        panelEl.hidden = false;
      }
      previewEl.src = displayUrl;
      previewEl.style.display = "block";
      return true;
    }

    function clearUploadPreview(previewEl) {
      if (!(previewEl instanceof HTMLImageElement)) {
        return;
      }

      const panelEl = previewEl.closest(".upload-preview-panel");
      if (panelEl instanceof HTMLElement) {
        panelEl.hidden = true;
      }
      previewEl.style.display = "none";
      previewEl.removeAttribute("src");
    }

    function normalizeUploadedInputPayload(payload) {
      if (!payload || typeof payload !== "object") {
        return null;
      }

      if (!isNonEmptyString(payload.preview_url) || !isNonEmptyString(payload.stored_name)) {
        return null;
      }

      return {
        image_id: isNonEmptyString(payload.image_id) ? payload.image_id.trim() : payload.stored_name.trim(),
        source_type: isNonEmptyString(payload.source_type) ? payload.source_type.trim().toLowerCase() : "file",
        original_name: isNonEmptyString(payload.original_name) ? payload.original_name.trim() : payload.stored_name.trim(),
        stored_name: payload.stored_name.trim(),
        mime_type: isNonEmptyString(payload.mime_type) ? payload.mime_type.trim() : "application/octet-stream",
        size_bytes: Number.isFinite(payload.size_bytes) ? Number(payload.size_bytes) : null,
        width: Number.isFinite(payload.width) ? Number(payload.width) : null,
        height: Number.isFinite(payload.height) ? Number(payload.height) : null,
        preview_url: payload.preview_url.trim()
      };
    }

    function isSameInputImage(left, right) {
      if (!left || !right) {
        return false;
      }

      return Boolean(
        left.preview_url === right.preview_url &&
        left.stored_name === right.stored_name
      );
    }

    function detachInputPreviewLoader() {
      if (!activeInputPreviewLoader) {
        return;
      }

      try {
        activeInputPreviewLoader.onload = null;
        activeInputPreviewLoader.onerror = null;
      } catch (error) {
      }
      activeInputPreviewLoader = null;
    }

    function clearInputPreviewDomBindings() {
      inputPreviewEl.onload = null;
      inputPreviewEl.onerror = null;
      delete inputPreviewEl.dataset.inputImageToken;
      delete inputPreviewEl.dataset.inputDisplayUrl;
    }

    function clearVisibleInputPreview() {
      detachInputPreviewLoader();
      clearInputPreviewDomBindings();
      clearUploadPreview(inputPreviewEl);
      displayedInputImage = {
        token: null,
        preview_url: null,
        display_url: null
      };
    }

    function clearCurrentInputImage(options = {}) {
      clearVisibleInputPreview();
      activeInputImage = createEmptyInputImageState();
      clearMaskEditorSourceState();
      if (options.clearNotice !== false) {
        inputUploadNotice = {
          state: "idle",
          text: "Bild fehlt noch",
          source_type: null,
          error_type: null,
          blocker: null
        };
      }
    }

    function setInputUploadNotice(state, text, options = {}) {
      inputUploadNotice = {
        state,
        text,
        source_type: options.source_type ?? null,
        error_type: options.error_type ?? null,
        blocker: options.blocker ?? null
      };
    }

    function isInputPreviewEventRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      return Boolean(
        activeInputImage &&
        activeInputImage.token === token &&
        activeInputImage.display_url === displayUrl
      );
    }

    function applyInputPreviewToDom(token, displayUrl) {
      if (!isInputPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      inputPreviewEl.dataset.inputImageToken = token;
      inputPreviewEl.dataset.inputDisplayUrl = displayUrl;
      inputPreviewEl.onload = () => {
        handleInputPreviewLoad(token, displayUrl, "dom");
      };
      inputPreviewEl.onerror = () => {
        handleInputPreviewError(token, displayUrl, "dom");
      };
      return showUploadPreview(inputPreviewEl, displayUrl);
    }

    function handleInputPreviewLoad(token, displayUrl, source = "unknown") {
      if (!isInputPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      if (source === "loader") {
        return applyInputPreviewToDom(token, displayUrl);
      }

      activeInputImage = {
        ...activeInputImage,
        state: "ready"
      };
      displayedInputImage = {
        token: activeInputImage.token,
        preview_url: activeInputImage.preview_url,
        display_url: activeInputImage.display_url
      };
      renderUi();
      return true;
    }

    function handleInputPreviewError(token, displayUrl, source = "unknown") {
      if (!isInputPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      activeInputImage = {
        ...activeInputImage,
        state: "error"
      };
      clearVisibleInputPreview();
      setInputUploadNotice("error", "Bild konnte nicht geladen werden | Vorschau nicht lesbar", {
        error_type: "upload_error",
        blocker: "preview_not_accessible"
      });
      renderUi();
      return true;
    }

    function setCurrentInputImage(payload, options = {}) {
      const normalized = normalizeUploadedInputPayload(payload);
      if (!normalized) {
        return null;
      }

      detachInputPreviewLoader();
      const token = `input-image-${String(++inputPreviewTokenCounter).padStart(6, "0")}`;
      const displayUrl = buildInputPreviewDisplayUrl(normalized.preview_url, token);
      activeInputImage = {
        ...normalized,
        token,
        display_url: displayUrl,
        state: "loading",
        restored_from_health: options.restored_from_health === true
      };
      syncMaskEditorSourceFromInput();
      if (options.noticeText || normalized.source_type) {
        const defaultNoticeText = normalized.source_type === "clipboard"
          ? "Bild eingefuegt"
          : "Bild geladen";
        setInputUploadNotice("ok", options.noticeText || defaultNoticeText, {
          source_type: normalized.source_type
        });
      }
      renderUi();

      const loader = new Image();
      activeInputPreviewLoader = loader;
      loader.onload = () => {
        handleInputPreviewLoad(token, displayUrl, "loader");
      };
      loader.onerror = () => {
        handleInputPreviewError(token, displayUrl, "loader");
      };
      loader.src = displayUrl;
      return {
        ...activeInputImage
      };
    }

    function syncInputImageFromHealth(payload) {
      if (currentUpload) {
        return;
      }

      const normalized = normalizeUploadedInputPayload(payload?.input_image);
      if (!normalized) {
        if (activeInputImage.state !== "none") {
          clearCurrentInputImage({ clearNotice: false });
          setInputUploadNotice("idle", "Bild fehlt noch");
          renderUi();
        }
        return;
      }

      if (isSameInputImage(activeInputImage, normalized)) {
        return;
      }

      setCurrentInputImage(normalized, {
        restored_from_health: true,
        noticeText: normalized.source_type === "clipboard"
          ? "Bild eingefuegt"
          : "Bild geladen"
      });
    }

    function formatBasicImageSummary(image, emptyText) {
      if (!image || image.state === "none") {
        return emptyText;
      }

      const parts = [];
      if (isNonEmptyString(image.original_name)) {
        parts.push(image.original_name.trim());
      } else if (isNonEmptyString(image.stored_name)) {
        parts.push(image.stored_name.trim());
      }
      if (Number.isFinite(image.width) && Number.isFinite(image.height)) {
        parts.push(`${image.width} x ${image.height}`);
      }
      if (parts.length === 0) {
        return "Bild geladen";
      }
      return parts.join(" | ");
    }

    function currentInputImageSummary() {
      if (activeInputImage.state === "none") {
        return isV7BasicModeActive() ? "kein Bild" : "kein Eingabebild";
      }

      if (isV7BasicModeActive()) {
        return formatBasicImageSummary(activeInputImage, "kein Bild");
      }

      return JSON.stringify({
        image_id: activeInputImage.image_id,
        source_type: activeInputImage.source_type,
        original_name: activeInputImage.original_name,
        stored_name: activeInputImage.stored_name,
        mime_type: activeInputImage.mime_type,
        size_bytes: activeInputImage.size_bytes,
        width: activeInputImage.width,
        height: activeInputImage.height,
        preview_url: activeInputImage.preview_url,
        state: activeInputImage.state
      }, null, 2);
    }

    function detachMaskPreviewLoader() {
      if (!activeMaskPreviewLoader) {
        return;
      }

      try {
        activeMaskPreviewLoader.onload = null;
        activeMaskPreviewLoader.onerror = null;
      } catch (error) {
      }
      activeMaskPreviewLoader = null;
    }

    function clearMaskPreviewDomBindings() {
      maskPreviewEl.onload = null;
      maskPreviewEl.onerror = null;
      delete maskPreviewEl.dataset.maskImageToken;
      delete maskPreviewEl.dataset.maskDisplayUrl;
    }

    function clearVisibleMaskPreview() {
      detachMaskPreviewLoader();
      clearMaskPreviewDomBindings();
      clearUploadPreview(maskPreviewEl);
      displayedMaskImage = {
        token: null,
        preview_url: null,
        display_url: null
      };
    }

    function clearCurrentMaskImage(options = {}) {
      clearVisibleMaskPreview();
      activeMaskImage = createEmptyMaskImageState();
      if (options.clearNotice !== false) {
        maskUploadNotice = {
          state: "idle",
          text: "Maske fehlt noch",
          source_type: "mask",
          error_type: null,
          blocker: null
        };
      }
    }

    function setMaskUploadNotice(state, text, options = {}) {
      maskUploadNotice = {
        state,
        text,
        source_type: "mask",
        error_type: options.error_type ?? null,
        blocker: options.blocker ?? null
      };
    }

    function isMaskPreviewEventRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      return Boolean(
        activeMaskImage &&
        activeMaskImage.token === token &&
        activeMaskImage.display_url === displayUrl
      );
    }

    function applyMaskPreviewToDom(token, displayUrl) {
      if (!isMaskPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      maskPreviewEl.dataset.maskImageToken = token;
      maskPreviewEl.dataset.maskDisplayUrl = displayUrl;
      maskPreviewEl.onload = () => {
        handleMaskPreviewLoad(token, displayUrl, "dom");
      };
      maskPreviewEl.onerror = () => {
        handleMaskPreviewError(token, displayUrl, "dom");
      };
      return showUploadPreview(maskPreviewEl, displayUrl);
    }

    function handleMaskPreviewLoad(token, displayUrl, source = "unknown") {
      if (!isMaskPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      if (source === "loader") {
        return applyMaskPreviewToDom(token, displayUrl);
      }

      activeMaskImage = {
        ...activeMaskImage,
        state: "ready"
      };
      displayedMaskImage = {
        token: activeMaskImage.token,
        preview_url: activeMaskImage.preview_url,
        display_url: activeMaskImage.display_url
      };
      renderUi();
      return true;
    }

    function handleMaskPreviewError(token, displayUrl, source = "unknown") {
      if (!isMaskPreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      activeMaskImage = {
        ...activeMaskImage,
        state: "error"
      };
      clearVisibleMaskPreview();
      setMaskUploadNotice("error", "Maske konnte nicht geladen werden | Vorschau nicht lesbar", {
        error_type: "upload_error",
        blocker: "mask_preview_not_accessible"
      });
      renderUi();
      return true;
    }

    function setCurrentMaskImage(payload, options = {}) {
      const normalized = normalizeUploadedInputPayload(payload);
      if (!normalized) {
        return null;
      }

      detachMaskPreviewLoader();
      const token = `mask-image-${String(++maskPreviewTokenCounter).padStart(6, "0")}`;
      const displayUrl = buildInputPreviewDisplayUrl(normalized.preview_url, token);
      activeMaskImage = {
        ...normalized,
        source_type: "mask",
        token,
        display_url: displayUrl,
        state: "loading",
        restored_from_health: options.restored_from_health === true
      };
      if (options.noticeText) {
        setMaskUploadNotice("ok", options.noticeText);
      }
      renderUi();

      const loader = new Image();
      activeMaskPreviewLoader = loader;
      loader.onload = () => {
        handleMaskPreviewLoad(token, displayUrl, "loader");
      };
      loader.onerror = () => {
        handleMaskPreviewError(token, displayUrl, "loader");
      };
      loader.src = displayUrl;
      return {
        ...activeMaskImage
      };
    }

    function isSameMaskImage(left, right) {
      if (!left || !right) {
        return false;
      }

      return Boolean(
        left.preview_url === right.preview_url &&
        left.stored_name === right.stored_name
      );
    }

    function syncMaskImageFromHealth(payload) {
      if (currentMaskUpload) {
        return;
      }

      const normalized = normalizeUploadedInputPayload(payload?.mask_image);
      if (!normalized) {
        if (activeMaskImage.state !== "none") {
          clearCurrentMaskImage({ clearNotice: false });
          setMaskUploadNotice("idle", "Maske fehlt noch");
          renderUi();
        }
        return;
      }

      if (isSameMaskImage(activeMaskImage, normalized)) {
        return;
      }

      setCurrentMaskImage(normalized, {
        restored_from_health: true,
        noticeText: "Maske geladen"
      });
    }

    function currentMaskImageSummary() {
      if (activeMaskImage.state === "none") {
        return "keine Maske";
      }

      if (isV7BasicModeActive()) {
        return formatBasicImageSummary(activeMaskImage, "keine Maske");
      }

      return JSON.stringify({
        image_id: activeMaskImage.image_id,
        source_type: activeMaskImage.source_type,
        original_name: activeMaskImage.original_name,
        stored_name: activeMaskImage.stored_name,
        mime_type: activeMaskImage.mime_type,
        size_bytes: activeMaskImage.size_bytes,
        width: activeMaskImage.width,
        height: activeMaskImage.height,
        preview_url: activeMaskImage.preview_url,
        state: activeMaskImage.state
      }, null, 2);
    }

    function detachIdentityReferencePreviewLoader() {
      if (!activeIdentityReferencePreviewLoader) {
        return;
      }

      try {
        activeIdentityReferencePreviewLoader.onload = null;
        activeIdentityReferencePreviewLoader.onerror = null;
      } catch (error) {
      }
      activeIdentityReferencePreviewLoader = null;
    }

    function clearIdentityReferencePreviewDomBindings() {
      identityReferencePreviewEl.onload = null;
      identityReferencePreviewEl.onerror = null;
      delete identityReferencePreviewEl.dataset.identityReferenceToken;
      delete identityReferencePreviewEl.dataset.identityReferenceDisplayUrl;
    }

    function clearVisibleIdentityReferencePreview() {
      detachIdentityReferencePreviewLoader();
      clearIdentityReferencePreviewDomBindings();
      clearUploadPreview(identityReferencePreviewEl);
      displayedIdentityReferenceImage = {
        token: null,
        preview_url: null,
        display_url: null
      };
    }

    function clearCurrentIdentityReferenceImage(options = {}) {
      clearVisibleIdentityReferencePreview();
      activeIdentityReferenceImage = createEmptyIdentityReferenceImageState();
      if (options.clearNotice !== false) {
        identityReferenceUploadNotice = {
          state: "idle",
          text: "Keine Referenz geladen",
          source_type: "reference",
          error_type: null,
          blocker: null
        };
      }
    }

    function setIdentityReferenceUploadNotice(state, text, options = {}) {
      identityReferenceUploadNotice = {
        state,
        text,
        source_type: "reference",
        error_type: options.error_type ?? null,
        blocker: options.blocker ?? null
      };
    }

    function isIdentityReferencePreviewEventRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      return Boolean(
        activeIdentityReferenceImage &&
        activeIdentityReferenceImage.token === token &&
        activeIdentityReferenceImage.display_url === displayUrl
      );
    }

    function applyIdentityReferencePreviewToDom(token, displayUrl) {
      if (!isIdentityReferencePreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      identityReferencePreviewEl.dataset.identityReferenceToken = token;
      identityReferencePreviewEl.dataset.identityReferenceDisplayUrl = displayUrl;
      identityReferencePreviewEl.onload = () => {
        handleIdentityReferencePreviewLoad(token, displayUrl, "dom");
      };
      identityReferencePreviewEl.onerror = () => {
        handleIdentityReferencePreviewError(token, displayUrl, "dom");
      };
      return showUploadPreview(identityReferencePreviewEl, displayUrl);
    }

    function handleIdentityReferencePreviewLoad(token, displayUrl, source = "unknown") {
      if (!isIdentityReferencePreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      if (source === "loader") {
        return applyIdentityReferencePreviewToDom(token, displayUrl);
      }

      activeIdentityReferenceImage = {
        ...activeIdentityReferenceImage,
        state: "ready"
      };
      displayedIdentityReferenceImage = {
        token: activeIdentityReferenceImage.token,
        preview_url: activeIdentityReferenceImage.preview_url,
        display_url: activeIdentityReferenceImage.display_url
      };
      renderUi();
      return true;
    }

    function handleIdentityReferencePreviewError(token, displayUrl, source = "unknown") {
      if (!isIdentityReferencePreviewEventRelevant(token, displayUrl)) {
        return false;
      }

      activeIdentityReferenceImage = {
        ...activeIdentityReferenceImage,
        state: "error"
      };
      clearVisibleIdentityReferencePreview();
      setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | Vorschau nicht lesbar", {
        error_type: "upload_error",
        blocker: "preview_not_accessible"
      });
      renderUi();
      return true;
    }

    function setCurrentIdentityReferenceImage(payload, options = {}) {
      const normalized = normalizeUploadedInputPayload(payload);
      if (!normalized) {
        return null;
      }

      detachIdentityReferencePreviewLoader();
      const token = `identity-reference-${String(++identityReferencePreviewTokenCounter).padStart(6, "0")}`;
      const displayUrl = buildInputPreviewDisplayUrl(normalized.preview_url, token);
      activeIdentityReferenceImage = {
        ...normalized,
        source_type: "reference",
        token,
        display_url: displayUrl,
        state: "loading",
        restored_from_health: options.restored_from_health === true
      };
      clearIdentityResult();
      currentIdentityRequest = null;
      if (options.noticeText) {
        setIdentityReferenceUploadNotice("ok", options.noticeText);
      }
      renderUi();

      const loader = new Image();
      activeIdentityReferencePreviewLoader = loader;
      loader.onload = () => {
        handleIdentityReferencePreviewLoad(token, displayUrl, "loader");
      };
      loader.onerror = () => {
        handleIdentityReferencePreviewError(token, displayUrl, "loader");
      };
      loader.src = displayUrl;
      return {
        ...activeIdentityReferenceImage
      };
    }

    function isSameIdentityReferenceImage(left, right) {
      if (!left || !right) {
        return false;
      }

      return Boolean(
        left.preview_url === right.preview_url &&
        left.stored_name === right.stored_name
      );
    }

    function syncIdentityReferenceImageFromHealth(payload) {
      if (currentIdentityReferenceUpload) {
        return;
      }

      const normalized = normalizeUploadedInputPayload(payload?.reference_image);
      if (!normalized) {
        if (activeIdentityReferenceImage.state !== "none") {
          clearCurrentIdentityReferenceImage({ clearNotice: false });
          setIdentityReferenceUploadNotice("idle", "Keine Referenz geladen");
          renderUi();
        }
        return;
      }

      if (isSameIdentityReferenceImage(activeIdentityReferenceImage, normalized)) {
        return;
      }

      setCurrentIdentityReferenceImage(normalized, {
        restored_from_health: true,
        noticeText: "Referenz geladen"
      });
    }

    function currentIdentityReferenceImageSummary() {
      if (activeIdentityReferenceImage.state === "none") {
        return "keine Referenz";
      }

      return JSON.stringify({
        image_id: activeIdentityReferenceImage.image_id,
        source_type: activeIdentityReferenceImage.source_type,
        original_name: activeIdentityReferenceImage.original_name,
        stored_name: activeIdentityReferenceImage.stored_name,
        mime_type: activeIdentityReferenceImage.mime_type,
        size_bytes: activeIdentityReferenceImage.size_bytes,
        width: activeIdentityReferenceImage.width,
        height: activeIdentityReferenceImage.height,
        preview_url: activeIdentityReferenceImage.preview_url,
        state: activeIdentityReferenceImage.state
      }, null, 2);
    }

    function hasUsableIdentityReferenceImage() {
      return activeIdentityReferenceImage.state !== "none" && isNonEmptyString(activeIdentityReferenceImage.image_id);
    }

    function resetSelectedIdentityReferenceFile() {
      selectedIdentityReferenceFile = null;
      identityReferenceFileEl.value = "";
    }

    function handleIdentityReferenceFileSelection() {
      const file = identityReferenceFileEl.files && identityReferenceFileEl.files.length > 0 ? identityReferenceFileEl.files[0] : null;
      if (!file) {
        selectedIdentityReferenceFile = null;
        if (!currentIdentityReferenceUpload && activeIdentityReferenceImage.state === "none") {
          setIdentityReferenceUploadNotice("idle", "Keine Referenz geladen");
        }
        renderUi();
        return;
      }

      if (!isSupportedUploadFile(file)) {
        resetSelectedIdentityReferenceFile();
        setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | ungueltiger Dateityp", {
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return;
      }

      selectedIdentityReferenceFile = file;
      setIdentityReferenceUploadNotice("idle", `Datei gewaehlt | ${file.name}`);
      renderUi();
    }

    async function submitIdentityReferenceImage(file) {
      if (currentIdentityReferenceUpload) {
        return false;
      }

      if (!(file instanceof File)) {
        setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | keine Datei gewaehlt", {
          error_type: "invalid_request",
          blocker: "missing_file"
        });
        renderUi();
        return false;
      }

      if (!isSupportedUploadFile(file)) {
        resetSelectedIdentityReferenceFile();
        setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | ungueltiger Dateityp", {
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return false;
      }

      const uploadToken = `identity-reference-upload-${String(++currentIdentityReferenceUploadCounter).padStart(6, "0")}`;
      currentIdentityReferenceUpload = {
        token: uploadToken,
        started_at_utc: new Date().toISOString(),
        file_name: file.name
      };
      setIdentityReferenceUploadNotice("uploading", "Referenz-Upload laeuft...");
      renderUi();

      const formData = new FormData();
      formData.append("image", file);
      formData.append("source_type", "file");

      try {
        const response = await fetch("/identity-reference-image", {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentIdentityReferenceUpload || currentIdentityReferenceUpload.token !== uploadToken) {
          return false;
        }

        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const errorType = INPUT_UPLOAD_ERROR_TYPES.has(payload?.error_type) ? payload.error_type : "upload_error";
          const blocker = isNonEmptyString(payload?.blocker) ? payload.blocker : "reference_upload_failed";
          setIdentityReferenceUploadNotice("error", `Referenz-Upload fehlgeschlagen | ${blocker}`, {
            error_type: errorType,
            blocker
          });
          renderUi();
          return false;
        }

        resetSelectedIdentityReferenceFile();
        setCurrentIdentityReferenceImage(payload, {
          noticeText: "Referenz erfolgreich"
        });
        await fetchHealth({ forceFresh: true });
        return true;
      } catch (error) {
        if (!currentIdentityReferenceUpload || currentIdentityReferenceUpload.token !== uploadToken) {
          return false;
        }

        setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | upload_request_failed", {
          error_type: "upload_error",
          blocker: "upload_request_failed"
        });
        return false;
      } finally {
        if (currentIdentityReferenceUpload && currentIdentityReferenceUpload.token === uploadToken) {
          currentIdentityReferenceUpload = null;
        }
        renderUi();
      }
    }

    async function attemptUploadIdentityReference() {
      return submitIdentityReferenceImage(selectedIdentityReferenceFile);
    }

    async function resetIdentityReferenceImage() {
      if (currentIdentityReferenceUpload) {
        return;
      }

      resetSelectedIdentityReferenceFile();
      if (activeIdentityReferenceImage.state === "none") {
        setIdentityReferenceUploadNotice("idle", "Keine Referenz geladen");
        renderUi();
        return;
      }

      currentIdentityReferenceUpload = {
        token: `identity-reference-upload-${String(++currentIdentityReferenceUploadCounter).padStart(6, "0")}`,
        started_at_utc: new Date().toISOString(),
        file_name: null
      };
      setIdentityReferenceUploadNotice("uploading", "Referenz-Upload laeuft...");
      renderUi();

      const uploadToken = currentIdentityReferenceUpload.token;
      try {
        const response = await fetch("/identity-reference-image/current", {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentIdentityReferenceUpload || currentIdentityReferenceUpload.token !== uploadToken) {
          return;
        }

        if (!response.ok || !payload || payload.status !== "ok") {
          setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | reference_reset_failed", {
            error_type: "upload_error",
            blocker: isNonEmptyString(payload?.blocker) ? payload.blocker : "reference_reset_failed"
          });
          renderUi();
          return;
        }

        clearCurrentIdentityReferenceImage({ clearNotice: false });
        setIdentityReferenceUploadNotice("idle", "Referenz entfernt");
        clearIdentityResult();
        currentIdentityRequest = null;
        await fetchHealth({ forceFresh: true });
      } catch (error) {
        if (!currentIdentityReferenceUpload || currentIdentityReferenceUpload.token !== uploadToken) {
          return;
        }

        setIdentityReferenceUploadNotice("error", "Referenz-Upload fehlgeschlagen | reference_reset_failed", {
          error_type: "upload_error",
          blocker: "reference_reset_failed"
        });
      } finally {
        if (currentIdentityReferenceUpload && currentIdentityReferenceUpload.token === uploadToken) {
          currentIdentityReferenceUpload = null;
        }
        renderUi();
      }
    }

    function computeIdentityReferenceUploadControl() {
      const hasSelection = selectedIdentityReferenceFile instanceof File;
      const hasReferenceImage = activeIdentityReferenceImage.state !== "none";
      const busy = Boolean(currentIdentityReferenceUpload) || currentIdentityRequest?.phase === "running";

      return {
        uploadEnabled: hasSelection && !busy,
        resetEnabled: !busy && (hasSelection || hasReferenceImage),
        fileEnabled: !busy
      };
    }

    function renderIdentityReferenceUploadUi() {
      const control = computeIdentityReferenceUploadControl();
      const basicIdentityMode = isV7BasicIdentitySingleMode();
      identityReferenceFileEl.disabled = !control.fileEnabled;
      uploadIdentityReferenceEl.disabled = !control.uploadEnabled;
      resetIdentityReferenceEl.disabled = !control.resetEnabled;

      if (currentIdentityReferenceUpload) {
        identityReferenceStateEl.textContent = basicIdentityMode ? "Referenzbild wird geladen..." : "Referenz-Upload laeuft...";
      } else if (basicIdentityMode && selectedIdentityReferenceFile && !currentIdentityReferenceUpload) {
        identityReferenceStateEl.textContent = "Referenzbild ausgewaehlt";
      } else if (basicIdentityMode && activeIdentityReferenceImage.state === "ready") {
        identityReferenceStateEl.textContent = "Referenzbild geladen";
      } else if (basicIdentityMode) {
        identityReferenceStateEl.textContent = "Referenzbild fehlt noch";
      } else {
        identityReferenceStateEl.textContent = identityReferenceUploadNotice.text;
      }
      identityReferenceStateEl.className = identityReferenceUploadNotice.state === "error" ? "request-state error" : "request-state";

      if (selectedIdentityReferenceFile && !currentIdentityReferenceUpload) {
        identityReferenceHintEl.textContent = basicIdentityMode
          ? `Ausgewaehlt | ${selectedIdentityReferenceFile.name}`
          : `Auswahl | ${selectedIdentityReferenceFile.name}`;
        identityReferenceHintEl.className = "request-state";
      } else if (identityReferenceUploadNotice.state === "error") {
        identityReferenceHintEl.textContent = basicIdentityMode
          ? "Referenzbild konnte gerade nicht geladen werden."
          : `${identityReferenceUploadNotice.error_type || "upload_error"} | ${identityReferenceUploadNotice.blocker || "reference_upload_failed"}`;
        identityReferenceHintEl.className = "request-state error";
      } else if (activeIdentityReferenceImage.state === "loading") {
        identityReferenceHintEl.textContent = basicIdentityMode ? "Vorschau wird geladen..." : "Referenzvorschau laedt...";
        identityReferenceHintEl.className = "request-state";
      } else if (activeIdentityReferenceImage.state === "ready") {
        identityReferenceHintEl.textContent = basicIdentityMode ? "Das Bild ist fuer diese Aufgabe bereit." : "Referenz bereit";
        identityReferenceHintEl.className = "request-state";
      } else {
        identityReferenceHintEl.textContent = "";
        identityReferenceHintEl.className = "request-state";
      }

      identityReferenceHintEl.hidden = basicIdentityMode && !isNonEmptyString(identityReferenceHintEl.textContent);
      identityReferenceMetaEl.textContent = currentIdentityReferenceImageSummary();
    }

    function detachIdentityResultPreviewLoader() {
      if (!activeIdentityResultLoader) {
        return;
      }

      try {
        activeIdentityResultLoader.onload = null;
        activeIdentityResultLoader.onerror = null;
      } catch (error) {
      }
      activeIdentityResultLoader = null;
    }

    function clearIdentityResultDomBindings() {
      identityResultImageEl.onload = null;
      identityResultImageEl.onerror = null;
      delete identityResultImageEl.dataset.identityResultToken;
      delete identityResultImageEl.dataset.identityResultDisplayUrl;
    }

    function clearIdentityResult() {
      detachIdentityResultPreviewLoader();
      clearIdentityResultDomBindings();
      identityResultImageEl.style.display = "none";
      identityResultImageEl.removeAttribute("src");
      activeIdentityResult = {
        token: null,
        result_id: null,
        output_file: null,
        display_url: null,
        request_id: null,
        prompt_id: null,
        state: "none",
        error_type: null,
        blocker: null
      };
    }

    function isIdentityResultPreviewRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      return Boolean(
        activeIdentityResult &&
        activeIdentityResult.token === token &&
        activeIdentityResult.display_url === displayUrl
      );
    }

    function applyIdentityResultPreviewToDom(token, displayUrl) {
      if (!isIdentityResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      identityResultImageEl.dataset.identityResultToken = token;
      identityResultImageEl.dataset.identityResultDisplayUrl = displayUrl;
      identityResultImageEl.onload = () => {
        handleIdentityResultPreviewLoad(token, displayUrl, "dom");
      };
      identityResultImageEl.onerror = () => {
        handleIdentityResultPreviewError(token, displayUrl, "dom");
      };
      identityResultImageEl.src = displayUrl;
      identityResultImageEl.style.display = "block";
      return true;
    }

    function handleIdentityResultPreviewLoad(token, displayUrl, source = "unknown") {
      if (!isIdentityResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      if (source === "loader") {
        return applyIdentityResultPreviewToDom(token, displayUrl);
      }

      activeIdentityResult = {
        ...activeIdentityResult,
        state: "ready"
      };
      renderUi();
      return true;
    }

    function handleIdentityResultPreviewError(token, displayUrl, source = "unknown") {
      if (!isIdentityResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      clearIdentityResult();
      currentIdentityRequest = {
        phase: "error",
        request_token: null,
        error_type: "output_file_missing",
        blocker: "generated_file_not_accessible",
        result_id: null,
        output_file: null
      };
      renderUi();
      return true;
    }

    function setIdentityResult(payload) {
      if (!payload || !isNonEmptyString(payload.output_file)) {
        return false;
      }

      detachIdentityResultPreviewLoader();
      const token = `identity-result-${String(++identityResultPreviewTokenCounter).padStart(6, "0")}`;
      const displayUrl = buildInputPreviewDisplayUrl(payload.output_file.trim(), token);
      activeIdentityResult = {
        token,
        result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
        output_file: payload.output_file.trim(),
        display_url: displayUrl,
        request_id: isNonEmptyString(payload.request_id) ? payload.request_id.trim() : null,
        prompt_id: isNonEmptyString(payload.prompt_id) ? payload.prompt_id.trim() : null,
        state: "loading",
        error_type: null,
        blocker: null
      };
      renderUi();

      const loader = new Image();
      activeIdentityResultLoader = loader;
      loader.onload = () => {
        handleIdentityResultPreviewLoad(token, displayUrl, "loader");
      };
      loader.onerror = () => {
        handleIdentityResultPreviewError(token, displayUrl, "loader");
      };
      loader.src = displayUrl;
      return true;
    }

    function getIdentityVerfuegbarkeitView() {
      if (identityVerfuegbarkeitState.phase === "pending") {
        return {
          ready: false,
          text: "Referenzpfad Verfuegbarkeit wird geprueft...",
          blocker: "identity_readiness_pending",
          is_error: false
        };
      }

      if (identityVerfuegbarkeitState.phase === "error") {
        const blocker = isNonEmptyString(identityVerfuegbarkeitState.payload?.blocker)
          ? identityVerfuegbarkeitState.payload.blocker.trim()
          : (isNonEmptyString(identityVerfuegbarkeitState.error) ? identityVerfuegbarkeitState.error.trim() : "identity_readiness_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${blocker}`,
          blocker,
          is_error: true
        };
      }

      const payload = identityVerfuegbarkeitState.payload;
      const version = isNonEmptyString(payload?.insightface_version) ? ` | insightface ${payload.insightface_version.trim()}` : "";
      return {
        ready: true,
          text: `Referenzpfad bereit | InstantID${version}`,
        blocker: null,
        is_error: false
      };
    }

    async function fetchIdentityVerfuegbarkeit(options = {}) {
      const forceFresh = options.forceFresh === true;

      if (identityVerfuegbarkeitFetchPromise && !forceFresh) {
        return identityVerfuegbarkeitFetchPromise;
      }

      if (identityVerfuegbarkeitFetchPromise && forceFresh) {
        try {
          await identityVerfuegbarkeitFetchPromise;
        } catch (error) {
        }
      }

      if (forceFresh || !identityVerfuegbarkeitState.payload) {
        identityVerfuegbarkeitState = {
          ...identityVerfuegbarkeitState,
          phase: "pending",
          error: "identity_readiness_pending"
        };
      }

      identityVerfuegbarkeitFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-reference/readiness", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("identity_readiness_invalid_payload");
          }

          if (response.ok && payload.ok === true) {
            identityVerfuegbarkeitState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            identityVerfuegbarkeitState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `identity_readiness_http_${response.status}`
            };
          }
          renderUi();
          return identityVerfuegbarkeitState;
        } catch (error) {
          identityVerfuegbarkeitState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          renderUi();
          return identityVerfuegbarkeitState;
        } finally {
          identityVerfuegbarkeitFetchPromise = null;
        }
      })();

      return identityVerfuegbarkeitFetchPromise;
    }

    function buildEmptyMultiReferenceStatusPayload() {
      return {
        status: "ok",
        max_slots: MULTI_REFERENCE_MAX_SLOTS,
        reference_count: 0,
        multi_reference_ready: false,
        slots: Array.from({ length: MULTI_REFERENCE_MAX_SLOTS }, (_, index) => ({
          slot_index: index + 1,
          occupied: false,
          image: null
        }))
      };
    }

    function getMultiReferenceStatusPayload() {
      if (multiReferenceStatusState.payload && typeof multiReferenceStatusState.payload === "object") {
        return multiReferenceStatusState.payload;
      }
      return buildEmptyMultiReferenceStatusPayload();
    }

    function getMultiReferenceVerfuegbarkeitView() {
      if (multiReferenceStatusState.phase === "pending") {
        return {
          ready: false,
          text: "Multi-Referenzpfad Verfuegbarkeit wird geprueft...",
          blocker: "multi_reference_status_pending",
          is_error: false
        };
      }

      if (multiReferenceStatusState.phase === "error") {
        const blocker = isNonEmptyString(multiReferenceStatusState.payload?.blocker)
          ? multiReferenceStatusState.payload.blocker.trim()
          : (isNonEmptyString(multiReferenceStatusState.error) ? multiReferenceStatusState.error.trim() : "multi_reference_status_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${blocker}`,
          blocker,
          is_error: true
        };
      }

      const payload = getMultiReferenceStatusPayload();
      const referenceCount = Number.isFinite(payload.reference_count) ? Number(payload.reference_count) : 0;
      if (payload.multi_reference_ready === true) {
        return {
          ready: true,
          text: `Multi-Referenzpfad bereit | ${referenceCount}/${MULTI_REFERENCE_MAX_SLOTS} Referenzen`,
          blocker: null,
          is_error: false
        };
      }

      return {
        ready: false,
        text: `Noch nicht bereit | ${referenceCount}/${MULTI_REFERENCE_MAX_SLOTS} Referenzen`,
        blocker: "multi_reference_not_ready",
        is_error: false
      };
    }

    function getMultiReferenceRuntimePayload() {
      if (multiReferenceRuntimeState.payload && typeof multiReferenceRuntimeState.payload === "object") {
        return multiReferenceRuntimeState.payload;
      }

      return {
        ok: false,
        error_type: "insufficient_multi_reference_images",
        blocker: "insufficient_multi_reference_images",
        adapter_state: {
          ready: false,
          reference_count: Number(getMultiReferenceStatusPayload().reference_count || 0),
          references: [],
          primary_reference: null,
          blockers: ["insufficient_multi_reference_images"],
          staging_plan: null
        }
      };
    }

    function formatMultiReferenceRuntimeBlocker(blocker) {
      const normalized = isNonEmptyString(blocker) ? blocker.trim() : "identity_multi_reference_not_ready";
      const labels = {
        insufficient_multi_reference_images: "Mindestens zwei Referenzen fehlen",
        identity_workflow_missing: "Multi-Referenzpfad-Workflow fehlt",
        identity_models_missing: "Identity-Modelle fehlen",
        identity_nodes_missing: "Identity-Nodes fehlen",
        identity_runtime_unavailable: "Identity-Runtime nicht nutzbar",
        multi_reference_status_unavailable: "Multi-Reference-Status nicht lesbar",
        multi_reference_not_ready: "Multi-Reference-Bestand noch nicht bereit"
      };
      return labels[normalized] || normalized;
    }

    function getMultiReferenceRuntimeVerfuegbarkeitView() {
      if (multiReferenceRuntimeState.phase === "pending") {
        return {
          ready: false,
          text: "Multi-Referenzpfad Verfuegbarkeit wird geprueft...",
          blocker: "multi_reference_readiness_pending",
          is_error: false
        };
      }

      if (multiReferenceRuntimeState.phase === "error") {
        const blocker = isNonEmptyString(multiReferenceRuntimeState.payload?.blocker)
          ? multiReferenceRuntimeState.payload.blocker.trim()
          : (isNonEmptyString(multiReferenceRuntimeState.error) ? multiReferenceRuntimeState.error.trim() : "multi_reference_readiness_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${formatMultiReferenceRuntimeBlocker(blocker)}`,
          blocker,
          is_error: true
        };
      }

      const payload = getMultiReferenceRuntimePayload();
      const adapterState = payload.adapter_state && typeof payload.adapter_state === "object"
        ? payload.adapter_state
        : null;
      const referenceCount = Number.isFinite(adapterState?.reference_count) ? Number(adapterState.reference_count) : 0;

      if (payload.ok === true && adapterState?.ready === true) {
        return {
          ready: true,
          text: `Multi-Referenzpfad bereit | ${referenceCount} Referenzen`,
          blocker: null,
          is_error: false
        };
      }

      const blocker = isNonEmptyString(payload.blocker)
        ? payload.blocker.trim()
        : (Array.isArray(adapterState?.blockers) && isNonEmptyString(adapterState.blockers[0]) ? adapterState.blockers[0].trim() : "identity_multi_reference_not_ready");
      return {
        ready: false,
        text: `Nicht bereit | ${formatMultiReferenceRuntimeBlocker(blocker)}`,
        blocker,
        is_error: payload.error_type ? true : false
      };
    }

    function isMultiReferenceActionRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        currentMultiReferenceAction &&
        isNonEmptyString(currentMultiReferenceAction.request_token) &&
        currentMultiReferenceAction.request_token === requestToken
      );
    }

    function setMultiReferenceNotice(state, text, errorType = null, blocker = null) {
      multiReferenceNotice = {
        state,
        text,
        error_type: errorType,
        blocker
      };
    }

    function resetSelectedMultiReferenceFile() {
      selectedMultiReferenceFile = null;
      multiReferenceFileEl.value = "";
    }

    function handleMultiReferenceFileSelection(event) {
      const file = event.target?.files?.[0] ?? null;
      selectedMultiReferenceFile = file instanceof File ? file : null;
      if (selectedMultiReferenceFile) {
        setMultiReferenceNotice("idle", `Auswahl | ${selectedMultiReferenceFile.name}`);
      } else {
        setMultiReferenceNotice("idle", "Noch kein Multi-Reference-Bild geladen");
      }
      renderUi();
    }

    async function fetchMultiReferenceStatus(options = {}) {
      const forceFresh = options.forceFresh === true;
      const showLoading = options.showLoading !== false;

      if (multiReferenceStatusFetchPromise && !forceFresh) {
        return multiReferenceStatusFetchPromise;
      }

      if (multiReferenceStatusFetchPromise && forceFresh) {
        try {
          await multiReferenceStatusFetchPromise;
        } catch (error) {
        }
      }

      if (showLoading && (forceFresh || !multiReferenceStatusState.payload)) {
        multiReferenceStatusState = {
          ...multiReferenceStatusState,
          phase: "pending",
          error: "multi_reference_status_pending"
        };
      }

      multiReferenceStatusFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-multi-reference/status", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("multi_reference_status_invalid_payload");
          }

          if (response.ok && Array.isArray(payload.slots)) {
            multiReferenceStatusState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            multiReferenceStatusState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `multi_reference_status_http_${response.status}`
            };
          }
          void fetchMultiReferenceRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
          renderUi();
          return multiReferenceStatusState;
        } catch (error) {
          multiReferenceStatusState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          void fetchMultiReferenceRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
          renderUi();
          return multiReferenceStatusState;
        } finally {
          multiReferenceStatusFetchPromise = null;
        }
      })();

      return multiReferenceStatusFetchPromise;
    }

    async function fetchMultiReferenceRuntimeVerfuegbarkeit(options = {}) {
      const forceFresh = options.forceFresh === true;
      const showLoading = options.showLoading !== false;

      if (multiReferenceRuntimeFetchPromise && !forceFresh) {
        return multiReferenceRuntimeFetchPromise;
      }

      if (multiReferenceRuntimeFetchPromise && forceFresh) {
        try {
          await multiReferenceRuntimeFetchPromise;
        } catch (error) {
        }
      }

      if (showLoading && (forceFresh || !multiReferenceRuntimeState.payload)) {
        multiReferenceRuntimeState = {
          ...multiReferenceRuntimeState,
          phase: "pending",
          error: "multi_reference_readiness_pending"
        };
      }

      multiReferenceRuntimeFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-multi-reference/readiness", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("multi_reference_readiness_invalid_payload");
          }

          if (response.ok && payload.ok === true) {
            multiReferenceRuntimeState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            multiReferenceRuntimeState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `multi_reference_readiness_http_${response.status}`
            };
          }
          renderUi();
          return multiReferenceRuntimeState;
        } catch (error) {
          multiReferenceRuntimeState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          renderUi();
          return multiReferenceRuntimeState;
        } finally {
          multiReferenceRuntimeFetchPromise = null;
        }
      })();

      return multiReferenceRuntimeFetchPromise;
    }

    function isMultiReferenceRequestRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        currentMultiReferenceRequest &&
        isNonEmptyString(currentMultiReferenceRequest.request_token) &&
        currentMultiReferenceRequest.request_token === requestToken
      );
    }

    function computeMultiReferenceControl() {
      return {
        busy: Boolean(currentMultiReferenceAction),
        fileEnabled: !currentMultiReferenceAction,
        slotEnabled: !currentMultiReferenceAction,
        uploadEnabled: selectedMultiReferenceFile instanceof File && !currentMultiReferenceAction,
        resetAllEnabled: !currentMultiReferenceAction && getMultiReferenceStatusPayload().reference_count > 0
      };
    }

    function formatMultiReferenceSlotMeta(slot) {
      if (!slot || slot.occupied !== true || !slot.image) {
        return "frei";
      }
      const image = slot.image;
      const lines = [
        image.image_id || "multi_reference",
        image.original_name || image.stored_name || "referenz",
      ];
      if (Number.isFinite(image.width) && Number.isFinite(image.height)) {
        lines.push(`${image.width} x ${image.height}`);
      }
      if (isNonEmptyString(image.created_at)) {
        lines.push(formatResultCreatedAt(image.created_at));
      }
      return lines.join("\n");
    }

    function renderMultiReferenceUi() {
      const basicMode = isV7BasicIdentityMultiMode();
      const readinessView = getMultiReferenceVerfuegbarkeitView();
      const runtimeVerfuegbarkeitView = getMultiReferenceRuntimeVerfuegbarkeitView();
      const statusPayload = getMultiReferenceStatusPayload();
      const control = computeMultiReferenceControl();
      const running = currentMultiReferenceRequest?.phase === "running";
      const actionBusy = Boolean(currentMultiReferenceAction);
      const prompt = multiReferencePromptEl.value.trim();
      const referenceCount = Number.isFinite(statusPayload.reference_count) ? Number(statusPayload.reference_count) : 0;
      const runtimeEnabled = runtimeVerfuegbarkeitView.ready && !running && !actionBusy && isNonEmptyString(prompt);

      if (basicMode) {
        if (multiReferenceStatusState.phase === "pending") {
          multiReferenceVerfuegbarkeitEl.textContent = "Referenzbilder werden geprueft...";
          multiReferenceVerfuegbarkeitEl.className = "request-state";
        } else if (multiReferenceStatusState.phase === "error") {
          multiReferenceVerfuegbarkeitEl.textContent = "Referenzbilder koennen gerade nicht gelesen werden";
          multiReferenceVerfuegbarkeitEl.className = "request-state error";
        } else if (referenceCount >= 2) {
          multiReferenceVerfuegbarkeitEl.textContent = "Referenzbilder sind bereit";
          multiReferenceVerfuegbarkeitEl.className = "request-state";
        } else if (referenceCount === 1) {
          multiReferenceVerfuegbarkeitEl.textContent = "Ein Referenzbild geladen";
          multiReferenceVerfuegbarkeitEl.className = "request-state";
        } else {
          multiReferenceVerfuegbarkeitEl.textContent = "Es fehlen noch Referenzbilder";
          multiReferenceVerfuegbarkeitEl.className = "request-state";
        }
      } else {
        multiReferenceVerfuegbarkeitEl.textContent = readinessView.text;
        multiReferenceVerfuegbarkeitEl.className = readinessView.is_error ? "request-state error" : "request-state";
      }

      multiReferenceFileEl.disabled = !control.fileEnabled;
      multiReferenceSlotSelectEl.disabled = !control.slotEnabled;
      uploadMultiReferenceEl.disabled = !control.uploadEnabled;
      resetAllMultiReferenceEl.disabled = !control.resetAllEnabled;

      if (currentMultiReferenceAction?.phase === "running") {
        if (basicMode) {
          if (currentMultiReferenceAction.kind === "upload") {
            multiReferenceStateEl.textContent = "Referenzbild wird geladen...";
          } else if (currentMultiReferenceAction.kind === "reset_all") {
            multiReferenceStateEl.textContent = "Referenzbilder werden entfernt...";
          } else {
            multiReferenceStateEl.textContent = "Referenzbild wird entfernt...";
          }
        } else {
          if (currentMultiReferenceAction.kind === "upload") {
            multiReferenceStateEl.textContent = "Referenz-Upload laeuft...";
          } else if (currentMultiReferenceAction.kind === "reset_all") {
            multiReferenceStateEl.textContent = "Alle Referenzslots werden geleert...";
          } else {
            multiReferenceStateEl.textContent = `Slot ${currentMultiReferenceAction.slot_index} wird geleert...`;
          }
        }
        multiReferenceStateEl.className = "request-state";
      } else {
        if (basicMode) {
          if (multiReferenceNotice.state === "error") {
            multiReferenceStateEl.textContent = "Referenzbild konnte gerade nicht geladen werden";
            multiReferenceStateEl.className = "request-state error";
          } else if (referenceCount >= 2) {
            multiReferenceStateEl.textContent = "Referenzbilder sind bereit";
            multiReferenceStateEl.className = "request-state";
          } else if (referenceCount === 1) {
            multiReferenceStateEl.textContent = "Noch ein Referenzbild fehlt";
            multiReferenceStateEl.className = "request-state";
          } else {
            multiReferenceStateEl.textContent = "Noch kein Referenzbild geladen";
            multiReferenceStateEl.className = "request-state";
          }
        } else {
          multiReferenceStateEl.textContent = multiReferenceNotice.text;
          multiReferenceStateEl.className = multiReferenceNotice.state === "error" ? "request-state error" : "request-state";
        }
      }

      if (selectedMultiReferenceFile && !currentMultiReferenceAction) {
        const selectionTarget = multiReferenceSlotSelectEl.value === "auto"
          ? (basicMode ? "Wird automatisch abgelegt" : "Auto-Slot")
          : (basicMode ? `Wird in Slot ${multiReferenceSlotSelectEl.value} ersetzt` : `Slot ${multiReferenceSlotSelectEl.value}`);
        multiReferenceHintEl.textContent = `${selectionTarget} | ${selectedMultiReferenceFile.name}`;
        multiReferenceHintEl.className = "request-state";
      } else if (multiReferenceNotice.state === "error") {
        multiReferenceHintEl.textContent = basicMode
          ? "Das Referenzbild konnte gerade nicht geladen werden."
          : `Fehler | ${multiReferenceNotice.error_type || "api_error"} | ${multiReferenceNotice.blocker || "multi_reference_failed"}`;
        multiReferenceHintEl.className = multiReferenceNotice.state === "error" ? "request-state error" : "request-state";
      } else if (referenceCount > 0) {
        multiReferenceHintEl.textContent = basicMode
          ? `${referenceCount} von ${MULTI_REFERENCE_MAX_SLOTS} Referenzbildern geladen`
          : `${referenceCount}/${MULTI_REFERENCE_MAX_SLOTS} Slots belegt`;
        multiReferenceHintEl.className = "request-state";
      } else {
        multiReferenceHintEl.textContent = basicMode
          ? "Lade bis zu drei Bilder derselben Person hoch."
          : "Bis zu drei Referenzen derselben Person getrennt laden.";
        multiReferenceHintEl.className = "request-state";
      }

      if (basicMode) {
        if (multiReferenceRuntimeState.phase === "pending") {
          multiReferenceRuntimeVerfuegbarkeitEl.textContent = "Funktion wird geprueft...";
          multiReferenceRuntimeVerfuegbarkeitEl.className = "request-state";
        } else if (runtimeVerfuegbarkeitView.ready) {
          multiReferenceRuntimeVerfuegbarkeitEl.textContent = "Funktion ist bereit";
          multiReferenceRuntimeVerfuegbarkeitEl.className = "request-state";
        } else if (referenceCount < 2) {
          multiReferenceRuntimeVerfuegbarkeitEl.textContent = "Du brauchst mindestens zwei Referenzbilder derselben Person";
          multiReferenceRuntimeVerfuegbarkeitEl.className = "request-state";
        } else {
          multiReferenceRuntimeVerfuegbarkeitEl.textContent = "Funktion aktuell nicht verfuegbar";
          multiReferenceRuntimeVerfuegbarkeitEl.className = "request-state error";
        }
      } else {
        multiReferenceRuntimeVerfuegbarkeitEl.textContent = runtimeVerfuegbarkeitView.text;
        multiReferenceRuntimeVerfuegbarkeitEl.className = runtimeVerfuegbarkeitView.is_error ? "request-state error" : "request-state";
      }
      multiReferencePromptEl.disabled = running || actionBusy;
      multiReferenceGenerateEl.disabled = !runtimeEnabled;
      multiReferenceGenerateEl.title = runtimeVerfuegbarkeitView.ready
        ? (!isNonEmptyString(prompt) ? "Bitte beschreibe zuerst deinen Wunsch." : "")
        : formatImageGenerationErrorMessage(runtimeVerfuegbarkeitView.blocker || "identity_multi_reference_not_ready", {
          fallback: "Der Multi-Reference-Pfad ist gerade nicht bereit."
        });

      if (running) {
        multiReferenceRunStateEl.textContent = basicMode ? "Bild wird erstellt..." : "Multi-Referenzpfad-Testlauflauf laeuft...";
        multiReferenceRunStateEl.className = "request-state";
      } else if (currentMultiReferenceRequest?.phase === "success") {
        multiReferenceRunStateEl.textContent = basicMode ? "Ergebnis ist fertig" : "Multi-Referenzpfad-Ergebnis bereit";
        multiReferenceRunStateEl.className = "request-state";
      } else if (currentMultiReferenceRequest?.phase === "error") {
        multiReferenceRunStateEl.textContent = basicMode
          ? "Erstellung fehlgeschlagen"
          : `Multi-Referenzpfad-Testlauflauf fehlgeschlagen | ${currentMultiReferenceRequest.blocker || currentMultiReferenceRequest.error_type || "identity_multi_reference_failed"}`;
        multiReferenceRunStateEl.className = basicMode ? "request-state" : "request-state error";
      } else if (!runtimeVerfuegbarkeitView.ready && basicMode && referenceCount < 2) {
        multiReferenceRunStateEl.textContent = "Du brauchst mindestens zwei Referenzbilder derselben Person";
        multiReferenceRunStateEl.className = "request-state";
      } else if (!runtimeVerfuegbarkeitView.ready && basicMode) {
        multiReferenceRunStateEl.textContent = multiReferenceRuntimeState.phase === "pending"
          ? "Funktion wird geprueft..."
          : "Funktion aktuell nicht verfuegbar";
        multiReferenceRunStateEl.className = runtimeVerfuegbarkeitView.is_error ? "request-state error" : "request-state";
      } else if (basicMode && !isNonEmptyString(prompt)) {
        multiReferenceRunStateEl.textContent = "Gib einen Wunsch ein";
        multiReferenceRunStateEl.className = "request-state";
      } else if (!runtimeVerfuegbarkeitView.ready) {
        multiReferenceRunStateEl.textContent = "Multi-Referenzpfad-Testlauflauf nicht bereit";
        multiReferenceRunStateEl.className = "request-state";
      } else {
        multiReferenceRunStateEl.textContent = basicMode ? "Jetzt kannst du starten" : "Multi-Referenzpfad-Testlauflauf bereit";
        multiReferenceRunStateEl.className = "request-state";
      }

      if (currentMultiReferenceRequest?.phase === "error") {
        multiReferenceRunHintEl.textContent = basicMode
          ? formatImageGenerationErrorMessage(
            currentMultiReferenceRequest.message || currentMultiReferenceRequest.blocker,
            { fallback: "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden." }
          )
          : `Fehler | ${currentMultiReferenceRequest.error_type || "api_error"} | ${currentMultiReferenceRequest.blocker || "identity_multi_reference_failed"}`;
        multiReferenceRunHintEl.className = basicMode ? "request-state" : "request-state error";
      } else if (currentMultiReferenceRequest?.phase === "success" && isNonEmptyString(currentMultiReferenceRequest.result_id)) {
        const resultItem = findResultItemById(currentMultiReferenceRequest.result_id);
        const resultReferenceCount = Number.isFinite(resultItem?.reference_count)
          ? Number(resultItem.reference_count)
          : Number(currentMultiReferenceRequest.reference_count || 0);
        const resultReferenceSlots = Array.isArray(resultItem?.reference_slots)
          ? resultItem.reference_slots
          : (Array.isArray(currentMultiReferenceRequest.reference_slots) ? currentMultiReferenceRequest.reference_slots : []);
        const resultStrategy = isNonEmptyString(resultItem?.multi_reference_strategy)
          ? resultItem.multi_reference_strategy.trim()
          : (isNonEmptyString(currentMultiReferenceRequest.multi_reference_strategy) ? currentMultiReferenceRequest.multi_reference_strategy.trim() : "identity_multi_reference");
        const slotsText = resultReferenceSlots.length > 0
          ? resultReferenceSlots.join(",")
          : "-";
        multiReferenceRunHintEl.textContent = basicMode
          ? `Die neue Variante wurde mit allen geladenen Referenzbildern erstellt. Genutzte Slots: ${slotsText}.`
          : `${currentMultiReferenceRequest.result_id} | Referenzen: ${resultReferenceCount} | Slots: ${slotsText} | ${resultStrategy}`;
        multiReferenceRunHintEl.className = "request-state";
      } else if (runtimeVerfuegbarkeitView.ready && basicMode && !isNonEmptyString(prompt)) {
        multiReferenceRunHintEl.textContent = "Beschreibe jetzt die neue Variante derselben Person.";
        multiReferenceRunHintEl.className = "request-state";
      } else if (runtimeVerfuegbarkeitView.ready && basicMode) {
        multiReferenceRunHintEl.textContent = "Alle geladenen Referenzbilder werden fuer die neue Variante gemeinsam genutzt.";
        multiReferenceRunHintEl.className = "request-state";
      } else if (basicMode && referenceCount < 2) {
        multiReferenceRunHintEl.textContent = "Lade mindestens zwei Bilder derselben Person hoch.";
        multiReferenceRunHintEl.className = "request-state";
      } else if (runtimeVerfuegbarkeitView.ready) {
        const adapterState = getMultiReferenceRuntimePayload().adapter_state;
        const primarySlot = Number.isFinite(adapterState?.primary_reference?.slot_index) ? Number(adapterState.primary_reference.slot_index) : null;
        multiReferenceRunHintEl.textContent = primarySlot
          ? `Primaere Referenz aktuell aus Slot ${primarySlot}; alle belegten Slots gehen in den Testpfad ein.`
          : "Mindestens zwei belegte Slots werden im Testpfad gemeinsam verwendet.";
        multiReferenceRunHintEl.className = "request-state";
      } else {
        multiReferenceRunHintEl.textContent = "";
        multiReferenceRunHintEl.className = "request-state";
      }

      for (let slotIndex = 1; slotIndex <= MULTI_REFERENCE_MAX_SLOTS; slotIndex += 1) {
        const slot = Array.isArray(statusPayload.slots)
          ? statusPayload.slots.find((candidate) => Number(candidate?.slot_index) === slotIndex)
          : null;
        const occupied = slot?.occupied === true && slot?.image && isNonEmptyString(slot.image.preview_url);
        const slotStateEl = multiReferenceSlotStateEls[slotIndex];
        const slotMetaEl = multiReferenceSlotMetaEls[slotIndex];
        const slotPreviewEl = multiReferenceSlotPreviewEls[slotIndex];
        const resetButtonEl = resetMultiReferenceSlotEls[slotIndex];

        slotStateEl.textContent = basicMode
          ? (occupied ? "Referenzbild geladen" : "Frei")
          : (occupied ? `Slot ${slotIndex} belegt` : `Slot ${slotIndex} frei`);
        slotStateEl.className = "request-state";
        resetButtonEl.disabled = Boolean(currentMultiReferenceAction) || !occupied;
        slotMetaEl.textContent = formatMultiReferenceSlotMeta(slot);

        if (occupied) {
          showUploadPreview(slotPreviewEl, slot.image.preview_url);
        } else {
          clearUploadPreview(slotPreviewEl);
        }
      }
    }

    async function attemptIdentityMultiReferenceGenerate() {
      if (currentMultiReferenceRequest?.phase === "running" || currentMultiReferenceAction) {
        return;
      }

      const readiness = await fetchMultiReferenceRuntimeVerfuegbarkeit({ forceFresh: true });
      const readinessView = getMultiReferenceRuntimeVerfuegbarkeitView();
      if (!readiness || !readinessView.ready) {
        currentMultiReferenceRequest = {
          phase: "error",
          request_token: null,
          error_type: "api_error",
          blocker: readinessView.blocker || "identity_multi_reference_not_ready",
          message: formatImageGenerationErrorMessage(readinessView.blocker || "identity_multi_reference_not_ready", {
            fallback: "Der Multi-Reference-Pfad ist gerade nicht bereit."
          }),
          result_id: null,
          reference_count: 0,
          reference_slots: [],
          multi_reference_strategy: null
        };
        renderUi();
        return;
      }

      const prompt = multiReferencePromptEl.value.trim();
      if (!prompt) {
        currentMultiReferenceRequest = {
          phase: "error",
          request_token: null,
          error_type: "invalid_request",
          blocker: "empty_prompt",
          message: "Bitte gib zuerst einen Wunsch ein.",
          result_id: null,
          reference_count: 0,
          reference_slots: [],
          multi_reference_strategy: null
        };
        renderUi();
        return;
      }

      const requestToken = `identity-multi-reference-request-${String(++currentMultiReferenceRequestCounter).padStart(6, "0")}`;
      currentMultiReferenceRequest = {
        phase: "running",
        request_token: requestToken,
        error_type: null,
        blocker: null,
        message: null,
        result_id: null,
        reference_count: 0,
        reference_slots: [],
        multi_reference_strategy: null
      };
      renderUi();

      try {
        const healthPayload = healthState.payload || await fetchHealth({ forceFresh: true });
        const checkpoint = isNonEmptyString(healthPayload?.selected_checkpoint) ? healthPayload.selected_checkpoint.trim() : "";
        const response = await fetch("/identity-multi-reference/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            checkpoint
          })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isMultiReferenceRequestRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload && payload.status === "ok" && isNonEmptyString(payload.output_file)) {
          const resultItem = await fetchResultItemByIdWithRetry(payload.result_id);
          const resultReferenceCount = Number.isFinite(resultItem?.reference_count)
            ? Number(resultItem.reference_count)
            : (Number.isFinite(payload.reference_count) ? Number(payload.reference_count) : 0);
          const resultReferenceSlots = Array.isArray(resultItem?.reference_slots)
            ? resultItem.reference_slots
            : (Array.isArray(payload.reference_slots) ? payload.reference_slots : []);
          const resultStrategy = isNonEmptyString(resultItem?.multi_reference_strategy)
            ? resultItem.multi_reference_strategy.trim()
            : (isNonEmptyString(payload.multi_reference_strategy) ? payload.multi_reference_strategy.trim() : null);
          currentMultiReferenceRequest = {
            phase: "success",
            request_token: null,
            error_type: null,
            blocker: null,
            message: null,
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            reference_count: resultReferenceCount,
            reference_slots: resultReferenceSlots,
            multi_reference_strategy: resultStrategy
          };
          const result = {
            ...compactResult(payload),
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            restored_from_storage: false,
            v7_basic_task: isV7BasicIdentityMultiMode() ? "identity-multi" : null
          };
          lastResult = result;
          lastSuccessfulResult = result;
          persist_last_success(result);
          setActiveImage(result.output_file, {
            request_id: result.request_id,
            mode: result.mode,
            prompt_id: result.prompt_id,
            restored_from_storage: false
          });
          await fetchResults({ showLoading: false });
          renderUi();
          return;
        }

        currentMultiReferenceRequest = {
          phase: "error",
          request_token: null,
          error_type: isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "api_error",
          blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_multi_reference_http_${response.status}`,
          message: formatImageGenerationErrorMessage(
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_multi_reference_http_${response.status}`,
            { fallback: "Der Multi-Reference-Pfad konnte gerade nicht abgeschlossen werden." }
          ),
          result_id: null,
          reference_count: 0,
          reference_slots: [],
          multi_reference_strategy: null
        };
        renderUi();
      } catch (error) {
        if (!isMultiReferenceRequestRelevant(requestToken)) {
          return;
        }

        currentMultiReferenceRequest = {
          phase: "error",
          request_token: null,
          error_type: "api_error",
          blocker: error instanceof Error ? error.message : String(error),
          message: formatImageGenerationErrorMessage(error instanceof Error ? error.message : String(error), {
            fallback: "Der Multi-Reference-Pfad konnte gerade nicht abgeschlossen werden."
          }),
          result_id: null,
          reference_count: 0,
          reference_slots: [],
          multi_reference_strategy: null
        };
        renderUi();
      }
    }

    async function attemptUploadMultiReference() {
      if (currentMultiReferenceAction) {
        return;
      }
      if (!(selectedMultiReferenceFile instanceof File)) {
        setMultiReferenceNotice("error", "Referenz-Upload fehlgeschlagen | keine Datei ausgewaehlt", "invalid_request", "missing_file");
        renderUi();
        return;
      }

      const requestToken = `multi-reference-action-${String(++currentMultiReferenceActionCounter).padStart(6, "0")}`;
      currentMultiReferenceAction = {
        phase: "running",
        kind: "upload",
        request_token: requestToken,
        slot_index: null
      };
      renderUi();

      try {
        const formData = new FormData();
        formData.append("file", selectedMultiReferenceFile);
        const selectedSlot = multiReferenceSlotSelectEl.value;
        if (isNonEmptyString(selectedSlot) && selectedSlot !== "auto") {
          formData.append("slot_index", selectedSlot);
        }

        const response = await fetch("/identity-multi-reference-image", {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true && Number.isFinite(payload.slot_index)) {
          resetSelectedMultiReferenceFile();
          currentMultiReferenceRequest = null;
          setMultiReferenceNotice("success", `Referenz in Slot ${payload.slot_index} gespeichert`);
          await fetchMultiReferenceStatus({ forceFresh: true, showLoading: false });
        } else {
          setMultiReferenceNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : "Referenz-Upload fehlgeschlagen",
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `multi_reference_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }
        setMultiReferenceNotice(
          "error",
          "Referenz-Upload fehlgeschlagen",
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isMultiReferenceActionRelevant(requestToken)) {
          currentMultiReferenceAction = null;
          renderUi();
        }
      }
    }

    async function resetMultiReferenceSlot(slotIndex) {
      if (currentMultiReferenceAction) {
        return;
      }

      const requestToken = `multi-reference-action-${String(++currentMultiReferenceActionCounter).padStart(6, "0")}`;
      currentMultiReferenceAction = {
        phase: "running",
        kind: "reset_slot",
        request_token: requestToken,
        slot_index: slotIndex
      };
      renderUi();

      try {
        const response = await fetch(`/identity-multi-reference-image/slot/${slotIndex}`, {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true) {
          currentMultiReferenceRequest = null;
          setMultiReferenceNotice("success", `Slot ${slotIndex} geleert`);
          await fetchMultiReferenceStatus({ forceFresh: true, showLoading: false });
        } else {
          setMultiReferenceNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : `Slot ${slotIndex} konnte nicht geleert werden`,
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `multi_reference_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }
        setMultiReferenceNotice(
          "error",
          `Slot ${slotIndex} konnte nicht geleert werden`,
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isMultiReferenceActionRelevant(requestToken)) {
          currentMultiReferenceAction = null;
          renderUi();
        }
      }
    }

    async function resetAllMultiReferences() {
      if (currentMultiReferenceAction) {
        return;
      }

      const requestToken = `multi-reference-action-${String(++currentMultiReferenceActionCounter).padStart(6, "0")}`;
      currentMultiReferenceAction = {
        phase: "running",
        kind: "reset_all",
        request_token: requestToken,
        slot_index: null
      };
      renderUi();

      try {
        const response = await fetch("/identity-multi-reference-images/current", {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true) {
          currentMultiReferenceRequest = null;
          setMultiReferenceNotice("success", "Alle Multi-Reference-Slots geleert");
          await fetchMultiReferenceStatus({ forceFresh: true, showLoading: false });
        } else {
          setMultiReferenceNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : "Multi-Reference-Slots konnten nicht geleert werden",
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `multi_reference_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isMultiReferenceActionRelevant(requestToken)) {
          return;
        }
        setMultiReferenceNotice(
          "error",
          "Multi-Reference-Slots konnten nicht geleert werden",
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isMultiReferenceActionRelevant(requestToken)) {
          currentMultiReferenceAction = null;
          renderUi();
        }
      }
    }

    function buildEmptyIdentityTransferStatusPayload() {
      return {
        status: "ok",
        v6_3_transfer_ready: false,
        required_roles: IDENTITY_TRANSFER_ROLE_CONFIG.filter((config) => config.required).map((config) => config.role),
        optional_roles: IDENTITY_TRANSFER_ROLE_CONFIG.filter((config) => !config.required).map((config) => config.role),
        occupied_role_count: 0,
        roles: IDENTITY_TRANSFER_ROLE_CONFIG.map((config) => ({
          role: config.role,
          required: config.required,
          occupied: false,
          image: null
        })),
        blockers: [
          "missing_identity_head_reference",
          "missing_target_body_image"
        ]
      };
    }

    function getIdentityTransferStatusPayload() {
      if (identityTransferStatusState.payload && typeof identityTransferStatusState.payload === "object") {
        return identityTransferStatusState.payload;
      }
      return buildEmptyIdentityTransferStatusPayload();
    }

    function formatIdentityTransferBlocker(blocker) {
      if (!isNonEmptyString(blocker)) {
        return "identity_transfer_not_ready";
      }
      if (blocker === "missing_identity_head_reference") {
        return "Kopf-Referenzbild fehlt";
      }
      if (blocker === "missing_target_body_image") {
        return "Zielbild fehlt";
      }
      return blocker;
    }

    function getIdentityTransferVerfuegbarkeitView() {
      if (identityTransferStatusState.phase === "pending") {
        return {
          ready: false,
          text: "Standardpfad Verfuegbarkeit wird geprueft...",
          blocker: "identity_transfer_status_pending",
          is_error: false
        };
      }

      if (identityTransferStatusState.phase === "error") {
        const blocker = isNonEmptyString(identityTransferStatusState.payload?.blocker)
          ? identityTransferStatusState.payload.blocker.trim()
          : (isNonEmptyString(identityTransferStatusState.error) ? identityTransferStatusState.error.trim() : "identity_transfer_status_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${formatIdentityTransferBlocker(blocker)}`,
          blocker,
          is_error: true
        };
      }

      const payload = getIdentityTransferStatusPayload();
      if (payload.v6_3_transfer_ready === true) {
        return {
          ready: true,
          text: "Standardpfad bereit | Pflichtrollen vorhanden",
          blocker: null,
          is_error: false
        };
      }

      const blockers = Array.isArray(payload.blockers) ? payload.blockers.filter((value) => isNonEmptyString(value)) : [];
      const primaryBlocker = blockers.length > 0 ? String(blockers[0]).trim() : "identity_transfer_not_ready";
      return {
        ready: false,
        text: `Noch nicht bereit | ${formatIdentityTransferBlocker(primaryBlocker)}`,
        blocker: primaryBlocker,
        is_error: false
      };
    }

    function isIdentityTransferActionRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        currentIdentityTransferAction &&
        isNonEmptyString(currentIdentityTransferAction.request_token) &&
        currentIdentityTransferAction.request_token === requestToken
      );
    }

    function setIdentityTransferNotice(state, text, errorType = null, blocker = null) {
      identityTransferNotice = {
        state,
        text,
        error_type: errorType,
        blocker
      };
    }

    function resetSelectedIdentityTransferFile(role) {
      if (!(role in selectedIdentityTransferFiles)) {
        return;
      }
      selectedIdentityTransferFiles[role] = null;
      const roleView = identityTransferRoleViews[role];
      if (roleView?.fileEl) {
        roleView.fileEl.value = "";
      }
    }

    function handleIdentityTransferFileSelection(role, event) {
      const file = event.target?.files?.[0] ?? null;
      selectedIdentityTransferFiles[role] = file instanceof File ? file : null;
      if (selectedIdentityTransferFiles[role]) {
        setIdentityTransferNotice("idle", `Auswahl | ${identityTransferRoleViews[role].label}`);
      } else {
        setIdentityTransferNotice("idle", "Noch keine Standardpfad-Rolle geladen");
      }
      renderUi();
    }

    async function fetchIdentityTransferStatus(options = {}) {
      const forceFresh = options.forceFresh === true;
      const showLoading = options.showLoading !== false;

      if (identityTransferStatusFetchPromise && !forceFresh) {
        return identityTransferStatusFetchPromise;
      }

      if (identityTransferStatusFetchPromise && forceFresh) {
        try {
          await identityTransferStatusFetchPromise;
        } catch (error) {
        }
      }

      if (showLoading && (forceFresh || !identityTransferStatusState.payload)) {
        identityTransferStatusState = {
          ...identityTransferStatusState,
          phase: "pending",
          error: "identity_transfer_status_pending"
        };
      }

      identityTransferStatusFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-transfer/status", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("identity_transfer_status_invalid_payload");
          }

          if (response.ok && Array.isArray(payload.roles)) {
            identityTransferStatusState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            identityTransferStatusState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `identity_transfer_status_http_${response.status}`
            };
          }
          renderUi();
          return identityTransferStatusState;
        } catch (error) {
          identityTransferStatusState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          renderUi();
          return identityTransferStatusState;
        } finally {
          identityTransferStatusFetchPromise = null;
        }
      })();

      return identityTransferStatusFetchPromise;
    }

    function computeIdentityTransferControl() {
      const payload = getIdentityTransferStatusPayload();
      return {
        busy: Boolean(currentIdentityTransferAction),
        resetAllEnabled: !currentIdentityTransferAction && Number(payload.occupied_role_count || 0) > 0
      };
    }

    function formatIdentityTransferRoleMeta(roleEntry) {
      if (!roleEntry || roleEntry.occupied !== true || !roleEntry.image) {
        return "frei";
      }
      const image = roleEntry.image;
      const lines = [
        image.image_id || roleEntry.role || "role_image",
        image.original_name || image.stored_name || "bild",
      ];
      if (Number.isFinite(image.width) && Number.isFinite(image.height)) {
        lines.push(`${image.width} x ${image.height}`);
      }
      if (isNonEmptyString(image.created_at)) {
        lines.push(formatResultCreatedAt(image.created_at));
      }
      return lines.join("\n");
    }

    function renderIdentityTransferUi() {
      const readinessView = getIdentityTransferVerfuegbarkeitView();
      const payload = getIdentityTransferStatusPayload();
      const control = computeIdentityTransferControl();
      const basicMode = isV7BasicIdentityTransferMode();

      if (basicMode) {
        if (payload.v6_3_transfer_ready === true) {
          identityTransferVerfuegbarkeitEl.textContent = "Pflichtbilder sind bereit";
          identityTransferVerfuegbarkeitEl.className = "request-state";
        } else if (readinessView.is_error) {
          identityTransferVerfuegbarkeitEl.textContent = "Bilder koennen gerade nicht geprueft werden";
          identityTransferVerfuegbarkeitEl.className = "request-state error";
        } else if (hasIdentityTransferRoleImage("identity_head_reference") && !hasIdentityTransferRoleImage("target_body_image")) {
          identityTransferVerfuegbarkeitEl.textContent = "Zielbild fehlt noch";
          identityTransferVerfuegbarkeitEl.className = "request-state";
        } else if (!hasIdentityTransferRoleImage("identity_head_reference")) {
          identityTransferVerfuegbarkeitEl.textContent = "Kopf-Referenz fehlt noch";
          identityTransferVerfuegbarkeitEl.className = "request-state";
        } else {
          identityTransferVerfuegbarkeitEl.textContent = "Bilder werden geprueft...";
          identityTransferVerfuegbarkeitEl.className = "request-state";
        }
      } else {
        identityTransferVerfuegbarkeitEl.textContent = readinessView.text;
        identityTransferVerfuegbarkeitEl.className = readinessView.is_error ? "request-state error" : "request-state";
      }
      resetAllIdentityTransferEl.disabled = !control.resetAllEnabled;

      if (currentIdentityTransferAction?.phase === "running") {
        if (currentIdentityTransferAction.kind === "upload") {
          identityTransferStateEl.textContent = `${identityTransferRoleViews[currentIdentityTransferAction.role]?.label || currentIdentityTransferAction.role} wird ${basicMode ? "geladen" : "gespeichert"}...`;
        } else if (currentIdentityTransferAction.kind === "reset_all") {
          identityTransferStateEl.textContent = basicMode ? "Bilder werden entfernt..." : "Alle Rollen werden geleert...";
        } else {
          identityTransferStateEl.textContent = `${identityTransferRoleViews[currentIdentityTransferAction.role]?.label || currentIdentityTransferAction.role} wird ${basicMode ? "entfernt" : "geleert"}...`;
        }
        identityTransferStateEl.className = "request-state";
      } else {
        identityTransferStateEl.textContent = identityTransferNotice.text;
        identityTransferStateEl.className = identityTransferNotice.state === "error" ? "request-state error" : "request-state";
      }

      const selectedSummaries = IDENTITY_TRANSFER_ROLE_CONFIG
        .filter((config) => selectedIdentityTransferFiles[config.role] instanceof File)
        .map((config) => `${config.label} | ${selectedIdentityTransferFiles[config.role].name}`);
      if (selectedSummaries.length > 0 && !currentIdentityTransferAction) {
        identityTransferHintEl.textContent = selectedSummaries[0];
        identityTransferHintEl.className = "request-state";
      } else if (identityTransferNotice.state === "error") {
        identityTransferHintEl.textContent = basicMode
          ? "Das Bild konnte gerade nicht geladen werden."
          : `${identityTransferNotice.error_type || "api_error"} | ${identityTransferNotice.blocker || "identity_transfer_failed"}`;
        identityTransferHintEl.className = "request-state error";
      } else if (payload.v6_3_transfer_ready === true) {
        identityTransferHintEl.textContent = basicMode
          ? "Pose und Maske sind nur zusaetzlich."
          : "Pflichtbilder vorhanden | optionale Pose und Transfer-Maske getrennt.";
        identityTransferHintEl.className = "request-state";
      } else {
        identityTransferHintEl.textContent = basicMode
          ? "Du brauchst Kopf-Referenzbild und Zielbild."
          : "Pflichtbilder: Kopf-Referenzbild und Zielbild.";
        identityTransferHintEl.className = "request-state";
      }

      for (const config of IDENTITY_TRANSFER_ROLE_CONFIG) {
        const roleView = identityTransferRoleViews[config.role];
        const roleEntry = Array.isArray(payload.roles)
          ? payload.roles.find((candidate) => candidate?.role === config.role)
          : null;
        const occupied = roleEntry?.occupied === true && roleEntry?.image && isNonEmptyString(roleEntry.image.preview_url);
        const selectedFile = selectedIdentityTransferFiles[config.role];

        roleView.fileEl.disabled = control.busy;
        roleView.uploadEl.disabled = control.busy || !(selectedFile instanceof File);
        roleView.resetEl.disabled = control.busy || !occupied;
        roleView.metaEl.textContent = formatIdentityTransferRoleMeta(roleEntry);

        if (currentIdentityTransferAction?.phase === "running" && currentIdentityTransferAction.role === config.role) {
          roleView.stateEl.textContent = currentIdentityTransferAction.kind === "upload"
            ? (basicMode ? "Bild wird geladen..." : "Upload laeuft...")
            : (basicMode ? "Bild wird entfernt..." : "Wird geleert...");
          roleView.stateEl.className = "request-state";
        } else if (selectedFile instanceof File) {
          roleView.stateEl.textContent = basicMode ? `Ausgewaehlt | ${selectedFile.name}` : `Auswahl | ${selectedFile.name}`;
          roleView.stateEl.className = "request-state";
        } else if (occupied) {
          roleView.stateEl.textContent = basicMode
            ? (config.required ? "Bild geladen" : "Optional geladen")
            : (config.required ? "Pflichtrolle geladen" : "Optionale Rolle geladen");
          roleView.stateEl.className = "request-state";
        } else if (config.required) {
          roleView.stateEl.textContent = basicMode ? "Fehlt noch" : "Pflichtrolle fehlt";
          roleView.stateEl.className = basicMode ? "request-state" : "request-state error";
        } else {
          roleView.stateEl.textContent = basicMode ? "Optional" : "Optional";
          roleView.stateEl.className = "request-state";
        }

        if (occupied) {
          showUploadPreview(roleView.previewEl, roleEntry.image.preview_url);
        } else {
          clearUploadPreview(roleView.previewEl);
        }
      }
    }

    async function attemptUploadIdentityTransferRole(role) {
      if (currentIdentityTransferAction) {
        return;
      }

      const selectedFile = selectedIdentityTransferFiles[role];
      if (!(selectedFile instanceof File)) {
        setIdentityTransferNotice("error", "Upload fehlgeschlagen | keine Datei ausgewaehlt", "invalid_request", "missing_file");
        renderUi();
        return;
      }

      const requestToken = `identity-transfer-action-${String(++currentIdentityTransferActionCounter).padStart(6, "0")}`;
      currentIdentityTransferAction = {
        phase: "running",
        kind: "upload",
        request_token: requestToken,
        role
      };
      renderUi();

      try {
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("role", role);

        const response = await fetch("/identity-transfer-role-image", {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true && isNonEmptyString(payload.role)) {
          resetSelectedIdentityTransferFile(role);
          setIdentityTransferNotice("success", `${identityTransferRoleViews[role].label} gespeichert`);
          await fetchIdentityTransferStatus({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
        } else {
          setIdentityTransferNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : "Upload im Rollenbereich fehlgeschlagen",
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }
        setIdentityTransferNotice(
          "error",
          "Upload im Rollenbereich fehlgeschlagen",
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isIdentityTransferActionRelevant(requestToken)) {
          currentIdentityTransferAction = null;
          renderUi();
        }
      }
    }

    async function resetIdentityTransferRole(role) {
      if (currentIdentityTransferAction) {
        return;
      }

      const requestToken = `identity-transfer-action-${String(++currentIdentityTransferActionCounter).padStart(6, "0")}`;
      currentIdentityTransferAction = {
        phase: "running",
        kind: "reset_role",
        request_token: requestToken,
        role
      };
      renderUi();

      try {
        const response = await fetch(`/identity-transfer-role-image/${role}`, {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true) {
          resetSelectedIdentityTransferFile(role);
          setIdentityTransferNotice("success", `${identityTransferRoleViews[role].label} geleert`);
          await fetchIdentityTransferStatus({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
        } else {
          setIdentityTransferNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : "Rolle konnte nicht geleert werden",
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }
        setIdentityTransferNotice(
          "error",
          "Rolle konnte nicht geleert werden",
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isIdentityTransferActionRelevant(requestToken)) {
          currentIdentityTransferAction = null;
          renderUi();
        }
      }
    }

    async function resetAllIdentityTransferRoles() {
      if (currentIdentityTransferAction) {
        return;
      }

      const requestToken = `identity-transfer-action-${String(++currentIdentityTransferActionCounter).padStart(6, "0")}`;
      currentIdentityTransferAction = {
        phase: "running",
        kind: "reset_all",
        request_token: requestToken,
        role: null
      };
      renderUi();

      try {
        const response = await fetch("/identity-transfer-role-images/current", {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload?.ok === true) {
          for (const config of IDENTITY_TRANSFER_ROLE_CONFIG) {
            resetSelectedIdentityTransferFile(config.role);
          }
          setIdentityTransferNotice("success", "Alle Rollen geleert");
          await fetchIdentityTransferStatus({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
          await fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit({ forceFresh: true, showLoading: false });
        } else {
          setIdentityTransferNotice(
            "error",
            isNonEmptyString(payload?.message) ? payload.message.trim() : "Rollen konnten nicht geleert werden",
            isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "upload_error",
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_http_${response.status}`
          );
        }
      } catch (error) {
        if (!isIdentityTransferActionRelevant(requestToken)) {
          return;
        }
        setIdentityTransferNotice(
          "error",
          "Rollen konnten nicht geleert werden",
          "upload_error",
          error instanceof Error ? error.message : String(error)
        );
      } finally {
        if (isIdentityTransferActionRelevant(requestToken)) {
          currentIdentityTransferAction = null;
          renderUi();
        }
      }
    }

    function buildEmptyIdentityTransferRuntimePayload() {
      return {
        ok: false,
        error_type: "invalid_request",
        blocker: "missing_identity_head_reference",
        required_roles_present: {
          identity_head_reference: false,
          target_body_image: false
        },
        optional_roles_present: {
          pose_reference: false,
          transfer_mask: false
        },
        adapter_state: null,
        missing_nodes: [],
        missing_models: [],
        insightface_version: null
      };
    }

    function getIdentityTransferRuntimePayload() {
      if (identityTransferRuntimeState.payload && typeof identityTransferRuntimeState.payload === "object") {
        return identityTransferRuntimeState.payload;
      }
      return buildEmptyIdentityTransferRuntimePayload();
    }

    function findResultItemById(resultId) {
      if (!isNonEmptyString(resultId) || !Array.isArray(resultsState.items)) {
        return null;
      }
      return resultsState.items.find((item) => item?.result_id === resultId.trim()) || null;
    }

    async function fetchResultItemByIdWithRetry(resultId, attempts = 5, delayMs = 400) {
      if (!isNonEmptyString(resultId)) {
        return null;
      }

      const maxAttempts = Number.isFinite(attempts) && attempts > 0 ? Number(attempts) : 1;
      for (let index = 0; index < maxAttempts; index += 1) {
        const items = await fetchResults({ showLoading: false });
        const resultItem = Array.isArray(items) ? items.find((item) => item?.result_id === resultId.trim()) || null : null;
        if (resultItem) {
          return resultItem;
        }
        if (index + 1 < maxAttempts) {
          await new Promise((resolve) => window.setTimeout(resolve, delayMs));
        }
      }

      return findResultItemById(resultId);
    }

    function detachIdentityTransferResultPreviewLoader() {
      if (!activeIdentityTransferResultLoader) {
        return;
      }

      try {
        activeIdentityTransferResultLoader.onload = null;
        activeIdentityTransferResultLoader.onerror = null;
      } catch (error) {
      }
      activeIdentityTransferResultLoader = null;
    }

    function clearIdentityTransferResultDomBindings() {
      identityTransferResultImageEl.onload = null;
      identityTransferResultImageEl.onerror = null;
      delete identityTransferResultImageEl.dataset.identityTransferResultToken;
      delete identityTransferResultImageEl.dataset.identityTransferResultDisplayUrl;
    }

    function clearIdentityTransferResult() {
      detachIdentityTransferResultPreviewLoader();
      clearIdentityTransferResultDomBindings();
      identityTransferResultImageEl.style.display = "none";
      identityTransferResultImageEl.removeAttribute("src");
      activeIdentityTransferResult = {
        token: null,
        result_id: null,
        output_file: null,
        display_url: null,
        request_id: null,
        prompt_id: null,
        state: "none",
        error_type: null,
        blocker: null,
        used_roles: [],
        pose_reference_present: false,
        pose_reference_used: false,
        transfer_mask_present: false,
        transfer_mask_used: false,
        identity_transfer_strategy: null
      };
    }

    function isIdentityTransferResultPreviewRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      return Boolean(
        activeIdentityTransferResult &&
        activeIdentityTransferResult.token === token &&
        activeIdentityTransferResult.display_url === displayUrl
      );
    }

    function applyIdentityTransferResultPreviewToDom(token, displayUrl) {
      if (!isIdentityTransferResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      identityTransferResultImageEl.dataset.identityTransferResultToken = token;
      identityTransferResultImageEl.dataset.identityTransferResultDisplayUrl = displayUrl;
      identityTransferResultImageEl.onload = () => {
        handleIdentityTransferResultPreviewLoad(token, displayUrl, "dom");
      };
      identityTransferResultImageEl.onerror = () => {
        handleIdentityTransferResultPreviewError(token, displayUrl, "dom");
      };
      identityTransferResultImageEl.src = displayUrl;
      identityTransferResultImageEl.style.display = "block";
      return true;
    }

    function handleIdentityTransferResultPreviewLoad(token, displayUrl, source = "unknown") {
      if (!isIdentityTransferResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      if (source === "loader") {
        return applyIdentityTransferResultPreviewToDom(token, displayUrl);
      }

      activeIdentityTransferResult = {
        ...activeIdentityTransferResult,
        state: "ready"
      };
      renderUi();
      return true;
    }

    function handleIdentityTransferResultPreviewError(token, displayUrl, source = "unknown") {
      if (!isIdentityTransferResultPreviewRelevant(token, displayUrl)) {
        return false;
      }

      const previousPathMode = normalizeIdentityTransferPathMode(
        currentIdentityTransferRequest?.path_mode
          || (activeIdentityTransferResult.identity_transfer_strategy === "instantid_target_body_masked_latent" ? "mask_hybrid" : "standard")
      );
      clearIdentityTransferResult();
      currentIdentityTransferRequest = {
        phase: "error",
        path_mode: previousPathMode,
        request_token: null,
        error_type: "output_file_missing",
        blocker: "generated_file_not_accessible",
        result_id: null,
        output_file: null
      };
      renderUi();
      return true;
    }

    function setIdentityTransferResult(payload, resultItem = null) {
      if (!payload || !isNonEmptyString(payload.output_file)) {
        return false;
      }

      detachIdentityTransferResultPreviewLoader();
      const token = `identity-transfer-result-${String(++identityTransferResultPreviewTokenCounter).padStart(6, "0")}`;
      const preferredUrl = isNonEmptyString(resultItem?.preview_url) ? resultItem.preview_url.trim() : payload.output_file.trim();
      const displayUrl = buildInputPreviewDisplayUrl(preferredUrl, token);
      activeIdentityTransferResult = {
        token,
        result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : (isNonEmptyString(resultItem?.result_id) ? resultItem.result_id.trim() : null),
        output_file: preferredUrl,
        display_url: displayUrl,
        request_id: isNonEmptyString(payload.request_id) ? payload.request_id.trim() : null,
        prompt_id: isNonEmptyString(payload.prompt_id) ? payload.prompt_id.trim() : null,
        state: "loading",
        error_type: null,
        blocker: null,
        used_roles: Array.isArray(resultItem?.used_roles) ? resultItem.used_roles.slice() : [],
        pose_reference_present: resultItem?.pose_reference_present === true,
        pose_reference_used: resultItem?.pose_reference_used === true,
        transfer_mask_present: resultItem?.transfer_mask_present === true,
        transfer_mask_used: resultItem?.transfer_mask_used === true,
        identity_transfer_strategy: isNonEmptyString(resultItem?.identity_transfer_strategy) ? resultItem.identity_transfer_strategy.trim() : null
      };
      renderUi();

      const loader = new Image();
      activeIdentityTransferResultLoader = loader;
      loader.onload = () => {
        handleIdentityTransferResultPreviewLoad(token, displayUrl, "loader");
      };
      loader.onerror = () => {
        handleIdentityTransferResultPreviewError(token, displayUrl, "loader");
      };
      loader.src = displayUrl;
      return true;
    }

    function formatIdentityTransferRuntimeBlocker(blocker) {
      if (!isNonEmptyString(blocker)) {
        return "identity_transfer_not_ready";
      }
      if (blocker === "missing_identity_head_reference") {
        return "Kopf-Referenzbild fehlt";
      }
      if (blocker === "missing_target_body_image") {
        return "Zielbild fehlt";
      }
      if (blocker === "missing_transfer_mask") {
        return "Transfer-Maske fehlt";
      }
      if (blocker === "identity_workflow_missing") {
        return "Workflow fehlt";
      }
      if (blocker === "identity_models_missing") {
        return "Identity-Modelle fehlen";
      }
      if (blocker === "identity_nodes_missing") {
        return "InstantID-Nodes fehlen";
      }
      return blocker;
    }

    function getIdentityTransferTestVerfuegbarkeitView() {
      if (identityTransferRuntimeState.phase === "pending") {
        return {
          ready: false,
          text: "Standardpfad Verfuegbarkeit wird geprueft...",
          blocker: "identity_transfer_readiness_pending",
          is_error: false
        };
      }

      if (identityTransferRuntimeState.phase === "error") {
        const blocker = isNonEmptyString(identityTransferRuntimeState.payload?.blocker)
          ? identityTransferRuntimeState.payload.blocker.trim()
          : (isNonEmptyString(identityTransferRuntimeState.error) ? identityTransferRuntimeState.error.trim() : "identity_transfer_readiness_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${formatIdentityTransferRuntimeBlocker(blocker)}`,
          blocker,
          is_error: true
        };
      }

      const payload = getIdentityTransferRuntimePayload();
      const version = isNonEmptyString(payload.insightface_version) ? ` | insightface ${payload.insightface_version.trim()}` : "";
      return {
        ready: true,
        text: `Standardpfad bereit | Standardpfad${version}`,
        blocker: null,
        is_error: false
      };
    }

    function getIdentityTransferMaskHybridRuntimePayload() {
      if (identityTransferMaskHybridRuntimeState.payload && typeof identityTransferMaskHybridRuntimeState.payload === "object") {
        return identityTransferMaskHybridRuntimeState.payload;
      }
      return {
        ok: false,
        error_type: "invalid_request",
        blocker: "missing_identity_head_reference",
        required_roles_present: {
          identity_head_reference: false,
          target_body_image: false
        },
        optional_roles_present: {
          pose_reference: false,
          transfer_mask: false
        },
        adapter_state: null,
        missing_nodes: [],
        missing_models: [],
        insightface_version: null
      };
    }

    function getIdentityTransferMaskHybridVerfuegbarkeitView() {
      if (identityTransferMaskHybridRuntimeState.phase === "pending") {
        return {
          ready: false,
          text: "Masken-Hybrid Verfuegbarkeit wird geprueft...",
          blocker: "identity_transfer_mask_hybrid_readiness_pending",
          is_error: false
        };
      }

      if (identityTransferMaskHybridRuntimeState.phase === "error") {
        const blocker = isNonEmptyString(identityTransferMaskHybridRuntimeState.payload?.blocker)
          ? identityTransferMaskHybridRuntimeState.payload.blocker.trim()
          : (isNonEmptyString(identityTransferMaskHybridRuntimeState.error) ? identityTransferMaskHybridRuntimeState.error.trim() : "identity_transfer_mask_hybrid_readiness_unavailable");
        return {
          ready: false,
          text: `Nicht bereit | ${formatIdentityTransferRuntimeBlocker(blocker)}`,
          blocker,
          is_error: true
        };
      }

      const payload = getIdentityTransferMaskHybridRuntimePayload();
      const version = isNonEmptyString(payload.insightface_version) ? ` | insightface ${payload.insightface_version.trim()}` : "";
      return {
        ready: true,
        text: `Masken-Hybrid bereit | Masken-Hybrid${version}`,
        blocker: null,
        is_error: false
      };
    }

    async function fetchIdentityTransferRuntimeVerfuegbarkeit(options = {}) {
      const forceFresh = options.forceFresh === true;
      const showLoading = options.showLoading !== false;

      if (identityTransferRuntimeFetchPromise && !forceFresh) {
        return identityTransferRuntimeFetchPromise;
      }

      if (identityTransferRuntimeFetchPromise && forceFresh) {
        try {
          await identityTransferRuntimeFetchPromise;
        } catch (error) {
        }
      }

      if (showLoading && (forceFresh || !identityTransferRuntimeState.payload)) {
        identityTransferRuntimeState = {
          ...identityTransferRuntimeState,
          phase: "pending",
          error: "identity_transfer_readiness_pending"
        };
      }

      identityTransferRuntimeFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-transfer/readiness", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("identity_transfer_readiness_invalid_payload");
          }

          if (response.ok && payload.ok === true) {
            identityTransferRuntimeState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            identityTransferRuntimeState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `identity_transfer_readiness_http_${response.status}`
            };
          }
          renderUi();
          return identityTransferRuntimeState;
        } catch (error) {
          identityTransferRuntimeState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          renderUi();
          return identityTransferRuntimeState;
        } finally {
          identityTransferRuntimeFetchPromise = null;
        }
      })();

      return identityTransferRuntimeFetchPromise;
    }

    async function fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit(options = {}) {
      const forceFresh = options.forceFresh === true;
      const showLoading = options.showLoading !== false;

      if (identityTransferMaskHybridRuntimeFetchPromise && !forceFresh) {
        return identityTransferMaskHybridRuntimeFetchPromise;
      }

      if (identityTransferMaskHybridRuntimeFetchPromise && forceFresh) {
        try {
          await identityTransferMaskHybridRuntimeFetchPromise;
        } catch (error) {
        }
      }

      if (showLoading && (forceFresh || !identityTransferMaskHybridRuntimeState.payload)) {
        identityTransferMaskHybridRuntimeState = {
          ...identityTransferMaskHybridRuntimeState,
          phase: "pending",
          error: "identity_transfer_mask_hybrid_readiness_pending"
        };
      }

      identityTransferMaskHybridRuntimeFetchPromise = (async () => {
        try {
          const response = await fetch("/identity-transfer/mask-hybrid/readiness", { cache: "no-store" });
          let payload = null;
          try {
            payload = await response.json();
          } catch (error) {
            payload = null;
          }

          if (!payload || typeof payload !== "object") {
            throw new Error("identity_transfer_mask_hybrid_readiness_invalid_payload");
          }

          if (response.ok && payload.ok === true) {
            identityTransferMaskHybridRuntimeState = {
              phase: "ready",
              payload,
              error: null
            };
          } else {
            identityTransferMaskHybridRuntimeState = {
              phase: "error",
              payload,
              error: isNonEmptyString(payload.blocker) ? payload.blocker.trim() : `identity_transfer_mask_hybrid_readiness_http_${response.status}`
            };
          }
          renderUi();
          return identityTransferMaskHybridRuntimeState;
        } catch (error) {
          identityTransferMaskHybridRuntimeState = {
            phase: "error",
            payload: null,
            error: error instanceof Error ? error.message : String(error)
          };
          renderUi();
          return identityTransferMaskHybridRuntimeState;
        } finally {
          identityTransferMaskHybridRuntimeFetchPromise = null;
        }
      })();

      return identityTransferMaskHybridRuntimeFetchPromise;
    }

    function isIdentityTransferRequestRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        currentIdentityTransferRequest &&
        isNonEmptyString(currentIdentityTransferRequest.request_token) &&
        currentIdentityTransferRequest.request_token === requestToken
      );
    }

    function summarizeIdentityTransferUsedRoles(usedRoles) {
      if (!Array.isArray(usedRoles) || usedRoles.length === 0) {
        return "keine";
      }

      return usedRoles
        .map((role) => IDENTITY_TRANSFER_ROLE_CONFIG.find((config) => config.role === role)?.label || role)
        .join(" + ");
    }

    function normalizeIdentityTransferPathMode(pathMode) {
      return pathMode === "mask_hybrid" ? "mask_hybrid" : "standard";
    }

    function describeIdentityTransferPath(pathMode, basicMode = false) {
      const normalized = normalizeIdentityTransferPathMode(pathMode);
      if (normalized === "mask_hybrid") {
        return basicMode ? "Spezialpfad" : "Masken-Hybrid";
      }
      return basicMode ? "Standardpfad" : "Standardpfad";
    }

    function getIdentityTransferMaskHybridPromptScopeWarning(promptText) {
      const normalizedPrompt = isNonEmptyString(promptText) ? promptText.trim().toLowerCase() : "";
      if (!normalizedPrompt) {
        return null;
      }

      const nonHumanKeywords = [
        "fantasy",
        "monster",
        "creature",
        "dragon",
        "alien",
        "orc",
        "elf",
        "robot",
        "non-human",
        "non human",
        "nicht-mensch",
        "nicht mensch",
        "anime",
        "cartoon"
      ];
      const matchedKeyword = nonHumanKeywords.find((keyword) => normalizedPrompt.includes(keyword));
      if (!matchedKeyword) {
        return null;
      }
      return "Prompt wirkt nach Fantasy/Nicht-Mensch. Masken-Hybrid ist hier meist unzuverlaessig.";
    }

    function renderIdentityTransferTestUi() {
      const standardVerfuegbarkeitView = getIdentityTransferTestVerfuegbarkeitView();
      const maskHybridVerfuegbarkeitView = getIdentityTransferMaskHybridVerfuegbarkeitView();
      const statusPayload = getIdentityTransferStatusPayload();
      const running = currentIdentityTransferRequest?.phase === "running";
      const roleBusy = Boolean(currentIdentityTransferAction);
      const basicMode = isV7BasicIdentityTransferMode();
      const activePathMode = normalizeIdentityTransferPathMode(currentIdentityTransferRequest?.path_mode);
      const standardEnabled = standardVerfuegbarkeitView.ready && !running && !roleBusy;
      const maskHybridEnabled = maskHybridVerfuegbarkeitView.ready && !running && !roleBusy && !basicMode;
      const activePathLabel = describeIdentityTransferPath(activePathMode, basicMode);
      const targetBodyRoleEntry = Array.isArray(statusPayload.roles)
        ? statusPayload.roles.find((candidate) => candidate?.role === "target_body_image")
        : null;
      const transferMaskRoleEntry = Array.isArray(statusPayload.roles)
        ? statusPayload.roles.find((candidate) => candidate?.role === "transfer_mask")
        : null;
      const targetBodyImage = targetBodyRoleEntry?.occupied === true && targetBodyRoleEntry?.image ? targetBodyRoleEntry.image : null;
      const transferMaskImage = transferMaskRoleEntry?.occupied === true && transferMaskRoleEntry?.image ? transferMaskRoleEntry.image : null;
      const maskTargetSizeMismatch = Boolean(
        transferMaskImage &&
        targetBodyImage &&
        Number.isFinite(transferMaskImage.width) &&
        Number.isFinite(transferMaskImage.height) &&
        Number.isFinite(targetBodyImage.width) &&
        Number.isFinite(targetBodyImage.height) &&
        (
          Number(transferMaskImage.width) !== Number(targetBodyImage.width)
          || Number(transferMaskImage.height) !== Number(targetBodyImage.height)
        )
      );
      const maskHybridPromptScopeWarning = getIdentityTransferMaskHybridPromptScopeWarning(identityTransferPromptEl.value);

      if (basicMode) {
        if (standardVerfuegbarkeitView.ready) {
          identityTransferTestVerfuegbarkeitEl.textContent = "Transfer ist bereit";
          identityTransferTestVerfuegbarkeitEl.className = "request-state";
        } else if (!hasIdentityTransferRoleImage("identity_head_reference")) {
          identityTransferTestVerfuegbarkeitEl.textContent = "Kopf-Referenzbild fehlt noch";
          identityTransferTestVerfuegbarkeitEl.className = "request-state";
        } else if (!hasIdentityTransferRoleImage("target_body_image")) {
          identityTransferTestVerfuegbarkeitEl.textContent = "Zielbild fehlt noch";
          identityTransferTestVerfuegbarkeitEl.className = "request-state";
        } else if (standardVerfuegbarkeitView.is_error) {
          identityTransferTestVerfuegbarkeitEl.textContent = "Funktion aktuell nicht verfuegbar";
          identityTransferTestVerfuegbarkeitEl.className = "request-state error";
        } else {
          identityTransferTestVerfuegbarkeitEl.textContent = "Funktion wird geprueft...";
          identityTransferTestVerfuegbarkeitEl.className = "request-state";
        }
      } else {
        identityTransferTestVerfuegbarkeitEl.textContent = standardVerfuegbarkeitView.text;
        identityTransferTestVerfuegbarkeitEl.className = standardVerfuegbarkeitView.is_error ? "request-state error" : "request-state";
      }
      identityTransferPromptEl.disabled = basicMode ? (running || roleBusy) : (!standardVerfuegbarkeitView.ready || running || roleBusy);
      identityTransferGenerateEl.disabled = !standardEnabled;
      identityTransferGenerateEl.title = standardVerfuegbarkeitView.ready
        ? ""
        : formatImageGenerationErrorMessage(standardVerfuegbarkeitView.blocker || "identity_transfer_not_ready", {
          fallback: "Der Transfer-Pfad ist gerade nicht bereit."
        });
      identityTransferMaskHybridGenerateEl.hidden = basicMode;
      identityTransferMaskHybridScopeEl.hidden = basicMode;
      identityTransferMaskHybridLimitsEl.hidden = basicMode;
      identityTransferMaskHybridGenerateEl.disabled = !maskHybridEnabled;
      identityTransferMaskHybridGenerateEl.title = maskHybridVerfuegbarkeitView.ready
        ? ""
        : formatImageGenerationErrorMessage(maskHybridVerfuegbarkeitView.blocker || "identity_transfer_mask_hybrid_not_ready", {
          fallback: "Der Masken-Hybrid ist gerade nicht bereit."
        });
      if (!basicMode && maskHybridVerfuegbarkeitView.ready && maskHybridPromptScopeWarning) {
        identityTransferMaskHybridGenerateEl.title = maskHybridPromptScopeWarning;
      }
      if (!basicMode) {
        identityTransferMaskHybridScopeEl.textContent = "Normaler Weg: Standardpfad. Masken-Hybrid nur fuer Sonderfaelle mit klarer Kopfmaske.";
        if (!transferMaskImage) {
          identityTransferMaskHybridLimitsEl.textContent = "Masken-Hybrid braucht eine Transfer-Maske. Nutze eine gefuellte Kopfmaske statt reiner Kontur.";
          identityTransferMaskHybridLimitsEl.className = "request-state error";
        } else if (maskTargetSizeMismatch) {
          identityTransferMaskHybridLimitsEl.textContent = "Maske passt nicht zur Zielbildgroesse. Masken-Hybrid erwartet gleiche Aufloesung fuer Zielbild und Maske.";
          identityTransferMaskHybridLimitsEl.className = "request-state error";
        } else if (maskHybridPromptScopeWarning) {
          identityTransferMaskHybridLimitsEl.textContent = `${maskHybridPromptScopeWarning} Realistische Einzelperson wird fuer Masken-Hybrid empfohlen.`;
          identityTransferMaskHybridLimitsEl.className = "request-state error";
        } else if (maskHybridVerfuegbarkeitView.ready) {
          identityTransferMaskHybridLimitsEl.textContent = "Geeignet: realistische Einzelperson + sinnvoll gefuellte Kopfmaske. Konturmasken sind meist zu schwach. Fuer maximale Gesichtstreue zuerst Standardpfad pruefen.";
          identityTransferMaskHybridLimitsEl.className = "request-state";
        } else if (maskHybridVerfuegbarkeitView.is_error) {
          identityTransferMaskHybridLimitsEl.textContent = `Masken-Hybrid nicht bereit | ${formatIdentityTransferRuntimeBlocker(maskHybridVerfuegbarkeitView.blocker)}`;
          identityTransferMaskHybridLimitsEl.className = "request-state error";
        } else {
          identityTransferMaskHybridLimitsEl.textContent = "Masken-Hybrid-Spezialpfad wird geprueft. Bereite eine realistische Einzelperson und eine gefuellte Kopfmaske vor.";
          identityTransferMaskHybridLimitsEl.className = "request-state";
        }
      }

      if (currentIdentityTransferRequest?.phase === "running") {
        identityTransferRunStateEl.textContent = basicMode ? "Bild wird erstellt..." : `${activePathLabel} laeuft...`;
        identityTransferRunStateEl.className = "request-state";
      } else if (currentIdentityTransferRequest?.phase === "success" && activeIdentityTransferResult.state === "loading") {
        identityTransferRunStateEl.textContent = basicMode ? "Ergebnis wird geladen..." : `${activePathLabel} Ergebnis laedt...`;
        identityTransferRunStateEl.className = "request-state";
      } else if (currentIdentityTransferRequest?.phase === "success" && activeIdentityTransferResult.state === "ready") {
        identityTransferRunStateEl.textContent = basicMode ? "Ergebnis ist fertig" : `${activePathLabel} Ergebnis bereit`;
        identityTransferRunStateEl.className = "request-state";
      } else if (currentIdentityTransferRequest?.phase === "error") {
        identityTransferRunStateEl.textContent = basicMode
          ? "Erstellung fehlgeschlagen"
          : `${activePathLabel} fehlgeschlagen | ${currentIdentityTransferRequest.blocker || currentIdentityTransferRequest.error_type || "identity_transfer_failed"}`;
        identityTransferRunStateEl.className = "request-state error";
      } else if (!hasIdentityTransferRoleImage("identity_head_reference")) {
        identityTransferRunStateEl.textContent = "Kopf-Referenzbild fehlt noch";
        identityTransferRunStateEl.className = "request-state";
      } else if (!hasIdentityTransferRoleImage("target_body_image")) {
        identityTransferRunStateEl.textContent = "Zielbild fehlt noch";
        identityTransferRunStateEl.className = "request-state";
      } else if (!standardVerfuegbarkeitView.ready) {
        identityTransferRunStateEl.textContent = basicMode
          ? (standardVerfuegbarkeitView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...")
          : "Standardpfad nicht bereit";
        identityTransferRunStateEl.className = standardVerfuegbarkeitView.is_error && basicMode ? "request-state error" : "request-state";
      } else if (basicMode && !isNonEmptyString(identityTransferPromptEl.value.trim())) {
        identityTransferRunStateEl.textContent = "Gib einen Wunsch ein";
        identityTransferRunStateEl.className = "request-state";
      } else {
        identityTransferRunStateEl.textContent = basicMode ? "Jetzt kannst du starten" : `${activePathLabel} bereit`;
        identityTransferRunStateEl.className = "request-state";
      }

      const optionalRolesPresent = getIdentityTransferRuntimePayload().optional_roles_present || {};
      if (currentIdentityTransferRequest?.phase === "error") {
        const errorCode = currentIdentityTransferRequest.blocker || currentIdentityTransferRequest.error_type || "identity_transfer_failed";
        const fallback = activePathMode === "mask_hybrid"
          ? "Der Masken-Hybrid konnte gerade nicht abgeschlossen werden."
          : "Der Transfer-Pfad konnte gerade nicht abgeschlossen werden.";
        const friendlyError = formatImageGenerationErrorMessage(errorCode, { fallback });
        identityTransferRunHintEl.textContent = basicMode
          ? friendlyError
          : (activePathMode === "mask_hybrid"
            ? `${friendlyError} | ${errorCode}`
            : `Fehler | ${currentIdentityTransferRequest.error_type || "api_error"} | ${currentIdentityTransferRequest.blocker || "identity_transfer_failed"}`);
        identityTransferRunHintEl.className = "request-state error";
      } else if (currentIdentityTransferRequest?.phase === "success" && activeIdentityTransferResult.result_id) {
        if (basicMode) {
          identityTransferRunHintEl.textContent = (
            activeIdentityTransferResult.pose_reference_present === true ||
            activeIdentityTransferResult.transfer_mask_present === true
          )
            ? "Zusatzbilder waren vorhanden. Der stabile Pfad hat sich hier aber auf Kopf-Referenzbild und Zielbild konzentriert."
            : "Der stabile Pfad nutzt aktuell Kopf-Referenzbild und Zielbild.";
        } else {
          const posePresence = activeIdentityTransferResult.pose_reference_present === true ? "ja" : "nein";
          const maskPresence = activeIdentityTransferResult.transfer_mask_present === true ? "ja" : "nein";
          const poseUsed = activeIdentityTransferResult.pose_reference_used === true ? "ja" : "nein";
          const maskUsed = activeIdentityTransferResult.transfer_mask_used === true ? "ja" : "nein";
          identityTransferRunHintEl.textContent = `${activeIdentityTransferResult.result_id} | Rollen: ${summarizeIdentityTransferUsedRoles(activeIdentityTransferResult.used_roles)} | Pose vorhanden/genutzt: ${posePresence}/${poseUsed} | Maske vorhanden/genutzt: ${maskPresence}/${maskUsed} | ${activeIdentityTransferResult.identity_transfer_strategy || "identity_transfer"}`;
        }
        identityTransferRunHintEl.className = "request-state";
      } else if (standardVerfuegbarkeitView.ready) {
        if (basicMode) {
          identityTransferRunHintEl.textContent = isNonEmptyString(identityTransferPromptEl.value.trim())
            ? "Pose und Maske sind nur Zusatzmaterial."
            : "Beschreibe jetzt kurz, wie Kopf/Gesicht ins Zielbild uebergehen soll.";
        } else if (activePathMode === "mask_hybrid") {
          identityTransferRunHintEl.textContent = maskHybridPromptScopeWarning
            ? `${maskHybridPromptScopeWarning} Du kannst trotzdem testen, aber Ergebnisse sind oft schwach.`
            : "Masken-Hybrid-Spezialpfad: fuer gefuellte Kopfmasken und lokale Kopfanpassung. Bei schwankender Gesichtstreue zuerst Standardpfad nutzen.";
        } else {
          identityTransferRunHintEl.textContent = `Standardpfad ist der Default fuer konstante Gesichtstreue | Optionale Rollen vorhanden | Pose: ${optionalRolesPresent.pose_reference === true ? "ja" : "nein"} | Maske: ${optionalRolesPresent.transfer_mask === true ? "ja" : "nein"}`;
        }
        identityTransferRunHintEl.className = "request-state";
      } else {
        identityTransferRunHintEl.textContent = basicMode ? "Lade zuerst Kopf-Referenzbild und Zielbild hoch." : "";
        identityTransferRunHintEl.className = "request-state";
      }

      if (standardVerfuegbarkeitView.is_error) {
        identityTransferTestHintEl.textContent = basicMode
          ? "Funktion aktuell nicht verfuegbar"
          : `Nicht bereit | ${formatIdentityTransferRuntimeBlocker(standardVerfuegbarkeitView.blocker)}`;
        identityTransferTestHintEl.className = "request-state error";
      } else if (standardVerfuegbarkeitView.ready) {
        identityTransferTestHintEl.textContent = basicMode
          ? "Der stabile Pfad nutzt aktuell Kopf-Referenzbild plus Zielbild."
          : "Stabiler Standardpfadpfad nutzt aktuell Kopf-Referenzbild plus Zielbild.";
        identityTransferTestHintEl.className = "request-state";
      } else {
        identityTransferTestHintEl.textContent = "Pflichtbilder: Kopf-Referenzbild und Zielbild.";
        identityTransferTestHintEl.className = "request-state";
      }

      for (const config of IDENTITY_TRANSFER_ROLE_CONFIG) {
        const roleView = identityTransferTestRoleViews[config.role];
        const roleEntry = Array.isArray(statusPayload.roles)
          ? statusPayload.roles.find((candidate) => candidate?.role === config.role)
          : null;
        const occupied = roleEntry?.occupied === true && roleEntry?.image && isNonEmptyString(roleEntry.image.preview_url);

        if (occupied) {
          roleView.stateEl.textContent = basicMode
            ? (config.required ? "Bild geladen" : "Optional geladen")
            : (config.required ? "Vorhanden" : "Optional vorhanden");
          roleView.stateEl.className = "request-state";
          showUploadPreview(roleView.previewEl, roleEntry.image.preview_url);
        } else {
          roleView.stateEl.textContent = basicMode
            ? (config.required ? "Fehlt noch" : "Optional")
            : (config.required ? "Pflichtrolle fehlt" : "Optional nicht vorhanden");
          roleView.stateEl.className = config.required && !basicMode ? "request-state error" : "request-state";
          clearUploadPreview(roleView.previewEl);
        }
      }
    }

    async function attemptIdentityTransferGenerate() {
      if (currentIdentityTransferRequest?.phase === "running" || currentIdentityTransferAction) {
        return;
      }

      const readiness = await fetchIdentityTransferRuntimeVerfuegbarkeit({ forceFresh: true });
      const readinessView = getIdentityTransferTestVerfuegbarkeitView();
      if (!readiness || !readinessView.ready) {
        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "standard",
          request_token: null,
          error_type: "api_error",
          blocker: readinessView.blocker || "identity_transfer_not_ready",
          message: formatImageGenerationErrorMessage(readinessView.blocker || "identity_transfer_not_ready", {
            fallback: "Der Transfer-Pfad ist gerade nicht bereit."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      const prompt = identityTransferPromptEl.value.trim();
      if (!prompt) {
        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "standard",
          request_token: null,
          error_type: "invalid_request",
          blocker: "empty_prompt",
          message: "Bitte gib zuerst einen Wunsch ein.",
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      clearIdentityTransferResult();
      const requestToken = `identity-transfer-request-${String(++currentIdentityTransferRequestCounter).padStart(6, "0")}`;
      currentIdentityTransferRequest = {
        phase: "running",
        path_mode: "standard",
        request_token: requestToken,
        error_type: null,
        blocker: null,
        message: null,
        result_id: null,
        output_file: null
      };
      renderUi();

      try {
        const healthPayload = healthState.payload || await fetchHealth({ forceFresh: true });
        const checkpoint = isNonEmptyString(healthPayload?.selected_checkpoint) ? healthPayload.selected_checkpoint.trim() : "";
        const response = await fetch("/identity-transfer/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            checkpoint
          })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityTransferRequestRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload && payload.status === "ok" && isNonEmptyString(payload.output_file)) {
          const items = await fetchResults({ showLoading: false });
          const resultItem = Array.isArray(items) ? items.find((item) => item?.result_id === payload.result_id) || null : null;
          setIdentityTransferResult(payload, resultItem);
          const transferResult = {
            ...compactResult(payload),
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            restored_from_storage: false,
            v7_basic_task: isV7BasicIdentityTransferMode() ? "identity-transfer" : null
          };
          lastResult = transferResult;
          lastSuccessfulResult = transferResult;
          persist_last_success(transferResult);
          setActiveImage(transferResult.output_file, {
            request_id: transferResult.request_id,
            mode: transferResult.mode,
            prompt_id: transferResult.prompt_id,
            restored_from_storage: false
          });
          currentIdentityTransferRequest = {
            phase: "success",
            path_mode: "standard",
            request_token: null,
            error_type: null,
            blocker: null,
            message: null,
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            output_file: payload.output_file.trim()
          };
          renderUi();
          return;
        }

        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "standard",
          request_token: null,
          error_type: isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "api_error",
          blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_http_${response.status}`,
          message: formatImageGenerationErrorMessage(
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_http_${response.status}`,
            { fallback: "Der Transfer-Pfad konnte gerade nicht abgeschlossen werden." }
          ),
          result_id: null,
          output_file: null
        };
        renderUi();
      } catch (error) {
        if (!isIdentityTransferRequestRelevant(requestToken)) {
          return;
        }

        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "standard",
          request_token: null,
          error_type: "api_error",
          blocker: error instanceof Error ? error.message : String(error),
          message: formatImageGenerationErrorMessage(error instanceof Error ? error.message : String(error), {
            fallback: "Der Transfer-Pfad konnte gerade nicht abgeschlossen werden."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
      }
    }

    async function attemptIdentityTransferMaskHybridGenerate() {
      if (currentIdentityTransferRequest?.phase === "running" || currentIdentityTransferAction) {
        return;
      }

      const readiness = await fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit({ forceFresh: true });
      const readinessView = getIdentityTransferMaskHybridVerfuegbarkeitView();
      if (!readiness || !readinessView.ready) {
        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "mask_hybrid",
          request_token: null,
          error_type: "api_error",
          blocker: readinessView.blocker || "identity_transfer_mask_hybrid_not_ready",
          message: formatImageGenerationErrorMessage(readinessView.blocker || "identity_transfer_mask_hybrid_not_ready", {
            fallback: "Der Masken-Hybrid ist gerade nicht bereit."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      const prompt = identityTransferPromptEl.value.trim();
      if (!prompt) {
        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "mask_hybrid",
          request_token: null,
          error_type: "invalid_request",
          blocker: "empty_prompt",
          message: "Bitte gib zuerst einen Wunsch ein.",
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      clearIdentityTransferResult();
      const requestToken = `identity-transfer-mask-hybrid-request-${String(++currentIdentityTransferRequestCounter).padStart(6, "0")}`;
      currentIdentityTransferRequest = {
        phase: "running",
        path_mode: "mask_hybrid",
        request_token: requestToken,
        error_type: null,
        blocker: null,
        message: null,
        result_id: null,
        output_file: null
      };
      renderUi();

      try {
        const healthPayload = healthState.payload || await fetchHealth({ forceFresh: true });
        const checkpoint = isNonEmptyString(healthPayload?.selected_checkpoint) ? healthPayload.selected_checkpoint.trim() : "";
        const response = await fetch("/identity-transfer/mask-hybrid/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            checkpoint
          })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityTransferRequestRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload && payload.status === "ok" && isNonEmptyString(payload.output_file)) {
          const items = await fetchResults({ showLoading: false });
          const resultItem = Array.isArray(items) ? items.find((item) => item?.result_id === payload.result_id) || null : null;
          setIdentityTransferResult(payload, resultItem);
          const transferResult = {
            ...compactResult(payload),
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            restored_from_storage: false,
            v7_basic_task: isV7BasicIdentityTransferMode() ? "identity-transfer" : null
          };
          lastResult = transferResult;
          lastSuccessfulResult = transferResult;
          persist_last_success(transferResult);
          setActiveImage(transferResult.output_file, {
            request_id: transferResult.request_id,
            mode: transferResult.mode,
            prompt_id: transferResult.prompt_id,
            restored_from_storage: false
          });
          currentIdentityTransferRequest = {
            phase: "success",
            path_mode: "mask_hybrid",
            request_token: null,
            error_type: null,
            blocker: null,
            message: null,
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            output_file: payload.output_file.trim()
          };
          renderUi();
          return;
        }

        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "mask_hybrid",
          request_token: null,
          error_type: isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "api_error",
          blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_mask_hybrid_http_${response.status}`,
          message: formatImageGenerationErrorMessage(
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_transfer_mask_hybrid_http_${response.status}`,
            { fallback: "Der Masken-Hybrid konnte gerade nicht abgeschlossen werden." }
          ),
          result_id: null,
          output_file: null
        };
        renderUi();
      } catch (error) {
        if (!isIdentityTransferRequestRelevant(requestToken)) {
          return;
        }

        currentIdentityTransferRequest = {
          phase: "error",
          path_mode: "mask_hybrid",
          request_token: null,
          error_type: "api_error",
          blocker: error instanceof Error ? error.message : String(error),
          message: formatImageGenerationErrorMessage(error instanceof Error ? error.message : String(error), {
            fallback: "Der Masken-Hybrid konnte gerade nicht abgeschlossen werden."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
      }
    }

    function isIdentityRequestRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        currentIdentityRequest &&
        isNonEmptyString(currentIdentityRequest.request_token) &&
        currentIdentityRequest.request_token === requestToken
      );
    }

    function buildMaskTransferText(phase, blocker = null) {
      if (phase === "processing") {
        return "Maske wird geladen...";
      }
      if (phase === "success") {
        return "Maske geladen";
      }
      if (phase === "missing_input") {
        return "Maske fehlt noch";
      }
      if (phase === "invalid_type") {
        return "Maske konnte nicht geladen werden | ungueltiger Dateityp";
      }
      if (phase === "request_failed") {
        return "Maske konnte nicht geladen werden | upload_request_failed";
      }
      if (phase === "failed") {
        return `Maske konnte nicht geladen werden | ${blocker || "upload_failed"}`;
      }
      return "Maske";
    }

    function computeMaskUploadControl() {
      const hasSelection = selectedMaskFile instanceof File;
      const hasMaskImage = activeMaskImage.state !== "none";
      const busy = Boolean(currentMaskUpload);

      return {
        uploadEnabled: hasSelection && !busy,
        resetEnabled: !busy && (hasSelection || hasMaskImage),
        fileEnabled: !busy
      };
    }

    function renderMaskUploadUi() {
      const basicMode = isV7BasicModeActive();
      const maskControl = computeMaskUploadControl();
      maskFileEl.disabled = !maskControl.fileEnabled;
      uploadMaskEl.disabled = !maskControl.uploadEnabled;
      resetMaskImageEl.disabled = !maskControl.resetEnabled;

      if (currentMaskUpload) {
        maskUploadStateEl.textContent = currentMaskUpload.source_type === "mask_editor"
          ? "Maske wird gespeichert..."
          : "Maske wird geladen...";
      } else {
        maskUploadStateEl.textContent = maskUploadNotice.text;
      }
      maskUploadStateEl.className = maskUploadNotice.state === "error" ? "request-state error" : "request-state";

      if (selectedMaskFile && !currentMaskUpload) {
        maskUploadHintEl.textContent = `Ausgewaehlt | ${selectedMaskFile.name}`;
        maskUploadHintEl.className = "request-state";
      } else if (maskUploadNotice.state === "error") {
        maskUploadHintEl.textContent = `${maskUploadNotice.error_type || "upload_error"} | ${maskUploadNotice.blocker || "upload_failed"}`;
        maskUploadHintEl.className = "request-state error";
      } else if (activeMaskImage.state === "loading") {
        maskUploadHintEl.textContent = "Maskenvorschau laedt...";
        maskUploadHintEl.className = "request-state";
      } else if (hasUsableMaskImage() && hasUsableInputImage() && !isCurrentMaskCompatibleWithSource()) {
        maskUploadHintEl.textContent = "Maske passt nicht zum Eingabebild";
        maskUploadHintEl.className = "request-state error";
      } else if (!basicMode && activeMaskImage.state === "ready") {
        maskUploadHintEl.textContent = "Maske geladen";
        maskUploadHintEl.className = "request-state";
      } else {
        maskUploadHintEl.textContent = "";
        maskUploadHintEl.className = "request-state";
      }

      maskMetaEl.textContent = currentMaskImageSummary();
    }

    function getMaskEditorPoint(event) {
      const rect = maskEditorOverlayEl.getBoundingClientRect();
      if (!(rect.width > 0) || !(rect.height > 0)) {
        return null;
      }

      const scaleX = maskEditorOverlayEl.width / rect.width;
      const scaleY = maskEditorOverlayEl.height / rect.height;
      return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
      };
    }

    function drawMaskEditorSegment(fromPoint, toPoint) {
      if (!hasMaskEditorSource()) {
        return false;
      }

      const brushSize = normalizeMaskEditorBrushSize(maskEditorState.brush_size);
      const maskCtx = getMaskEditorMaskContext();
      const overlayCtx = getMaskEditorOverlayContext();

      maskCtx.save();
      overlayCtx.save();
      maskCtx.lineCap = "round";
      maskCtx.lineJoin = "round";
      overlayCtx.lineCap = "round";
      overlayCtx.lineJoin = "round";
      maskCtx.lineWidth = brushSize;
      overlayCtx.lineWidth = brushSize;

      if (maskEditorState.tool === "eraser") {
        maskCtx.globalCompositeOperation = "source-over";
        maskCtx.strokeStyle = "#000000";
        maskCtx.fillStyle = "#000000";
        overlayCtx.globalCompositeOperation = "destination-out";
        overlayCtx.strokeStyle = "rgba(0,0,0,1)";
        overlayCtx.fillStyle = "rgba(0,0,0,1)";
      } else {
        maskCtx.globalCompositeOperation = "source-over";
        maskCtx.strokeStyle = "#ffffff";
        maskCtx.fillStyle = "#ffffff";
        overlayCtx.globalCompositeOperation = "source-over";
        overlayCtx.strokeStyle = "rgba(255,80,80,0.8)";
        overlayCtx.fillStyle = "rgba(255,80,80,0.8)";
      }

      maskCtx.beginPath();
      maskCtx.moveTo(fromPoint.x, fromPoint.y);
      maskCtx.lineTo(toPoint.x, toPoint.y);
      maskCtx.stroke();
      maskCtx.beginPath();
      maskCtx.arc(toPoint.x, toPoint.y, brushSize / 2, 0, Math.PI * 2);
      maskCtx.fill();

      overlayCtx.beginPath();
      overlayCtx.moveTo(fromPoint.x, fromPoint.y);
      overlayCtx.lineTo(toPoint.x, toPoint.y);
      overlayCtx.stroke();
      overlayCtx.beginPath();
      overlayCtx.arc(toPoint.x, toPoint.y, brushSize / 2, 0, Math.PI * 2);
      overlayCtx.fill();

      maskCtx.restore();
      overlayCtx.restore();

      maskEditorState = {
        ...maskEditorState,
        dirty: true
      };
      if (maskEditorState.tool === "brush") {
        maskEditorState = {
          ...maskEditorState,
          has_painted: true
        };
      }
      return true;
    }

    function beginMaskEditorStroke(event) {
      if (!hasMaskEditorSource() || currentMaskUpload || maskEditorState.saving) {
        return;
      }

      const point = getMaskEditorPoint(event);
      if (!point) {
        return;
      }

      currentMaskEditorStroke = {
        pointer_id: event.pointerId,
        last_point: point
      };
      try {
        maskEditorOverlayEl.setPointerCapture(event.pointerId);
      } catch (error) {
      }
      drawMaskEditorSegment(point, point);
      setMaskEditorStatus("drawing", `Maske lokal bearbeitet | ${maskEditorState.tool === "eraser" ? "Radierer" : "Pinsel"}`);
      renderUi();
      event.preventDefault();
    }

    function continueMaskEditorStroke(event) {
      if (!currentMaskEditorStroke || currentMaskEditorStroke.pointer_id !== event.pointerId) {
        return;
      }

      const point = getMaskEditorPoint(event);
      if (!point) {
        return;
      }

      drawMaskEditorSegment(currentMaskEditorStroke.last_point, point);
      currentMaskEditorStroke = {
        ...currentMaskEditorStroke,
        last_point: point
      };
      event.preventDefault();
    }

    function endMaskEditorStroke(event) {
      if (!currentMaskEditorStroke || currentMaskEditorStroke.pointer_id !== event.pointerId) {
        return;
      }

      clearMaskEditorStroke();
      updateMaskEditorPaintState();
      if (maskEditorState.has_painted) {
        setMaskEditorStatus("dirty", "Lokale Maske bereit zum Uebernehmen");
      } else {
        setMaskEditorStatus("idle", "Noch kein Bereich markiert");
      }
      renderUi();
      event.preventDefault();
    }

    function resetMaskEditorDrawing() {
      if (!hasMaskEditorSource() || currentMaskUpload) {
        return;
      }
      clearMaskEditorDraft({ message: "Lokale Maske zurueckgesetzt" });
      renderUi();
    }

    async function saveMaskEditorDrawing() {
      if (currentMaskUpload || maskEditorState.saving) {
        return false;
      }

      if (!hasUsableInputImage()) {
        setMaskEditorStatus("error", "Maske speichern fehlgeschlagen | missing_input_image");
        renderUi();
        return false;
      }

      updateMaskEditorPaintState();
      if (!maskEditorState.has_painted) {
        setMaskEditorStatus("error", "Maske speichern fehlgeschlagen | empty_mask");
        renderUi();
        return false;
      }

      const uploadToken = `mask-editor-${String(++currentMaskUploadCounter).padStart(6, "0")}`;
      currentMaskUpload = {
        token: uploadToken,
        started_at_utc: new Date().toISOString(),
        source_type: "mask_editor",
        file_name: "browser-mask.png"
      };
      maskEditorState = {
        ...maskEditorState,
        saving: true
      };
      setMaskUploadNotice("uploading", "Maske wird gespeichert...");
      setMaskEditorStatus("saving", "Maske wird gespeichert...");
      renderUi();

      try {
        const response = await fetch("/mask-image/editor", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_image_id: activeInputImage.image_id,
            mask_data_url: maskEditorStorageCanvas.toDataURL("image/png")
          })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return false;
        }

        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const errorType = INPUT_UPLOAD_ERROR_TYPES.has(payload?.error_type) ? payload.error_type : "upload_error";
          const blocker = isNonEmptyString(payload?.blocker) ? payload.blocker : "mask_editor_save_failed";
          setMaskUploadNotice("error", `Maske speichern fehlgeschlagen | ${blocker}`, {
            error_type: errorType,
            blocker
          });
          setMaskEditorStatus("error", `Maske speichern fehlgeschlagen | ${blocker}`);
          renderUi();
          return false;
        }

        resetSelectedMaskFile();
        setCurrentMaskImage(payload, {
          noticeText: "Maske uebernommen"
        });
        maskEditorState = {
          ...maskEditorState,
          saving: false,
          dirty: false,
          has_painted: maskEditorHasPaintedPixels()
        };
        setMaskEditorStatus("ok", "Maske uebernommen");
        await fetchHealth({ forceFresh: true });
        return true;
      } catch (error) {
        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return false;
        }

        setMaskUploadNotice("error", "Maske speichern fehlgeschlagen | upload_request_failed", {
          error_type: "upload_error",
          blocker: "upload_request_failed"
        });
        setMaskEditorStatus("error", "Maske speichern fehlgeschlagen | upload_request_failed");
        return false;
      } finally {
        maskEditorState = {
          ...maskEditorState,
          saving: false
        };
        if (currentMaskUpload && currentMaskUpload.token === uploadToken) {
          currentMaskUpload = null;
        }
        renderUi();
      }
    }

    function renderMaskEditorUi() {
      syncMaskEditorSourceFromInput();
      const hasSource = hasMaskEditorSource();
      const busy = Boolean(currentMaskUpload);
      const tool = maskEditorState.tool === "eraser" ? "eraser" : "brush";
      const brushSize = normalizeMaskEditorBrushSize(maskEditorState.brush_size);

      maskToolBrushEl.disabled = !hasSource || busy;
      maskToolEraserEl.disabled = !hasSource || busy;
      maskToolBrushEl.classList.toggle("active", tool === "brush");
      maskToolEraserEl.classList.toggle("active", tool === "eraser");
      maskBrushSizeEl.disabled = !hasSource || busy;
      maskBrushSizeEl.value = String(brushSize);
      maskEditorClearEl.disabled = !hasSource || busy || !maskEditorState.has_painted;
      maskEditorSaveEl.disabled = !hasSource || busy || !maskEditorState.has_painted;

      if (!hasSource) {
        maskEditorStageEl.style.display = "none";
        maskEditorEmptyEl.style.display = "block";
        maskEditorEmptyEl.textContent = "Lade zuerst ein Bild. Danach kannst du den Bereich markieren.";
      } else {
        maskEditorStageEl.style.display = "block";
        maskEditorEmptyEl.style.display = "none";
      }

      if (!hasSource) {
        maskEditorStateEl.textContent = "Lade zuerst ein Bild. Danach kannst du den Bereich markieren.";
        maskEditorStateEl.className = "request-state";
      } else {
        maskEditorStateEl.textContent = maskEditorState.message;
        maskEditorStateEl.className = maskEditorState.status === "error" ? "request-state error" : "request-state";
      }
    }

    function setMaskEditorTool(tool) {
      const nextTool = tool === "eraser" ? "eraser" : "brush";
      if (maskEditorState.tool === nextTool) {
        return;
      }
      maskEditorState = {
        ...maskEditorState,
        tool: nextTool
      };
      if (hasMaskEditorSource()) {
        setMaskEditorStatus("idle", nextTool === "eraser" ? "Radierer aktiv" : "Pinsel aktiv");
      }
      renderUi();
    }

    function handleMaskBrushSizeChange() {
      maskEditorState = {
        ...maskEditorState,
        brush_size: normalizeMaskEditorBrushSize(maskBrushSizeEl.value)
      };
      renderUi();
    }

    function resetSelectedMaskFile() {
      selectedMaskFile = null;
      maskFileEl.value = "";
    }

    function handleMaskFileSelection() {
      const file = maskFileEl.files && maskFileEl.files.length > 0 ? maskFileEl.files[0] : null;
      if (!file) {
        selectedMaskFile = null;
        if (!currentMaskUpload && activeMaskImage.state === "none") {
          setMaskUploadNotice("idle", "Maske fehlt noch");
        }
        renderUi();
        return;
      }

      if (!isSupportedUploadFile(file)) {
        resetSelectedMaskFile();
        setMaskUploadNotice("error", buildMaskTransferText("invalid_type"), {
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return;
      }

      selectedMaskFile = file;
      setMaskUploadNotice("idle", `Maske ausgewaehlt | ${file.name}`);
      renderUi();
    }

    async function submitMaskImage(file) {
      if (currentMaskUpload) {
        return false;
      }

      if (!(file instanceof File)) {
        setMaskUploadNotice("error", buildMaskTransferText("missing_input"), {
          error_type: "invalid_request",
          blocker: "missing_file"
        });
        renderUi();
        return false;
      }

      if (!isSupportedUploadFile(file)) {
        resetSelectedMaskFile();
        setMaskUploadNotice("error", buildMaskTransferText("invalid_type"), {
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return false;
      }

      const uploadToken = `mask-upload-${String(++currentMaskUploadCounter).padStart(6, "0")}`;
      currentMaskUpload = {
        token: uploadToken,
        started_at_utc: new Date().toISOString(),
        source_type: "mask",
        file_name: file.name
      };
      setMaskUploadNotice("uploading", buildMaskTransferText("processing"));
      renderUi();

      const formData = new FormData();
      formData.append("image", file);
      formData.append("source_type", "mask");

      try {
        const response = await fetch("/input-image", {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return false;
        }

        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const errorType = INPUT_UPLOAD_ERROR_TYPES.has(payload?.error_type) ? payload.error_type : "upload_error";
          const blocker = isNonEmptyString(payload?.blocker) ? payload.blocker : "upload_failed";
          const message = blocker === "invalid_file_type"
            ? buildMaskTransferText("invalid_type")
            : buildMaskTransferText("failed", blocker);
          setMaskUploadNotice("error", message, {
            error_type: errorType,
            blocker
          });
          renderUi();
          return false;
        }

        resetSelectedMaskFile();
        setCurrentMaskImage(payload, {
          noticeText: buildMaskTransferText("success")
        });
        await fetchHealth({ forceFresh: true });
        return true;
      } catch (error) {
        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return false;
        }

        setMaskUploadNotice("error", buildMaskTransferText("request_failed"), {
          error_type: "upload_error",
          blocker: "upload_request_failed"
        });
        return false;
      } finally {
        if (currentMaskUpload && currentMaskUpload.token === uploadToken) {
          currentMaskUpload = null;
        }
        renderUi();
      }
    }

    async function attemptUploadMask() {
      return submitMaskImage(selectedMaskFile);
    }

    async function resetUploadedMaskImage() {
      if (currentMaskUpload) {
        return;
      }

      resetSelectedMaskFile();
      if (activeMaskImage.state === "none") {
        setMaskUploadNotice("idle", "Maske fehlt noch");
        renderUi();
        return;
      }

      currentMaskUpload = {
        token: `mask-upload-${String(++currentMaskUploadCounter).padStart(6, "0")}`,
        started_at_utc: new Date().toISOString(),
        source_type: "mask",
        file_name: null
      };
      setMaskUploadNotice("uploading", "Maske wird geladen...");
      renderUi();

      const uploadToken = currentMaskUpload.token;
      try {
        const response = await fetch("/mask-image/current", {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return;
        }

        if (!response.ok || !payload || payload.status !== "ok") {
          setMaskUploadNotice("error", "Maske konnte nicht entfernt werden | mask_reset_failed", {
            error_type: "upload_error",
            blocker: isNonEmptyString(payload?.blocker) ? payload.blocker : "mask_reset_failed"
          });
          renderUi();
          return;
        }

        clearCurrentMaskImage({ clearNotice: false });
        setMaskUploadNotice("idle", "Maske entfernt");
        await fetchHealth({ forceFresh: true });
      } catch (error) {
        if (!currentMaskUpload || currentMaskUpload.token !== uploadToken) {
          return;
        }

        setMaskUploadNotice("error", "Maske konnte nicht entfernt werden | mask_reset_failed", {
          error_type: "upload_error",
          blocker: "mask_reset_failed"
        });
      } finally {
        if (currentMaskUpload && currentMaskUpload.token === uploadToken) {
          currentMaskUpload = null;
        }
        renderUi();
      }
    }

    function computeUploadControl() {
      const hasSelection = selectedUploadFile instanceof File;
      const hasUploadedImage = activeInputImage.state !== "none";
      const busy = Boolean(currentUpload);

      return {
        uploadEnabled: hasSelection && !busy,
        resetEnabled: !busy && (hasSelection || hasUploadedImage),
        fileEnabled: !busy,
        pasteEnabled: !busy
      };
    }

    function renderUploadUi() {
      const basicMode = isV7BasicModeActive();
      syncGenerateInputControls();
      const uploadControl = computeUploadControl();
      inputFileEl.disabled = !uploadControl.fileEnabled;
      uploadImageEl.disabled = !uploadControl.uploadEnabled;
      resetInputImageEl.disabled = !uploadControl.resetEnabled;
      pasteTargetEl.tabIndex = uploadControl.pasteEnabled ? 0 : -1;
      pasteTargetEl.setAttribute("aria-disabled", uploadControl.pasteEnabled ? "false" : "true");

      if (currentUpload) {
        uploadStateEl.textContent = currentUpload.source_type === "clipboard"
          ? "Bild wird eingefuegt..."
          : "Bild wird geladen...";
      } else {
        uploadStateEl.textContent = inputUploadNotice.text;
      }
      uploadStateEl.className = inputUploadNotice.state === "error" ? "request-state error" : "request-state";

      if (selectedUploadFile && !currentUpload) {
        uploadHintEl.textContent = `Ausgewaehlt | ${selectedUploadFile.name}`;
        uploadHintEl.className = "request-state";
      } else if (inputUploadNotice.state === "error") {
        uploadHintEl.textContent = `${inputUploadNotice.error_type || "upload_error"} | ${inputUploadNotice.blocker || "upload_failed"}`;
        uploadHintEl.className = "request-state error";
      } else if (activeInputImage.state === "loading") {
        uploadHintEl.textContent = "Bildvorschau laedt...";
        uploadHintEl.className = "request-state";
      } else if (!basicMode && activeInputImage.state === "ready") {
        uploadHintEl.textContent = activeInputImage.source_type === "clipboard"
          ? "Bild eingefuegt"
          : "Bild geladen";
        uploadHintEl.className = "request-state";
      } else {
        uploadHintEl.textContent = "";
        uploadHintEl.className = "request-state";
      }

      pasteTargetEl.textContent = currentUpload && currentUpload.source_type === "clipboard"
        ? "Bild wird eingefuegt..."
        : "Bild hier einfuegen (Ctrl+V)";
      pasteTargetEl.className = inputUploadNotice.state === "error" && inputUploadNotice.source_type === "clipboard"
        ? "request-state error"
        : "request-state";

      inputMetaEl.textContent = currentInputImageSummary();
    }

    function resetSelectedUploadFile() {
      selectedUploadFile = null;
      inputFileEl.value = "";
    }

    function handleInputFileSelection() {
      const file = inputFileEl.files && inputFileEl.files.length > 0 ? inputFileEl.files[0] : null;
      if (!file) {
        selectedUploadFile = null;
        if (!currentUpload && activeInputImage.state === "none") {
          setInputUploadNotice("idle", "Bild fehlt noch");
        }
        renderUi();
        return;
      }

      if (!isSupportedUploadFile(file)) {
        resetSelectedUploadFile();
        setInputUploadNotice("error", "Bild konnte nicht geladen werden | ungueltiger Dateityp", {
          source_type: "file",
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return;
      }

      selectedUploadFile = file;
      setInputUploadNotice("idle", `Bild ausgewaehlt | ${file.name}`, {
        source_type: "file"
      });
      renderUi();
    }

    function buildTransferText(sourceType, phase, blocker = null) {
      const normalizedSourceType = sourceType === "clipboard" ? "clipboard" : "file";
      if (phase === "processing") {
        return normalizedSourceType === "clipboard" ? "Bild wird eingefuegt..." : "Bild wird geladen...";
      }
      if (phase === "success") {
        return normalizedSourceType === "clipboard" ? "Bild eingefuegt" : "Bild geladen";
      }
      if (phase === "missing_input") {
        return normalizedSourceType === "clipboard"
          ? "Keine Bilddaten in Zwischenablage"
          : "Bild fehlt noch";
      }
      if (phase === "invalid_type") {
        return normalizedSourceType === "clipboard"
          ? "Bild konnte nicht eingefuegt werden | ungueltiger Dateityp"
          : "Bild konnte nicht geladen werden | ungueltiger Dateityp";
      }
      if (phase === "request_failed") {
        return normalizedSourceType === "clipboard"
          ? "Bild konnte nicht eingefuegt werden | upload_request_failed"
          : "Bild konnte nicht geladen werden | upload_request_failed";
      }
      if (phase === "failed") {
        return normalizedSourceType === "clipboard"
          ? `Bild konnte nicht eingefuegt werden | ${blocker || "upload_failed"}`
          : `Bild konnte nicht geladen werden | ${blocker || "upload_failed"}`;
      }
      return normalizedSourceType === "clipboard" ? "Zwischenablage" : "Bild";
    }

    async function submitInputImage(file, sourceType) {
      if (currentUpload) {
        return false;
      }

      if (!(file instanceof File)) {
        setInputUploadNotice("error", buildTransferText(sourceType, "missing_input"), {
          source_type: sourceType,
          error_type: "invalid_request",
          blocker: sourceType === "clipboard" ? "clipboard_no_image" : "missing_file"
        });
        renderUi();
        return false;
      }

      if (!isSupportedUploadFile(file)) {
        if (sourceType === "file") {
          resetSelectedUploadFile();
        }
        setInputUploadNotice("error", buildTransferText(sourceType, "invalid_type"), {
          source_type: sourceType,
          error_type: "invalid_upload",
          blocker: "invalid_file_type"
        });
        renderUi();
        return false;
      }

      const uploadToken = `upload-${String(++currentUploadCounter).padStart(6, "0")}`;
      currentUpload = {
        token: uploadToken,
        started_at_utc: new Date().toISOString(),
        source_type: sourceType,
        file_name: file.name
      };
      setInputUploadNotice("uploading", buildTransferText(sourceType, "processing"), {
        source_type: sourceType
      });
      renderUi();

      const formData = new FormData();
      formData.append("image", file);
      formData.append("source_type", sourceType);

      try {
        const response = await fetch("/input-image", {
          method: "POST",
          body: formData
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentUpload || currentUpload.token !== uploadToken) {
          return;
        }

        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const errorType = INPUT_UPLOAD_ERROR_TYPES.has(payload?.error_type) ? payload.error_type : "upload_error";
          const blocker = isNonEmptyString(payload?.blocker) ? payload.blocker : "upload_failed";
          const message = blocker === "invalid_file_type"
            ? buildTransferText(sourceType, "invalid_type")
            : buildTransferText(sourceType, "failed", blocker);
          setInputUploadNotice("error", message, {
            source_type: sourceType,
            error_type: errorType,
            blocker
          });
          renderUi();
          return false;
        }

        resetSelectedUploadFile();
        setCurrentInputImage(payload, {
          noticeText: buildTransferText(sourceType, "success")
        });
        await fetchHealth({ forceFresh: true });
        return true;
      } catch (error) {
        if (!currentUpload || currentUpload.token !== uploadToken) {
          return false;
        }

        setInputUploadNotice("error", buildTransferText(sourceType, "request_failed"), {
          source_type: sourceType,
          error_type: "upload_error",
          blocker: "upload_request_failed"
        });
        return false;
      } finally {
        if (currentUpload && currentUpload.token === uploadToken) {
          currentUpload = null;
        }
        renderUi();
      }
    }

    async function attemptUploadImage() {
      return submitInputImage(selectedUploadFile, "file");
    }

    async function handlePasteEvent(event) {
      const clipboardFile = extractClipboardImageFile(event.clipboardData);
      const targetIsPasteTarget = event.target === pasteTargetEl || pasteTargetEl.contains(event.target);

      if (!(clipboardFile instanceof File)) {
        if (targetIsPasteTarget) {
          event.preventDefault();
          setInputUploadNotice("error", buildTransferText("clipboard", "missing_input"), {
            source_type: "clipboard",
            error_type: "invalid_request",
            blocker: "clipboard_no_image"
          });
          renderUi();
        }
        return;
      }

      event.preventDefault();
      await submitInputImage(clipboardFile, "clipboard");
    }

    async function resetUploadedInputImage() {
      if (currentUpload) {
        return;
      }

      resetSelectedUploadFile();
      if (activeInputImage.state === "none") {
        setInputUploadNotice("idle", "Bild fehlt noch");
        renderUi();
        return;
      }

      currentUpload = {
        token: `upload-${String(++currentUploadCounter).padStart(6, "0")}`,
        started_at_utc: new Date().toISOString(),
        source_type: "file",
        file_name: null
      };
      setInputUploadNotice("uploading", "Bild wird entfernt...", {
        source_type: "file"
      });
      renderUi();

      const uploadToken = currentUpload.token;
      try {
        const response = await fetch("/input-image/current", {
          method: "DELETE"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!currentUpload || currentUpload.token !== uploadToken) {
          return;
        }

        if (!response.ok || !payload || payload.status !== "ok") {
          setInputUploadNotice("error", "Bild konnte nicht entfernt werden | input_reset_failed", {
            error_type: "upload_error",
            blocker: isNonEmptyString(payload?.blocker) ? payload.blocker : "input_reset_failed"
          });
          renderUi();
          return;
        }

        clearCurrentInputImage({ clearNotice: false });
        setInputUploadNotice("idle", "Bild entfernt");
        await fetchHealth({ forceFresh: true });
      } catch (error) {
        if (!currentUpload || currentUpload.token !== uploadToken) {
          return;
        }

        setInputUploadNotice("error", "Bild konnte nicht entfernt werden | input_reset_failed", {
          error_type: "upload_error",
          blocker: "input_reset_failed"
        });
      } finally {
        if (currentUpload && currentUpload.token === uploadToken) {
          currentUpload = null;
        }
        renderUi();
      }
    }

    function detachImageLoader() {
      if (!activeImageLoader) {
        return;
      }

      try {
        activeImageLoader.onload = null;
        activeImageLoader.onerror = null;
      } catch (error) {
      }
      activeImageLoader = null;
    }

    function clearImageDomBindings() {
      imageEl.onload = null;
      imageEl.onerror = null;
      delete imageEl.dataset.imageToken;
      delete imageEl.dataset.imageDisplayUrl;
      delete imageEl.dataset.imageRequestId;
    }

    function createEmptyImageContext() {
      return {
        token: null,
        output_file: null,
        display_url: null,
        request_id: null,
        mode: null,
        prompt_id: null,
        restored_from_storage: false,
        state: "none"
      };
    }

    function buildImageDisplayUrl(url, token) {
      return `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}-${encodeURIComponent(token)}`;
    }

    function createImageContext(url, metadata = {}) {
      const token = `image-${String(++imageTokenCounter).padStart(6, "0")}`;
      const normalizedUrl = url.trim();
      return {
        token,
        output_file: normalizedUrl,
        display_url: buildImageDisplayUrl(normalizedUrl, token),
        request_id: metadata.request_id ?? null,
        mode: metadata.mode ?? null,
        prompt_id: metadata.prompt_id ?? null,
        restored_from_storage: metadata.restored_from_storage === true,
        state: "loading"
      };
    }

    function logIgnoredImageEvent(token, displayUrl, reason) {
      void token;
      void displayUrl;
      void reason;
    }

    function isImageEventRelevant(token, displayUrl) {
      if (!isNonEmptyString(token) || !isNonEmptyString(displayUrl)) {
        return false;
      }

      const normalizedToken = token.trim();
      const normalizedDisplayUrl = displayUrl.trim();
      return Boolean(
        activeImageContext &&
        activeImageContext.token === normalizedToken &&
        activeImageContext.display_url === normalizedDisplayUrl
      );
    }

    function setDisplayedImageContext(context) {
      displayedImage = {
        token: context.token,
        output_file: context.output_file,
        display_url: context.display_url,
        request_id: context.request_id ?? null
      };
      imageEl.dataset.imageToken = context.token;
      imageEl.dataset.imageDisplayUrl = context.display_url;
      imageEl.dataset.imageRequestId = context.request_id ?? "";
    }

    function commitActiveImageToDom(token, displayUrl) {
      if (!isImageEventRelevant(token, displayUrl)) {
        logIgnoredImageEvent(token, displayUrl, "commit_not_relevant");
        return false;
      }

      const context = {
        ...activeImageContext,
        state: "loading"
      };
      activeImageContext = context;

      imageEl.onload = () => {
        handleImageLoadEvent(context.token, context.display_url, "dom");
      };
      imageEl.onerror = () => {
        handleImageErrorEvent(context.token, context.display_url, "dom");
      };
      imageEl.src = context.display_url;
      imageEl.style.display = "block";
      return true;
    }

    function handleActiveImageFailure(token, displayUrl, source = "unknown") {
      if (!isImageEventRelevant(token, displayUrl)) {
        logIgnoredImageEvent(token, displayUrl, `${source}_not_relevant`);
        return false;
      }

      const failedImage = {
        token: activeImageContext.token,
        output_file: activeImageContext.output_file,
        display_url: activeImageContext.display_url,
        request_id: activeImageContext.request_id
      };
      activeImageContext = {
        ...activeImageContext,
        state: "error"
      };

      clearSuccessfulImageState({ preserveActiveContext: true });

      if (
        lastResult &&
        lastResult.status === "ok" &&
        lastResult.output_file === failedImage.output_file &&
        lastResult.request_id === failedImage.request_id
      ) {
        lastResult = {
          status: "error",
          mode: lastResult.mode,
          output_file: null,
          error_type: "output_file_missing",
          blocker: "generated_file_not_accessible",
          prompt_id: lastResult.prompt_id,
          request_id: lastResult.request_id
        };
      }

      clearTransientInfoNotice("image_error");
      clearTransientBusyNotice("image_error");
      setTransientRequestError(
        "output_file_missing",
        "generated_file_not_accessible",
        failedImage.request_id,
        { message: "Datei nicht lesbar | output_file_missing" }
      );

      renderUi();
      return true;
    }

    function handleImageLoadEvent(token, displayUrl, source = "unknown") {
      if (!isImageEventRelevant(token, displayUrl)) {
        logIgnoredImageEvent(token, displayUrl, `${source}_not_relevant`);
        return false;
      }

      if (source === "loader") {
        return commitActiveImageToDom(token, displayUrl);
      }

      activeImageContext = {
        ...activeImageContext,
        state: "ready"
      };
      setDisplayedImageContext(activeImageContext);
      renderUi();
      return true;
    }

    function handleImageErrorEvent(token, displayUrl, source = "unknown") {
      return handleActiveImageFailure(token, displayUrl, source);
    }

    function clearVisibleImage() {
      detachImageLoader();
      clearImageDomBindings();
      imageEl.style.display = "none";
      imageEl.removeAttribute("src");
      displayedImage = {
        token: null,
        output_file: null,
        display_url: null,
        request_id: null
      };
    }

    function clearImage() {
      clearVisibleImage();
      activeImageContext = createEmptyImageContext();
    }

    function setActiveImage(url, metadata = {}) {
      if (!isNonEmptyString(url)) {
        return null;
      }

      detachImageLoader();
      const context = createImageContext(url, metadata);
      activeImageContext = context;
      renderUi();

      const loader = new Image();
      activeImageLoader = loader;
      loader.onload = () => {
        handleImageLoadEvent(context.token, context.display_url, "loader");
      };
      loader.onerror = () => {
        handleImageErrorEvent(context.token, context.display_url, "loader");
      };
      loader.src = context.display_url;
      return {
        ...context
      };
    }

    function compactResult(payload) {
      if (!payload || typeof payload !== "object") {
        return null;
      }
      return {
        status: payload.status ?? null,
        mode: payload.mode ?? null,
        output_file: payload.output_file ?? null,
        error_type: payload.error_type ?? null,
        blocker: payload.blocker ?? null,
        prompt_id: payload.prompt_id ?? null,
        request_id: payload.request_id ?? null
      };
    }

    function readStorageJson(key) {
      try {
        const raw = window.localStorage.getItem(key);
        if (!raw) {
          return null;
        }
        const payload = JSON.parse(raw);
        return payload && typeof payload === "object" ? payload : null;
      } catch (error) {
        return null;
      }
    }

    function writeStorageJson(key, payload) {
      try {
        window.localStorage.setItem(key, JSON.stringify(payload));
      } catch (error) {
      }
    }

    function removeStorageItem(key) {
      try {
        window.localStorage.removeItem(key);
      } catch (error) {
      }
    }

    function readStorageString(key) {
      try {
        const raw = window.localStorage.getItem(key);
        if (typeof raw !== "string") {
          return null;
        }
        const value = JSON.parse(raw);
        return typeof value === "string" ? value : null;
      } catch (error) {
        return null;
      }
    }

    function normalizeV7ViewMode(value) {
      return value === "expert" ? "expert" : "basic";
    }

    function normalizeV7BasicTask(value) {
      return V7_TASK_CONFIG_BY_ID[value] ? value : "text";
    }

    function normalizeBasicImageStyle(value) {
      return BASIC_IMAGE_STYLE_CONFIG[value] ? value : "photo";
    }

    function persistV7NavigationState() {
      writeStorageJson(V7_VIEW_MODE_STORAGE_KEY, currentV7ViewMode);
      writeStorageJson(V7_BASIC_TASK_STORAGE_KEY, currentV7BasicTask);
      writeStorageJson(V11_BASIC_IMAGE_STYLE_STORAGE_KEY, currentBasicImageStyle);
      writeStorageJson(V11_IDENTITY_SINGLE_IMAGE_STYLE_STORAGE_KEY, currentIdentitySingleImageStyle);
    }

    function restoreV7NavigationState() {
      currentV7ViewMode = normalizeV7ViewMode(readStorageString(V7_VIEW_MODE_STORAGE_KEY));
      currentV7BasicTask = normalizeV7BasicTask(readStorageString(V7_BASIC_TASK_STORAGE_KEY));
      currentBasicImageStyle = normalizeBasicImageStyle(readStorageString(V11_BASIC_IMAGE_STYLE_STORAGE_KEY));
      currentIdentitySingleImageStyle = normalizeBasicImageStyle(readStorageString(V11_IDENTITY_SINGLE_IMAGE_STYLE_STORAGE_KEY));
    }

    function getCurrentV7TaskConfig() {
      return V7_TASK_CONFIG_BY_ID[currentV7BasicTask] || V7_TASK_CONFIG_BY_ID.text;
    }

    function setV7SectionVisibility(element, visible) {
      if (!element) {
        return;
      }
      element.hidden = !visible;
    }

    function buildV7VisibleSectionIds() {
      if (currentV7ViewMode === "expert") {
        return new Set([
          "section-expert-overview",
          "section-generate",
          "section-text-service-test",
          "section-input-images",
          "section-identity-reference",
          "section-identity-multi-reference",
          "section-identity-transfer",
          "section-current-result",
          "section-results"
        ]);
      }

      const taskConfig = getCurrentV7TaskConfig();
      const visibleSectionIds = new Set([
        "section-basic-task-focus"
      ]);
      taskConfig.section_ids.forEach((sectionId) => {
        visibleSectionIds.add(sectionId);
      });
      if (taskConfig.id !== "text") {
        visibleSectionIds.add("section-current-result");
        visibleSectionIds.add("section-results");
      }
      return visibleSectionIds;
    }

    function applyV7SectionVisibility() {
      const visibleSectionIds = buildV7VisibleSectionIds();
      setV7SectionVisibility(sectionBasicTaskFocusEl, visibleSectionIds.has("section-basic-task-focus"));
      setV7SectionVisibility(sectionExpertOverviewEl, visibleSectionIds.has("section-expert-overview"));
      setV7SectionVisibility(sectionGenerateEl, visibleSectionIds.has("section-generate"));
      setV7SectionVisibility(sectionTextServiceBasicEl, visibleSectionIds.has("section-text-service-basic"));
      setV7SectionVisibility(sectionTextServiceTestEl, visibleSectionIds.has("section-text-service-test"));
      setV7SectionVisibility(sectionInputImagesEl, visibleSectionIds.has("section-input-images"));
      setV7SectionVisibility(sectionIdentityReferenceEl, visibleSectionIds.has("section-identity-reference"));
      setV7SectionVisibility(sectionIdentityMultiReferenceEl, visibleSectionIds.has("section-identity-multi-reference"));
      setV7SectionVisibility(sectionIdentityTransferEl, visibleSectionIds.has("section-identity-transfer"));
      setV7SectionVisibility(sectionCurrentResultEl, visibleSectionIds.has("section-current-result"));
      setV7SectionVisibility(sectionResultsEl, visibleSectionIds.has("section-results"));
      guidedTaskAreaEl.hidden = currentV7ViewMode === "expert";
    }

    function setGuidedTaskNote(element, title, text, visible) {
      if (!element) {
        return;
      }

      if (!visible || !isNonEmptyString(title) || !isNonEmptyString(text)) {
        element.hidden = true;
        element.replaceChildren();
        return;
      }

      const strong = document.createElement("strong");
      strong.textContent = title.trim();
      const span = document.createElement("span");
      span.textContent = text.trim();
      element.replaceChildren(strong, span);
      element.hidden = false;
    }

    function isV7BasicModeActive() {
      return currentV7ViewMode === "basic";
    }

    function isV7BasicIdentitySingleMode() {
      return isV7BasicModeActive() && getCurrentV7TaskConfig().id === "identity-single";
    }

    function isV7BasicIdentityMultiMode() {
      return isV7BasicModeActive() && getCurrentV7TaskConfig().id === "identity-multi";
    }

    function isV7BasicIdentityTransferMode() {
      return isV7BasicModeActive() && getCurrentV7TaskConfig().id === "identity-transfer";
    }

    function isV11BasicImageTask(taskId = getCurrentV7TaskConfig().id) {
      return isV7BasicModeActive() && BASIC_IMAGE_TASK_IDS.includes(taskId);
    }

    function getBasicTaskNegativePromptDefault(taskId) {
      if (!BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return "";
      }
      return basicTaskStandardNegativeEnabled[taskId] === true ? STANDARD_NEGATIVE_PROMPT_TEXT : "";
    }

    function ensureBasicTaskNegativePromptDraft(taskId) {
      if (!BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return "";
      }
      if (typeof basicTaskNegativePromptDrafts[taskId] === "string") {
        return basicTaskNegativePromptDrafts[taskId];
      }
      const fallbackValue = getBasicTaskNegativePromptDefault(taskId);
      basicTaskNegativePromptDrafts[taskId] = fallbackValue;
      basicTaskNegativePromptAutoManaged[taskId] = isNonEmptyString(fallbackValue);
      return fallbackValue;
    }

    function persistBasicTaskNegativePromptDraft(taskId) {
      if (!(negativePromptEl instanceof HTMLTextAreaElement) || !BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return;
      }
      const normalizedValue = isNonEmptyString(negativePromptEl.value) ? negativePromptEl.value.trim() : "";
      basicTaskNegativePromptDrafts[taskId] = normalizedValue;
      basicTaskNegativePromptAutoManaged[taskId] = basicTaskStandardNegativeEnabled[taskId] === true
        && normalizedValue === getBasicTaskNegativePromptDefault(taskId);
    }

    function setBasicTaskStandardNegativePromptEnabled(taskId, enabled) {
      if (!BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return;
      }
      const previousDefault = getBasicTaskNegativePromptDefault(taskId);
      const currentDraft = typeof basicTaskNegativePromptDrafts[taskId] === "string" ? basicTaskNegativePromptDrafts[taskId] : "";
      const wasAutoManaged = basicTaskNegativePromptAutoManaged[taskId] === true;

      basicTaskStandardNegativeEnabled[taskId] = enabled === true;
      const nextDefault = getBasicTaskNegativePromptDefault(taskId);

      if (enabled === true) {
        if (!isNonEmptyString(currentDraft) || wasAutoManaged) {
          basicTaskNegativePromptDrafts[taskId] = nextDefault;
          basicTaskNegativePromptAutoManaged[taskId] = true;
        }
      } else {
        if (wasAutoManaged && currentDraft === previousDefault) {
          basicTaskNegativePromptDrafts[taskId] = "";
        }
        basicTaskNegativePromptAutoManaged[taskId] = false;
      }
    }

    function syncBasicTaskNegativePrompt(taskId, basicMode) {
      if (!(negativePromptEl instanceof HTMLTextAreaElement)) {
        return;
      }
      if (!basicMode || !BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return;
      }
      const nextValue = ensureBasicTaskNegativePromptDraft(taskId);
      if (negativePromptEl.value !== nextValue) {
        negativePromptEl.value = nextValue;
      }
    }

    function renderStandardNegativePromptControl(taskId, basicMode) {
      if (!standardNegativePromptRowEl || !useStandardNegativePromptEl || !standardNegativePromptCopyEl) {
        return;
      }

      const visible = basicMode && BASIC_IMAGE_TASK_IDS.includes(taskId);
      standardNegativePromptRowEl.hidden = !visible;
      if (!visible) {
        return;
      }

      useStandardNegativePromptEl.checked = basicTaskStandardNegativeEnabled[taskId] === true;
      standardNegativePromptCopyEl.textContent = useStandardNegativePromptEl.checked
        ? `Aktiv setzt optional: ${STANDARD_NEGATIVE_PROMPT_TEXT}`
        : "Deaktiviert: Das Feld bleibt komplett unter deiner Kontrolle.";
    }

    function getCurrentBasicImageStyleConfig() {
      return BASIC_IMAGE_STYLE_CONFIG[currentBasicImageStyle] || BASIC_IMAGE_STYLE_CONFIG.photo;
    }

    function getCurrentIdentitySingleImageStyleConfig() {
      return BASIC_IMAGE_STYLE_CONFIG[currentIdentitySingleImageStyle] || BASIC_IMAGE_STYLE_CONFIG.photo;
    }

    function syncV7BasicTaskDefaults() {
      if (!isV7BasicModeActive()) {
        return;
      }

      if (!BASIC_IMAGE_TASK_IDS.includes(currentV7BasicTask)) {
        return;
      }

      if (modeEl.value !== "auto") {
        modeEl.value = "auto";
      }

      if (currentV7BasicTask === "create") {
        useInputImageEl.checked = false;
        useInpaintingEl.checked = false;
        return;
      }

      if (currentV7BasicTask === "edit") {
        useInputImageEl.checked = true;
        useInpaintingEl.checked = false;
        denoiseStrengthEl.value = DEFAULT_IMG2IMG_DENOISE.toFixed(2);
        return;
      }

      if (currentV7BasicTask === "inpaint") {
        useInputImageEl.checked = true;
        useInpaintingEl.checked = true;
        denoiseStrengthEl.value = DEFAULT_INPAINT_DENOISE.toFixed(2);
      }
      syncBasicTaskNegativePrompt(currentV7BasicTask, true);
    }

    function renderNegativePromptGuidance(taskId, basicMode) {
      if (!(negativePromptEl instanceof HTMLTextAreaElement) || !negativePromptHintEl) {
        return;
      }

      if (basicMode && BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        syncBasicTaskNegativePrompt(taskId, true);
      }

      renderStandardNegativePromptControl(taskId, basicMode);

      if (!basicMode || !BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        negativePromptEl.placeholder = "Optional: Elemente oder Artefakte, die vermieden werden sollen.";
        negativePromptHintEl.textContent = "Optional: Beschreibe kurz, was im Bild vermieden werden soll.";
        return;
      }

      if (taskId === "create") {
        negativePromptEl.placeholder = "z. B. unscharf, low quality, chaotischer Hintergrund";
        negativePromptHintEl.textContent = basicTaskStandardNegativeEnabled.create === true
          ? "Der Standard-Negativprompt ist aktiv, bleibt aber editierbar und abschaltbar."
          : "Optional: Unerwuenschte Bildanteile beim neuen Bild vermeiden.";
        return;
      }

      if (taskId === "edit") {
        negativePromptEl.placeholder = "z. B. keine neue Person, kein Hintergrundchaos, nicht unscharf";
        negativePromptHintEl.textContent = basicTaskStandardNegativeEnabled.edit === true
          ? "Der Standard-Negativprompt ist aktiv, bleibt aber editierbar und wird nicht staendig ueberschrieben."
          : "Optional: Hilft, das Ausgangsbild ruhiger zu erhalten.";
        return;
      }

      negativePromptEl.placeholder = "z. B. keine Aenderung ausserhalb der Maske, keine Unschaerfe";
      negativePromptHintEl.textContent = basicTaskStandardNegativeEnabled.inpaint === true
        ? "Der Standard-Negativprompt ist aktiv, bleibt aber editierbar. Fuer groessere Inpaint-Faelle lieber ruhig und gezielt bleiben."
        : "Optional: Hilft, die Aenderung lokaler im markierten Bereich zu halten.";
    }

    function renderV7GenerateActiveInputContext(taskId, basicMode) {
      if (!generateActiveInputContextEl || !generateActiveInputPreviewEl || !generateActiveInputMetaEl) {
        return;
      }

      const showContext = basicMode && ["edit", "inpaint"].includes(taskId);
      if (!showContext) {
        generateActiveInputContextEl.hidden = true;
        generateActiveInputMetaEl.textContent = "";
        generateActiveInputMetaEl.className = "request-state";
        generateActiveInputPreviewEl.hidden = true;
        generateActiveInputPreviewEl.removeAttribute("src");
        delete generateActiveInputPreviewEl.dataset.inputDisplayUrl;
        return;
      }

      generateActiveInputContextEl.hidden = false;
      if (activeInputImage.state === "ready" && isNonEmptyString(activeInputImage.display_url)) {
        const displayUrl = activeInputImage.display_url.trim();
        if (generateActiveInputPreviewEl.dataset.inputDisplayUrl !== displayUrl) {
          generateActiveInputPreviewEl.src = displayUrl;
          generateActiveInputPreviewEl.dataset.inputDisplayUrl = displayUrl;
        }
        generateActiveInputPreviewEl.hidden = false;
        generateActiveInputMetaEl.textContent = `Aktiv | ${formatBasicImageSummary(activeInputImage, "Bild geladen")}`;
        generateActiveInputMetaEl.className = "request-state";
        return;
      }

      generateActiveInputPreviewEl.hidden = true;
      generateActiveInputPreviewEl.removeAttribute("src");
      delete generateActiveInputPreviewEl.dataset.inputDisplayUrl;

      if (currentUpload || activeInputImage.state === "loading") {
        generateActiveInputMetaEl.textContent = "Eingabebild wird geladen...";
        generateActiveInputMetaEl.className = "request-state";
        return;
      }

      if (inputUploadNotice.state === "error") {
        const blocker = isNonEmptyString(inputUploadNotice.blocker) ? ` | ${inputUploadNotice.blocker}` : "";
        generateActiveInputMetaEl.textContent = `Kein aktives Eingabebild${blocker}`;
        generateActiveInputMetaEl.className = "request-state error";
        return;
      }

      generateActiveInputMetaEl.textContent = "Noch kein Eingabebild geladen. Lade zuerst ein Bild im Bereich Eingabebilder.";
      generateActiveInputMetaEl.className = "request-state";
    }

    function renderV7GenerateSectionUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;
      const styleConfig = getCurrentBasicImageStyleConfig();
      renderNegativePromptGuidance(taskId, basicMode);
      renderV7GenerateActiveInputContext(taskId, basicMode);

      if (!basicMode || !["create", "edit", "inpaint"].includes(taskId)) {
        generateSectionTitleEl.textContent = "Bild erstellen";
        generateSectionHintEl.textContent = "Prompt, optional Bild und Maske, danach Ergebnis";
        setGuidedTaskNote(generateBasicGuideEl, null, null, false);
        basicImageStyleSwitchEl.hidden = true;
        generateControlModeEl.hidden = false;
        generateControlCheckpointEl.hidden = false;
        generateControlInputToggleEl.hidden = false;
        generateControlDenoiseEl.hidden = false;
        generateControlInpaintToggleEl.hidden = false;
        generateControlGridEl.hidden = false;
        return;
      }

      basicImageStyleSwitchEl.hidden = false;
      basicImageStyleHintEl.textContent = `${styleConfig.label} ${styleConfig.hint.toLowerCase()}`;
      basicImageStylePhotoEl.classList.toggle("active", currentBasicImageStyle === "photo");
      basicImageStyleAnimeEl.classList.toggle("active", currentBasicImageStyle === "anime");
      generateControlModeEl.hidden = true;
      generateControlCheckpointEl.hidden = true;
      generateControlInputToggleEl.hidden = true;
      generateControlInpaintToggleEl.hidden = true;
      generateControlDenoiseEl.hidden = taskId !== "edit";
      generateControlGridEl.hidden = taskId !== "edit";

      if (taskId === "create") {
        generateSectionTitleEl.textContent = "Neues Bild erstellen";
        generateSectionHintEl.textContent = `Beschreibe kurz Motiv, Stil, Licht und Stimmung fuer dein ${currentBasicImageStyle === "anime" ? "Anime-Bild" : "Bild"}.`;
        setGuidedTaskNote(
          generateBasicGuideEl,
          "1. Prompt schreiben",
          `${styleConfig.label} ist aktiv und steuert den Bildstil. Schreibe am besten Motiv + Stil + Licht/Stimmung in einem Satz, z. B. "Portrait bei warmem Abendlicht". Danach kannst du direkt starten.`,
          true
        );
        return;
      }

      if (taskId === "edit") {
        generateSectionTitleEl.textContent = "Bild anpassen";
        generateSectionHintEl.textContent = "Dein Ausgangsbild bleibt die Grundlage. Beschreibe nur die gewuenschte Aenderung. Fuer Spezialfaelle mit derselben Person nutze den getrennten Expertenbereich.";
        setGuidedTaskNote(
          generateBasicGuideEl,
          "2. Aenderung beschreiben",
          `${styleConfig.label} ist aktiv und steuert, ob die Aenderung eher realistisch oder stilisiert wirkt. Kleine, klare Aenderungen funktionieren oft besser als eine komplette Neuschreibung (z. B. "Jacke rot", "Licht waermer"). Fuer neue Szene oder neue Pose derselben Person wechsle in den getrennten Expertenbereich. Starte bei Aenderungsstaerke 0.25 und erhoehe nur bei Bedarf.`,
          true
        );
        return;
      }

      generateSectionTitleEl.textContent = "Bereich im Bild aendern";
      generateSectionHintEl.textContent = "Markiere zuerst den Bereich. Dieser Modus ist am staerksten bei kleineren lokalen Aenderungen. Grosse Kleidungs-/Formwechsel sind aktuell nicht verlaesslich genug.";
      setGuidedTaskNote(
        generateBasicGuideEl,
        "3. Bereich beschreiben",
        `${styleConfig.label} ist aktiv und steuert den Stil des geaenderten Bereichs. Beschreibe nur die lokale Aenderung im markierten Bereich (z. B. "Himmel als Sonnenuntergang", "kleines Objekt ersetzen", "Detail lokal korrigieren"). Der Rest soll moeglichst stehenbleiben. Starte bei Aenderungsstaerke 0.58. Fuer feinere Details eher etwas niedriger. Groessere Kleidungs-/Farbwechsel mit gleicher Form sind auf dem aktuellen lokalen Stand nicht verlaesslich genug.`,
        true
      );
    }

    function renderV7TextServiceBasicUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;
      const userState = getTextServiceUserState();
      if (!basicMode || taskId !== "text") {
        textServiceBasicSectionTitleEl.textContent = "Schreiben und Ueberarbeiten";
        textServiceBasicSectionHintEl.textContent = "Textkoerper schreiben, ueberarbeiten und Bildprompts ableiten";
        setGuidedTaskNote(textServiceBasicGuideEl, null, null, false);
        return;
      }

      textServiceBasicSectionTitleEl.textContent = "Schreiben und Ueberarbeiten";
      textServiceBasicSectionHintEl.textContent = userState.focus_hint;
      setGuidedTaskNote(
        textServiceBasicGuideEl,
        "Text eingeben, ueberarbeiten oder als Bildprompt ableiten",
        userState.guide_detail,
        true
      );
    }

    function deriveBasicTextTaskLeadView() {
      const textServiceState = getTextServiceHealthState();
      const userState = getTextServiceUserState(textServiceState);
      if (textServiceBasicPromptState.phase === "sending") {
        return {
          text: "Antwort wird erzeugt...",
          is_error: false
        };
      }

      if (textServiceState.phase === "pending") {
        return {
          text: userState.short_text,
          is_error: false
        };
      }

      if (textServiceBasicPromptState.phase === "error") {
        return {
          text: formatTextServiceBasicError(
            textServiceBasicPromptState.error,
            textServiceBasicPromptState.error_message
          ),
          is_error: false
        };
      }

      if (["not_configured", "unreachable", "stub", "not_ready"].includes(userState.key)) {
        return {
          text: userState.short_text,
          is_error: false
        };
      }

      if (textServiceBasicPromptState.phase === "success") {
        return {
          text: "Antwort ist fertig",
          is_error: false
        };
      }

      if (!isNonEmptyString(textServiceBasicPromptEl.value)) {
        return {
          text: "Gib zuerst deinen Text ein",
          is_error: false
        };
      }

      return {
        text: "Jetzt kannst du starten",
        is_error: false
      };
    }

    function renderV7BasicTaskFocusUi() {
      const basicMode = isV7BasicModeActive();
      if (!basicMode) {
        setGuidedTaskNote(basicTaskFocusNoteEl, null, null, false);
        basicTaskFocusExtraEl.textContent = "";
        basicTaskFocusExtraEl.className = "request-state";
        basicTaskFocusActionsEl.hidden = true;
        basicTaskOpenExpertEl.textContent = "Im Expertenbereich oeffnen";
        basicTaskOpenExpertEl.dataset.action = "open_expert";
        basicTaskOpenExpertEl.dataset.targetTask = "";
        basicTaskOpenExpertHintEl.textContent = "";
        return;
      }

      const taskId = getCurrentV7TaskConfig().id;
      basicTaskFocusActionsEl.hidden = true;
      basicTaskOpenExpertEl.textContent = "Im Expertenbereich oeffnen";
      basicTaskOpenExpertEl.dataset.action = "open_expert";
      basicTaskOpenExpertEl.dataset.targetTask = "";
      basicTaskOpenExpertHintEl.textContent = "";
      basicTaskFocusExtraEl.className = "request-state";

      if (taskId === "create") {
        basicTaskFocusTitleEl.textContent = "Neues Bild erstellen";
        basicTaskFocusHintEl.textContent = "Beschreibe kurz Motiv, Stil, Licht und Stimmung. Danach kannst du direkt starten.";
        setGuidedTaskNote(
          basicTaskFocusNoteEl,
          "Du brauchst nur einen Prompt",
          `Schreibe kurz, was auf dem Bild zu sehen sein soll und wie es wirken soll. Foto wirkt realistischer, Anime ist ein freierer Stilmodus derselben Idee. Beispielrichtung: "Portrait bei weichem Abendlicht".`,
          true
        );
        basicTaskFocusExtraEl.textContent = `${getCurrentBasicImageStyleConfig().label} ist aktiv und steuert die Bildwelt direkt vor dem Start.`;
        return;
      }

      if (taskId === "text") {
        const leadView = deriveBasicTextTaskLeadView();
        const userState = getTextServiceUserState();
        basicTaskFocusExtraEl.className = leadView.is_error ? "request-state error" : "request-state";
        basicTaskFocusTitleEl.textContent = "Text schreiben / Text-KI nutzen";
        basicTaskFocusHintEl.textContent = userState.focus_hint;
        setGuidedTaskNote(
          basicTaskFocusNoteEl,
          "Du brauchst nur deinen Text",
          userState.guide_detail,
          true
        );
        basicTaskFocusExtraEl.textContent = leadView.text;
        return;
      }

      if (taskId === "edit") {
        basicTaskFocusTitleEl.textContent = "Bild anpassen";
        basicTaskFocusHintEl.textContent = "Bild laden, Aenderung beschreiben, mit 0.30 starten und nur bei Bedarf staerker gehen.";
        setGuidedTaskNote(
          basicTaskFocusNoteEl,
          "Du brauchst ein Bild",
          `Lade zuerst ein Bild hoch. Das Ausgangsbild bleibt die Basis. Kleine Aenderungen wie "Jacke rot" oder "Licht waermer" sind meist stabiler als ein kompletter Neuaufbau. Fuer neue Pose oder neue Szene derselben Person gibt es aktuell nur einen Sonderpfad im Expertenbereich.`,
          true
        );
        basicTaskFocusExtraEl.textContent = `${getCurrentBasicImageStyleConfig().label} ist aktiv. 0.30 wirkt meist stabiler, hoehere Werte greifen staerker in das Ursprungsbild ein.`;
        basicTaskFocusActionsEl.hidden = false;
        basicTaskOpenExpertEl.textContent = "Im Expertenbereich oeffnen";
        basicTaskOpenExpertEl.dataset.action = "open_expert";
        basicTaskOpenExpertEl.dataset.targetTask = "";
        basicTaskOpenExpertHintEl.textContent = "Der Szenenpfad mit derselben Person ist aktuell nur als Sonderpfad verfuegbar und noch nicht verlaesslich freigegeben.";
        return;
      }

      if (taskId === "identity-single") {
        basicTaskFocusTitleEl.textContent = "Sonderpfad: Neue Szene mit derselben Person";
        basicTaskFocusHintEl.textContent = "Aktuell nicht verlaesslich freigegeben. Gleiche Person in neuer Szene driftet auf diesem lokalen Stand noch zu stark.";
        setGuidedTaskNote(
          basicTaskFocusNoteEl,
          "Referenz-Sonderpfad",
          "Dieser Modus bleibt technisch erreichbar, ist aber aktuell nicht stabil genug fuer einen verlaesslichen Produktlauf. Nutze ihn nur fuer gezielte Tests, nicht fuer belastbare gleiche-Person-Ergebnisse.",
          true
        );
        basicTaskFocusExtraEl.textContent = `${getCurrentIdentitySingleImageStyleConfig().label} ist aktiv. Foto und Anime laufen technisch, halten die Person aber derzeit nicht verlaesslich genug.`;
        basicTaskFocusActionsEl.hidden = false;
        basicTaskOpenExpertEl.textContent = "Zur Aufgabe Bild anpassen";
        basicTaskOpenExpertEl.dataset.action = "switch_task";
        basicTaskOpenExpertEl.dataset.targetTask = "edit";
        basicTaskOpenExpertHintEl.textContent = "Nutze Bild anpassen fuer den verlaesslicheren Hauptpfad bei leichten bis mittleren Aenderungen.";
        return;
      }

      if (taskId === "inpaint") {
        basicTaskFocusTitleEl.textContent = "Bereich im Bild aendern";
        basicTaskFocusHintEl.textContent = "Bild laden, Bereich markieren, lokale Aenderung beschreiben, mit 0.58 starten.";
        setGuidedTaskNote(
          basicTaskFocusNoteEl,
          "Du brauchst Bild plus Maske",
          `Lade zuerst dein Bild. Danach markierst du den Bereich und beschreibst nur die Aenderung dort, z. B. "ersetze den Himmel durch Sonnenuntergang" oder "kleines Objekt lokal austauschen". Dieser Modus ist aktuell am brauchbarsten fuer kleinere lokale Korrekturen und klar begrenzte Teilbereichswechsel. Grosse Kleidungs-/Farbwechsel mit Form-Erhalt sind auf diesem lokalen Stand nicht verlaesslich genug.`,
          true
        );
        basicTaskFocusExtraEl.textContent = `${getCurrentBasicImageStyleConfig().label} ist aktiv. 0.58 trifft lokale Maskenaenderungen meist besser; fuer feinere Korrekturen etwas niedriger. Fuer grosse Kleidungsflaechen mit gleicher Form ist dieser Modus aktuell nur eingeschraenkt verlaesslich.`;
        return;
      }

      const leadView = deriveBasicTextTaskLeadView();
      basicTaskFocusExtraEl.className = leadView.is_error ? "request-state error" : "request-state";
      basicTaskFocusTitleEl.textContent = "Text schreiben / Text-KI nutzen";
      basicTaskFocusHintEl.textContent = "Nutze die Text-KI fuer Texte, Umformulierungen und Bildprompts.";
      setGuidedTaskNote(
        basicTaskFocusNoteEl,
        "Du brauchst nur deinen Text",
        "Wenn die Antwort als Bildprompt passt, kannst du sie direkt in den Bildgenerator uebernehmen.",
        true
      );
      basicTaskFocusExtraEl.textContent = leadView.text;
      basicTaskFocusActionsEl.hidden = true;
      basicTaskOpenExpertHintEl.textContent = "";
    }

    function renderV7InputSectionUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;

      if (!basicMode || !["edit", "inpaint"].includes(taskId)) {
        inputImagesSectionTitleEl.textContent = "Eingabebilder";
        inputImagesSectionHintEl.textContent = "Bild fuer Aenderungen, bei Bedarf mit Maske";
        setGuidedTaskNote(inputImagesBasicGuideEl, null, null, false);
        inputCardSourceEl.hidden = false;
        inputCardMaskEl.hidden = false;
        return;
      }

      inputCardSourceEl.hidden = false;
      inputCardMaskEl.hidden = taskId !== "inpaint";

      if (taskId === "edit") {
        inputImagesSectionTitleEl.textContent = "Ausgangsbild";
        inputImagesSectionHintEl.textContent = "Lade das Bild, das du veraendern willst. Fuer neue Pose/Szene derselben Person nutze den Szenenpfad.";
        setGuidedTaskNote(
          inputImagesBasicGuideEl,
          "1. Bild laden",
          "Du brauchst nur ein Bild als Ausgangspunkt. Dieser Weg ist fuer leichte bis mittlere Aenderungen am bestehenden Bild.",
          true
        );
        return;
      }

      inputImagesSectionTitleEl.textContent = "Bild und Bereich";
      inputImagesSectionHintEl.textContent = "Lade dein Bild und markiere den Bereich, der geaendert werden soll.";
      setGuidedTaskNote(
        inputImagesBasicGuideEl,
        "1. Bild laden, 2. Bereich markieren",
        "Nutze danach Upload oder Masken-Editor, um nur den gewuenschten Bereich zu markieren.",
        true
      );
    }

    function renderV7IdentityReferenceSectionUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;
      if (!basicMode || taskId !== "identity-single") {
        sectionIdentityReferenceEl.classList.remove("basic-surface", "basic-surface-work");
        identityReferenceSectionTitleEl.textContent = "Neue Szene mit derselben Person";
        identityReferenceSectionHintEl.textContent = "Sonderpfad mit Referenzbild, getrennt vom Hauptweg";
        identityReferenceCardTitleEl.textContent = "Referenzbild";
        identityReferenceCardCopyEl.textContent = "Hier liegt nur das Referenzbild fuer diesen getrennten Sonderpfad.";
        identityRunCardTitleEl.textContent = "Start und Ergebnis";
        identityRunCardCopyEl.textContent = "Nur dieser Start nutzt den getrennten Referenz-Sonderpfad.";
        uploadIdentityReferenceEl.textContent = "Referenz hochladen";
        resetIdentityReferenceEl.textContent = "Referenz zuruecksetzen";
        identityGenerateEl.textContent = "Sonderpfad starten";
        identitySingleStyleSwitchEl.hidden = true;
        identityReferenceMetaEl.hidden = false;
        identityReferenceHintEl.hidden = false;
        identityRunHintEl.hidden = false;
        setGuidedTaskNote(identityReferenceBasicGuideEl, null, null, false);
        return;
      }

      const styleConfig = getCurrentIdentitySingleImageStyleConfig();
      sectionIdentityReferenceEl.classList.add("basic-surface", "basic-surface-work");
      identityReferenceSectionTitleEl.textContent = "Sonderpfad: Neue Szene mit derselben Person";
      identityReferenceSectionHintEl.textContent = "Aktuell nicht verlaesslich freigegeben. Gleiche Person in neuer Szene oder Pose ist auf diesem lokalen Stand noch nicht stabil genug.";
      identityReferenceCardTitleEl.textContent = "Referenzbild";
      identityReferenceCardCopyEl.textContent = "Lade ein Bild derselben Person hoch, wenn du den Referenz-Sonderpfad trotzdem pruefen willst.";
      identityRunCardTitleEl.textContent = "Sonderpfad-Lauf";
      identityRunCardCopyEl.textContent = currentIdentitySingleImageStyle === "anime"
        ? "Anime ist aktiv. Der Lauf ist aktuell nur als Sonderpfad verfuegbar und stilisiert die Person oft zu frei. Keine verlaessliche gleiche-Person-Erwartung."
        : "Foto ist aktiv. Der Lauf ist aktuell nur als Sonderpfad verfuegbar und haelt dieselbe Person in neuer Szene noch nicht verlaesslich genug.";
      uploadIdentityReferenceEl.textContent = "Referenzbild laden";
      resetIdentityReferenceEl.textContent = "Referenzbild entfernen";
      identityGenerateEl.textContent = "Sonderpfad starten";
      identitySingleStyleSwitchEl.hidden = false;
      identitySingleStyleHintEl.textContent = currentIdentitySingleImageStyle === "anime"
        ? "Anime bleibt aktuell ein Sonderpfad und ist inhaltlich noch nicht verlaesslich."
        : "Foto bleibt aktuell ein Sonderpfad und haelt dieselbe Person noch nicht stabil genug.";
      identitySingleStylePhotoEl.classList.toggle("active", currentIdentitySingleImageStyle === "photo");
      identitySingleStyleAnimeEl.classList.toggle("active", currentIdentitySingleImageStyle === "anime");
      identityReferenceMetaEl.hidden = true;
      setGuidedTaskNote(
        identityReferenceBasicGuideEl,
        "Sonderpfad und noch nicht freigegeben",
        "Auf diesem lokalen Stand laufen Foto und Anime technisch, aber dieselbe Person in neuer Szene ist noch nicht verlaesslich genug. Nutze den Pfad nur zum Testen, nicht als belastbaren Hauptmodus.",
        true
      );
    }

    function renderV7IdentityMultiSectionUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;
      if (!basicMode || taskId !== "identity-multi") {
        sectionIdentityMultiReferenceEl.classList.remove("basic-surface", "basic-surface-work");
        identityMultiSectionTitleEl.textContent = "Mehrere Referenzbilder derselben Person";
        identityMultiSectionHintEl.textContent = "Sonderpfad mit mehreren Referenzbildern, getrennt vom Hauptweg";
        multiReferenceCardTitleEl.textContent = "Referenzslots und Eingabe";
        multiReferenceCardCopyEl.textContent = "Bis zu drei Referenzbilder bleiben nur in diesem getrennten Sonderpfad.";
        multiReferenceSlotSelectLabelEl.textContent = "Zielslot";
        multiReferenceSlotSelectEl.options[0].textContent = "Auto (erster freier Slot)";
        multiReferenceSlotSelectEl.options[1].textContent = "Slot 1 ersetzen";
        multiReferenceSlotSelectEl.options[2].textContent = "Slot 2 ersetzen";
        multiReferenceSlotSelectEl.options[3].textContent = "Slot 3 ersetzen";
        uploadMultiReferenceEl.textContent = "Referenz speichern";
        resetAllMultiReferenceEl.textContent = "Alle Slots leeren";
        multiReferenceRunCardTitleEl.textContent = "Start und Ergebnis";
        multiReferenceRunCardCopyEl.textContent = "Nur dieser Start nutzt die belegten Referenzslots im getrennten Sonderpfad.";
        multiReferenceRunOutputCopyEl.textContent = "Ergebnis oder Fehler dieses Testpfads.";
        multiReferenceGenerateEl.textContent = "Sonderpfad starten";
        resetMultiReferenceSlotEls[1].textContent = "Slot 1 leeren";
        resetMultiReferenceSlotEls[2].textContent = "Slot 2 leeren";
        resetMultiReferenceSlotEls[3].textContent = "Slot 3 leeren";
        multiReferenceSlotMetaEls[1].hidden = false;
        multiReferenceSlotMetaEls[2].hidden = false;
        multiReferenceSlotMetaEls[3].hidden = false;
        setGuidedTaskNote(identityMultiBasicGuideEl, null, null, false);
        return;
      }

      sectionIdentityMultiReferenceEl.classList.add("basic-surface", "basic-surface-work");
      identityMultiSectionTitleEl.textContent = "Mehrere Referenzbilder nutzen";
      identityMultiSectionHintEl.textContent = "Lade zwei oder drei Bilder derselben Person und beschreibe danach die neue Variante.";
      multiReferenceCardTitleEl.textContent = "Referenzbilder";
      multiReferenceCardCopyEl.textContent = "Lade bis zu drei Bilder derselben Person hoch. Die Reihenfolge bleibt fuer diese Aufgabe stabil.";
      multiReferenceSlotSelectLabelEl.textContent = "Ablage";
      multiReferenceSlotSelectEl.options[0].textContent = "Automatisch (freier Platz)";
      multiReferenceSlotSelectEl.options[1].textContent = "Slot 1 ersetzen";
      multiReferenceSlotSelectEl.options[2].textContent = "Slot 2 ersetzen";
      multiReferenceSlotSelectEl.options[3].textContent = "Slot 3 ersetzen";
      uploadMultiReferenceEl.textContent = "Referenzbild laden";
      resetAllMultiReferenceEl.textContent = "Alle Referenzbilder entfernen";
      multiReferenceRunCardTitleEl.textContent = "Neue Variante";
      multiReferenceRunCardCopyEl.textContent = "Beschreibe jetzt die neue Variante derselben Person und starte dann die Erstellung.";
      multiReferenceRunOutputCopyEl.textContent = "Dein Ergebnis erscheint nach der Erstellung direkt hier.";
      multiReferenceGenerateEl.textContent = "Bild erstellen";
      resetMultiReferenceSlotEls[1].textContent = "Bild entfernen";
      resetMultiReferenceSlotEls[2].textContent = "Bild entfernen";
      resetMultiReferenceSlotEls[3].textContent = "Bild entfernen";
      multiReferenceSlotMetaEls[1].hidden = true;
      multiReferenceSlotMetaEls[2].hidden = true;
      multiReferenceSlotMetaEls[3].hidden = true;
      setGuidedTaskNote(
        identityMultiBasicGuideEl,
        "1. Referenzen laden, 2. Variante beschreiben",
        "Du brauchst mindestens zwei Referenzbilder derselben Person. Technische Multi-Referenzpfad-Details bleiben im Expertenbereich.",
        true
      );
    }

    function renderV7IdentityTransferSectionUi() {
      const basicMode = isV7BasicModeActive();
      const taskId = getCurrentV7TaskConfig().id;
      if (!basicMode || taskId !== "identity-transfer") {
        sectionIdentityTransferEl.classList.remove("basic-surface", "basic-surface-work");
        identityTransferSectionTitleEl.textContent = "Kopf/Gesicht auf Zielbild uebertragen";
        identityTransferSectionHintEl.textContent = "Sonderpfad fuer Transfer mit Standardlauf und optionalem Masken-Hybrid";
        identityTransferRolesSectionTitleEl.textContent = "Eingaben und Rollen";
        identityTransferRolesSectionHintEl.textContent = "Pflichtbilder fuer den Standardlauf, Transfer-Maske nur fuer den getrennten Masken-Hybrid-Spezialpfad";
        identityTransferTestSectionTitleEl.textContent = "Start und Ergebnis";
        identityTransferTestSectionHintEl.textContent = "Startpunkte bleiben getrennt: Standardlauf fuer den Normalfall, Masken-Hybrid nur als Spezialfall.";
        identityTransferStatusCardTitleEl.textContent = "Verfuegbarkeit und Rollen";
        identityTransferRunCardTitleEl.textContent = "Start und Ergebnis";
        identityTransferRunCardCopyEl.textContent = "Ergebnis oder Fehler des gestarteten Testpfads.";
        resetAllIdentityTransferEl.textContent = "Alle Rollen leeren";
        identityTransferGenerateEl.textContent = "Standardlauf starten";
        identityTransferMaskHybridGenerateEl.textContent = "Masken-Hybrid testen";
        identityTransferMaskHybridGenerateEl.hidden = false;
        identityTransferMaskHybridScopeEl.hidden = false;
        identityTransferMaskHybridLimitsEl.hidden = false;
        for (const config of IDENTITY_TRANSFER_ROLE_CONFIG) {
          const roleView = identityTransferRoleViews[config.role];
          roleView.uploadEl.textContent = "Bild speichern";
          roleView.resetEl.textContent = "Rolle leeren";
          roleView.metaEl.hidden = false;
        }
        setGuidedTaskNote(identityTransferRolesBasicGuideEl, null, null, false);
        setGuidedTaskNote(identityTransferTestBasicGuideEl, null, null, false);
        return;
      }

      sectionIdentityTransferEl.classList.add("basic-surface", "basic-surface-work");
      identityTransferSectionTitleEl.textContent = "Kopf/Gesicht auf Zielbild uebertragen";
      identityTransferSectionHintEl.textContent = "Lade Kopf-Referenzbild und Zielbild. Pose und Maske bleiben optional.";
      identityTransferRolesSectionTitleEl.textContent = "Kopf/Gesicht und Zielbild";
      identityTransferRolesSectionHintEl.textContent = "Pflicht sind Kopf-Referenzbild plus Zielbild. Pose und Transfer-Maske bleiben optional.";
      identityTransferTestSectionTitleEl.textContent = "Kopf/Gesicht auf Zielbild uebertragen";
      identityTransferTestSectionHintEl.textContent = "Der stabile Pfad nutzt aktuell Kopf/Gesicht plus Zielbild. Optionale Rollen bleiben nur zusaetzlich.";
      identityTransferStatusCardTitleEl.textContent = "Bereit fuer den Start";
      identityTransferRunCardTitleEl.textContent = "Ergebnis erstellen";
      identityTransferRunCardCopyEl.textContent = "Dein Ergebnis erscheint nach der Erstellung direkt hier.";
      resetAllIdentityTransferEl.textContent = "Alle Bilder entfernen";
      identityTransferGenerateEl.textContent = "Bild erstellen";
      identityTransferMaskHybridGenerateEl.hidden = true;
      identityTransferMaskHybridScopeEl.hidden = true;
      identityTransferMaskHybridLimitsEl.hidden = true;
      for (const config of IDENTITY_TRANSFER_ROLE_CONFIG) {
        const roleView = identityTransferRoleViews[config.role];
        roleView.uploadEl.textContent = "Bild laden";
        roleView.resetEl.textContent = "Bild entfernen";
        roleView.metaEl.hidden = true;
      }
      setGuidedTaskNote(
        identityTransferRolesBasicGuideEl,
        "1. Pflichtbilder laden",
        "Lade zuerst Kopf-Referenzbild und Zielbild. Pose und Transfer-Maske sind nur Zusatzmaterial.",
        true
      );
      setGuidedTaskNote(
        identityTransferTestBasicGuideEl,
        "2. Ergebnis beschreiben",
        "Beschreibe danach kurz die gewuenschte Uebertragung. Optionale Rollen bleiben im stabilen Stand nur zusaetzlich.",
        true
      );
    }

    function renderV7BasicTaskUi() {
      renderV7BasicTaskFocusUi();
      renderV7GenerateSectionUi();
      renderV7TextServiceBasicUi();
      renderV7InputSectionUi();
      renderV7IdentityReferenceSectionUi();
      renderV7IdentityMultiSectionUi();
      renderV7IdentityTransferSectionUi();
    }

    function renderV7NavigationUi() {
      const taskConfig = getCurrentV7TaskConfig();
      const expertModeActive = currentV7ViewMode === "expert";
      document.body.classList.toggle("v9-basic-mode", !expertModeActive);
      document.body.classList.toggle("v9-expert-mode", expertModeActive);
      guidedModeBasicEl.classList.toggle("active", !expertModeActive);
      guidedModeExpertEl.classList.toggle("active", expertModeActive);
      guidedModeStateEl.textContent = expertModeActive
        ? "Erweitert | Sonderpfade und Tests sind sichtbar."
        : `Basismodus | ${taskConfig.label} als Hauptpfad`;
      guidedTaskHintEl.textContent = expertModeActive
        ? "Hier bleiben Personen-/Szenen-Sonderpfade, technische Tests und Spezialstarts bewusst getrennt vom Basismodus erreichbar."
        : taskConfig.hint;
      guidedTaskHintEl.className = "request-state";
      V7_TASK_CONFIG.forEach((config) => {
        const button = guidedTaskButtonEls[config.id];
        if (!button) {
          return;
        }
        button.classList.toggle("active", config.id === taskConfig.id);
      });
      applyV7SectionVisibility();
      renderV7BasicTaskUi();
    }

    function setV7ViewMode(mode) {
      const normalizedMode = normalizeV7ViewMode(mode);
      if (currentV7ViewMode === normalizedMode) {
        return;
      }
      currentV7ViewMode = normalizedMode;
      persistV7NavigationState();
      renderUi();
    }

    function setV7BasicTask(taskId) {
      const normalizedTask = normalizeV7BasicTask(taskId);
      persistBasicTaskNegativePromptDraft(currentV7BasicTask);
      if (currentV7BasicTask === normalizedTask) {
        if (currentV7ViewMode !== "basic") {
          currentV7ViewMode = "basic";
          persistV7NavigationState();
          renderUi();
        }
        return;
      }
      currentV7BasicTask = normalizedTask;
      currentV7ViewMode = "basic";
      persistV7NavigationState();
      renderUi();
    }

    function setBasicImageStyle(styleId) {
      const normalizedStyle = normalizeBasicImageStyle(styleId);
      if (currentBasicImageStyle === normalizedStyle) {
        return;
      }
      currentBasicImageStyle = normalizedStyle;
      persistV7NavigationState();
      renderUi();
    }

    function setIdentitySingleImageStyle(styleId) {
      const normalizedStyle = normalizeBasicImageStyle(styleId);
      if (currentIdentitySingleImageStyle === normalizedStyle) {
        return;
      }
      currentIdentitySingleImageStyle = normalizedStyle;
      persistV7NavigationState();
      renderUi();
    }

    function buildRequestNotice(payload, level = "info") {
      if (!payload || typeof payload !== "object") {
        return null;
      }

      if (level === "info") {
        return {
          level,
          code: payload.code ?? null,
          message: payload.message ?? null,
          request_id: payload.request_id ?? null,
          mode: payload.mode ?? null,
          created_at_utc: payload.created_at_utc ?? null
        };
      }

      return {
        level,
        ...compactResult(payload)
      };
    }

    function persist_last_success(result) {
      if (!result || result.status !== "ok" || !result.output_file) {
        return;
      }

      writeStorageJson(LAST_SUCCESS_STORAGE_KEY, {
        status: "ok",
        mode: result.mode ?? null,
        output_file: result.output_file,
        prompt_id: result.prompt_id ?? null,
        request_id: result.request_id ?? null,
        saved_at_utc: new Date().toISOString()
      });
    }

    function load_last_success() {
      const payload = readStorageJson(LAST_SUCCESS_STORAGE_KEY);
      if (!payload || typeof payload.output_file !== "string" || !payload.output_file.trim()) {
        clear_last_success();
        return null;
      }

      return {
        status: "ok",
        mode: payload.mode ?? null,
        output_file: payload.output_file.trim(),
        error_type: null,
        blocker: null,
        prompt_id: payload.prompt_id ?? null,
        request_id: payload.request_id ?? null,
        saved_at_utc: payload.saved_at_utc ?? null,
        restored_from_storage: true
      };
    }

    function clear_last_success() {
      removeStorageItem(LAST_SUCCESS_STORAGE_KEY);
    }

    function normalizeResultItem(payload) {
      if (!payload || typeof payload !== "object") {
        return null;
      }

      if (
        !isNonEmptyString(payload.result_id) ||
        !isNonEmptyString(payload.file_name) ||
        !isNonEmptyString(payload.preview_url) ||
        !isNonEmptyString(payload.download_url)
      ) {
        return null;
      }

      return {
        result_id: payload.result_id.trim(),
        created_at: isNonEmptyString(payload.created_at) ? payload.created_at.trim() : null,
        mode: isNonEmptyString(payload.mode) ? payload.mode.trim() : "txt2img",
        prompt: isNonEmptyString(payload.prompt) ? payload.prompt.trim() : "",
        negative_prompt: isNonEmptyString(payload.negative_prompt) ? payload.negative_prompt.trim() : null,
        checkpoint: isNonEmptyString(payload.checkpoint) ? payload.checkpoint.trim() : null,
        width: Number.isFinite(payload.width) ? Number(payload.width) : null,
        height: Number.isFinite(payload.height) ? Number(payload.height) : null,
        size_bytes: Number.isFinite(payload.size_bytes) ? Number(payload.size_bytes) : null,
        file_name: payload.file_name.trim(),
        preview_url: payload.preview_url.trim(),
        download_url: payload.download_url.trim(),
        reference_count: Number.isFinite(payload.reference_count) ? Number(payload.reference_count) : null,
        reference_slots: Array.isArray(payload.reference_slots)
          ? payload.reference_slots.filter((value) => Number.isFinite(value)).map((value) => Number(value))
          : null,
        reference_image_ids: Array.isArray(payload.reference_image_ids)
          ? payload.reference_image_ids.filter((value) => isNonEmptyString(value)).map((value) => value.trim())
          : null,
        multi_reference_strategy: isNonEmptyString(payload.multi_reference_strategy) ? payload.multi_reference_strategy.trim() : null,
        used_roles: Array.isArray(payload.used_roles)
          ? payload.used_roles.filter((value) => isNonEmptyString(value)).map((value) => value.trim())
          : [],
        pose_reference_present: typeof payload.pose_reference_present === "boolean" ? payload.pose_reference_present : null,
        pose_reference_used: typeof payload.pose_reference_used === "boolean" ? payload.pose_reference_used : null,
        transfer_mask_present: typeof payload.transfer_mask_present === "boolean" ? payload.transfer_mask_present : null,
        transfer_mask_used: typeof payload.transfer_mask_used === "boolean" ? payload.transfer_mask_used : null,
        identity_head_reference_image_id: isNonEmptyString(payload.identity_head_reference_image_id) ? payload.identity_head_reference_image_id.trim() : null,
        target_body_image_id: isNonEmptyString(payload.target_body_image_id) ? payload.target_body_image_id.trim() : null,
        pose_reference_image_id: isNonEmptyString(payload.pose_reference_image_id) ? payload.pose_reference_image_id.trim() : null,
        transfer_mask_image_id: isNonEmptyString(payload.transfer_mask_image_id) ? payload.transfer_mask_image_id.trim() : null,
        identity_transfer_strategy: isNonEmptyString(payload.identity_transfer_strategy) ? payload.identity_transfer_strategy.trim() : null,
        store_scope: isNonEmptyString(payload.store_scope) ? payload.store_scope.trim() : "app_results",
        cleanup_policy: isNonEmptyString(payload.cleanup_policy) ? payload.cleanup_policy.trim() : "retention_limit",
        retention_limit: Number.isFinite(payload.retention_limit) ? Number(payload.retention_limit) : null,
        source_output_file: isNonEmptyString(payload.source_output_file) ? payload.source_output_file.trim() : null
      };
    }

    function normalizeResultsStorage(payload) {
      if (!payload || typeof payload !== "object") {
        return null;
      }

      return {
        results_scope: isNonEmptyString(payload.results_scope) ? payload.results_scope.trim() : "app_results_managed",
        results_dir: isNonEmptyString(payload.results_dir) ? payload.results_dir.trim() : "data/results",
        results_count: Number.isFinite(payload.results_count) ? Math.max(0, Math.trunc(Number(payload.results_count))) : 0,
        retention_limit: Number.isFinite(payload.retention_limit) ? Math.max(1, Math.trunc(Number(payload.retention_limit))) : 50,
        cleanup_scope: isNonEmptyString(payload.cleanup_scope) ? payload.cleanup_scope.trim() : "results_only",
        exports_scope: isNonEmptyString(payload.exports_scope) ? payload.exports_scope.trim() : "user_exports",
        exports_dir: isNonEmptyString(payload.exports_dir) ? payload.exports_dir.trim() : "data/exports",
        exports_count: Number.isFinite(payload.exports_count) ? Math.max(0, Math.trunc(Number(payload.exports_count))) : 0,
        exports_dir_accessible: payload.exports_dir_accessible === true,
        exports_dir_error: isNonEmptyString(payload.exports_dir_error) ? payload.exports_dir_error.trim() : null
      };
    }

    function formatResultCreatedAt(value) {
      if (!isNonEmptyString(value)) {
        return "unbekannt";
      }

      const candidate = new Date(value);
      if (Number.isNaN(candidate.getTime())) {
        return value.trim();
      }

      try {
        return candidate.toLocaleString("de-DE", {
          dateStyle: "short",
          timeStyle: "short"
        });
      } catch (error) {
        return candidate.toISOString();
      }
    }

    function formatResultModeLabel(mode) {
      const normalized = isNonEmptyString(mode) ? mode.trim().toLowerCase() : "";
      const labels = {
        txt2img: "Neues Bild erstellen",
        img2img: "Bild anpassen",
        inpainting: "Bereich im Bild aendern",
        identity_reference: "Sonderpfad: Neue Szene mit derselben Person",
        identity_multi_reference: "Sonderpfad: Mehrere Referenzbilder derselben Person",
        identity_transfer: "Sonderpfad: Kopf/Gesicht auf Zielbild uebertragen",
        identity_transfer_mask_hybrid: "Sonderpfad: Masken-Hybrid",
        placeholder: "Platzhalter-Testbild",
        sdxl: "SDXL"
      };
      return labels[normalized] || (isNonEmptyString(mode) ? mode.trim() : "Unbekannter Pfad");
    }

    function formatResultCheckpointAlias(value) {
      if (!isNonEmptyString(value)) {
        return null;
      }

      const normalized = value.trim().toLowerCase();
      if (normalized === BASIC_IMAGE_STYLE_CONFIG.photo.checkpoint_mode) {
        return "Foto";
      }
      if (normalized === BASIC_IMAGE_STYLE_CONFIG.anime.checkpoint_mode) {
        return "Anime";
      }
      return value.trim();
    }

    function formatBytes(value) {
      if (!Number.isFinite(value) || value < 0) {
        return null;
      }

      const units = ["B", "KB", "MB", "GB"];
      let unitIndex = 0;
      let current = Number(value);
      while (current >= 1024 && unitIndex < units.length - 1) {
        current /= 1024;
        unitIndex += 1;
      }

      const precision = current >= 100 || unitIndex === 0
        ? 0
        : (current >= 10 ? 1 : 2);
      return `${current.toFixed(precision)} ${units[unitIndex]}`;
    }

    function mapIdentityTransferRoleLabel(role) {
      const labels = {
        identity_head_reference: "Kopf",
        target_body_image: "Zielbild",
        pose_reference: "Pose",
        transfer_mask: "Maske"
      };
      return labels[role] || role;
    }

    function truncateText(value, maxLength = 160) {
      if (!isNonEmptyString(value)) {
        return "";
      }
      const normalized = value.trim();
      return normalized.length > maxLength
        ? `${normalized.slice(0, maxLength - 3)}...`
        : normalized;
    }

    function appendResultMetaLine(container, label, value) {
      if (!container || !isNonEmptyString(label) || !isNonEmptyString(value)) {
        return;
      }

      const rowEl = document.createElement("div");
      rowEl.className = "result-card-meta-line";

      const labelEl = document.createElement("span");
      labelEl.className = "result-card-meta-label";
      labelEl.textContent = `${label.trim()}:`;

      const valueEl = document.createElement("span");
      valueEl.textContent = value.trim();
      rowEl.append(labelEl, valueEl);
      container.appendChild(rowEl);
    }

    function appendResultCopyableTextLine(container, label, value) {
      if (!container || !isNonEmptyString(label) || !isNonEmptyString(value)) {
        return;
      }

      const normalizedValue = value.trim();
      const rowEl = document.createElement("div");
      rowEl.className = "result-card-meta-rich";

      const headEl = document.createElement("div");
      headEl.className = "result-card-meta-rich-head";

      const labelEl = document.createElement("span");
      labelEl.className = "result-card-meta-label";
      labelEl.textContent = `${label.trim()}:`;

      const copyButtonEl = document.createElement("button");
      copyButtonEl.type = "button";
      copyButtonEl.className = "result-card-copy-button";
      copyButtonEl.textContent = "Kopieren";
      copyButtonEl.addEventListener("click", async () => {
        const copied = await writeTextToClipboard(normalizedValue);
        copyButtonEl.textContent = copied ? "Kopiert" : "Fehler";
        window.setTimeout(() => {
          copyButtonEl.textContent = "Kopieren";
        }, 1400);
      });

      const textEl = document.createElement("div");
      textEl.className = "result-card-meta-text";
      textEl.textContent = normalizedValue;

      headEl.append(labelEl, copyButtonEl);
      rowEl.append(headEl, textEl);
      container.appendChild(rowEl);
    }

    function getResultsPreviewIndex(items = resultsState.items, resultId = resultsPreviewState.result_id) {
      if (!Array.isArray(items) || items.length === 0 || !isNonEmptyString(resultId)) {
        return -1;
      }
      const normalizedResultId = resultId.trim();
      return items.findIndex((item) => item?.result_id === normalizedResultId);
    }

    function getResultsPreviewNeighbor(step, items = resultsState.items) {
      if (!Array.isArray(items) || items.length === 0 || !Number.isFinite(step) || step === 0) {
        return null;
      }

      const currentIndex = getResultsPreviewIndex(items);
      if (currentIndex < 0) {
        return null;
      }

      const nextIndex = currentIndex + Math.sign(step);
      if (nextIndex < 0 || nextIndex >= items.length) {
        return null;
      }
      return items[nextIndex] || null;
    }

    function openAdjacentResultsPreview(step) {
      const neighbor = getResultsPreviewNeighbor(step);
      if (!neighbor) {
        return false;
      }
      openResultsPreview(neighbor);
      return true;
    }

    function getMimeTypeForFileName(fileName) {
      if (!isNonEmptyString(fileName)) {
        return "image/png";
      }
      const normalized = fileName.trim().toLowerCase();
      if (normalized.endsWith(".jpg") || normalized.endsWith(".jpeg")) {
        return "image/jpeg";
      }
      if (normalized.endsWith(".webp")) {
        return "image/webp";
      }
      return "image/png";
    }

    async function downloadResultAsFile(item) {
      if (!item || !isNonEmptyString(item.download_url)) {
        return {
          ok: false,
          blocker: "result_download_url_missing",
          file: null,
          file_name: null
        };
      }

      const fileName = isNonEmptyString(item.file_name)
        ? item.file_name.trim()
        : `result-${item.result_id || Date.now()}.png`;
      try {
        const response = await fetch(item.download_url.trim(), { cache: "no-store" });
        if (!response.ok) {
          return {
            ok: false,
            blocker: `result_download_http_${response.status}`,
            file: null,
            file_name: fileName
          };
        }

        const blob = await response.blob();
        const mimeType = isNonEmptyString(blob.type) ? blob.type : getMimeTypeForFileName(fileName);
        const file = new File([blob], fileName, {
          type: mimeType,
          lastModified: Date.now()
        });
        return {
          ok: true,
          blocker: null,
          file,
          file_name: fileName
        };
      } catch (error) {
        return {
          ok: false,
          blocker: "result_download_request_failed",
          file: null,
          file_name: fileName
        };
      }
    }

    async function loadResultAsInputImage(resultId, options = {}) {
      const normalizedResultId = isNonEmptyString(resultId) ? resultId.trim() : "";
      if (!normalizedResultId) {
        return false;
      }

      if (currentUpload) {
        setTransientInfoNotice({
          code: "input_upload_running",
          message: "Bild-Upload laeuft noch. Bitte kurz warten."
        });
        renderUi();
        return false;
      }

      const fallbackItem = options.item && typeof options.item === "object"
        ? normalizeResultItem(options.item)
        : null;
      const item = findResultItemById(normalizedResultId) || fallbackItem;
      if (!item) {
        setTransientClientPrecheckError("invalid_request", "invalid_result_id", {
          message: "Ergebnis nicht gefunden."
        });
        renderUi();
        return false;
      }

      const download = await downloadResultAsFile(item);
      if (!download.ok || !(download.file instanceof File)) {
        const blocker = isNonEmptyString(download.blocker) ? download.blocker.trim() : "result_download_failed";
        setInputUploadNotice("error", formatResultActionMessage(blocker, "Das Ergebnis konnte nicht als Eingabebild geladen werden."), {
          source_type: "file",
          error_type: "upload_error",
          blocker
        });
        renderUi();
        return false;
      }

      const uploaded = await submitInputImage(download.file, "file");
      if (!uploaded) {
        return false;
      }

      if (isV7BasicModeActive()) {
        const currentTaskId = getCurrentV7TaskConfig().id;
        if (currentTaskId !== "edit" && currentTaskId !== "inpaint") {
          setV7BasicTask("edit");
        }
      }

      if (options.closePreview === true) {
        closeResultsPreview();
      }

      setTransientInfoNotice({
        code: "result_loaded_as_input",
        message: `Als Eingabebild geladen | ${download.file_name || normalizedResultId}. Bild anpassen ist jetzt aktiv.`
      });
      renderUi();
      return true;
    }

    function closeResultsPreview() {
      if (!resultsPreviewState.open) {
        return;
      }

      resultsPreviewState = {
        open: false,
        result_id: null,
        mode: null,
        file_name: null,
        created_at: null,
        width: null,
        height: null,
        preview_url: null,
        download_url: null
      };
      renderResultsPreview();
    }

    function openResultsPreview(item) {
      if (!item || !isNonEmptyString(item.preview_url) || !isNonEmptyString(item.download_url)) {
        return;
      }

      resultsPreviewState = {
        open: true,
        result_id: item.result_id,
        mode: item.mode,
        file_name: item.file_name,
        created_at: item.created_at,
        width: item.width,
        height: item.height,
        preview_url: item.preview_url,
        download_url: item.download_url
      };
      renderResultsPreview();
    }

    function renderResultsPreview() {
      if (!resultsPreviewModalEl || !resultsPreviewImageEl || !resultsPreviewTitleEl || !resultsPreviewMetaEl || !resultsPreviewDownloadEl) {
        return;
      }

      const state = resultsPreviewState;
      const isOpen = state.open === true && isNonEmptyString(state.preview_url);
      const items = Array.isArray(resultsState.items) ? resultsState.items : [];
      const previewIndex = getResultsPreviewIndex(items, state.result_id);
      const activeItem = previewIndex >= 0
        ? items[previewIndex]
        : (isNonEmptyString(state.result_id) ? findResultItemById(state.result_id) : null);
      document.body.classList.toggle("results-preview-open", isOpen);

      if (!isOpen) {
        resultsPreviewModalEl.hidden = true;
        resultsPreviewImageEl.removeAttribute("src");
        resultsPreviewTitleEl.textContent = "Ergebnisvorschau";
        resultsPreviewMetaEl.textContent = "";
        resultsPreviewDownloadEl.href = "#";
        resultsPreviewDownloadEl.download = "";
        if (resultsPreviewLoadInputEl) {
          resultsPreviewLoadInputEl.disabled = true;
          resultsPreviewLoadInputEl.textContent = "Als Eingabebild laden";
        }
        if (resultsPreviewDeleteEl) {
          resultsPreviewDeleteEl.disabled = true;
          resultsPreviewDeleteEl.textContent = "Loeschen";
        }
        if (resultsPreviewPrevEl) {
          resultsPreviewPrevEl.disabled = true;
        }
        if (resultsPreviewNextEl) {
          resultsPreviewNextEl.disabled = true;
        }
        return;
      }

      const modeLabel = formatResultModeLabel(state.mode);
      const dimensionText = Number.isFinite(state.width) && Number.isFinite(state.height)
        ? `${state.width}x${state.height}`
        : null;
      const timeText = formatResultCreatedAt(state.created_at);
      const metaParts = [`Pfad: ${modeLabel}`, `Zeit: ${timeText}`];
      if (previewIndex >= 0 && items.length > 0) {
        metaParts.unshift(`Bild ${previewIndex + 1} von ${items.length}`);
      }
      if (dimensionText) {
        metaParts.push(`Bild: ${dimensionText}`);
      }
      resultsPreviewTitleEl.textContent = isNonEmptyString(state.file_name)
        ? `${modeLabel} | ${state.file_name}`
        : modeLabel;
      resultsPreviewMetaEl.textContent = metaParts.join(" | ");
      resultsPreviewImageEl.src = state.preview_url.trim();
      resultsPreviewDownloadEl.href = state.download_url.trim();
      resultsPreviewDownloadEl.download = isNonEmptyString(state.file_name) ? state.file_name.trim() : "";
      resultsPreviewModalEl.hidden = false;
      if (resultsPreviewLoadInputEl) {
        resultsPreviewLoadInputEl.disabled = !(activeItem && isNonEmptyString(activeItem.result_id)) || Boolean(currentUpload);
        resultsPreviewLoadInputEl.textContent = currentUpload ? "Bild wird geladen..." : "Als Eingabebild laden";
      }
      if (resultsPreviewDeleteEl) {
        const deleteBusy = resultsDeleteState.phase === "running";
        const canDelete = Boolean(activeItem && isNonEmptyString(activeItem.result_id) && isAppManagedResultItem(activeItem));
        const isDeletingCurrent = deleteBusy && resultsDeleteState.result_id === state.result_id;
        resultsPreviewDeleteEl.disabled = !canDelete || deleteBusy;
        resultsPreviewDeleteEl.textContent = isDeletingCurrent ? "Loesche..." : "Loeschen";
        resultsPreviewDeleteEl.title = canDelete ? "" : "Nur App-Ergebnisse aus data/results sind loeschbar";
      }
      if (resultsPreviewPrevEl) {
        const hasPrev = previewIndex > 0;
        resultsPreviewPrevEl.disabled = !hasPrev;
        resultsPreviewPrevEl.title = hasPrev ? "" : "Kein vorheriges Bild";
      }
      if (resultsPreviewNextEl) {
        const hasNext = previewIndex >= 0 && previewIndex + 1 < items.length;
        resultsPreviewNextEl.disabled = !hasNext;
        resultsPreviewNextEl.title = hasNext ? "" : "Kein naechstes Bild";
      }
    }

    function renderResultsExportState() {
      if (!resultsExportStateEl) {
        return;
      }

      const state = resultsExportState;
      resultsExportStateEl.className = state.phase === "error" ? "request-state error" : "request-state";
      resultsExportStateEl.replaceChildren();

      const text = isNonEmptyString(state.text)
        ? state.text.trim()
        : "Optional: Ergebnis im Exportordner sichern.";
      resultsExportStateEl.appendChild(document.createTextNode(text));

      if (state.phase === "success" && isNonEmptyString(state.export_url)) {
        const linkEl = document.createElement("a");
        linkEl.href = state.export_url.trim();
        linkEl.download = isNonEmptyString(state.export_file_name) ? state.export_file_name.trim() : "";
        linkEl.textContent = "Export herunterladen";
        resultsExportStateEl.appendChild(document.createTextNode(" "));
        resultsExportStateEl.appendChild(linkEl);
      }
    }

    function isAppManagedResultItem(item) {
      if (!item || typeof item !== "object") {
        return false;
      }
      return String(item.store_scope || "").trim().toLowerCase() === "app_results";
    }

    function renderResultsDeleteState() {
      if (!resultsDeleteStateEl) {
        return;
      }

      const state = resultsDeleteState;
      resultsDeleteStateEl.className = state.phase === "error" ? "request-state error" : "request-state";
      const text = isNonEmptyString(state.text)
        ? state.text.trim()
        : "Optional: Ergebnis aus dem Haupt-Output entfernen.";
      resultsDeleteStateEl.textContent = text;
    }

    async function requestResultDelete(resultId, options = {}) {
      const normalizedResultId = isNonEmptyString(resultId) ? resultId.trim() : "";
      if (!normalizedResultId) {
        resultsDeleteState = {
          phase: "error",
          text: formatResultActionMessage("invalid_result_id", "Loeschen fehlgeschlagen."),
          result_id: null,
          blocker: "invalid_result_id"
        };
        renderUi();
        return { ok: false, blocker: "invalid_result_id" };
      }

      const item = findResultItemById(normalizedResultId);
      if (!item) {
        resultsDeleteState = {
          phase: "error",
          text: formatResultActionMessage("result_not_found", "Loeschen fehlgeschlagen."),
          result_id: normalizedResultId,
          blocker: "result_not_found"
        };
        renderUi();
        return { ok: false, blocker: "result_not_found" };
      }

      if (!isAppManagedResultItem(item)) {
        resultsDeleteState = {
          phase: "error",
          text: formatResultActionMessage("result_delete_forbidden_scope", "Loeschen fehlgeschlagen."),
          result_id: normalizedResultId,
          blocker: "result_delete_forbidden_scope"
        };
        renderUi();
        return { ok: false, blocker: "result_delete_forbidden_scope" };
      }

      if (resultsDeleteState.phase === "running") {
        return { ok: false, blocker: "result_delete_busy" };
      }

      const label = isNonEmptyString(options.fileName)
        ? options.fileName.trim()
        : (isNonEmptyString(item.file_name) ? item.file_name : normalizedResultId);
      const confirmText = [
        `Ergebnis wirklich loeschen?`,
        "",
        `${label}`,
        "",
        "Es wird nur aus data/results geloescht.",
        "Nutzer-Exporte in data/exports bleiben erhalten."
      ].join("\n");
      if (!window.confirm(confirmText)) {
        return { ok: false, blocker: "result_delete_cancelled" };
      }

      const token = `result-delete-${String(++resultDeleteCounter).padStart(6, "0")}`;
      activeResultDeleteToken = token;
      resultsDeleteState = {
        phase: "running",
        text: `Ergebnis wird geloescht... | ${label}`,
        result_id: normalizedResultId,
        blocker: null
      };
      renderUi();

      try {
        const response = await fetch("/results/delete", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            result_id: normalizedResultId
          })
        });

        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (activeResultDeleteToken !== token) {
          return { ok: false, blocker: "result_delete_superseded" };
        }

        if (!response.ok || !payload || payload.status !== "ok" || payload.ok !== true) {
          const blocker = isNonEmptyString(payload?.blocker)
            ? payload.blocker.trim()
            : `result_delete_http_${response.status}`;
          resultsDeleteState = {
            phase: "error",
            text: formatResultActionMessage(blocker, "Loeschen fehlgeschlagen."),
            result_id: normalizedResultId,
            blocker
          };
          renderUi();
          return { ok: false, blocker };
        }

        if (isNonEmptyString(resultsPreviewState.result_id) && resultsPreviewState.result_id === normalizedResultId) {
          closeResultsPreview();
        }

        if (resultsExportState.result_id === normalizedResultId && resultsExportState.phase === "success") {
          resultsExportState = {
            phase: "idle",
            text: "Optional: Ergebnis im Exportordner sichern.",
            result_id: null,
            export_url: null,
            export_file_name: null,
            exported_at: null,
            blocker: null
          };
        }

        resultsDeleteState = {
          phase: "success",
          text: `Aus Haupt-Output entfernt | ${label}. Exporte bleiben erhalten.`,
          result_id: normalizedResultId,
          blocker: null
        };
        await fetchResults({ showLoading: false });
        if (isNonEmptyString(sceneState.active_scene_id)) {
          void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
        }
        setTransientInfoNotice({
          code: "result_deleted",
          message: `Aus Haupt-Output entfernt | ${label}. Exporte bleiben erhalten.`
        });
        renderUi();
        return { ok: true, payload };
      } catch (error) {
        if (activeResultDeleteToken !== token) {
          return { ok: false, blocker: "result_delete_superseded" };
        }
        const blocker = "result_delete_request_failed";
        resultsDeleteState = {
          phase: "error",
          text: formatResultActionMessage(blocker, "Loeschen fehlgeschlagen."),
          result_id: normalizedResultId,
          blocker
        };
        renderUi();
        return { ok: false, blocker };
      }
    }

    async function requestResultExport(resultId) {
      const normalizedResultId = isNonEmptyString(resultId) ? resultId.trim() : "";
      if (!normalizedResultId) {
        resultsExportState = {
          phase: "error",
          text: formatResultActionMessage("invalid_result_id", "Export fehlgeschlagen."),
          result_id: null,
          export_url: null,
          export_file_name: null,
          exported_at: null,
          blocker: "invalid_result_id"
        };
        renderUi();
        return { ok: false, blocker: "invalid_result_id" };
      }

      const token = `result-export-${String(++resultExportCounter).padStart(6, "0")}`;
      activeResultExportToken = token;
      resultsExportState = {
        phase: "running",
        text: "Export wird vorbereitet...",
        result_id: normalizedResultId,
        export_url: null,
        export_file_name: null,
        exported_at: null,
        blocker: null
      };
      renderUi();

      try {
        const response = await fetch("/results/export", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            result_id: normalizedResultId
          })
        });

        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (activeResultExportToken !== token) {
          return { ok: false, blocker: "export_superseded" };
        }

        if (!response.ok || !payload || payload.status !== "ok" || !isNonEmptyString(payload.export_url)) {
          const blocker = isNonEmptyString(payload?.blocker)
            ? payload.blocker.trim()
            : `result_export_http_${response.status}`;
          resultsExportState = {
            phase: "error",
            text: formatResultActionMessage(blocker, "Export fehlgeschlagen."),
            result_id: normalizedResultId,
            export_url: null,
            export_file_name: null,
            exported_at: null,
            blocker
          };
          renderUi();
          return { ok: false, blocker };
        }

        const exportedFileName = isNonEmptyString(payload.export_file_name) ? payload.export_file_name.trim() : null;
        resultsExportState = {
          phase: "success",
          text: exportedFileName
            ? `Im Exportordner gespeichert | ${exportedFileName}. Download ist bereit.`
            : "Im Exportordner gespeichert. Download ist bereit.",
          result_id: normalizedResultId,
          export_url: payload.export_url.trim(),
          export_file_name: exportedFileName,
          exported_at: isNonEmptyString(payload.exported_at) ? payload.exported_at.trim() : null,
          blocker: null
        };
        renderUi();
        await fetchResults({ showLoading: false });
        return { ok: true, payload };
      } catch (error) {
        if (activeResultExportToken !== token) {
          return { ok: false, blocker: "export_superseded" };
        }

        const blocker = "result_export_request_failed";
        resultsExportState = {
          phase: "error",
          text: formatResultActionMessage(blocker, "Export fehlgeschlagen."),
          result_id: normalizedResultId,
          export_url: null,
          export_file_name: null,
          exported_at: null,
          blocker
        };
        renderUi();
        return { ok: false, blocker };
      }
    }

    async function fetchResults(options = {}) {
      const limit = Number.isFinite(options.limit) && options.limit > 0
        ? Math.trunc(options.limit)
        : RESULTS_FETCH_LIMIT;
      const showLoading = options.showLoading !== false;
      const fetchToken = `results-fetch-${String(++resultsFetchCounter).padStart(6, "0")}`;
      activeResultsFetchToken = fetchToken;
      resultsState = {
        ...resultsState,
        loading: showLoading,
        error: null
      };
      if (showLoading) {
        renderUi();
      }

      try {
        const response = await fetch(`/results?limit=${encodeURIComponent(String(limit))}`, { cache: "no-store" });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (activeResultsFetchToken !== fetchToken) {
          return null;
        }

        if (!response.ok || !payload || payload.status !== "ok" || !Array.isArray(payload.items)) {
          resultsState = {
            ...resultsState,
            loading: false,
            initialized: true,
            error: {
              error_type: isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "api_error",
              blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `results_http_${response.status}`,
              message: isNonEmptyString(payload?.message) ? payload.message.trim() : "Ergebnisliste nicht verfuegbar."
            }
          };
          renderUi();
          return null;
        }

        resultsState = {
          items: payload.items
            .map((item) => normalizeResultItem(item))
            .filter((item) => item !== null),
          loading: false,
          error: null,
          initialized: true,
          total_count: Number.isFinite(payload.total_count)
            ? Math.max(0, Math.trunc(Number(payload.total_count)))
            : Array.isArray(payload.items)
              ? payload.items.length
              : 0,
          limit: Number.isFinite(payload.limit)
            ? Math.max(1, Math.trunc(Number(payload.limit)))
            : limit,
          storage: normalizeResultsStorage(payload.storage)
        };
        renderUi();
        return resultsState.items;
      } catch (error) {
        if (activeResultsFetchToken !== fetchToken) {
          return null;
        }

        resultsState = {
          ...resultsState,
          loading: false,
          initialized: true,
          error: {
            error_type: "api_error",
            blocker: error instanceof Error ? error.message : String(error),
            message: "Ergebnisliste nicht verfuegbar."
          }
        };
        renderUi();
        return null;
      }
    }

    function renderResultsGallery() {
      const items = Array.isArray(resultsState.items) ? resultsState.items : [];
      if (resultsPreviewState.open && !items.some((item) => item?.result_id === resultsPreviewState.result_id)) {
        closeResultsPreview();
      }
      const hasItems = items.length > 0;
      const totalCount = Number.isFinite(resultsState.total_count)
        ? Math.max(0, Math.trunc(Number(resultsState.total_count)))
        : items.length;
      const effectiveLimit = Number.isFinite(resultsState.limit)
        ? Math.max(1, Math.trunc(Number(resultsState.limit)))
        : RESULTS_FETCH_LIMIT;
      const basicMode = isV7BasicModeActive();
      const storage = resultsState.storage;
      const inputLoadBusy = Boolean(currentUpload);

      if (resultsRefreshEl) {
        resultsRefreshEl.disabled = resultsState.loading || resultsExportState.phase === "running" || resultsDeleteState.phase === "running";
        resultsRefreshEl.textContent = resultsState.loading ? "Aktualisiere..." : "Aktualisieren";
      }
      renderResultsExportState();
      renderResultsDeleteState();

      if (!resultsState.initialized && !hasItems) {
        resultsStateEl.textContent = "Ergebnisliste laedt...";
        resultsStateEl.className = "request-state";
      } else if (resultsState.loading && !hasItems) {
        resultsStateEl.textContent = "Ergebnisliste laedt...";
        resultsStateEl.className = "request-state";
      } else if (resultsState.loading && hasItems) {
        resultsStateEl.textContent = `${items.length} Ergebnisse sichtbar | aktualisiere...`;
        resultsStateEl.className = "request-state";
      } else if (resultsState.error) {
        resultsStateEl.textContent = formatResultActionMessage(
          resultsState.error.blocker || resultsState.error.error_type || "results_unavailable",
          "Die Ergebnisliste ist gerade nicht verfuegbar."
        );
        resultsStateEl.className = "request-state error";
      } else if (!hasItems) {
        resultsStateEl.textContent = "Noch keine gespeicherten Ergebnisse. Erstelle zuerst ein Bild, dann erscheint es hier.";
        resultsStateEl.className = "request-state";
      } else {
        const limitedSuffix = totalCount > effectiveLimit ? ` (Anzeige auf ${effectiveLimit} begrenzt)` : "";
        resultsStateEl.textContent = basicMode
          ? `${items.length} von ${totalCount} Bildern sichtbar | neueste zuerst${limitedSuffix}`
          : `${items.length} von ${totalCount} Ergebnissen | neueste zuerst${limitedSuffix}`;
        resultsStateEl.className = "request-state";
      }

      if (storage) {
        if (basicMode) {
          if (storage.exports_dir_accessible) {
            resultsStorageEl.textContent = `${storage.results_count} Bilder in der Hauptliste | ${storage.exports_count} Exporte gesichert`;
            resultsStorageEl.className = "request-state results-storage";
          } else {
            resultsStorageEl.textContent = `${storage.results_count} Bilder in der Hauptliste | Exportordner gerade nicht erreichbar`;
            resultsStorageEl.className = "request-state results-storage error";
          }
        } else {
          const resultsSegment = `Haupt-Output: ${storage.results_count}/${storage.retention_limit} in ${storage.results_dir} (app-verwaltet)`;
          if (storage.exports_dir_accessible) {
            resultsStorageEl.textContent = `${resultsSegment} | Nutzer-Exporte: ${storage.exports_count} in ${storage.exports_dir} (kein Auto-Cleanup)`;
            resultsStorageEl.className = "request-state results-storage";
          } else {
            resultsStorageEl.textContent = `${resultsSegment} | Exportordner nicht erreichbar (${storage.exports_dir_error || "exports_dir_not_accessible"})`;
            resultsStorageEl.className = "request-state results-storage error";
          }
        }
      } else {
        resultsStorageEl.textContent = basicMode
          ? "Speicherstatus wird noch geladen."
          : "Speicherstatus ist noch nicht verfuegbar.";
        resultsStorageEl.className = "request-state results-storage";
      }

      resultsGalleryEl.replaceChildren();
      for (const item of items) {
        const cardEl = document.createElement("article");
        cardEl.className = "result-card";
        cardEl.title = item.prompt || item.file_name;

        const headEl = document.createElement("div");
        headEl.className = "result-card-head";

        const titleEl = document.createElement("h3");
        titleEl.className = "result-card-title";
        titleEl.textContent = formatResultModeLabel(item.mode);
        headEl.appendChild(titleEl);

        const previewEl = document.createElement("img");
        previewEl.alt = `${item.mode} preview`;
        previewEl.src = item.preview_url;
        previewEl.loading = "lazy";
        previewEl.decoding = "async";
        previewEl.tabIndex = 0;
        previewEl.title = "Vorschau gross anzeigen";
        previewEl.addEventListener("click", () => {
          openResultsPreview(item);
        });
        previewEl.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openResultsPreview(item);
          }
        });

        const metaEl = document.createElement("div");
        metaEl.className = "result-card-meta";

        appendResultMetaLine(
          metaEl,
          basicMode ? "Aufgabe" : "Pfad",
          basicMode
            ? formatResultModeLabel(item.mode)
            : `${formatResultModeLabel(item.mode)} | ${item.mode}`
        );
        appendResultMetaLine(metaEl, "Zeit", formatResultCreatedAt(item.created_at));

        if (Number.isFinite(item.width) && Number.isFinite(item.height)) {
          const dimensions = `${item.width}x${item.height}`;
          const byteText = formatBytes(item.size_bytes);
          appendResultMetaLine(metaEl, basicMode ? "Bild" : "Bild", byteText ? `${dimensions} | ${byteText}` : dimensions);
        }

        const checkpointAlias = formatResultCheckpointAlias(item.checkpoint);
        if (checkpointAlias) {
          appendResultMetaLine(
            metaEl,
            basicMode ? "Stil" : "Checkpoint",
            !basicMode && checkpointAlias !== item.checkpoint
              ? `${checkpointAlias} | ${item.checkpoint}`
              : checkpointAlias
          );
        }

        if (Number.isFinite(item.reference_count) && item.reference_count > 0) {
          appendResultMetaLine(metaEl, "Referenzen", String(item.reference_count));
        }

        if (isNonEmptyString(item.multi_reference_strategy)) {
          appendResultMetaLine(metaEl, "Strategie", item.multi_reference_strategy);
        }
        if (isNonEmptyString(item.identity_transfer_strategy)) {
          appendResultMetaLine(metaEl, "Strategie", item.identity_transfer_strategy);
        }

        if (!basicMode && Array.isArray(item.used_roles) && item.used_roles.length > 0) {
          const roleLabel = item.used_roles.map((role) => mapIdentityTransferRoleLabel(role)).join(", ");
          appendResultMetaLine(metaEl, "Rollen", roleLabel);
        }

        if (!basicMode) {
          appendResultMetaLine(metaEl, "Store", `${item.store_scope} | ${item.cleanup_policy}`);
          if (Number.isFinite(item.retention_limit) && item.retention_limit > 0) {
            appendResultMetaLine(metaEl, "Retention", String(item.retention_limit));
          }
        }
        if (isNonEmptyString(item.prompt)) {
          appendResultCopyableTextLine(metaEl, basicMode ? "Prompt" : "Prompt", item.prompt);
        }
        if (isNonEmptyString(item.negative_prompt)) {
          appendResultCopyableTextLine(metaEl, basicMode ? "Negativ" : "Negativ", item.negative_prompt);
        }

        const actionsEl = document.createElement("div");
        actionsEl.className = "result-card-actions";

        const previewButton = document.createElement("button");
        previewButton.type = "button";
        previewButton.className = "result-preview-button";
        previewButton.textContent = basicMode ? "Gross ansehen" : "Vorschau";
        previewButton.addEventListener("click", () => {
          openResultsPreview(item);
        });
        actionsEl.appendChild(previewButton);

        const downloadEl = document.createElement("a");
        downloadEl.href = item.download_url;
        downloadEl.download = item.file_name;
        downloadEl.textContent = basicMode ? "Herunterladen" : "Download";
        actionsEl.appendChild(downloadEl);

        const exportButton = document.createElement("button");
        exportButton.type = "button";
        exportButton.textContent = resultsExportState.phase === "running" && resultsExportState.result_id === item.result_id
          ? "Export laeuft..."
          : (basicMode ? "In Exportordner sichern" : "In Exportordner kopieren");
        exportButton.disabled = resultsExportState.phase === "running" || resultsDeleteState.phase === "running";
        exportButton.addEventListener("click", () => {
          void requestResultExport(item.result_id);
        });
        actionsEl.appendChild(exportButton);

        const loadInputButton = document.createElement("button");
        loadInputButton.type = "button";
        loadInputButton.className = "result-load-input-button";
        loadInputButton.textContent = inputLoadBusy ? "Bild wird geladen..." : (basicMode ? "Als Ausgangsbild verwenden" : "Als Eingabebild laden");
        loadInputButton.disabled = inputLoadBusy || resultsDeleteState.phase === "running";
        loadInputButton.addEventListener("click", () => {
          void loadResultAsInputImage(item.result_id, { closePreview: false });
        });
        actionsEl.appendChild(loadInputButton);

        if (isAppManagedResultItem(item)) {
          const deleteButton = document.createElement("button");
          deleteButton.type = "button";
          deleteButton.className = "result-delete-button";
          deleteButton.textContent = resultsDeleteState.phase === "running" && resultsDeleteState.result_id === item.result_id
            ? "Loesche..."
            : (basicMode ? "Aus Hauptliste entfernen" : "Loeschen");
          deleteButton.disabled = resultsDeleteState.phase === "running";
          deleteButton.addEventListener("click", () => {
            void requestResultDelete(item.result_id, { fileName: item.file_name });
          });
          actionsEl.appendChild(deleteButton);
        }

        if (resultsExportState.phase === "success" && resultsExportState.result_id === item.result_id && isNonEmptyString(resultsExportState.export_url)) {
          const exportLinkEl = document.createElement("a");
          exportLinkEl.href = resultsExportState.export_url.trim();
          exportLinkEl.download = isNonEmptyString(resultsExportState.export_file_name) ? resultsExportState.export_file_name.trim() : "";
          exportLinkEl.textContent = basicMode ? "Export herunterladen" : "Export herunterladen";
          actionsEl.appendChild(exportLinkEl);
        }

        cardEl.appendChild(headEl);
        cardEl.appendChild(previewEl);
        cardEl.appendChild(metaEl);
        cardEl.appendChild(actionsEl);
        resultsGalleryEl.appendChild(cardEl);
      }
    }

    function persist_interrupted_request(request) {
      if (!request) {
        return;
      }

      writeStorageJson(INTERRUPTED_REQUEST_STORAGE_KEY, {
        client_request_id: request.client_request_id ?? null,
        request_id: request.request_id ?? null,
        mode: request.mode ?? null,
        started_at_utc: request.started_at_utc ?? null,
        created_at_utc: new Date().toISOString()
      });
    }

    function consume_interrupted_request() {
      const payload = readStorageJson(INTERRUPTED_REQUEST_STORAGE_KEY);
      removeStorageItem(INTERRUPTED_REQUEST_STORAGE_KEY);
      if (!payload) {
        return null;
      }

      return {
        code: "request_interrupted_by_reload",
        message: "reload interrupted active request",
        request_id: payload.request_id ?? payload.client_request_id ?? null,
        mode: payload.mode ?? null,
        created_at_utc: payload.created_at_utc ?? null
      };
    }

    function hasSuccessfulResult() {
      return Boolean(
        lastSuccessfulResult &&
        lastSuccessfulResult.status === "ok" &&
        lastSuccessfulResult.output_file
      );
    }

    function isNonEmptyString(value) {
      return typeof value === "string" && value.trim() !== "";
    }

    function getActiveClientRequestId() {
      return currentRequest ? currentRequest.client_request_id : null;
    }

    function rememberSettledRequestId(clientRequestId) {
      if (!isNonEmptyString(clientRequestId)) {
        return;
      }

      const normalizedRequestId = clientRequestId.trim();
      if (settledClientRequestIdSet.has(normalizedRequestId)) {
        return;
      }

      settledClientRequestIdSet.add(normalizedRequestId);
      settledClientRequestIds.push(normalizedRequestId);

      while (settledClientRequestIds.length > SETTLED_REQUEST_HISTORY_LIMIT) {
        const staleRequestId = settledClientRequestIds.shift();
        if (staleRequestId) {
          settledClientRequestIdSet.delete(staleRequestId);
        }
      }
    }

    function isResponseRelevant(responseClientRequestId, activeClientRequestId = getActiveClientRequestId(), settledRequestIds = settledClientRequestIdSet) {
      if (!isNonEmptyString(responseClientRequestId) || !isNonEmptyString(activeClientRequestId)) {
        return false;
      }

      const normalizedResponseClientRequestId = responseClientRequestId.trim();
      const normalizedActiveClientRequestId = activeClientRequestId.trim();
      if (normalizedResponseClientRequestId !== normalizedActiveClientRequestId) {
        return false;
      }

      if (settledRequestIds instanceof Set) {
        if (settledRequestIds.has(normalizedResponseClientRequestId)) {
          return false;
        }
      } else if (Array.isArray(settledRequestIds) && settledRequestIds.includes(normalizedResponseClientRequestId)) {
        return false;
      }

      return Boolean(
        currentRequest &&
        currentRequest.client_request_id === normalizedActiveClientRequestId
      );
    }

    function logIgnoredGenerateResponse(clientRequestId, reason) {
      void clientRequestId;
      void reason;
    }

    function evaluateServerRender(payload) {
      if (!payload || typeof payload !== "object") {
        return {
          status: "idle",
          request_id: null,
          started_at_utc: null,
          age_ms: null,
          is_plausible: true,
          is_running: false,
          reason: "missing"
        };
      }

      const status = typeof payload.server_render_status === "string"
        ? payload.server_render_status.trim().toLowerCase()
        : "idle";
      const requestId = isNonEmptyString(payload.server_render_request_id)
        ? payload.server_render_request_id.trim()
        : null;
      const startedAt = isNonEmptyString(payload.server_render_started_at_utc)
        ? payload.server_render_started_at_utc.trim()
        : null;

      if (status === "idle") {
        return {
          status,
          request_id: requestId,
          started_at_utc: startedAt,
          age_ms: null,
          is_plausible: requestId === null && startedAt === null,
          is_running: false,
          reason: requestId === null && startedAt === null ? null : "server_render_idle_inconsistent"
        };
      }

      if (status !== "running") {
        return {
          status,
          request_id: requestId,
          started_at_utc: startedAt,
          age_ms: null,
          is_plausible: false,
          is_running: false,
          reason: "server_render_status_invalid"
        };
      }

      if (requestId === null) {
        return {
          status,
          request_id: null,
          started_at_utc: startedAt,
          age_ms: null,
          is_plausible: false,
          is_running: false,
          reason: "server_render_request_id_missing"
        };
      }

      if (startedAt === null) {
        return {
          status,
          request_id: requestId,
          started_at_utc: null,
          age_ms: null,
          is_plausible: false,
          is_running: false,
          reason: "server_render_started_at_missing"
        };
      }

      const startedAtMs = Date.parse(startedAt);
      if (!Number.isFinite(startedAtMs)) {
        return {
          status,
          request_id: requestId,
          started_at_utc: startedAt,
          age_ms: null,
          is_plausible: false,
          is_running: false,
          reason: "server_render_started_at_invalid"
        };
      }

      const ageMs = Date.now() - startedAtMs;
      if (ageMs < -SERVER_RENDER_FUTURE_SKEW_MS) {
        return {
          status,
          request_id: requestId,
          started_at_utc: startedAt,
          age_ms: ageMs,
          is_plausible: false,
          is_running: false,
          reason: "server_render_started_at_future"
        };
      }

      if (ageMs > SERVER_RENDER_STALE_MS) {
        return {
          status,
          request_id: requestId,
          started_at_utc: startedAt,
          age_ms: ageMs,
          is_plausible: false,
          is_running: false,
          reason: "server_render_stale"
        };
      }

      return {
        status,
        request_id: requestId,
        started_at_utc: startedAt,
        age_ms: Math.max(0, ageMs),
        is_plausible: true,
        is_running: true,
        reason: null
      };
    }

    function resolveHealthView() {
      if (healthState.error) {
        if (healthState.payload && healthState.consecutiveFailures < OFFLINE_FAILURE_THRESHOLD) {
          return {
            state: "degraded",
            cause: "health_probe_retrying",
            service: healthState.payload?.service ?? null,
            comfyui_reachable: healthState.payload?.comfyui_reachable === true,
            runner_status: isNonEmptyString(healthState.payload?.runner_status) ? healthState.payload.runner_status.trim().toLowerCase() : null,
            output_dir_accessible: healthState.payload?.output_dir_accessible === true,
            results_dir_accessible: healthState.payload?.results_dir_accessible === true,
            selected_checkpoint: healthState.payload?.selected_checkpoint ?? null,
            server_render: evaluateServerRender(healthState.payload)
          };
        }
        return {
          state: "offline",
          cause: healthState.error,
          service: healthState.payload?.service ?? null,
          comfyui_reachable: false,
          runner_status: isNonEmptyString(healthState.payload?.runner_status) ? healthState.payload.runner_status.trim().toLowerCase() : null,
          output_dir_accessible: healthState.payload?.output_dir_accessible === true,
          results_dir_accessible: healthState.payload?.results_dir_accessible === true,
          selected_checkpoint: healthState.payload?.selected_checkpoint ?? null,
          server_render: evaluateServerRender(healthState.payload)
        };
      }

      if (!healthState.payload) {
        return {
          state: "offline",
          cause: "health_unreachable",
          service: null,
          comfyui_reachable: false,
          runner_status: null,
          output_dir_accessible: false,
          results_dir_accessible: false,
          selected_checkpoint: null,
          server_render: evaluateServerRender(null)
        };
      }

      const payload = healthState.payload;
      const runnerStatus = isNonEmptyString(payload.runner_status)
        ? payload.runner_status.trim().toLowerCase()
        : null;
      const comfyuiReachable = payload.comfyui_reachable === true;
      const outputDirAccessible = payload.output_dir_accessible === true;
      const resultsDirAccessible = payload.results_dir_accessible === true;
      const baseServerRender = evaluateServerRender(payload);
      let serverRender = {
        ...baseServerRender,
        is_consistent: baseServerRender.is_plausible
      };
      let state = "ready";
      let cause = "ok";

      if (baseServerRender.status === "running") {
        if (!baseServerRender.is_plausible) {
          serverRender = {
            ...baseServerRender,
            is_consistent: false,
            is_running: false
          };
        } else if (!(runnerStatus === "started" || runnerStatus === "already_running")) {
          serverRender = {
            ...baseServerRender,
            is_consistent: false,
            is_running: false,
            reason: "server_render_runner_inconsistent"
          };
        } else if (!comfyuiReachable) {
          serverRender = {
            ...baseServerRender,
            is_consistent: false,
            is_running: false,
            reason: "server_render_comfyui_inconsistent"
          };
        }
      } else if (!baseServerRender.is_plausible) {
        serverRender = {
          ...baseServerRender,
          is_consistent: false
        };
      }

      if (payload.service !== "local-image-app") {
        state = "degraded";
        cause = "unexpected_service";
      } else if (runnerStatus === null || runnerStatus === "unknown") {
        state = "degraded";
        cause = payload.runner_error || "runner_state_invalid";
      } else if (runnerStatus === "busy") {
        state = "degraded";
        cause = "runner_startup_in_progress";
      } else if (runnerStatus === "error") {
        state = "degraded";
        cause = "runner_error";
      } else if ((runnerStatus === "started" || runnerStatus === "already_running") && !comfyuiReachable) {
        state = "degraded";
        cause = "runner_comfyui_inconsistent";
      } else if (!comfyuiReachable) {
        state = "degraded";
        cause = payload.comfyui_error || "comfyui_unreachable";
      } else if (!outputDirAccessible) {
        state = "degraded";
        cause = payload.output_dir_error || "output_dir_not_accessible";
      } else if (!resultsDirAccessible) {
        state = "degraded";
        cause = payload.results_dir_error || "results_dir_not_accessible";
      } else if (serverRender.status === "running" && !serverRender.is_consistent) {
        state = "degraded";
        cause = "server_render_state_invalid";
      }

      return {
        state,
        cause,
        service: payload.service ?? null,
        comfyui_reachable: comfyuiReachable,
        runner_status: runnerStatus,
        output_dir_accessible: outputDirAccessible,
        results_dir_accessible: resultsDirAccessible,
        selected_checkpoint: payload.selected_checkpoint ?? null,
        server_render: serverRender
      };
    }

    function deriveHealthState() {
      const healthView = resolveHealthView();
      return {
        state: healthView.state,
        cause: healthView.cause
      };
    }

    function deriveUiState() {
      if (currentRequest && currentRequest.phase === "preflight") {
        return { state: "preflight", cause: "preflight_in_progress", origin: "client" };
      }

      if (currentRequest && currentRequest.phase === "running") {
        return { state: "running", cause: "render_in_progress", origin: "client" };
      }

      const healthView = resolveHealthView();
      return healthView;
    }

    function computeGenerateEnabled(state) {
      if (!state || typeof state !== "object") {
        return {
          enabled: false,
          reason: "health_unreachable"
        };
      }

      if (state.current_request && state.current_request.phase === "preflight") {
        return {
          enabled: false,
          reason: "preflight_in_progress"
        };
      }

      if (state.current_request && state.current_request.phase === "running") {
        return {
          enabled: false,
          reason: "render_in_progress"
        };
      }

      if (state.health_state.state !== "ready") {
        return {
          enabled: false,
          reason: state.health_state.cause || "health_not_ready"
        };
      }

      return {
        enabled: true,
        reason: null
      };
    }

    function getActiveImageState() {
      if (!activeImageContext || !isNonEmptyString(activeImageContext.state)) {
        return "none";
      }

      const normalizedState = activeImageContext.state.trim().toLowerCase();
      if (normalizedState === "loading" || normalizedState === "ready" || normalizedState === "error") {
        return normalizedState;
      }
      return "none";
    }

    function hasVisibleImage() {
      return Boolean(displayedImage && isNonEmptyString(displayedImage.output_file));
    }

    function isActiveImageVisible() {
      return Boolean(
        hasVisibleImage() &&
        activeImageContext &&
        displayedImage.token === activeImageContext.token &&
        getActiveImageState() === "ready"
      );
    }

    function getMainPromptValue() {
      return promptEl.value.trim();
    }

    function hasMainPromptValue() {
      return isNonEmptyString(getMainPromptValue());
    }

    function hasIdentityTransferRoleImage(role) {
      const payload = getIdentityTransferStatusPayload();
      const roles = Array.isArray(payload.roles) ? payload.roles : [];
      const roleView = roles.find((entry) => entry && entry.role === role);
      return Boolean(roleView && roleView.occupied === true && roleView.image);
    }

    function hasCurrentBasicTaskCompletedSuccessfully(taskId = getCurrentV7TaskConfig().id) {
      if (taskId === "create" || taskId === "edit" || taskId === "inpaint") {
        return Boolean(
          lastSuccessfulResult &&
          lastSuccessfulResult.status === "ok" &&
          lastSuccessfulResult.v7_basic_task === taskId
        );
      }

      if (taskId === "identity-single") {
        return Boolean(
          currentIdentityRequest?.phase === "success" &&
          activeIdentityResult.state === "ready" &&
          isNonEmptyString(activeIdentityResult.result_id)
        );
      }

      if (taskId === "identity-multi") {
        return Boolean(
          currentMultiReferenceRequest?.phase === "success" &&
          isNonEmptyString(currentMultiReferenceRequest.result_id)
        );
      }

      if (taskId === "identity-transfer") {
        return Boolean(
          currentIdentityTransferRequest?.phase === "success" &&
          activeIdentityTransferResult.state === "ready" &&
          isNonEmptyString(activeIdentityTransferResult.result_id)
        );
      }

      return false;
    }

    function deriveBasicGenerateLeadView(taskId = getCurrentV7TaskConfig().id) {
      const healthView = resolveHealthView();
      if (currentRequest && currentRequest.phase === "preflight") {
        return {
          state: "preflight",
          text: "Pruefe, ob alles bereit ist...",
          request_id: currentRequest.request_id || currentRequest.client_request_id,
          is_error: false
        };
      }

      if (currentRequest && currentRequest.phase === "running") {
        const runningText = taskId === "create"
          ? "Bild wird erstellt..."
          : (taskId === "inpaint" ? "Bildbereich wird geaendert..." : "Bild wird bearbeitet...");
        return {
          state: "running",
          text: runningText,
          request_id: currentRequest.request_id || currentRequest.client_request_id,
          is_error: false
        };
      }

      if (taskId === "create") {
        if (!hasMainPromptValue()) {
          return {
            state: "missing",
            text: "Gib zuerst einen Prompt ein",
            request_id: null,
            is_error: false
          };
        }
      }

      if (taskId === "edit") {
        if (!hasUsableInputImage()) {
          return {
            state: "missing",
            text: "Lade zuerst ein Bild hoch",
            request_id: null,
            is_error: false
          };
        }
        if (!hasMainPromptValue()) {
          return {
            state: "missing",
            text: "Beschreibe danach die Aenderung",
            request_id: null,
            is_error: false
          };
        }
      }

      if (taskId === "inpaint") {
        if (!hasUsableInputImage()) {
          return {
            state: "missing",
            text: "Lade zuerst ein Bild hoch",
            request_id: null,
            is_error: false
          };
        }
        if (!hasUsableMaskImage()) {
          return {
            state: "missing",
            text: "Maske fehlt noch",
            request_id: null,
            is_error: false
          };
        }
        if (!isCurrentMaskCompatibleWithSource()) {
          return {
            state: "error",
            text: "Maske passt nicht zum Bild",
            request_id: null,
            is_error: true
          };
        }
        if (!hasMainPromptValue()) {
          return {
            state: "missing",
            text: "Beschreibe den markierten Bereich",
            request_id: null,
            is_error: false
          };
        }
      }

      if (healthView.state !== "ready") {
        return {
          state: "blocked",
          text: `Noch nicht bereit | ${formatUiCause(healthView.cause)}`,
          request_id: null,
          is_error: true
        };
      }

      return {
        state: "ready",
        text: "Jetzt kannst du starten",
        request_id: null,
        is_error: false
      };
    }

    function getElapsedMsFromIso(value) {
      if (!isNonEmptyString(value)) {
        return null;
      }
      const parsed = Date.parse(value.trim());
      if (!Number.isFinite(parsed)) {
        return null;
      }
      return Math.max(0, Date.now() - parsed);
    }

    function formatElapsedRuntime(ms) {
      if (!Number.isFinite(ms) || ms < 0) {
        return "Lauf aktiv";
      }
      const seconds = Math.max(0, Math.floor(ms / 1000));
      return seconds < 1 ? "Lauf aktiv" : `Seit ${seconds}s aktiv`;
    }

    function buildRenderProgressPhases(elapsedMs, finalLabel = "Ergebnis wird geladen") {
      const basePhases = [
        "Vorbereitung",
        "Bild wird berechnet",
        "Fast fertig",
        finalLabel
      ];
      if (!Number.isFinite(elapsedMs) || elapsedMs < 4000) {
        return { activeIndex: 0, phases: basePhases, title: "Vorbereitung", meta: "Workflow wird vorbereitet" };
      }
      if (elapsedMs < 18000) {
        return { activeIndex: 1, phases: basePhases, title: "Bild wird berechnet", meta: "Der laufende Bildjob arbeitet aktiv" };
      }
      return { activeIndex: 2, phases: basePhases, title: "Fast fertig", meta: "Die Berechnung laeuft noch, das Ergebnis sollte gleich kommen" };
    }

    function deriveGenerateProgressView() {
      if (!isV7BasicModeActive()) {
        return { visible: false };
      }
      const taskId = getCurrentV7TaskConfig().id;
      if (!BASIC_IMAGE_TASK_IDS.includes(taskId)) {
        return { visible: false };
      }

      if (currentRequest && currentRequest.phase === "preflight") {
        return {
          visible: true,
          phase: "preflight",
          title: "Vorbereitung",
          meta: "Einstellungen und Verfuegbarkeit werden geprueft",
          elapsed_ms: getElapsedMsFromIso(currentRequest.started_at_utc),
          active_index: 0,
          steps: ["Vorbereitung", "Bild wird berechnet", "Fast fertig", "Ergebnis wird geladen"]
        };
      }

      if (currentRequest && currentRequest.phase === "running") {
        const healthView = resolveHealthView();
        const elapsedMs = Number.isFinite(healthView.server_render?.age_ms)
          ? healthView.server_render.age_ms
          : getElapsedMsFromIso(currentRequest.started_at_utc);
        const progress = buildRenderProgressPhases(elapsedMs);
        return {
          visible: true,
          phase: "running",
          title: progress.title,
          meta: formatElapsedRuntime(elapsedMs),
          elapsed_ms: elapsedMs,
          active_index: progress.activeIndex,
          steps: progress.phases
        };
      }

      if (
        lastResult &&
        lastResult.status === "ok" &&
        lastResult.v7_basic_task === taskId &&
        getActiveImageState() === "loading"
      ) {
        return {
          visible: true,
          phase: "loading",
          title: "Ergebnis wird geladen",
          meta: "Die Vorschau wird vorbereitet",
          elapsed_ms: null,
          active_index: 3,
          steps: ["Vorbereitung", "Bild wird berechnet", "Fast fertig", "Ergebnis wird geladen"]
        };
      }

      return { visible: false };
    }

    function deriveIdentityProgressView() {
      if (!(isV7BasicModeActive() && getCurrentV7TaskConfig().id === "identity-single")) {
        return { visible: false };
      }

      if (currentIdentityRequest?.phase === "running") {
        const elapsedMs = getElapsedMsFromIso(currentIdentityRequest.started_at_utc);
        const progress = buildRenderProgressPhases(elapsedMs);
        return {
          visible: true,
          phase: "running",
          title: progress.title,
          meta: formatElapsedRuntime(elapsedMs),
          elapsed_ms: elapsedMs,
          active_index: progress.activeIndex,
          steps: progress.phases
        };
      }

      if (currentIdentityRequest?.phase === "success" && activeIdentityResult.state === "loading") {
        return {
          visible: true,
          phase: "loading",
          title: "Ergebnis wird geladen",
          meta: "Die neue Variante wird vorbereitet",
          elapsed_ms: null,
          active_index: 3,
          steps: ["Vorbereitung", "Bild wird berechnet", "Fast fertig", "Ergebnis wird geladen"]
        };
      }

      return { visible: false };
    }

    function renderProgressSteps(containerEl, activeIndex, steps) {
      if (!containerEl) {
        return;
      }
      containerEl.replaceChildren();
      steps.forEach((label, index) => {
        const stepEl = document.createElement("div");
        stepEl.className = "progress-step";
        if (index < activeIndex) {
          stepEl.classList.add("is-complete");
        } else if (index === activeIndex) {
          stepEl.classList.add("is-active");
        }
        stepEl.textContent = label;
        containerEl.appendChild(stepEl);
      });
    }

    function renderGenerateProgressUi() {
      if (!generateProgressPanelEl || !generateProgressTitleEl || !generateProgressMetaEl || !generateProgressStepsEl) {
        return false;
      }
      const view = deriveGenerateProgressView();
      generateProgressPanelEl.hidden = !view.visible;
      if (!view.visible) {
        generateProgressPanelEl.removeAttribute("data-phase");
        generateProgressStepsEl.replaceChildren();
        return false;
      }
      generateProgressPanelEl.dataset.phase = view.phase || "running";
      generateProgressTitleEl.textContent = view.title;
      generateProgressMetaEl.textContent = view.meta;
      renderProgressSteps(generateProgressStepsEl, view.active_index, view.steps);
      return true;
    }

    function renderIdentityProgressUi() {
      if (!identityProgressPanelEl || !identityProgressTitleEl || !identityProgressMetaEl || !identityProgressStepsEl) {
        return false;
      }
      const view = deriveIdentityProgressView();
      identityProgressPanelEl.hidden = !view.visible;
      if (!view.visible) {
        identityProgressPanelEl.removeAttribute("data-phase");
        identityProgressStepsEl.replaceChildren();
        return false;
      }
      identityProgressPanelEl.dataset.phase = view.phase || "running";
      identityProgressTitleEl.textContent = view.title;
      identityProgressMetaEl.textContent = view.meta;
      renderProgressSteps(identityProgressStepsEl, view.active_index, view.steps);
      return true;
    }

    function syncProgressRenderTimer(isActive) {
      window.clearTimeout(progressRenderTimer);
      if (!isActive) {
        progressRenderTimer = null;
        return;
      }
      progressRenderTimer = window.setTimeout(() => {
        renderUi();
      }, 1000);
    }

    function deriveBasicExpertTaskLeadView(taskId = getCurrentV7TaskConfig().id) {
      if (taskId === "identity-single") {
        const readinessView = getIdentityVerfuegbarkeitView();
        const hasPrompt = isNonEmptyString(identityPromptEl.value.trim());
        if (currentIdentityRequest?.phase === "running") {
          return {
            text: "Bild wird erstellt...",
            is_error: false
          };
        }
        if (currentIdentityRequest?.phase === "success") {
          return {
            text: activeIdentityResult.state === "loading" ? "Ergebnis wird geladen..." : "Ergebnis ist fertig",
            is_error: false
          };
        }
        if (currentIdentityRequest?.phase === "error") {
          return {
            text: "Erstellung fehlgeschlagen",
            is_error: true
          };
        }
        if (!hasUsableIdentityReferenceImage()) {
          return {
            text: "Referenzbild fehlt noch",
            is_error: false
          };
        }
        if (!readinessView.ready) {
          return {
            text: readinessView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...",
            is_error: readinessView.is_error
          };
        }
        if (!hasPrompt) {
          return {
            text: "Gib einen Wunsch ein",
            is_error: false
          };
        }
        return {
          text: "Jetzt kannst du starten",
          is_error: false
        };
      }

      if (taskId === "identity-multi") {
        const statusPayload = getMultiReferenceStatusPayload();
        const referenceCount = Number.isFinite(statusPayload.reference_count) ? Number(statusPayload.reference_count) : 0;
        const readinessView = getMultiReferenceRuntimeVerfuegbarkeitView();
        const hasPrompt = isNonEmptyString(multiReferencePromptEl.value);
        if (currentMultiReferenceRequest?.phase === "running") {
          return {
            text: "Bild wird erstellt...",
            is_error: false
          };
        }
        if (currentMultiReferenceRequest?.phase === "success") {
          return {
            text: "Ergebnis ist fertig",
            is_error: false
          };
        }
        if (currentMultiReferenceRequest?.phase === "error") {
          return {
            text: "Testlauf fehlgeschlagen",
            is_error: true
          };
        }
        if (referenceCount === 0) {
          return {
            text: "Es fehlen noch Referenzbilder",
            is_error: false
          };
        }
        if (referenceCount === 1) {
          return {
            text: "Du brauchst noch ein Referenzbild",
            is_error: false
          };
        }
        if (!readinessView.ready) {
          return {
            text: readinessView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...",
            is_error: readinessView.is_error
          };
        }
        if (!hasPrompt) {
          return {
            text: "Gib einen Wunsch ein",
            is_error: false
          };
        }
        return {
          text: "Jetzt kannst du starten",
          is_error: false
        };
      }

      const readinessView = getIdentityTransferTestVerfuegbarkeitView();
      const hasPrompt = isNonEmptyString(identityTransferPromptEl.value);
      if (currentIdentityTransferRequest?.phase === "running") {
        return {
          text: "Bild wird erstellt...",
          is_error: false
        };
      }
      if (currentIdentityTransferRequest?.phase === "success") {
        return {
          text: activeIdentityTransferResult.state === "loading" ? "Ergebnis wird geladen..." : "Ergebnis ist fertig",
          is_error: false
        };
      }
      if (currentIdentityTransferRequest?.phase === "error") {
        return {
          text: "Transfer fehlgeschlagen",
          is_error: true
        };
      }
      if (!hasIdentityTransferRoleImage("identity_head_reference")) {
        return {
          text: "Kopf-Referenz fehlt noch",
          is_error: false
        };
      }
      if (!hasIdentityTransferRoleImage("target_body_image")) {
        return {
          text: "Zielbild fehlt noch",
          is_error: false
        };
      }
      if (!readinessView.ready) {
        return {
          text: readinessView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...",
          is_error: readinessView.is_error
        };
      }
      if (!hasPrompt) {
        return {
          text: "Gib einen Wunsch ein",
          is_error: false
        };
      }
      return {
        text: "Jetzt kannst du starten",
        is_error: false
      };
    }

    function deriveRequestStatusView() {
      if (isV7BasicModeActive()) {
        const taskId = getCurrentV7TaskConfig().id;
        if (taskId === "create" || taskId === "edit" || taskId === "inpaint") {
          return deriveBasicGenerateLeadView(taskId);
        }
      }

      if (currentRequest && currentRequest.phase === "preflight") {
        return {
          state: "preflight",
          text: "Pruefe App, Bild-Engine und Speicher...",
          request_id: currentRequest.request_id || currentRequest.client_request_id
        };
      }

      if (currentRequest && currentRequest.phase === "running") {
        const taskId = getCurrentV7TaskConfig().id;
        return {
          state: "running",
          text: taskId === "create" ? "Bild-Erstellung laeuft..." : "Bild-Bearbeitung laeuft...",
          request_id: currentRequest.request_id || currentRequest.client_request_id
        };
      }

      const healthView = resolveHealthView();
      if (healthView.state === "ready") {
        return {
          state: "idle",
          text: "Jetzt kannst du starten",
          request_id: null
        };
      }

      return {
        state: "idle",
        text: "Noch nicht bereit",
        request_id: null
      };
    }

    function deriveForeignServerRequestView() {
      const healthView = resolveHealthView();
      const hasLocalActiveRequest = Boolean(
        currentRequest &&
        (currentRequest.phase === "preflight" || currentRequest.phase === "running")
      );
      const isForeignActive = Boolean(
        healthView.state === "ready" &&
        healthView.server_render.is_running &&
        !hasLocalActiveRequest
      );

      if (!isForeignActive) {
        return {
          active: false,
          request_id: null,
          text: "",
          cause: null
        };
      }

      return {
        active: true,
        request_id: healthView.server_render.request_id,
        text: `Server verarbeitet gerade eine andere Anfrage${healthView.server_render.request_id ? ` | ${healthView.server_render.request_id}` : ""}`,
        cause: "foreign_server_request_active"
      };
    }

    function deriveImageStatusView() {
      const imageState = getActiveImageState();
      const hasVisible = hasVisibleImage();
      const activeVisible = isActiveImageVisible();
      const visibleIsPrevious = hasVisible && activeImageContext && displayedImage.token !== activeImageContext.token;
      const basicMode = isV7BasicModeActive();

      if (imageState === "loading") {
        return {
          state: "loading",
          text: basicMode
            ? "Ergebnis wird geladen..."
            : (visibleIsPrevious
              ? "Bild wird geladen... letztes sichtbares Ergebnis bleibt sichtbar"
              : "Bild wird geladen..."),
          active_image_token: activeImageContext.token,
          active_image_url: activeImageContext.output_file,
          visible_image_token: displayedImage.token,
          visible_image_url: displayedImage.output_file,
          is_active_image_visible: activeVisible
        };
      }

      if (imageState === "ready" && activeVisible) {
        return {
          state: "ready",
          text: basicMode
            ? "Ergebnis sichtbar"
            : (activeImageContext.restored_from_storage === true
              ? "Letztes sichtbares Ergebnis geladen"
              : "Aktuelles Bild sichtbar"),
          active_image_token: activeImageContext.token,
          active_image_url: activeImageContext.output_file,
          visible_image_token: displayedImage.token,
          visible_image_url: displayedImage.output_file,
          is_active_image_visible: true
        };
      }

      if (imageState === "error") {
        return {
          state: "error",
          text: basicMode ? "Ergebnis konnte nicht geladen werden" : "Bildfehler | generated_file_not_accessible",
          active_image_token: activeImageContext.token,
          active_image_url: activeImageContext.output_file,
          visible_image_token: displayedImage.token,
          visible_image_url: displayedImage.output_file,
          is_active_image_visible: false
        };
      }

      if (hasVisible) {
        return {
          state: "ready",
          text: basicMode ? "Letztes Ergebnis sichtbar" : "Letztes sichtbares Ergebnis",
          active_image_token: activeImageContext.token,
          active_image_url: activeImageContext.output_file,
          visible_image_token: displayedImage.token,
          visible_image_url: displayedImage.output_file,
          is_active_image_visible: activeVisible
        };
      }

      return {
        state: "none",
        text: basicMode ? "Noch kein Ergebnis sichtbar" : "Kein sichtbares Bild",
        active_image_token: activeImageContext.token,
        active_image_url: activeImageContext.output_file,
        visible_image_token: null,
        visible_image_url: null,
        is_active_image_visible: false
      };
    }

    function deriveResultStatusView() {
      const imageStatus = deriveImageStatusView();
      const basicMode = isV7BasicModeActive();
      if (!lastResult) {
        return {
          state: "none",
          text: basicMode ? "Noch kein Ergebnis" : "Kein Render-Ergebnis",
          request_id: null
        };
      }

      if (lastResult.status === "error") {
        return {
          state: "error",
          text: basicMode
            ? (hasSuccessfulResult()
              ? "Erstellung fehlgeschlagen | letztes Ergebnis bleibt sichtbar"
              : "Erstellung fehlgeschlagen")
            : (hasSuccessfulResult()
              ? `Fehler | ${lastResult.error_type || lastResult.blocker || "unknown_error"} | letztes sichtbares Ergebnis bleibt`
              : `Fehler | ${lastResult.error_type || lastResult.blocker || "unknown_error"}`),
          request_id: lastResult.request_id ?? null
        };
      }

      const isActiveResult = Boolean(
        lastResult.status === "ok" &&
        activeImageContext &&
        lastResult.output_file === activeImageContext.output_file &&
        lastResult.request_id === activeImageContext.request_id
      );

      if (isActiveResult && imageStatus.state === "loading") {
        return {
          state: "loading",
          text: imageStatus.text,
          request_id: lastResult.request_id ?? null
        };
      }

      if (isActiveResult && imageStatus.state === "ready") {
        return {
          state: "ok",
          text: basicMode
            ? "Ergebnis ist fertig"
            : (activeImageContext.restored_from_storage === true
              ? "Letztes Ergebnis sichtbar"
              : "Neues Bild sichtbar"),
          request_id: lastResult.request_id ?? null
        };
      }

      if (isActiveResult && imageStatus.state === "error") {
        return {
          state: "error",
          text: "Fehler | output_file_missing",
          request_id: lastResult.request_id ?? null
        };
      }

      if (hasSuccessfulResult()) {
        return {
          state: "ok",
          text: basicMode
            ? (hasCurrentBasicTaskCompletedSuccessfully() ? "Ergebnis ist fertig" : "Letztes Ergebnis sichtbar")
            : "Letztes erfolgreiches Ergebnis sichtbar",
          request_id: lastSuccessfulResult?.request_id ?? null
        };
      }

      return {
        state: "ok",
        text: basicMode ? "Ergebnis ist fertig" : "Render erfolgreich",
        request_id: lastResult.request_id ?? null
      };
    }

    function formatUiCause(cause) {
      const normalized = isNonEmptyString(cause) ? cause.trim() : "unbekannt";
      const labels = {
        ok: "bereit",
        health_pending: "System wird vorbereitet",
        health_probe_retrying: "Status wird erneut geprueft",
        health_unreachable: "App antwortet nicht",
        unexpected_service: "falscher App-Dienst",
        runner_state_invalid: "Bild-Engine meldet keinen klaren Status",
        runner_status_missing: "Runner-Status fehlt",
        runner_status_unreadable: "Runner-Status ist unlesbar",
        runner_startup_in_progress: "Bild-Engine startet noch",
        runner_error: "Bild-Engine meldet einen Fehler",
        runner_comfyui_inconsistent: "Bild-Engine nicht erreichbar",
        comfyui_unreachable: "Bild-Engine nicht erreichbar",
        output_dir_not_accessible: "ComfyUI-Output nicht zugreifbar",
        results_dir_not_accessible: "Ergebnisordner nicht zugreifbar",
        input_dir_not_accessible: "Bildspeicher nicht zugreifbar",
        mask_dir_not_accessible: "Maskenspeicher nicht zugreifbar",
        server_render_state_invalid: "Laufstatus ist gerade unklar",
        health_not_ready: "System nicht bereit",
        preflight_in_progress: "Vorabpruefung laeuft",
        render_in_progress: "Bild-Erstellung laeuft",
        empty_prompt: "Prompt fehlt",
        negative_prompt_not_string: "Negativ-Prompt ungueltig",
        negative_prompt_too_long: "Negativ-Prompt zu lang",
        invalid_mode: "ungueltiger Modus"
      };
      return labels[normalized] || normalized.replaceAll("_", " ");
    }

    function isSoftSystemCause(cause) {
      const normalized = isNonEmptyString(cause) ? cause.trim() : "";
      return [
        "health_pending",
        "health_probe_retrying",
        "runner_startup_in_progress",
        "preflight_in_progress",
        "render_in_progress"
      ].includes(normalized);
    }

    function formatResultActionMessage(blocker, fallback = "Aktion konnte gerade nicht abgeschlossen werden.") {
      const normalized = isNonEmptyString(blocker) ? blocker.trim() : "";
      const labels = {
        invalid_result_id: "Das ausgewaehlte Ergebnis ist ungueltig.",
        result_not_found: "Dieses Ergebnis wurde nicht gefunden.",
        result_delete_forbidden_scope: "Nur App-Ergebnisse aus data/results koennen hier geloescht werden.",
        result_delete_request_failed: "Das Ergebnis konnte gerade nicht geloescht werden.",
        result_export_request_failed: "Der Export konnte gerade nicht erstellt werden.",
        results_unavailable: "Die Ergebnisliste ist gerade nicht verfuegbar.",
        result_download_failed: "Das Ergebnis konnte gerade nicht geladen werden.",
        result_download_request_failed: "Das Ergebnis konnte gerade nicht geladen werden."
      };
      if (labels[normalized]) {
        return labels[normalized];
      }
      if (normalized.startsWith("result_delete_http_")) {
        return "Das Ergebnis konnte gerade nicht geloescht werden.";
      }
      if (normalized.startsWith("result_export_http_")) {
        return "Der Export konnte gerade nicht erstellt werden.";
      }
      if (normalized.startsWith("results_http_")) {
        return "Die Ergebnisliste ist gerade nicht verfuegbar.";
      }
      if (normalized.startsWith("result_download_http_")) {
        return "Das Ergebnis konnte gerade nicht geladen werden.";
      }
      return fallback;
    }

    function formatImageGenerationErrorMessage(blocker, options = {}) {
      const normalized = isNonEmptyString(blocker) ? blocker.trim() : "";
      const fallback = isNonEmptyString(options.fallback) ? options.fallback.trim() : "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden.";
      const labels = {
        empty_prompt: "Bitte gib zuerst einen Prompt ein.",
        negative_prompt_not_string: "Der Negativ-Prompt ist ungueltig.",
        negative_prompt_too_long: `Bitte kuerze den Negativ-Prompt auf ${NEGATIVE_PROMPT_MAX_LENGTH} Zeichen.`,
        invalid_mode: "Die Bildwelt oder der Modus ist ungueltig.",
        invalid_json: "Die Anfrage war unvollstaendig.",
        invalid_use_input_image: "Die Einstellung fuer das Eingabebild ist ungueltig.",
        invalid_use_inpainting: "Die Einstellung fuer die Maske ist ungueltig.",
        invalid_denoise_strength: "Die Aenderungsstaerke ist ungueltig.",
        missing_checkpoint: "Das gewaehlte Bildmodell wurde lokal nicht gefunden.",
        invalid_checkpoint: "Das gewaehlte Bildmodell ist ungueltig.",
        checkpoint_load_error: "Das Bildmodell konnte im aktuellen Pfad nicht geladen werden.",
        missing_input_image: "Das Eingabebild fehlt oder ist nicht lesbar.",
        missing_mask_image: "Die Maske fehlt oder ist nicht lesbar.",
        mask_size_mismatch: "Die Maske passt nicht zum aktuellen Eingabebild.",
        empty_mask: "Die Maske enthaelt noch keinen markierten Bereich.",
        render_in_progress: "Es laeuft gerade schon eine andere Bild-Erstellung.",
        comfyui_unreachable: "Die Bild-Engine ist gerade nicht erreichbar.",
        runner_state_invalid: "Die Bild-Engine ist noch nicht bereit.",
        invalid_generate_response: "Die Antwort der Bild-Engine war ungueltig.",
        server_error: "Der Bildpfad konnte gerade nicht sauber abgeschlossen werden.",
        generated_file_not_accessible: "Das Ergebnisbild konnte danach nicht mehr gelesen werden.",
        missing_reference_image: "Das Referenzbild fehlt oder ist nicht lesbar.",
        identity_not_ready: "Dieser Referenzpfad ist gerade noch nicht bereit.",
        identity_reference_failed: "Der Referenzpfad konnte nicht abgeschlossen werden.",
        insufficient_multi_reference_images: "Es werden mindestens zwei Referenzbilder derselben Person gebraucht.",
        identity_multi_reference_not_ready: "Der Multi-Reference-Pfad ist gerade nicht bereit.",
        identity_multi_reference_failed: "Der Multi-Reference-Pfad konnte nicht abgeschlossen werden.",
        missing_identity_head_reference: "Das Kopf-Referenzbild fehlt noch.",
        missing_target_body_image: "Das Zielbild fehlt noch.",
        missing_transfer_mask: "Die Transfer-Maske fehlt noch.",
        identity_transfer_unavailable: "Der Transfer-Pfad ist gerade nicht verfuegbar.",
        identity_transfer_failed: "Der Transfer-Pfad konnte nicht abgeschlossen werden.",
        identity_transfer_mask_hybrid_not_ready: "Der Masken-Hybrid ist gerade nicht bereit.",
        identity_transfer_mask_hybrid_failed: "Der Masken-Hybrid konnte nicht abgeschlossen werden.",
        identity_transfer_mask_hybrid_readiness_pending: "Der Masken-Hybrid wird noch geprueft."
      };

      if (labels[normalized]) {
        return labels[normalized];
      }
      if (normalized.startsWith("identity_reference_http_")) {
        return "Der Referenzpfad konnte gerade nicht abgeschlossen werden.";
      }
      if (normalized.startsWith("identity_multi_reference_http_")) {
        return "Der Multi-Reference-Pfad konnte gerade nicht abgeschlossen werden.";
      }
      if (normalized.startsWith("identity_transfer_http_")) {
        return "Der Transfer-Pfad konnte gerade nicht abgeschlossen werden.";
      }
      if (normalized.startsWith("identity_transfer_mask_hybrid_http_")) {
        return "Der Masken-Hybrid konnte gerade nicht abgeschlossen werden.";
      }
      if (normalized.startsWith("output_http_")) {
        return "Das Ergebnisbild ist gerade nicht erreichbar.";
      }
      if (normalized.includes("Failed to fetch") || normalized.includes("NetworkError")) {
        return "Die Verbindung zur Bild-Engine ist gerade unterbrochen.";
      }
      return fallback;
    }

    function buildSystemSummaryView() {
      const healthView = resolveHealthView();
      const textServiceUserState = getTextServiceUserState();
      const textSummary = textServiceUserState.key === "ready"
        ? "Text-KI bereit"
        : (textServiceUserState.key === "pending"
          ? "Text-KI wird geprueft"
          : (textServiceUserState.key === "unreachable" || textServiceUserState.key === "not_configured"
            ? "Text-KI eingeschraenkt"
            : "Text-KI noch nicht bereit"));
      const runnerSummary = healthView.runner_status === "started" || healthView.runner_status === "already_running"
        ? "Runner bereit"
        : (healthView.runner_status === "busy" ? "Runner startet" : "Runner nicht bereit");
      const comfySummary = healthView.comfyui_reachable ? "ComfyUI bereit" : "ComfyUI nicht bereit";
      if (healthView.state === "ready") {
        return {
          hidden: isV7BasicModeActive(),
          text: isV7BasicModeActive()
            ? "Bereit"
            : `System bereit | ${comfySummary} | ${runnerSummary} | ${textSummary}${isNonEmptyString(healthView.selected_checkpoint) ? ` | ${healthView.selected_checkpoint.trim()}` : ""}`,
          is_error: false
        };
      }

      if (healthView.state === "offline") {
        return {
          hidden: false,
          text: `System nicht erreichbar | ${formatUiCause(healthView.cause)}`,
          is_error: true
        };
      }

      return {
        hidden: false,
        text: `${isSoftSystemCause(healthView.cause) ? "System wird vorbereitet" : "System eingeschraenkt"} | ${formatUiCause(healthView.cause)} | ${comfySummary} | ${runnerSummary}`,
        is_error: !isSoftSystemCause(healthView.cause)
      };
    }

    function getTextServiceHealthState() {
      const payload = healthState.payload;
      if (!payload || typeof payload !== "object") {
        return {
          phase: "pending",
          configured: false,
          reachable: false,
          service_name: null,
          service_mode: null,
          stub_mode: null,
          inference_available: null,
          model_status: null,
          error: null
        };
      }

      const textService = payload.text_service && typeof payload.text_service === "object"
        ? payload.text_service
        : null;

      return {
        phase: "ready",
        configured: payload.text_service_configured === true,
        reachable: payload.text_service_reachable === true,
        service_name: isNonEmptyString(textService?.service_name) ? textService.service_name.trim() : null,
        service_mode: isNonEmptyString(textService?.service_mode) ? textService.service_mode.trim() : null,
        stub_mode: textService?.stub_mode === true,
        inference_available: textService?.inference_available === true,
        model_status: isNonEmptyString(textService?.model_status) ? textService.model_status.trim() : null,
        error: isNonEmptyString(payload.text_service_error) ? payload.text_service_error.trim() : null
      };
    }

    function getTextServiceUserState(textServiceState = getTextServiceHealthState()) {
      if (!textServiceState || textServiceState.phase === "pending") {
        return {
          key: "pending",
          short_text: "Text-KI wird geprueft...",
          status_text: "Arbeitsbereich wird vorbereitet.",
          focus_hint: "Die lokale Text-KI wird geprueft.",
          guide_detail: "Sobald sie bereit ist, kannst du hier direkt weiterschreiben."
        };
      }

      if (!textServiceState.configured) {
        return {
          key: "not_configured",
          short_text: "Text-KI ist gerade nicht verfuegbar",
          status_text: "Die lokale Text-KI ist noch nicht eingerichtet.",
          focus_hint: "Die lokale Text-KI ist gerade nicht verfuegbar.",
          guide_detail: "Du kannst weiter schreiben. KI-Textfunktionen werden aktiv, sobald die Einrichtung abgeschlossen ist."
        };
      }

      if (!textServiceState.reachable) {
        return {
          key: "unreachable",
          short_text: "Text-KI ist gerade nicht verfuegbar",
          status_text: "Die lokale Text-KI antwortet gerade nicht.",
          focus_hint: "Die lokale Text-KI ist gerade nicht verfuegbar.",
          guide_detail: "Du kannst weiter schreiben und spaeter erneut starten."
        };
      }

      if (textServiceState.service_mode === "real_model_ready" && textServiceState.inference_available === true && textServiceState.stub_mode !== true) {
        return {
          key: "ready",
          short_text: "Jetzt kannst du starten",
          status_text: "Lokale Text-KI ist bereit.",
          focus_hint: "Textkoerper schreiben, ueberarbeiten oder als Bildprompt ableiten.",
          guide_detail: "Text eingeben, Modus waehlen und starten."
        };
      }

      if (textServiceState.stub_mode === true) {
        return {
          key: "stub",
          short_text: "Lokales Modell noch nicht bereit",
          status_text: "Die lokale Text-KI ist sichtbar, aber das Modell ist noch nicht bereit.",
          focus_hint: "Die lokale Text-KI ist sichtbar, aber noch nicht voll einsatzbereit.",
          guide_detail: "Du kannst weiter schreiben. KI-Antworten folgen, sobald das Modell bereit ist."
        };
      }

      const modelStatus = textServiceState.model_status;
      let statusText = "Das lokale Modell ist noch nicht bereit.";
      if (modelStatus === "model_missing") {
        statusText = "Das lokale Modell fehlt noch.";
      } else if (modelStatus === "runner_missing") {
        statusText = "Der lokale Textdienst ist unvollstaendig eingerichtet.";
      } else if (modelStatus === "runner_not_running") {
        statusText = "Der lokale Textdienst ist noch nicht gestartet.";
      } else if (modelStatus === "runner_port_unusable") {
        statusText = "Der lokale Textdienst kann gerade nicht starten.";
      }

      return {
        key: "not_ready",
        short_text: "Lokales Modell noch nicht bereit",
        status_text: statusText,
        focus_hint: "Die Text-KI ist konfiguriert, aber das lokale Modell ist noch nicht bereit.",
        guide_detail: "Du kannst weiter schreiben. KI-Antworten werden aktiv, sobald das Modell bereit ist."
      };
    }

    function buildTextServiceSummaryView() {
      const textServiceState = getTextServiceHealthState();
      if (textServiceState.phase === "pending") {
        return {
          text: "Text-Service wird geprueft...",
          is_error: false
        };
      }

      if (!textServiceState.configured) {
        return {
          text: "Text-Service | nicht konfiguriert",
          is_error: false
        };
      }

      if (!textServiceState.reachable) {
        return {
          text: "Text-Service | nicht erreichbar",
          is_error: false
        };
      }

      const serviceName = isNonEmptyString(textServiceState.service_name)
        ? textServiceState.service_name.trim()
        : "Text-Service";
      const userState = getTextServiceUserState(textServiceState);
      let summary = `${serviceName} | `;
      if (userState.key === "ready") {
        summary += "lokales Modell bereit";
      } else if (userState.key === "stub") {
        summary += "Teststand aktiv";
      } else if (userState.key === "not_ready") {
        summary += "Modell noch nicht bereit";
      } else {
        summary += "online";
      }

      return {
        text: summary,
        is_error: false
      };
    }

    function formatTextServicePromptTestError(error, message) {
      const labels = {
        invalid_json: "Ungueltige Anfrage",
        prompt_not_string: "Prompt ist ungueltig",
        empty_prompt: "Prompt fehlt",
        prompt_too_long: "Prompt ist zu lang",
        text_service_not_configured: "Text-Service nicht konfiguriert",
        config_invalid: "Text-Service Konfiguration ungueltig",
        text_service_unreachable: "Text-Service nicht erreichbar",
        text_service_invalid_response: "Text-Service Antwort ungueltig",
        text_service_request_failed: "Text-Service Anfrage fehlgeschlagen"
      };

      if (isNonEmptyString(message)) {
        return message.trim();
      }
      if (isNonEmptyString(error) && labels[error.trim()]) {
        return labels[error.trim()];
      }
      return "Text-Service-Test fehlgeschlagen";
    }

    function formatTextServiceBasicError(error, message) {
      const labels = {
        invalid_json: "Die Anfrage war ungueltig",
        prompt_not_string: "Bitte gib normalen Text ein",
        empty_prompt: "Bitte gib zuerst Text ein",
        prompt_too_long: `Bitte kuerze deinen Text auf ${TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH} Zeichen`,
        text_service_not_configured: "Text-KI ist gerade nicht verfuegbar",
        config_invalid: "Text-KI ist gerade nicht verfuegbar",
        text_service_unreachable: "Text-KI ist gerade nicht verfuegbar",
        text_service_invalid_response: "Die Antwort konnte gerade nicht gelesen werden",
        text_service_request_failed: "Die Antwort konnte gerade nicht erzeugt werden"
      };

      if (isNonEmptyString(error) && labels[error.trim()]) {
        return labels[error.trim()];
      }
      if (isNonEmptyString(message)) {
        return message.trim();
      }
      return "Die Anfrage konnte nicht abgeschlossen werden";
    }

    function clearTextResponseCopyNotice(scope, rerender = true) {
      if (scope === "basic") {
        if (textServiceBasicCopyNoticeTimeoutId !== null) {
          window.clearTimeout(textServiceBasicCopyNoticeTimeoutId);
          textServiceBasicCopyNoticeTimeoutId = null;
        }
        textServiceBasicCopyNotice = {
          state: "idle",
          text: ""
        };
      } else {
        if (textServicePromptTestCopyNoticeTimeoutId !== null) {
          window.clearTimeout(textServicePromptTestCopyNoticeTimeoutId);
          textServicePromptTestCopyNoticeTimeoutId = null;
        }
        textServicePromptTestCopyNotice = {
          state: "idle",
          text: ""
        };
      }

      if (rerender) {
        renderUi();
      }
    }

    function setTextResponseCopyNotice(scope, state, text) {
      clearTextResponseCopyNotice(scope, false);
      const normalizedText = isNonEmptyString(text) ? text.trim() : "";
      const nextNotice = {
        state,
        text: normalizedText
      };

      if (scope === "basic") {
        textServiceBasicCopyNotice = nextNotice;
        if (state !== "idle" && normalizedText) {
          textServiceBasicCopyNoticeTimeoutId = window.setTimeout(() => {
            clearTextResponseCopyNotice("basic");
          }, TEXT_RESPONSE_COPY_NOTICE_DURATION_MS);
        }
      } else {
        textServicePromptTestCopyNotice = nextNotice;
        if (state !== "idle" && normalizedText) {
          textServicePromptTestCopyNoticeTimeoutId = window.setTimeout(() => {
            clearTextResponseCopyNotice("test");
          }, TEXT_RESPONSE_COPY_NOTICE_DURATION_MS);
        }
      }

      renderUi();
    }

    function clearTextServiceBasicApplyNotice(rerender = true) {
      if (textServiceBasicApplyNoticeTimeoutId !== null) {
        window.clearTimeout(textServiceBasicApplyNoticeTimeoutId);
        textServiceBasicApplyNoticeTimeoutId = null;
      }
      textServiceBasicApplyNotice = {
        state: "idle",
        text: ""
      };
      if (rerender) {
        renderUi();
      }
    }

    function setTextServiceBasicApplyNotice(state, text) {
      clearTextServiceBasicApplyNotice(false);
      const normalizedText = isNonEmptyString(text) ? text.trim() : "";
      textServiceBasicApplyNotice = {
        state,
        text: normalizedText
      };
      if (state !== "idle" && normalizedText) {
        textServiceBasicApplyNoticeTimeoutId = window.setTimeout(() => {
          clearTextServiceBasicApplyNotice();
        }, TEXT_RESPONSE_COPY_NOTICE_DURATION_MS);
      }
      renderUi();
    }

    function loadTextWorkModeMap() {
      try {
        const rawValue = window.localStorage.getItem("local_image_text_work_modes_v1");
        if (!isNonEmptyString(rawValue)) {
          return {};
        }
        const parsed = JSON.parse(rawValue);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch (error) {
        return {};
      }
    }

    function saveTextWorkModeMap(modeMap) {
      try {
        window.localStorage.setItem("local_image_text_work_modes_v1", JSON.stringify(modeMap || {}));
      } catch (error) {
      }
    }

    function normalizeTextWorkMode(value) {
      const normalized = isNonEmptyString(value) ? value.trim().toLowerCase() : "writing";
      return ["writing", "rewrite", "image_prompt"].includes(normalized) ? normalized : "writing";
    }

    function loadTextBodyDraft() {
      try {
        return window.localStorage.getItem("storyforge_text_body_v1") || "";
      } catch {
        return "";
      }
    }

    function saveTextBodyDraft(value) {
      try {
        window.localStorage.setItem("storyforge_text_body_v1", typeof value === "string" ? value : "");
      } catch {}
    }

    function loadSpeechUsageState() {
      try {
        const rawValue = window.localStorage.getItem(SPEECH_USAGE_STORAGE_KEY);
        if (!isNonEmptyString(rawValue)) {
          return {
            text_body_used: false
          };
        }
        const parsed = JSON.parse(rawValue);
        return {
          text_body_used: parsed?.text_body_used === true
        };
      } catch {
        return {
          text_body_used: false
        };
      }
    }

    function persistSpeechUsageState() {
      try {
        window.localStorage.setItem(SPEECH_USAGE_STORAGE_KEY, JSON.stringify({
          text_body_used: speechUsageState.text_body_used === true
        }));
      } catch {}
    }

    function markSpeechUsedForTextBody() {
      if (speechUsageState.text_body_used === true) {
        return;
      }
      speechUsageState.text_body_used = true;
      persistSpeechUsageState();
    }

    function composeTextBodyPrompt(body, instruction, mode) {
      const b = isNonEmptyString(body) ? body.trim() : "";
      const i = isNonEmptyString(instruction) ? instruction.trim() : "";
      if (b && i) return `${b}\n\n${i}`;
      return b || i;
    }

    function getTextBodyEffectiveSource(mode) {
      if (!textBodyEl) return "";
      const normalizedMode = normalizeTextWorkMode(mode);
      if (normalizedMode === "image_prompt") {
        const start = textBodyEl.selectionStart;
        const end = textBodyEl.selectionEnd;
        if (typeof start === "number" && typeof end === "number" && end > start) {
          const selected = textBodyEl.value.substring(start, end).trim();
          if (selected) return selected;
        }
      }
      return textBodyEl.value;
    }

    function hasTextBodySelection() {
      if (!textBodyEl) return false;
      const start = textBodyEl.selectionStart;
      const end = textBodyEl.selectionEnd;
      return typeof start === "number" && typeof end === "number" && end > start;
    }

    function applySceneOverview(overview) {
      if (!overview || typeof overview !== "object") return;
      const previousActiveSceneId = sceneState.active_scene_id;
      sceneState.scenes = Array.isArray(overview.scenes) ? overview.scenes : [];
      sceneState.active_scene_id = typeof overview.active_scene_id === "string" ? overview.active_scene_id : null;
      sceneState.active_scene = overview.active_scene && typeof overview.active_scene === "object" ? overview.active_scene : null;
      sceneState.phase = "ready";
      sceneState.error = null;
      if (sceneState.active_scene_id !== previousActiveSceneId) {
        sceneExportState = {
          phase: "idle",
          text: "",
          export_url: null,
          export_file_name: null,
          export_json_url: null,
          export_json_file_name: null
        };
      }
    }

    function resetSceneResultsState(sceneId = null) {
      sceneResultsState = {
        scene_id: sceneId,
        items: [],
        result_ids: [],
        missing_result_ids: [],
        total_result_count: 0,
        limit: 24,
        loading: false,
        error: null,
        initialized: false
      };
    }

    async function fetchScenes() {
      try {
        const response = await fetch("/scenes");
        if (!response.ok) return;
        const data = await response.json();
        applySceneOverview(data);
        if (isNonEmptyString(sceneState.active_scene_id)) {
          void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
        } else {
          resetSceneResultsState(null);
        }
        renderUi();
      } catch {}
    }

    async function fetchSceneResults(sceneId = sceneState.active_scene_id, options = {}) {
      const normalizedSceneId = isNonEmptyString(sceneId) ? sceneId.trim() : "";
      if (!normalizedSceneId) {
        resetSceneResultsState(null);
        renderUi();
        return null;
      }

      const showLoading = options.showLoading !== false;
      const limit = Number.isFinite(options.limit) && options.limit > 0
        ? Math.min(100, Math.trunc(options.limit))
        : 24;
      const fetchToken = `scene-results-${String(++sceneResultsFetchCounter).padStart(6, "0")}`;
      activeSceneResultsFetchToken = fetchToken;
      sceneResultsState = {
        ...sceneResultsState,
        scene_id: normalizedSceneId,
        loading: showLoading,
        error: null
      };
      if (showLoading) {
        renderUi();
      }

      try {
        const response = await fetch(`/scenes/${encodeURIComponent(normalizedSceneId)}/results?limit=${encodeURIComponent(String(limit))}`, {
          cache: "no-store"
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (activeSceneResultsFetchToken !== fetchToken) {
          return null;
        }

        if (!response.ok || !payload || !Array.isArray(payload.result_ids)) {
          sceneResultsState = {
            ...sceneResultsState,
            loading: false,
            initialized: true,
            error: {
              blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `scene_results_http_${response.status}`,
              message: isNonEmptyString(payload?.message) ? payload.message.trim() : "Szenenbilder sind gerade nicht verfuegbar."
            }
          };
          renderUi();
          return null;
        }

        sceneResultsState = {
          scene_id: normalizedSceneId,
          items: Array.isArray(payload.result_items)
            ? payload.result_items.map((item) => normalizeResultItem(item)).filter((item) => item !== null)
            : [],
          result_ids: payload.result_ids
            .map((value) => (isNonEmptyString(value) ? value.trim() : ""))
            .filter((value) => value),
          missing_result_ids: Array.isArray(payload.missing_result_ids)
            ? payload.missing_result_ids.map((value) => (isNonEmptyString(value) ? value.trim() : "")).filter((value) => value)
            : [],
          total_result_count: Number.isFinite(payload.total_result_count)
            ? Math.max(0, Math.trunc(Number(payload.total_result_count)))
            : (Array.isArray(payload.result_ids) ? payload.result_ids.length : 0),
          limit: Number.isFinite(payload.limit) ? Math.max(1, Math.trunc(Number(payload.limit))) : limit,
          loading: false,
          error: null,
          initialized: true
        };
        renderUi();
        return sceneResultsState.items;
      } catch (error) {
        if (activeSceneResultsFetchToken !== fetchToken) {
          return null;
        }
        sceneResultsState = {
          ...sceneResultsState,
          loading: false,
          initialized: true,
          error: {
            blocker: "scene_results_request_failed",
            message: "Szenenbilder sind gerade nicht verfuegbar."
          }
        };
        renderUi();
        return null;
      }
    }

    async function createScene(title, body) {
      const token = ++sceneActionCounter;
      sceneSaveState = { phase: "loading", message: "Szene wird angelegt..." };
      renderUi();
      try {
        const response = await fetch("/scenes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, body: body || "" })
        });
        if (sceneActionCounter !== token) return;
        const data = await response.json();
        if (response.ok) {
          applySceneOverview(data);
          if (textBodyEl && sceneState.active_scene) {
            textBodyEl.value = sceneState.active_scene.body || "";
            saveTextBodyDraft(textBodyEl.value);
          }
          if (sceneTitleEl && sceneState.active_scene) {
            sceneTitleEl.value = sceneState.active_scene.title || "";
          }
          sceneListOpen = false;
          sceneSaveState = { phase: "idle", message: "" };
          if (isNonEmptyString(sceneState.active_scene_id)) {
            void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
          }
        } else {
          sceneSaveState = { phase: "error", message: data.message || "Fehler beim Anlegen der Szene." };
        }
      } catch {
        if (sceneActionCounter !== token) return;
        sceneSaveState = { phase: "error", message: "Netzwerkfehler" };
      }
      renderUi();
    }

    async function saveScene(sceneId, updates) {
      if (!sceneId) return;
      const token = ++sceneActionCounter;
      sceneSaveState = { phase: "loading", message: "Wird gespeichert..." };
      renderUi();
      try {
        const response = await fetch(`/scenes/${sceneId}/save`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates)
        });
        if (sceneActionCounter !== token) return;
        const data = await response.json();
        if (response.ok) {
          applySceneOverview(data);
          sceneSaveState = { phase: "saved", message: "Gespeichert" };
          window.setTimeout(() => {
            if (sceneSaveState.phase === "saved") {
              sceneSaveState = { phase: "idle", message: "" };
              renderUi();
            }
          }, 2000);
        } else {
          sceneSaveState = { phase: "error", message: data.message || "Fehler beim Speichern." };
        }
      } catch {
        if (sceneActionCounter !== token) return;
        sceneSaveState = { phase: "error", message: "Netzwerkfehler" };
      }
      renderUi();
    }

    async function activateScene(sceneId) {
      if (!sceneId) return;
      const currentBody = textBodyEl ? textBodyEl.value : "";
      if (sceneState.active_scene_id && sceneState.active_scene_id !== sceneId) {
        await saveScene(sceneState.active_scene_id, { body: currentBody });
      }
      const token = ++sceneActionCounter;
      try {
        const response = await fetch(`/scenes/${sceneId}/activate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        if (sceneActionCounter !== token) return;
        if (response.ok) {
          const data = await response.json();
          applySceneOverview(data);
          if (textBodyEl && sceneState.active_scene) {
            textBodyEl.value = sceneState.active_scene.body || "";
            saveTextBodyDraft(textBodyEl.value);
          }
          if (sceneTitleEl && sceneState.active_scene) {
            sceneTitleEl.value = sceneState.active_scene.title || "";
          }
          sceneListOpen = false;
          sceneSaveState = { phase: "idle", message: "" };
          if (isNonEmptyString(sceneState.active_scene_id)) {
            void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
          } else {
            resetSceneResultsState(null);
          }
        }
      } catch {}
      renderUi();
    }

    async function deleteScene(sceneId) {
      if (!sceneId) return;
      const token = ++sceneActionCounter;
      try {
        const response = await fetch(`/scenes/${sceneId}`, { method: "DELETE" });
        if (sceneActionCounter !== token) return;
        if (response.ok) {
          const data = await response.json();
          applySceneOverview(data);
          if (textBodyEl) {
            const body = sceneState.active_scene ? (sceneState.active_scene.body || "") : "";
            textBodyEl.value = body;
            saveTextBodyDraft(body);
          }
          if (sceneTitleEl) {
            sceneTitleEl.value = sceneState.active_scene ? (sceneState.active_scene.title || "") : "";
          }
          sceneSaveState = { phase: "idle", message: "" };
          if (isNonEmptyString(sceneState.active_scene_id)) {
            void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
          } else {
            resetSceneResultsState(null);
          }
        }
      } catch {}
      renderUi();
    }

    async function addResultToActiveScene(resultId) {
      if (!sceneState.active_scene_id || !resultId) return;
      try {
        const response = await fetch(`/scenes/${sceneState.active_scene_id}/results`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ result_id: resultId })
        });
        if (response.ok) {
          void fetchSceneResults(sceneState.active_scene_id, { showLoading: false });
        }
      } catch {}
    }

    function scheduleSaveScene() {
      if (sceneSaveTimer) window.clearTimeout(sceneSaveTimer);
      sceneSaveTimer = window.setTimeout(() => {
        sceneSaveTimer = null;
        if (sceneState.active_scene_id && textBodyEl) {
          saveScene(sceneState.active_scene_id, { body: textBodyEl.value });
        }
      }, 2000);
    }

    function formatSceneLinkedAt(value) {
      if (!isNonEmptyString(value)) {
        return null;
      }
      const parsed = new Date(value.trim());
      if (Number.isNaN(parsed.getTime())) {
        return null;
      }
      return parsed.toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    }

    async function requestSceneExport(sceneId = sceneState.active_scene_id) {
      const normalizedSceneId = isNonEmptyString(sceneId) ? sceneId.trim() : "";
      if (!normalizedSceneId) {
        sceneExportState = {
          phase: "error",
          text: "Keine aktive Szene fuer Export ausgewaehlt.",
          export_url: null,
          export_file_name: null,
          export_json_url: null,
          export_json_file_name: null
        };
        renderUi();
        return { ok: false, blocker: "scene_not_selected" };
      }

      const token = `scene-export-${String(++sceneExportCounter).padStart(6, "0")}`;
      activeSceneExportToken = token;
      sceneExportState = {
        phase: "running",
        text: "Szenenexport wird erstellt...",
        export_url: null,
        export_file_name: null,
        export_json_url: null,
        export_json_file_name: null
      };
      renderUi();

      try {
        const response = await fetch(`/scenes/${encodeURIComponent(normalizedSceneId)}/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }
        if (activeSceneExportToken !== token) {
          return { ok: false, blocker: "scene_export_superseded" };
        }

        if (!response.ok || !payload || payload.status !== "ok" || !isNonEmptyString(payload.export_url)) {
          const fallbackMessage = "Szenenexport konnte gerade nicht erstellt werden.";
          sceneExportState = {
            phase: "error",
            text: isNonEmptyString(payload?.message) ? payload.message.trim() : fallbackMessage,
            export_url: null,
            export_file_name: null,
            export_json_url: null,
            export_json_file_name: null
          };
          renderUi();
          return { ok: false, blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `scene_export_http_${response.status}` };
        }

        const exportedCount = Number.isFinite(payload.exported_result_count) ? Math.max(0, Math.trunc(Number(payload.exported_result_count))) : 0;
        const totalCount = Number.isFinite(payload.total_result_count) ? Math.max(0, Math.trunc(Number(payload.total_result_count))) : exportedCount;
        const fileName = isNonEmptyString(payload.export_file_name) ? payload.export_file_name.trim() : "scene-export.md";
        sceneExportState = {
          phase: "success",
          text: `Szenenexport erstellt | ${exportedCount}/${totalCount} Bildbezuge enthalten.`,
          export_url: payload.export_url.trim(),
          export_file_name: fileName,
          export_json_url: isNonEmptyString(payload.export_json_url) ? payload.export_json_url.trim() : null,
          export_json_file_name: isNonEmptyString(payload.export_json_file_name) ? payload.export_json_file_name.trim() : null
        };
        renderUi();
        return { ok: true, payload };
      } catch (error) {
        if (activeSceneExportToken !== token) {
          return { ok: false, blocker: "scene_export_superseded" };
        }
        sceneExportState = {
          phase: "error",
          text: "Szenenexport konnte gerade nicht erstellt werden.",
          export_url: null,
          export_file_name: null,
          export_json_url: null,
          export_json_file_name: null
        };
        renderUi();
        return { ok: false, blocker: "scene_export_request_failed" };
      }
    }

    function renderSceneResultsPanel() {
      if (!sceneResultsPanelEl || !sceneResultsStateEl || !sceneResultsGridEl) {
        return;
      }

      const hasScene = isNonEmptyString(sceneState.active_scene_id);
      sceneResultsPanelEl.hidden = false;
      if (sceneResultsRefreshEl) {
        sceneResultsRefreshEl.disabled = !hasScene || sceneResultsState.loading;
      }
      if (sceneExportEl) {
        sceneExportEl.disabled = !hasScene || sceneExportState.phase === "running";
      }

      if (!hasScene) {
        sceneResultsStateEl.textContent = "Szene laden, um zugeordnete Bilder zu sehen.";
        sceneResultsStateEl.className = "request-state";
        sceneResultsGridEl.replaceChildren();
      } else if (sceneResultsState.loading && !sceneResultsState.initialized) {
        sceneResultsStateEl.textContent = "Szenenbilder werden geladen...";
        sceneResultsStateEl.className = "request-state";
      } else if (sceneResultsState.error) {
        sceneResultsStateEl.textContent = sceneResultsState.error.message || "Szenenbilder sind gerade nicht verfuegbar.";
        sceneResultsStateEl.className = "request-state error";
      } else {
        const visibleCount = Array.isArray(sceneResultsState.items) ? sceneResultsState.items.length : 0;
        const totalCount = Number.isFinite(sceneResultsState.total_result_count)
          ? Math.max(0, Math.trunc(Number(sceneResultsState.total_result_count)))
          : visibleCount;
        if (totalCount <= 0) {
          sceneResultsStateEl.textContent = "Noch keine Bilder mit dieser Szene verknuepft.";
          sceneResultsStateEl.className = "request-state";
        } else {
          const hiddenCount = Math.max(0, totalCount - visibleCount);
          sceneResultsStateEl.textContent = hiddenCount > 0
            ? `${visibleCount} von ${totalCount} Szenenbildern sichtbar.`
            : `${visibleCount} Szenenbilder sichtbar.`;
          sceneResultsStateEl.className = "request-state";
        }
      }

      if (sceneExportStateEl) {
        sceneExportStateEl.className = sceneExportState.phase === "error" ? "request-state error" : "request-state";
        sceneExportStateEl.replaceChildren();
        if (!hasScene) {
          sceneExportStateEl.appendChild(document.createTextNode("Export wird aktiv, sobald eine Szene ausgewaehlt ist."));
        } else if (isNonEmptyString(sceneExportState.text)) {
          sceneExportStateEl.appendChild(document.createTextNode(sceneExportState.text.trim()));
        } else {
          sceneExportStateEl.appendChild(document.createTextNode("Exportiert Text und Bildbezuge der aktiven Szene."));
        }
        if (isNonEmptyString(sceneExportState.export_url)) {
          const linkEl = document.createElement("a");
          linkEl.href = sceneExportState.export_url.trim();
          linkEl.download = isNonEmptyString(sceneExportState.export_file_name) ? sceneExportState.export_file_name.trim() : "";
          linkEl.textContent = "Markdown herunterladen";
          sceneExportStateEl.appendChild(document.createTextNode(" "));
          sceneExportStateEl.appendChild(linkEl);
        }
        if (isNonEmptyString(sceneExportState.export_json_url)) {
          const jsonLinkEl = document.createElement("a");
          jsonLinkEl.href = sceneExportState.export_json_url.trim();
          jsonLinkEl.download = isNonEmptyString(sceneExportState.export_json_file_name) ? sceneExportState.export_json_file_name.trim() : "";
          jsonLinkEl.textContent = "JSON herunterladen";
          sceneExportStateEl.appendChild(document.createTextNode(" "));
          sceneExportStateEl.appendChild(jsonLinkEl);
        }
      }

      sceneResultsGridEl.replaceChildren();
      if (!hasScene || !Array.isArray(sceneResultsState.items) || sceneResultsState.items.length === 0) {
        return;
      }

      for (const item of sceneResultsState.items) {
        const cardEl = document.createElement("article");
        cardEl.className = "scene-result-card";

        const thumbEl = document.createElement("img");
        thumbEl.className = "scene-result-thumb";
        thumbEl.src = item.preview_url;
        thumbEl.alt = "Szenenbild";
        thumbEl.loading = "lazy";
        thumbEl.decoding = "async";
        thumbEl.addEventListener("click", () => {
          openResultsPreview(item);
        });

        const metaEl = document.createElement("div");
        metaEl.className = "scene-result-meta";
        const linkedAtText = formatSceneLinkedAt(item.scene_linked_at);
        const createdAtText = formatResultCreatedAt(item.created_at);
        metaEl.textContent = linkedAtText
          ? `${formatResultModeLabel(item.mode)} | Zugeordnet: ${linkedAtText} | Bild: ${createdAtText}`
          : `${formatResultModeLabel(item.mode)} | Bild: ${createdAtText}`;

        const actionsEl = document.createElement("div");
        actionsEl.className = "scene-result-actions";

        const previewButtonEl = document.createElement("button");
        previewButtonEl.type = "button";
        previewButtonEl.className = "text-copy-button";
        previewButtonEl.textContent = "Vorschau";
        previewButtonEl.addEventListener("click", () => {
          openResultsPreview(item);
        });
        actionsEl.appendChild(previewButtonEl);

        const loadButtonEl = document.createElement("button");
        loadButtonEl.type = "button";
        loadButtonEl.className = "text-copy-button";
        loadButtonEl.textContent = currentUpload ? "Bild wird geladen..." : "Als Ausgangsbild";
        loadButtonEl.disabled = Boolean(currentUpload);
        loadButtonEl.addEventListener("click", () => {
          void loadResultAsInputImage(item.result_id, { closePreview: false, item });
        });
        actionsEl.appendChild(loadButtonEl);

        cardEl.appendChild(thumbEl);
        cardEl.appendChild(metaEl);
        cardEl.appendChild(actionsEl);
        sceneResultsGridEl.appendChild(cardEl);
      }
    }

    function renderScenePanel() {
      if (!sceneTitleEl || !sceneListEl || !sceneListPanelEl || !sceneToggleListEl) return;
      const activeScene = sceneState.active_scene;
      const hasScene = Boolean(activeScene);
      const scenes = Array.isArray(sceneState.scenes) ? sceneState.scenes : [];
      const totalSceneCount = scenes.length;

      if (hasScene && document.activeElement !== sceneTitleEl) {
        const newTitle = activeScene.title || "";
        if (sceneTitleEl.value !== newTitle) sceneTitleEl.value = newTitle;
      }

      if (scenePanelRootEl) {
        scenePanelRootEl.classList.toggle("scene-panel-active", hasScene);
        scenePanelRootEl.classList.toggle("scene-panel-inactive", !hasScene);
      }

      if (sceneDeleteEl) sceneDeleteEl.hidden = !hasScene;

      if (sceneToggleListEl) {
        sceneToggleListEl.textContent = sceneListOpen
          ? `Szenen ausblenden (${totalSceneCount})`
          : `Szenen anzeigen (${totalSceneCount})`;
        sceneToggleListEl.classList.toggle("active", sceneListOpen);
      }

      if (sceneListPanelEl) sceneListPanelEl.hidden = !sceneListOpen;

      if (sceneListOpen && sceneListEl) {
        if (scenes.length === 0) {
          sceneListEl.innerHTML = '<div class="scene-list-empty">Noch keine Szenen vorhanden.</div>';
        } else {
          sceneListEl.innerHTML = scenes.map((scene) => {
            const isActive = scene.id === sceneState.active_scene_id;
            const preview = scene.body ? scene.body.slice(0, 60).replace(/\s+/g, " ").trim() : "";
            return `<div class="scene-list-item${isActive ? " scene-list-item-active" : ""}" data-scene-id="${scene.id}">
              <div class="scene-list-item-title">${escapeHtml(scene.title)}</div>
              ${preview ? `<div class="scene-list-item-preview">${escapeHtml(preview)}${scene.body && scene.body.length > 60 ? "..." : ""}</div>` : ""}
            </div>`;
          }).join("");
        }
      }

      if (sceneContextMetaEl) {
        if (!hasScene) {
          sceneContextMetaEl.textContent = "Noch keine aktive Szene. Neue Szene anlegen, um Text und Bilder gemeinsam zu fuehren.";
        } else {
          const sceneTitle = isNonEmptyString(activeScene.title) ? activeScene.title.trim() : "Unbenannte Szene";
          if (
            sceneResultsState.loading &&
            sceneResultsState.scene_id === sceneState.active_scene_id &&
            sceneResultsState.initialized !== true
          ) {
            sceneContextMetaEl.textContent = `Aktiv: ${sceneTitle} | Bildbezuege werden geladen...`;
          } else if (
            sceneResultsState.error &&
            sceneResultsState.scene_id === sceneState.active_scene_id
          ) {
            sceneContextMetaEl.textContent = `Aktiv: ${sceneTitle} | Bildbezuege sind gerade nicht verfuegbar.`;
          } else {
            const totalCount = Number.isFinite(sceneResultsState.total_result_count)
              ? Math.max(0, Math.trunc(Number(sceneResultsState.total_result_count)))
              : 0;
            sceneContextMetaEl.textContent = totalCount > 0
              ? `Aktiv: ${sceneTitle} | ${totalCount} zugeordnete Bilder`
              : `Aktiv: ${sceneTitle} | Noch keine zugeordneten Bilder`;
          }
        }
      }

      if (sceneSaveStateEl) {
        if (sceneSaveState.phase === "loading") {
          sceneSaveStateEl.textContent = sceneSaveState.message;
          sceneSaveStateEl.className = "request-state scene-save-state scene-save-loading";
        } else if (sceneSaveState.phase === "saved") {
          sceneSaveStateEl.textContent = sceneSaveState.message;
          sceneSaveStateEl.className = "request-state scene-save-state scene-save-ok";
        } else if (sceneSaveState.phase === "error") {
          sceneSaveStateEl.textContent = sceneSaveState.message;
          sceneSaveStateEl.className = "request-state scene-save-state scene-save-error";
        } else {
          sceneSaveStateEl.textContent = hasScene ? "" : "Neue Szene anlegen, um Texte zu speichern.";
          sceneSaveStateEl.className = "request-state scene-save-state";
        }
      }
      renderSceneResultsPanel();
    }

    function escapeHtml(str) {
      return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function getTextWorkModeHint(mode = currentTextWorkMode) {
      const normalizedMode = normalizeTextWorkMode(mode);
      if (normalizedMode === "rewrite") {
        return "Ueberarbeiten: KI verbessert, schaerft oder formiert den Textkoerper um.";
      }
      if (normalizedMode === "image_prompt") {
        return "Bildprompt: KI leitet aus dem Textkoerper einen visuellen Prompt ab.";
      }
      return "Schreiben: KI setzt den Textkoerper fort oder entwickelt ihn weiter.";
    }

    function syncTextWorkModeFromActiveSlot() {
      const slotIndex = Number.isFinite(Number(textChatState.active_slot_index)) ? Number(textChatState.active_slot_index) : 1;
      const modeMap = loadTextWorkModeMap();
      currentTextWorkMode = normalizeTextWorkMode(modeMap[String(slotIndex)] || "writing");
    }

    function setTextWorkMode(mode) {
      const normalizedMode = normalizeTextWorkMode(mode);
      currentTextWorkMode = normalizedMode;
      const slotIndex = Number.isFinite(Number(textChatState.active_slot_index)) ? Number(textChatState.active_slot_index) : 1;
      const modeMap = loadTextWorkModeMap();
      modeMap[String(slotIndex)] = normalizedMode;
      saveTextWorkModeMap(modeMap);
      renderUi();
    }

    function getTextChatActiveChat() {
      return textChatState && textChatState.active_chat && typeof textChatState.active_chat === "object"
        ? textChatState.active_chat
        : null;
    }

    function getTextChatModelProfiles() {
      return textChatState && Array.isArray(textChatState.model_profiles) ? textChatState.model_profiles : [];
    }

    function getTextChatActiveModelProfile() {
      const activeChat = getTextChatActiveChat();
      const activeProfileId = activeChat && isNonEmptyString(activeChat.model_profile)
        ? activeChat.model_profile.trim()
        : (isNonEmptyString(textChatState.current_model_profile_id) ? textChatState.current_model_profile_id.trim() : "standard");
      return getTextChatModelProfiles().find((profile) => profile && profile.id === activeProfileId) || null;
    }

    function getEffectiveTextModelSwitchState() {
      if (textModelSwitchUiState.phase === "loading") {
        return {
          phase: "loading",
          target_profile_id: textModelSwitchUiState.profile_id,
          message: textModelSwitchUiState.message
        };
      }
      if (textChatState && textChatState.model_switch_state && typeof textChatState.model_switch_state === "object") {
        return textChatState.model_switch_state;
      }
      return null;
    }

    function getTextChatLastAssistantMessage() {
      const activeChat = getTextChatActiveChat();
      if (!activeChat || !Array.isArray(activeChat.messages)) {
        return "";
      }
      for (let index = activeChat.messages.length - 1; index >= 0; index -= 1) {
        const message = activeChat.messages[index];
        if (message && message.role === "assistant" && isNonEmptyString(message.content)) {
          return message.content.trim();
        }
      }
      return "";
    }

    function syncTextServiceBasicStateFromChat() {
      const lastAssistantMessage = getTextChatLastAssistantMessage();
      const activeChat = getTextChatActiveChat();
      if (textServiceBasicPromptState.phase === "sending") {
        return;
      }
      if (isNonEmptyString(lastAssistantMessage)) {
        textServiceBasicPromptState = {
          phase: "success",
          request_token: null,
          response_text: lastAssistantMessage,
          error: null,
          error_message: null,
          stub: false,
          service: getTextServiceHealthState().service_name,
          model_status: activeChat && isNonEmptyString(activeChat.model) ? activeChat.model.trim() : getTextServiceHealthState().model_status
        };
        return;
      }
      textServiceBasicPromptState = {
        phase: "idle",
        request_token: null,
        response_text: null,
        error: null,
        error_message: null,
        stub: null,
        service: null,
        model_status: null
      };
    }

    function applyTextChatPayload(payload) {
      if (!payload || payload.ok !== true) {
        return false;
      }
      const nextSlots = Array.isArray(payload.slots) ? payload.slots : [];
      const activeSlotIndex = Number.isFinite(Number(payload.active_slot_index)) ? Number(payload.active_slot_index) : 1;
      textChatState = {
        phase: "ready",
        slots: nextSlots,
        active_slot_index: activeSlotIndex,
        active_chat: payload.active_chat && typeof payload.active_chat === "object" ? payload.active_chat : null,
        model_profiles: Array.isArray(payload.model_profiles) ? payload.model_profiles : [],
        current_model_profile_id: isNonEmptyString(payload.current_model_profile_id) ? payload.current_model_profile_id.trim() : "standard",
        model_switch_state: payload.model_switch_state && typeof payload.model_switch_state === "object" ? payload.model_switch_state : null,
        error: null
      };
      textModelSwitchUiState = {
        phase: "idle",
        profile_id: null,
        message: ""
      };
      syncTextWorkModeFromActiveSlot();
      syncTextServiceBasicStateFromChat();
      return true;
    }

    async function fetchTextChats(options = {}) {
      const forceFresh = options.forceFresh === true;
      if (textChatFetchPromise && !forceFresh) {
        return textChatFetchPromise;
      }
      if (textChatFetchPromise && forceFresh) {
        try {
          await textChatFetchPromise;
        } catch (error) {
        }
      }
      textChatState.phase = "loading";
      textChatFetchPromise = (async () => {
        try {
          const response = await fetch("/text-service/chats", { cache: "no-store" });
          const payload = await response.json();
          if (!response.ok || !applyTextChatPayload(payload)) {
            throw new Error(isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : "text_chat_fetch_failed");
          }
          renderUi();
          return payload;
        } catch (error) {
          textChatState.phase = "error";
          textChatState.error = error instanceof Error ? error.message : String(error);
          renderUi();
          return null;
        } finally {
          textChatFetchPromise = null;
        }
      })();
      return textChatFetchPromise;
    }

    async function postTextChatAction(url, payload = {}) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      let responsePayload = null;
      try {
        responsePayload = await response.json();
      } catch (error) {
        responsePayload = null;
      }
      if (!response.ok || !responsePayload || responsePayload.ok !== true) {
        const blocker = isNonEmptyString(responsePayload?.blocker) ? responsePayload.blocker.trim() : `text_chat_http_${response.status}`;
        const message = isNonEmptyString(responsePayload?.message) ? responsePayload.message.trim() : "Text-Chat-Aktion fehlgeschlagen.";
        throw new Error(`${blocker} | ${message}`);
      }
      applyTextChatPayload(responsePayload);
      renderUi();
      return responsePayload;
    }

    async function activateTextChatSlot(slotIndex) {
      const slot = Array.isArray(textChatState.slots)
        ? textChatState.slots.find((candidate) => candidate && Number(candidate.slot_index) === Number(slotIndex))
        : null;
      textModelSwitchUiState = {
        phase: "loading",
        profile_id: slot && isNonEmptyString(slot.model_profile) ? slot.model_profile.trim() : null,
        message: "Modellstatus wird aktualisiert..."
      };
      renderUi();
      try {
        await postTextChatAction(`/text-service/chats/slot/${slotIndex}/activate`);
      } catch (error) {
        textModelSwitchUiState = {
          phase: "idle",
          profile_id: null,
          message: ""
        };
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_activate_failed",
          error_message: error instanceof Error ? error.message : "Chat konnte nicht aktiviert werden.",
          stub: false,
          service: null,
          model_status: null
        };
        renderUi();
      }
    }

    async function createTextChat() {
      try {
        const activeSlotIndex = Number(textChatState.active_slot_index);
        const activeChat = getTextChatActiveChat();
        const slotCount = Number(textChatState.slot_count) > 0 ? Number(textChatState.slot_count) : 5;
        if (Number.isFinite(activeSlotIndex) && activeSlotIndex >= 1 && activeSlotIndex <= slotCount && activeChat && activeChat.occupied !== true) {
          await postTextChatAction(`/text-service/chats/slot/${activeSlotIndex}/replace`, {});
          return;
        }
        await postTextChatAction("/text-service/chats/new", {});
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_create_failed",
          error_message: message.includes("text_chat_slots_full")
            ? "Alle 5 Chat-Slots sind belegt. Leere zuerst einen Slot."
            : "Neuer Chat konnte gerade nicht angelegt werden.",
          stub: false,
          service: null,
          model_status: null
        };
        renderUi();
      }
    }

    async function renameActiveTextChat() {
      const activeChat = getTextChatActiveChat();
      if (!activeChat) {
        return;
      }
      const nextTitle = window.prompt("Chat-Titel", activeChat.title || "");
      if (nextTitle === null) {
        return;
      }
      try {
        await postTextChatAction(`/text-service/chats/slot/${textChatState.active_slot_index}/rename`, {
          title: nextTitle
        });
      } catch (error) {
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_rename_failed",
          error_message: "Chat konnte nicht umbenannt werden.",
          stub: false,
          service: null,
          model_status: null
        };
        renderUi();
      }
    }

    async function clearActiveTextChat() {
      const activeChat = getTextChatActiveChat();
      if (!activeChat || activeChat.occupied !== true) {
        return;
      }
      if (!window.confirm(`Diesen Chat wirklich leeren?\n\n${activeChat.title || "Aktiver Chat"}`)) {
        return;
      }
      try {
        await postTextChatAction(`/text-service/chats/slot/${textChatState.active_slot_index}/clear`, {});
        textServiceBasicPromptEl.value = "";
      } catch (error) {
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_clear_failed",
          error_message: "Chat konnte nicht geleert werden.",
          stub: false,
          service: null,
          model_status: null
        };
        renderUi();
      }
    }

    async function selectTextModelProfile(profileId) {
      const activeChat = getTextChatActiveChat();
      if (!activeChat || activeChat.occupied !== true) {
        return;
      }
      try {
        textModelSwitchUiState = {
          phase: "loading",
          profile_id: profileId,
          message: "Modell wird vorbereitet..."
        };
        renderUi();
        await postTextChatAction(`/text-service/chats/slot/${textChatState.active_slot_index}/profile`, {
          model_profile: profileId
        });
      } catch (error) {
        textModelSwitchUiState = {
          phase: "idle",
          profile_id: null,
          message: ""
        };
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_model_profile_change_failed",
          error_message: error instanceof Error ? error.message : "Modellprofil konnte nicht gewechselt werden.",
          stub: false,
          service: null,
          model_status: null
        };
        renderUi();
      }
    }

    function getTextServiceBasicResponseText() {
      if (textServiceBasicPromptState.phase !== "success" || !isNonEmptyString(textServiceBasicPromptState.response_text)) {
        return "";
      }
      return textServiceBasicPromptState.response_text.trim();
    }

    function getTextServiceBasicApplyTargetTaskId() {
      if (!(textServiceBasicApplyTargetEl instanceof HTMLSelectElement)) {
        return "create";
      }
      const selected = isNonEmptyString(textServiceBasicApplyTargetEl.value) ? textServiceBasicApplyTargetEl.value.trim() : "create";
      return ["create", "edit", "inpaint"].includes(selected) ? selected : "create";
    }

    function applyTextServiceBasicResponseToImagePrompt(targetTaskId = "create") {
      const normalizedTaskId = ["create", "edit", "inpaint"].includes(targetTaskId) ? targetTaskId : "create";
      const responseText = getTextServiceBasicResponseText();
      if (!responseText) {
        setTextServiceBasicApplyNotice("error", "Keine nutzbare Antwort vorhanden");
        return false;
      }

      const taskLabelById = {
        create: "Neues Bild erstellen",
        edit: "Bild anpassen",
        inpaint: "Bereich im Bild aendern"
      };
      promptEl.value = responseText;
      setV7BasicTask(normalizedTaskId);
      promptEl.focus();
      promptEl.setSelectionRange(promptEl.value.length, promptEl.value.length);
      const successText = `Prompt uebernommen fuer ${taskLabelById[normalizedTaskId] || "Neues Bild erstellen"}`;
      setTextServiceBasicApplyNotice("success", successText);
      setTransientInfoNotice({
        code: "text_prompt_applied",
        message: successText
      });
      renderUi();
      return true;
    }

    async function writeTextToClipboard(text) {
      const normalizedText = isNonEmptyString(text) ? text.trim() : "";
      if (!normalizedText) {
        return false;
      }

      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        try {
          await navigator.clipboard.writeText(normalizedText);
          return true;
        } catch (error) {
        }
      }

      const fallbackArea = document.createElement("textarea");
      fallbackArea.value = normalizedText;
      fallbackArea.setAttribute("readonly", "readonly");
      fallbackArea.style.position = "fixed";
      fallbackArea.style.opacity = "0";
      fallbackArea.style.pointerEvents = "none";
      fallbackArea.style.left = "-9999px";
      fallbackArea.style.top = "0";
      document.body.appendChild(fallbackArea);
      fallbackArea.focus();
      fallbackArea.select();
      fallbackArea.setSelectionRange(0, fallbackArea.value.length);

      try {
        return document.execCommand("copy") === true;
      } catch (error) {
        return false;
      } finally {
        fallbackArea.remove();
      }
    }

    async function attemptCopyTextResponse(scope) {
      const responseEl = scope === "basic" ? textServiceBasicResponseEl : textServiceTestResponseEl;
      const visibleText = responseEl.textContent.trim();
      if (!isNonEmptyString(visibleText)) {
        setTextResponseCopyNotice(scope, "error", "Kopieren fehlgeschlagen");
        return false;
      }

      const copied = await writeTextToClipboard(visibleText);
      if (copied) {
        setTextResponseCopyNotice(scope, "success", "Kopiert");
        return true;
      }

      setTextResponseCopyNotice(scope, "error", "Kopieren fehlgeschlagen");
      return false;
    }

    function isTextServicePromptTestRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        isNonEmptyString(textServicePromptTestState.request_token) &&
        textServicePromptTestState.request_token === requestToken
      );
    }

    function renderTextServiceTestUi() {
      const textServiceState = getTextServiceHealthState();
      const sending = textServicePromptTestState.phase === "sending";
      const enabled = textServiceState.reachable && !sending;
      const hasCopyableResponse = textServicePromptTestState.phase === "success" && isNonEmptyString(textServicePromptTestState.response_text);

      textServicePromptEl.disabled = !enabled;
      textServiceSendEl.disabled = !enabled;
      textServiceTestCopyEl.disabled = !hasCopyableResponse;

      if (sending) {
        textServiceTestStateEl.textContent = "Test laeuft...";
      } else if (textServiceState.phase === "pending") {
        textServiceTestStateEl.textContent = "Verfuegbarkeit wird geprueft...";
      } else if (!textServiceState.configured) {
        textServiceTestStateEl.textContent = "Text-Service nicht konfiguriert";
      } else if (!textServiceState.reachable) {
        textServiceTestStateEl.textContent = "Text-Service nicht erreichbar";
      } else if (textServiceState.stub_mode === true) {
        textServiceTestStateEl.textContent = "Stub-Betrieb bereit";
      } else if (textServiceState.inference_available === true) {
        textServiceTestStateEl.textContent = "Text-Service bereit";
      } else {
        textServiceTestStateEl.textContent = "Modell noch nicht bereit";
      }
      textServiceTestStateEl.className = "request-state";

      if (textServicePromptTestState.phase === "success" && isNonEmptyString(textServicePromptTestState.response_text)) {
        const serviceName = isNonEmptyString(textServicePromptTestState.service)
          ? `${textServicePromptTestState.service} | `
          : "";
        textServiceTestResponseEl.textContent = `${serviceName}${textServicePromptTestState.response_text}`;
        textServiceTestResponseEl.className = "request-state";
      } else if (textServicePromptTestState.phase === "error") {
        textServiceTestResponseEl.textContent = formatTextServicePromptTestError(
          textServicePromptTestState.error,
          textServicePromptTestState.error_message
        );
        textServiceTestResponseEl.className = "request-state error";
      } else if (textServiceState.reachable) {
        let responseSummary = "Text-Service online | Modell noch nicht bereit";
        if (textServiceState.stub_mode === true) {
          responseSummary = "Stub-Betrieb aktiv | keine Inferenz";
        } else if (textServiceState.inference_available === true) {
          responseSummary = "Lokales Modell aktiv | Inferenz bereit";
        }
        textServiceTestResponseEl.textContent = responseSummary;
        textServiceTestResponseEl.className = "request-state";
      } else {
        textServiceTestResponseEl.textContent = "";
        textServiceTestResponseEl.className = "request-state";
      }

      if (!hasCopyableResponse && textServicePromptTestCopyNotice.state !== "idle") {
        clearTextResponseCopyNotice("test", false);
      }
      textServiceTestCopyStateEl.textContent = hasCopyableResponse ? textServicePromptTestCopyNotice.text : "";
      textServiceTestCopyStateEl.className = textServicePromptTestCopyNotice.state === "error" ? "text-copy-feedback error" : "text-copy-feedback";
    }

    function isTextServiceBasicPromptRelevant(requestToken) {
      return (
        isNonEmptyString(requestToken) &&
        isNonEmptyString(textServiceBasicPromptState.request_token) &&
        textServiceBasicPromptState.request_token === requestToken
      );
    }

    function renderTextServiceBasicUi() {
      const textServiceState = getTextServiceHealthState();
      const userState = getTextServiceUserState(textServiceState);
      const sending = textServiceBasicPromptState.phase === "sending";
      const available = userState.key === "ready";
      const basicLeadView = deriveBasicTextTaskLeadView();
      const hasCopyableResponse = textServiceBasicPromptState.phase === "success" && isNonEmptyString(textServiceBasicPromptState.response_text);
      const hasTransferableResponse = hasCopyableResponse;
      const activeChat = getTextChatActiveChat();
      const activeMessages = activeChat && Array.isArray(activeChat.messages) ? activeChat.messages : [];
      const hasActiveChat = Boolean(activeChat);
      const activeMode = normalizeTextWorkMode(currentTextWorkMode);
      const modelProfiles = getTextChatModelProfiles();
      const activeProfile = getTextChatActiveModelProfile();
      const modelSwitchState = getEffectiveTextModelSwitchState();
      const activeProfileReady = !hasActiveChat || activeChat.occupied !== true || (activeProfile && activeProfile.active_for_requests === true);
      let statusText = userState.status_text;

      textServiceBasicPromptEl.disabled = sending;
      textServiceBasicSendEl.disabled = !available || sending || !activeProfileReady || (modelSwitchState && modelSwitchState.phase === "loading");
      if (textChatNewEl) {
        textChatNewEl.disabled = sending;
      }
      if (textChatRenameEl) {
        textChatRenameEl.disabled = sending || !(hasActiveChat && activeChat.occupied === true);
      }
      if (textChatClearEl) {
        textChatClearEl.disabled = sending || !(hasActiveChat && activeChat.occupied === true);
      }
      if (textServiceBasicApplyImagePromptEl) {
        textServiceBasicApplyImagePromptEl.disabled = !hasTransferableResponse;
      }
      if (textBodyInsertEl) {
        textBodyInsertEl.disabled = !hasTransferableResponse;
      }
      if (textBodyReplaceEl) {
        textBodyReplaceEl.disabled = !hasTransferableResponse;
      }
      if (textResponsePanelEl) {
        textResponsePanelEl.dataset.mode = activeMode;
      }
      if (textBodyContextHintEl) {
        if (activeMode === "image_prompt" && textBodyEl && isNonEmptyString(textBodyEl.value)) {
          const hasSelection = hasTextBodySelection();
          textBodyContextHintEl.hidden = false;
          textBodyContextHintEl.textContent = hasSelection
            ? "Markierter Abschnitt wird als Quelle verwendet"
            : "Gesamter Textkoerper wird als Quelle verwendet";
          textBodyContextHintEl.className = hasSelection
            ? "text-body-context-hint text-body-context-hint-selection"
            : "text-body-context-hint text-body-context-hint-full";
        } else {
          textBodyContextHintEl.hidden = true;
        }
      }
      const hasImagePromptSuccess = hasCopyableResponse && activeMode === "image_prompt";
      if (textToImageForwardEl) {
        textToImageForwardEl.hidden = !hasImagePromptSuccess;
      }
      if (textImageNegativePromptBlockEl) {
        textImageNegativePromptBlockEl.hidden = activeMode !== "image_prompt";
      }
      if (textImageNegativePromptHintEl) {
        if (activeMode !== "image_prompt") {
          textImageNegativePromptHintEl.textContent = "";
        } else {
          const negativePromptValue = isNonEmptyString(textImageNegativePromptEl?.value)
            ? textImageNegativePromptEl.value.trim()
            : "";
          textImageNegativePromptHintEl.textContent = negativePromptValue
            ? "Negativprompt aktiv."
            : "Kein Negativprompt gesetzt (optional).";
        }
      }
      renderScenePanel();
      if (textServiceBasicApplyTargetEl instanceof HTMLSelectElement) {
        const normalizedTarget = getTextServiceBasicApplyTargetTaskId();
        if (textServiceBasicApplyTargetEl.value !== normalizedTarget) {
          textServiceBasicApplyTargetEl.value = normalizedTarget;
        }
      }
      textServiceBasicCopyEl.disabled = !hasCopyableResponse;
      textServiceBasicSendEl.textContent = activeMode === "rewrite"
        ? "Text ueberarbeiten"
        : (activeMode === "image_prompt" ? "Bildprompt ableiten" : "Weiter mit Text");
      const instructionPlaceholder = activeMode === "rewrite"
        ? "Worauf soll die KI bei der Ueberarbeitung achten? (optional)"
        : (activeMode === "image_prompt"
          ? "Stil oder Fokus fuer den Bildprompt (optional)"
          : "Wie soll der Text weitergehen? (optional)");
      if (textServiceBasicPromptEl && textServiceBasicPromptEl.placeholder !== instructionPlaceholder) {
        textServiceBasicPromptEl.placeholder = instructionPlaceholder;
      }
      textServiceBasicStateEl.textContent = basicLeadView.text;
      textServiceBasicStateEl.className = basicLeadView.is_error ? "request-state error" : "request-state";
      if (textWorkModeWritingEl) {
        textWorkModeWritingEl.classList.toggle("active", activeMode === "writing");
      }
      if (textWorkModeRewriteEl) {
        textWorkModeRewriteEl.classList.toggle("active", activeMode === "rewrite");
      }
      if (textWorkModeImageEl) {
        textWorkModeImageEl.classList.toggle("active", activeMode === "image_prompt");
      }
      if (textWorkModeHintEl) {
        textWorkModeHintEl.textContent = getTextWorkModeHint(activeMode);
      }
      if (textServiceBasicSectionHintEl) {
        textServiceBasicSectionHintEl.textContent = activeMode === "rewrite"
          ? "Textkoerper gezielt verbessern"
          : (activeMode === "image_prompt"
            ? "Bildprompt aus dem Textkoerper ableiten"
            : "Textkoerper schreiben und mit lokaler KI weiterfuehren");
      }
      if (textServiceBasicGuideEl) {
        textServiceBasicGuideEl.hidden = false;
        textServiceBasicGuideEl.textContent = activeMode === "rewrite"
          ? "Text markieren oder komplett ueberarbeiten lassen."
          : (activeMode === "image_prompt"
            ? "Textquelle waehlen, Prompt ableiten und in den Bildschritt geben."
            : "Text schreiben und lokal weiterentwickeln.");
      }
      if (textChatSlotStateEl) {
        if (textChatState.phase === "loading") {
          textChatSlotStateEl.textContent = "Chat-Slots werden geladen...";
          textChatSlotStateEl.className = "request-state";
        } else if (textChatState.phase === "error") {
          textChatSlotStateEl.textContent = "Chat-Slots gerade nicht verfuegbar";
          textChatSlotStateEl.className = "request-state error";
        } else {
          const occupiedCount = Array.isArray(textChatState.slots)
            ? textChatState.slots.filter((slot) => slot && slot.occupied === true).length
            : 0;
          textChatSlotStateEl.textContent = `${occupiedCount} von 5 Slots belegt`;
          textChatSlotStateEl.className = "request-state";
        }
      }
      if (sending) {
        statusText = "Text wird verarbeitet...";
      } else if (modelSwitchState && modelSwitchState.phase === "loading") {
        statusText = isNonEmptyString(modelSwitchState.message) ? modelSwitchState.message.trim() : "Modell wird geladen...";
      } else if (textServiceBasicPromptState.phase === "success" && isNonEmptyString(textServiceBasicPromptState.response_text)) {
        statusText = "Du kannst jetzt direkt den naechsten Text eingeben.";
      } else if (hasActiveChat && activeChat.occupied === true && activeMessages.length > 0) {
        statusText = "Aktiver Chat geladen.";
      } else if (hasActiveChat && activeChat.occupied === true && activeProfile && activeProfile.active_for_requests !== true) {
        statusText = `${activeProfile.label} ist fuer diesen Chat gespeichert, aber aktuell nicht lauffaehig.`;
      } else if (available && !isNonEmptyString(textBodyEl ? textBodyEl.value : "") && !isNonEmptyString(textServiceBasicPromptEl.value)) {
        statusText = activeMode === "rewrite"
          ? "Text eingeben oder einfuegen, dann ueberarbeiten."
          : (activeMode === "image_prompt"
            ? "Text eingeben, um einen Bildprompt abzuleiten."
            : "Text eingeben und dann starten.");
      } else if (available) {
        statusText = activeMode === "rewrite"
          ? "Lokale Text-KI bereit fuer Ueberarbeitung."
          : (activeMode === "image_prompt"
            ? "Lokale Text-KI bereit fuer Promptableitung."
            : "Lokale Text-KI ist bereit.");
      }
      textServiceBasicStatusEl.textContent = statusText;
      textServiceBasicStatusEl.className = "request-state";

      if (textChatSlotsEl) {
        textChatSlotsEl.replaceChildren();
        const slots = Array.isArray(textChatState.slots) ? textChatState.slots : [];
        slots.forEach((slot) => {
          if (!slot || !Number.isFinite(Number(slot.slot_index))) {
            return;
          }
          const slotButton = document.createElement("button");
          slotButton.type = "button";
          slotButton.className = "text-chat-slot";
          if (slot.occupied !== true) {
            slotButton.classList.add("empty");
          }
          if (Number(slot.slot_index) === Number(textChatState.active_slot_index)) {
            slotButton.classList.add("active");
          }
          const titleEl = document.createElement("div");
          titleEl.className = "text-chat-slot-title";
          const slotTitle = slot.occupied === true && isNonEmptyString(slot.title)
            ? slot.title.trim()
            : `Slot ${slot.slot_index} frei`;
          titleEl.textContent = slotTitle;
          // Add full title as tooltip if it might be truncated
          slotButton.title = slotTitle;
          slotButton.setAttribute("aria-label", slotTitle);
          const metaEl = document.createElement("div");
          metaEl.className = "text-chat-slot-meta";
          metaEl.textContent = slot.occupied === true
            ? `${slot.message_count || 0} Nachrichten${isNonEmptyString(slot.updated_at) ? ` | ${formatResultCreatedAt(slot.updated_at)}` : ""}`
            : "Leer";
          const previewEl = document.createElement("div");
          previewEl.className = "text-chat-slot-preview";
          previewEl.textContent = slot.occupied === true && isNonEmptyString(slot.last_message_preview)
            ? slot.last_message_preview.trim()
            : (slot.occupied === true
              ? "Noch keine KI-Antwort"
              : "Neuen Chat hier beginnen");
          slotButton.appendChild(titleEl);
          slotButton.appendChild(metaEl);
          slotButton.appendChild(previewEl);
          slotButton.addEventListener("click", () => {
            void activateTextChatSlot(slot.slot_index);
          });
          textChatSlotsEl.appendChild(slotButton);
        });
      }

      if (textChatActiveMetaEl) {
        if (!hasActiveChat) {
          textChatActiveMetaEl.textContent = "Aktiver Chat wird vorbereitet...";
          textChatActiveMetaEl.className = "request-state";
        } else if (activeChat.occupied !== true) {
          textChatActiveMetaEl.textContent = `Aktiver Slot ${activeChat.slot_index} ist leer. Du kannst direkt losschreiben oder erst einen neuen Chat anlegen.`;
          textChatActiveMetaEl.className = "request-state";
        } else {
          const metaParts = [
            activeChat.title,
            activeProfile && isNonEmptyString(activeProfile.label) ? `Profil: ${activeProfile.label}` : null,
            activeProfile && isNonEmptyString(activeProfile.status_label) ? `Status: ${activeProfile.status_label}` : null,
            isNonEmptyString(activeChat.language) ? `Sprache: ${activeChat.language}` : null,
            isNonEmptyString(activeChat.model) ? `Modell: ${activeChat.model}` : null,
            isNonEmptyString(activeChat.updated_at) ? `Aktualisiert: ${formatResultCreatedAt(activeChat.updated_at)}` : null
          ].filter(Boolean);
          textChatActiveMetaEl.textContent = metaParts.join(" | ");
          textChatActiveMetaEl.className = "request-state";
        }
      }

      if (textModelProfileGridEl) {
        textModelProfileGridEl.replaceChildren();
        modelProfiles.forEach((profile) => {
          if (!profile || !isNonEmptyString(profile.id)) {
            return;
          }
          const buttonEl = document.createElement("button");
          buttonEl.type = "button";
          buttonEl.className = "mode-button text-model-profile-card";
          const isActiveProfile = Boolean(activeProfile && activeProfile.id === profile.id);
          if (isActiveProfile || profile.status === "loading") {
            buttonEl.classList.add("active");
          }
          if (profile.active_for_requests !== true) {
            buttonEl.classList.add("unavailable");
          }
          const selectable = profile.selectable !== false && hasActiveChat && activeChat.occupied === true && !(modelSwitchState && modelSwitchState.phase === "loading");
          if (!selectable) {
            buttonEl.classList.add("unavailable");
            buttonEl.disabled = true;
          }

          const titleEl = document.createElement("span");
          titleEl.className = "text-model-profile-title";
          titleEl.textContent = isNonEmptyString(profile.label) ? profile.label.trim() : profile.id;

          const subtitleEl = document.createElement("span");
          subtitleEl.className = "text-model-profile-subtitle";
          subtitleEl.textContent = isNonEmptyString(profile.subtitle) ? profile.subtitle.trim() : "";

          const metaEl = document.createElement("span");
          metaEl.className = "text-model-profile-meta";
          metaEl.textContent = isNonEmptyString(profile.actual_model_name)
            ? profile.actual_model_name.trim()
            : (isNonEmptyString(profile.target_model_name) ? `Ziel: ${profile.target_model_name.trim()}` : "Noch kein Modell erkannt");

          const statusEl = document.createElement("span");
          statusEl.className = "text-model-profile-status";
          statusEl.textContent = isNonEmptyString(profile.status_label)
            ? profile.status_label.trim()
            : (profile.available === true ? "Verfuegbar" : "Vorbereitet");

          buttonEl.appendChild(titleEl);
          buttonEl.appendChild(subtitleEl);
          buttonEl.appendChild(metaEl);
          buttonEl.appendChild(statusEl);
          buttonEl.addEventListener("click", () => {
            void selectTextModelProfile(profile.id);
          });
          textModelProfileGridEl.appendChild(buttonEl);
        });
      }

      if (textModelProfileHintEl) {
        if (modelSwitchState && modelSwitchState.phase === "loading") {
          textModelProfileHintEl.textContent = isNonEmptyString(modelSwitchState.message) ? modelSwitchState.message.trim() : "Modell wird geladen...";
        } else if (!hasActiveChat || activeChat.occupied !== true) {
          textModelProfileHintEl.textContent = "Lege zuerst einen Chat an oder oeffne einen belegten Slot. Danach gilt das Modellprofil direkt fuer diesen Chat.";
        } else if (activeProfile && activeProfile.active_for_requests === true) {
          textModelProfileHintEl.textContent = `${activeProfile.label}: ${activeProfile.subtitle}${isNonEmptyString(activeProfile.actual_model_name) ? ` | Aktiv: ${activeProfile.actual_model_name}` : ""}`;
        } else if (activeProfile) {
          textModelProfileHintEl.textContent = `${activeProfile.label}: ${activeProfile.status_label}${isNonEmptyString(activeProfile.target_model_name) ? ` | Ziel: ${activeProfile.target_model_name}` : ""}${isNonEmptyString(activeProfile.error_message) ? ` | ${activeProfile.error_message.trim()}` : ""}`;
        } else {
          textModelProfileHintEl.textContent = "Modellprofile werden geladen...";
        }
      }

      if (textChatSummaryEl) {
        if (hasActiveChat && activeChat.occupied === true && isNonEmptyString(activeChat.summary)) {
          textChatSummaryEl.textContent = `Kurz-Zusammenfassung: ${activeChat.summary.trim()}`;
          textChatSummaryEl.className = "request-state";
          textChatSummaryEl.style.display = "block";
        } else {
          textChatSummaryEl.textContent = "";
          textChatSummaryEl.className = "request-state";
          textChatSummaryEl.style.display = "none";
        }
      }

      if (textChatHistoryEl) {
        textChatHistoryEl.replaceChildren();
        if (!hasActiveChat || activeMessages.length === 0) {
          const emptyEl = document.createElement("div");
          emptyEl.className = "text-chat-history-empty";
          emptyEl.textContent = "Noch kein Verlauf. Der Chat ist optional und unterstuetzt den Hauptpfad.";
          textChatHistoryEl.appendChild(emptyEl);
        } else {
          activeMessages.forEach((message) => {
            const role = message && isNonEmptyString(message.role) ? message.role.trim().toLowerCase() : "assistant";
            const itemEl = document.createElement("div");
            itemEl.className = `text-chat-message ${role === "user" ? "user" : "assistant"}`;
            const headEl = document.createElement("div");
            headEl.className = "text-chat-message-head";
            const roleEl = document.createElement("div");
            roleEl.className = "text-chat-message-role";
            roleEl.textContent = role === "user" ? "Du" : "Text-KI";
            const timeEl = document.createElement("div");
            timeEl.textContent = isNonEmptyString(message.created_at) ? formatResultCreatedAt(message.created_at) : "";
            headEl.appendChild(roleEl);
            headEl.appendChild(timeEl);
            const contentEl = document.createElement("div");
            contentEl.className = "text-chat-message-content";
            contentEl.textContent = isNonEmptyString(message.content) ? message.content : "";
            itemEl.appendChild(headEl);
            itemEl.appendChild(contentEl);
            textChatHistoryEl.appendChild(itemEl);
          });
        }
      }

      if (textServiceBasicPromptState.phase === "success" && isNonEmptyString(textServiceBasicPromptState.response_text)) {
        textServiceBasicResponseEl.textContent = textServiceBasicPromptState.response_text;
        textServiceBasicResponseEl.className = "request-state";
      } else if (textServiceBasicPromptState.phase === "error") {
        textServiceBasicResponseEl.textContent = formatTextServiceBasicError(
          textServiceBasicPromptState.error,
          textServiceBasicPromptState.error_message
        );
        textServiceBasicResponseEl.className = "request-state error";
      } else {
        textServiceBasicResponseEl.textContent = "";
        textServiceBasicResponseEl.className = "request-state";
      }

      if (!hasCopyableResponse && textServiceBasicCopyNotice.state !== "idle") {
        clearTextResponseCopyNotice("basic", false);
      }
      textServiceBasicCopyStateEl.textContent = hasCopyableResponse ? textServiceBasicCopyNotice.text : "";
      textServiceBasicCopyStateEl.className = textServiceBasicCopyNotice.state === "error" ? "text-copy-feedback error" : "text-copy-feedback";
      if (!hasTransferableResponse && textServiceBasicApplyNotice.state !== "idle") {
        clearTextServiceBasicApplyNotice(false);
      }
      if (textServiceBasicApplyStateEl) {
        if (hasTransferableResponse) {
          textServiceBasicApplyStateEl.textContent = textServiceBasicApplyNotice.text;
          textServiceBasicApplyStateEl.className = textServiceBasicApplyNotice.state === "error" ? "text-copy-feedback error" : "text-copy-feedback";
        } else if (activeMode === "image_prompt") {
          textServiceBasicApplyStateEl.textContent = "Noch kein Bildprompt abgeleitet.";
          textServiceBasicApplyStateEl.className = "text-copy-feedback";
        } else {
          textServiceBasicApplyStateEl.textContent = "";
          textServiceBasicApplyStateEl.className = "text-copy-feedback";
        }
      }
    }

    function renderIdentityTestUi() {
      const readinessView = getIdentityVerfuegbarkeitView();
      const basicIdentityMode = isV7BasicIdentitySingleMode();
      const identityStyleConfig = getCurrentIdentitySingleImageStyleConfig();
      const running = currentIdentityRequest?.phase === "running";
      const uploadBusy = Boolean(currentIdentityReferenceUpload);
      const hasReference = hasUsableIdentityReferenceImage();
      const hasPrompt = isNonEmptyString(identityPromptEl.value.trim());
      const enabled = readinessView.ready && hasReference && (basicIdentityMode ? hasPrompt : true) && !running && !uploadBusy;

      renderIdentityReferenceUploadUi();

      if (basicIdentityMode) {
        if (identityVerfuegbarkeitState.phase === "pending") {
          identityVerfuegbarkeitEl.textContent = "Funktion wird geprueft...";
        } else if (!readinessView.ready) {
          identityVerfuegbarkeitEl.textContent = readinessView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...";
        } else {
          identityVerfuegbarkeitEl.textContent = "Funktion ist bereit";
        }
      } else {
        identityVerfuegbarkeitEl.textContent = readinessView.text;
      }
      identityVerfuegbarkeitEl.className = readinessView.is_error ? "request-state error" : "request-state";

      identityPromptEl.disabled = running || uploadBusy || (basicIdentityMode ? !hasReference || !readinessView.ready : !readinessView.ready);
      identityGenerateEl.disabled = !enabled;
      identityGenerateEl.title = !readinessView.ready
        ? formatImageGenerationErrorMessage(readinessView.blocker || "identity_not_ready", {
          fallback: "Dieser Referenzpfad ist gerade nicht bereit."
        })
        : (!hasReference
          ? "Bitte lade zuerst ein Referenzbild hoch."
          : (!hasPrompt && basicIdentityMode ? "Bitte beschreibe zuerst deinen Wunsch." : ""));

      if (running) {
        identityRunStateEl.textContent = basicIdentityMode ? "Bild wird erstellt..." : "Referenzpfad-Testlauf laeuft...";
        identityRunStateEl.className = "request-state";
      } else if (currentIdentityRequest?.phase === "success" && activeIdentityResult.state === "loading") {
        identityRunStateEl.textContent = basicIdentityMode ? "Ergebnis wird geladen..." : "Referenzpfad-Ergebnis laedt...";
        identityRunStateEl.className = "request-state";
      } else if (currentIdentityRequest?.phase === "success" && activeIdentityResult.state === "ready") {
        identityRunStateEl.textContent = basicIdentityMode ? "Ergebnis ist fertig" : "Referenzpfad-Ergebnis bereit";
        identityRunStateEl.className = "request-state";
      } else if (currentIdentityRequest?.phase === "error") {
        identityRunStateEl.textContent = basicIdentityMode
          ? "Erstellung fehlgeschlagen"
          : `Referenzpfad-Testlauf fehlgeschlagen | ${currentIdentityRequest.blocker || currentIdentityRequest.error_type || "identity_reference_failed"}`;
        identityRunStateEl.className = "request-state error";
      } else if (!hasReference) {
        identityRunStateEl.textContent = "Referenzbild fehlt noch";
        identityRunStateEl.className = "request-state";
      } else if (!readinessView.ready) {
        identityRunStateEl.textContent = basicIdentityMode
          ? (readinessView.is_error ? "Funktion aktuell nicht verfuegbar" : "Funktion wird geprueft...")
          : "Referenzpfad-Testlauf nicht bereit";
        identityRunStateEl.className = "request-state";
      } else if (basicIdentityMode && !hasPrompt) {
        identityRunStateEl.textContent = "Gib einen Wunsch ein";
        identityRunStateEl.className = "request-state";
      } else {
        identityRunStateEl.textContent = basicIdentityMode ? "Jetzt kannst du starten" : "Referenzpfad-Testlauf bereit";
        identityRunStateEl.className = "request-state";
      }

      if (currentIdentityRequest?.phase === "error") {
        identityRunHintEl.textContent = basicIdentityMode
          ? formatImageGenerationErrorMessage(
            currentIdentityRequest.message || currentIdentityRequest.blocker,
            { fallback: "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden." }
          )
          : `Fehler | ${currentIdentityRequest.error_type || "api_error"} | ${currentIdentityRequest.blocker || "identity_reference_failed"}`;
        identityRunHintEl.className = "request-state error";
      } else if (currentIdentityRequest?.phase === "success" && activeIdentityResult.result_id) {
        identityRunHintEl.textContent = basicIdentityMode
          ? `Du kannst jetzt direkt eine weitere ${identityStyleConfig.label.toLowerCase()}-Variante beschreiben.`
          : `${activeIdentityResult.result_id}${activeIdentityResult.output_file ? ` | ${activeIdentityResult.output_file}` : ""}`;
        identityRunHintEl.className = "request-state";
      } else if (basicIdentityMode && readinessView.ready && hasReference && !hasPrompt) {
        identityRunHintEl.textContent = `Schreibe jetzt kurz, wie die Person als ${identityStyleConfig.label.toLowerCase()} neu erscheinen soll.`;
        identityRunHintEl.className = "request-state";
      } else if (!basicIdentityMode && readinessView.ready && hasReference) {
        identityRunHintEl.textContent = "Getrennter Referenzpfad-Testlaufpfad aktiv.";
        identityRunHintEl.className = "request-state";
      } else {
        identityRunHintEl.textContent = "";
        identityRunHintEl.className = "request-state";
      }

      identityRunHintEl.hidden = basicIdentityMode && !isNonEmptyString(identityRunHintEl.textContent);
    }

    function buildResultSummaryView() {
      const resultStatus = deriveResultStatusView();
      const rawModeLabel = isNonEmptyString(lastSuccessfulResult?.mode)
        ? lastSuccessfulResult.mode.trim()
        : (isNonEmptyString(lastResult?.mode) ? lastResult.mode.trim() : null);
      const modeLabel = isV7BasicModeActive() ? formatModeSummaryLabel(rawModeLabel) : rawModeLabel;

      if (resultStatus.state === "loading") {
        return {
          text: isV7BasicModeActive()
            ? "Ergebnis wird geladen..."
            : (modeLabel ? `Ergebnis laedt | ${modeLabel}` : "Ergebnis laedt"),
          is_error: false
        };
      }

      if (resultStatus.state === "error") {
        return {
          text: isV7BasicModeActive() ? resultStatus.text : resultStatus.text,
          is_error: true
        };
      }

      if (hasSuccessfulResult()) {
        return {
          text: isV7BasicModeActive()
            ? (hasCurrentBasicTaskCompletedSuccessfully()
              ? "Ergebnis ist fertig"
              : "Letztes Ergebnis")
            : (modeLabel ? `Letztes Ergebnis | ${modeLabel}` : "Letztes Ergebnis"),
          is_error: false
        };
      }

      return {
        text: "Noch kein Ergebnis",
        is_error: false
      };
    }

    function formatModeSummaryLabel(mode) {
      const normalized = isNonEmptyString(mode) ? mode.trim() : null;
      if (!normalized) {
        return null;
      }

      const labels = {
        sdxl: getCurrentV7TaskConfig().label,
        placeholder: "Testbild",
        identity_reference: "Neue Szene mit derselben Person",
        identity_multi_reference: "Mehrere Referenzbilder nutzen",
        identity_transfer: "Kopf/Gesicht auf Zielbild uebertragen",
        identity_transfer_mask_hybrid: "Masken-Hybrid"
      };
      return labels[normalized] || normalized;
    }

    function deriveLocalNoticeView() {
      const requestStatus = deriveRequestStatusView();
      const prioritizedLocalHint = derivePrioritizedLocalFaultView();
      const infoNotice = deriveTransientInfoNoticeView();

      if (requestStatus.state === "preflight" || requestStatus.state === "running") {
        return {
          channel: "request",
          text: requestStatus.text,
          state: requestStatus.state,
          request_id: requestStatus.request_id ?? null,
          is_error: false
        };
      }

      if (prioritizedLocalHint.active) {
        return {
          channel: prioritizedLocalHint.channel,
          text: prioritizedLocalHint.text,
          state: prioritizedLocalHint.state,
          request_id: prioritizedLocalHint.request_id,
          is_error: true
        };
      }

      if (infoNotice.active) {
        return {
          channel: "info_notice",
          text: infoNotice.text,
          state: "info",
          request_id: infoNotice.request_id,
          is_error: false
        };
      }

      return {
        channel: null,
        text: "",
        state: "idle",
        request_id: null,
        is_error: false
      };
    }

    function renderStatus() {
      const systemSummary = buildSystemSummaryView();
      const resultSummary = buildResultSummaryView();

      systemSummaryEl.hidden = systemSummary.hidden === true;
      systemSummaryEl.textContent = systemSummary.text;
      systemSummaryEl.className = systemSummary.is_error ? "status-line error" : "status-line";

      resultSummaryEl.textContent = resultSummary.text;
      resultSummaryEl.className = resultSummary.is_error ? "section-hint error" : "section-hint";
    }

    function renderImageState() {
      const imageStatus = deriveImageStatusView();
      imageStateEl.textContent = imageStatus.text;
      imageStateEl.className = imageStatus.state === "error" ? "request-state error" : "request-state";
    }

    function renderUi() {
      reconcileTransientLocalHintState();
      syncGenerateInputControls();
      syncV7BasicTaskDefaults();
      renderV7NavigationUi();
      const derivedState = deriveUiState();
      const requestStatus = deriveRequestStatusView();
      const localNoticeView = deriveLocalNoticeView();
      const foreignServerRequest = deriveForeignServerRequestView();
      const generateControl = computeGenerateEnabled({
        health_state: {
          state: derivedState.state === "preflight" || derivedState.state === "running"
            ? resolveHealthView().state
            : derivedState.state,
          cause: derivedState.state === "preflight" || derivedState.state === "running"
            ? resolveHealthView().cause
            : derivedState.cause
        },
        current_request: currentRequest ? {
          phase: currentRequest.phase
        } : null
      });
      generateEl.disabled = !generateControl.enabled;
      generateEl.title = generateControl.reason ? formatUiCause(generateControl.reason) : "";
      requestStateEl.textContent = requestStatus.text;
      const activeFeedback = foreignServerRequest.active
        ? {
            text: foreignServerRequest.text,
            is_error: false
          }
        : (localNoticeView.channel && isNonEmptyString(localNoticeView.text)
          ? {
              text: localNoticeView.text,
              is_error: localNoticeView.is_error === true
            }
          : {
              text: "Bereit",
              is_error: false
            });
      actionFeedbackEl.textContent = activeFeedback.text;
      actionFeedbackEl.className = activeFeedback.is_error ? "status-line error" : "status-line";
      const basicProgressActive = renderGenerateProgressUi();
      renderUploadUi();
      renderIdentityTestUi();
      const identityProgressActive = renderIdentityProgressUi();
      renderMultiReferenceUi();
      renderIdentityTransferUi();
      renderIdentityTransferTestUi();
      renderMaskUploadUi();
      renderMaskEditorUi();
      renderTextServiceBasicUi();
      renderTextServiceTestUi();
      syncSpeechInputControls();
      renderImageState();
      renderResultsGallery();
      renderResultsPreview();
      renderStatus();
      syncProgressRenderTimer(basicProgressActive || identityProgressActive);
    }

    async function fetchHealth(options = {}) {
      const forceFresh = options.forceFresh === true;

      if (healthFetchPromise && !forceFresh) {
        return healthFetchPromise;
      }

      if (healthFetchPromise && forceFresh) {
        try {
          await healthFetchPromise;
        } catch (error) {
        }
      }

      healthFetchPromise = (async () => {
        try {
          const response = await fetch("/health", { cache: "no-store" });
          if (!response.ok) {
            throw new Error(`health_http_${response.status}`);
          }
          const payload = await response.json();
          if (!payload || typeof payload !== "object") {
            throw new Error("health_invalid_payload");
          }
          healthState.payload = payload;
          healthState.error = null;
          healthState.consecutiveFailures = 0;
          syncInputImageFromHealth(payload);
          syncIdentityReferenceImageFromHealth(payload);
          syncMaskImageFromHealth(payload);
          void fetchIdentityVerfuegbarkeit();
          void fetchMultiReferenceRuntimeVerfuegbarkeit();
          void fetchIdentityTransferRuntimeVerfuegbarkeit();
          void fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit();
          renderUi();
          if (!currentRequest && !hasSuccessfulResult()) {
            await restore_last_success();
          }
          return payload;
        } catch (error) {
          healthState.consecutiveFailures += 1;
          healthState.error = error instanceof Error ? error.message : String(error);
          renderUi();
          return null;
        } finally {
          healthFetchPromise = null;
        }
      })();

      return healthFetchPromise;
    }

    function scheduleHealthPoll() {
      window.clearTimeout(healthPollTimer);
      healthPollTimer = window.setTimeout(async () => {
        await fetchHealth();
        scheduleHealthPoll();
      }, HEALTH_POLL_INTERVAL_MS);
    }

    function clearSuccessfulImageState(options = {}) {
      if (options.preserveActiveContext === true) {
        clearVisibleImage();
      } else {
        clearImage();
      }
      lastSuccessfulResult = null;
      clear_last_success();
    }

    async function probe_output_file(url) {
      const probeUrl = `${url}${url.includes("?") ? "&" : "?"}probe=${Date.now()}`;
      try {
        const response = await fetch(probeUrl, { cache: "no-store" });
        if (response.ok) {
          return { status: "ok" };
        }
        if (response.status === 404) {
          return { status: "missing" };
        }
        return { status: "unavailable", reason: `output_http_${response.status}` };
      } catch (error) {
        return {
          status: "unavailable",
          reason: error instanceof Error ? error.message : String(error)
        };
      }
    }

    async function restore_last_success() {
      if (restoringLastSuccess) {
        return false;
      }

      const persisted = load_last_success();
      if (!persisted) {
        return false;
      }

      const requiresResultsDir = persisted.output_file.startsWith("/results/files/");
      const requiresOutputDir = persisted.output_file.startsWith("/output/");
      if (
        healthState.error ||
        !healthState.payload ||
        healthState.payload.service !== "local-image-app" ||
        (requiresResultsDir && healthState.payload.results_dir_accessible !== true) ||
        (requiresOutputDir && healthState.payload.output_dir_accessible !== true)
      ) {
        return false;
      }

      if (
        lastSuccessfulResult &&
        lastSuccessfulResult.output_file === persisted.output_file &&
        displayedImage.output_file === persisted.output_file
      ) {
        return true;
      }

      restoringLastSuccess = true;
      try {
        const probe = await probe_output_file(persisted.output_file);
        if (probe.status === "ok") {
          lastSuccessfulResult = persisted;
          lastResult = persisted;
          setActiveImage(persisted.output_file, {
            request_id: persisted.request_id,
            mode: persisted.mode,
            prompt_id: persisted.prompt_id,
            restored_from_storage: true
          });
          renderUi();
          return true;
        }

        if (probe.status === "missing") {
          clear_last_success();
          if (
            lastSuccessfulResult &&
            lastSuccessfulResult.output_file === persisted.output_file
          ) {
            lastSuccessfulResult = null;
          }
          if (
            lastResult &&
            lastResult.status === "ok" &&
            lastResult.output_file === persisted.output_file
          ) {
            lastResult = null;
          }
          if (displayedImage.output_file === persisted.output_file) {
            clearImage();
          }
          renderUi();
        }
        return false;
      } finally {
        restoringLastSuccess = false;
      }
    }

    function handleGenerateSuccess(payload) {
      clearTransientInfoNotice("success");
      clearTransientClientPrecheckError("success");
      clearTransientRequestError("success");
      clearTransientBusyNotice("success");
      const currentTaskId = getCurrentV7TaskConfig().id;
      const basicTaskId = isV7BasicModeActive() && ["create", "edit", "inpaint"].includes(currentTaskId)
        ? currentTaskId
        : null;
      const result = {
        ...compactResult(payload),
        restored_from_storage: false,
        v7_basic_task: basicTaskId
      };
      lastResult = result;
      lastSuccessfulResult = result;
      persist_last_success(result);
      setActiveImage(result.output_file, {
        request_id: result.request_id,
        mode: result.mode,
        prompt_id: result.prompt_id,
        restored_from_storage: false
      });
      if (result.result_id && sceneState.active_scene_id) {
        void addResultToActiveScene(result.result_id);
      }
    }

    function handleGenerateError(payload) {
      clearTransientInfoNotice("server_error");
      clearTransientClientPrecheckError("server_error");
      if (payload?.status === "busy" || payload?.error_type === "busy") {
        clearTransientRequestError("busy");
        setTransientBusyNotice(payload);
        return;
      }

      clearTransientBusyNotice("request_error");
      setTransientRequestError(
        payload?.error_type ?? "api_error",
        payload?.blocker ?? "request_failed",
        payload?.request_id ?? null,
        {
          message: formatImageGenerationErrorMessage(payload?.blocker, {
            fallback: "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden."
          })
        }
      );
    }

    function beginCurrentRequest(mode, phase) {
      clearTransientInfoNotice("request_start");
      const clientRequestId = `client-${String(++currentRequestCounter).padStart(6, "0")}`;
      currentRequest = {
        client_request_id: clientRequestId,
        request_id: null,
        phase,
        mode,
        started_at_utc: new Date().toISOString()
      };
      renderUi();
      return clientRequestId;
    }

    function updateCurrentRequest(clientRequestId, updates) {
      if (!currentRequest || currentRequest.client_request_id !== clientRequestId) {
        return false;
      }

      currentRequest = {
        ...currentRequest,
        ...updates
      };
      return true;
    }

    function finalizeCurrentRequest(clientRequestId) {
      if (!currentRequest || currentRequest.client_request_id !== clientRequestId) {
        return false;
      }

      removeStorageItem(INTERRUPTED_REQUEST_STORAGE_KEY);
      currentRequest = null;
      renderUi();
      return true;
    }

    function settleCurrentRequest(clientRequestId) {
      const didFinalize = finalizeCurrentRequest(clientRequestId);
      rememberSettledRequestId(clientRequestId);
      return didFinalize;
    }

    function clearTransientLocalNotices(reason = null) {
      clearTransientInfoNotice(reason);
      clearTransientClientPrecheckError(reason);
      clearTransientRequestError(reason);
      clearTransientBusyNotice(reason);
    }

    async function attemptTextServicePromptTest() {
      if (textServicePromptTestState.phase === "sending") {
        return;
      }

      const normalizedPrompt = textServicePromptEl.value.trim();
      if (!normalizedPrompt) {
        textServicePromptTestState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "empty_prompt",
          error_message: "Prompt fehlt.",
          stub: true,
          service: null,
          model_status: null
        };
        renderUi();
        return;
      }

      if (normalizedPrompt.length > TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH) {
        textServicePromptTestState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "prompt_too_long",
          error_message: `Prompt ist laenger als ${TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH} Zeichen.`,
          stub: true,
          service: null,
          model_status: null
        };
        renderUi();
        return;
      }

      const requestToken = `text-service-test-${String(++textServicePromptTestCounter).padStart(6, "0")}`;
      textServicePromptTestState = {
        phase: "sending",
        request_token: requestToken,
        response_text: null,
        error: null,
        error_message: null,
        stub: true,
        service: null,
        model_status: null
      };
      renderUi();

      await fetchHealth({ forceFresh: true });
      const textServiceState = getTextServiceHealthState();
      if (!isTextServicePromptTestRelevant(requestToken)) {
        return;
      }

      if (!textServiceState.reachable) {
        textServicePromptTestState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: textServiceState.configured ? "text_service_unreachable" : "text_service_not_configured",
          error_message: textServiceState.configured ? "Text-Service nicht erreichbar." : "Text-Service nicht konfiguriert.",
          stub: true,
          service: textServiceState.service_name,
          model_status: textServiceState.model_status
        };
        renderUi();
        return;
      }

      try {
        const response = await fetch("/text-service/prompt-test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: normalizedPrompt })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isTextServicePromptTestRelevant(requestToken)) {
          return;
        }

        if (payload && payload.ok === true && isNonEmptyString(payload.response_text)) {
          textServicePromptTestState = {
            phase: "success",
            request_token: null,
            response_text: payload.response_text.trim(),
            error: null,
            error_message: null,
            stub: payload.stub === true,
            service: isNonEmptyString(payload.service) ? payload.service.trim() : textServiceState.service_name,
            model_status: isNonEmptyString(payload.model_status) ? payload.model_status.trim() : textServiceState.model_status
          };
          renderUi();
          return;
        }

        textServicePromptTestState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: isNonEmptyString(payload?.error) ? payload.error.trim() : (response.ok ? "text_service_invalid_response" : "text_service_request_failed"),
          error_message: isNonEmptyString(payload?.error_message) ? payload.error_message.trim() : null,
          stub: payload?.stub === true,
          service: isNonEmptyString(payload?.service) ? payload.service.trim() : textServiceState.service_name,
          model_status: isNonEmptyString(payload?.model_status) ? payload.model_status.trim() : textServiceState.model_status
        };
        renderUi();
      } catch (error) {
        if (!isTextServicePromptTestRelevant(requestToken)) {
          return;
        }

        textServicePromptTestState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_service_unreachable",
          error_message: error instanceof Error ? error.message : String(error),
          stub: true,
          service: textServiceState.service_name,
          model_status: textServiceState.model_status
        };
        renderUi();
      }
    }

    async function attemptTextServiceBasicPrompt() {
      if (textServiceBasicPromptState.phase === "sending") {
        return;
      }

      const normalizedPrompt = composeTextBodyPrompt(
        getTextBodyEffectiveSource(currentTextWorkMode),
        textServiceBasicPromptEl.value,
        currentTextWorkMode
      );
      if (!normalizedPrompt) {
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "empty_prompt",
          error_message: "Bitte gib zuerst Text in den Textkoerper oder die Anweisung ein.",
          stub: true,
          service: null,
          model_status: null
        };
        renderUi();
        return;
      }

      if (normalizedPrompt.length > TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH) {
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "prompt_too_long",
          error_message: `Bitte kuerze deinen Text auf ${TEXT_SERVICE_PROMPT_TEST_MAX_LENGTH} Zeichen.`,
          stub: true,
          service: null,
          model_status: null
        };
        renderUi();
        return;
      }

      const requestToken = `text-service-basic-${String(++textServiceBasicPromptCounter).padStart(6, "0")}`;
      textServiceBasicPromptState = {
        phase: "sending",
        request_token: requestToken,
        response_text: null,
        error: null,
        error_message: null,
        stub: true,
        service: null,
        model_status: null
      };
      renderUi();

      await fetchHealth({ forceFresh: true });
      const textServiceState = getTextServiceHealthState();
      if (!isTextServiceBasicPromptRelevant(requestToken)) {
        return;
      }

      if (!textServiceState.reachable) {
        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: textServiceState.configured ? "text_service_unreachable" : "text_service_not_configured",
          error_message: textServiceState.configured ? "Text-KI ist aktuell nicht verfuegbar." : "Text-KI ist aktuell noch nicht eingerichtet.",
          stub: true,
          service: textServiceState.service_name,
          model_status: textServiceState.model_status
        };
        renderUi();
        return;
      }

      try {
        const activeSlotIndex = Number.isFinite(Number(textChatState.active_slot_index))
          ? Number(textChatState.active_slot_index)
          : 1;
        const payload = await postTextChatAction(`/text-service/chats/slot/${activeSlotIndex}/message`, {
          prompt: normalizedPrompt,
          mode: normalizeTextWorkMode(currentTextWorkMode)
        });

        if (!isTextServiceBasicPromptRelevant(requestToken)) {
          return;
        }

        if (payload && isNonEmptyString(payload.last_response_text)) {
          textServiceBasicPromptState = {
            phase: "success",
            request_token: null,
            response_text: payload.last_response_text.trim(),
            error: null,
            error_message: null,
            stub: false,
            service: textServiceState.service_name,
            model_status: getTextChatActiveChat() && isNonEmptyString(getTextChatActiveChat().model)
              ? getTextChatActiveChat().model.trim()
              : textServiceState.model_status
          };
          renderUi();
          return;
        }

        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_invalid_response",
          error_message: "Text-KI lieferte keine nutzbare Antwort.",
          stub: false,
          service: textServiceState.service_name,
          model_status: textServiceState.model_status
        };
        renderUi();
      } catch (error) {
        if (!isTextServiceBasicPromptRelevant(requestToken)) {
          return;
        }

        textServiceBasicPromptState = {
          phase: "error",
          request_token: null,
          response_text: null,
          error: "text_chat_request_failed",
          error_message: error instanceof Error ? error.message : "Text-KI ist aktuell nicht verfuegbar.",
          stub: false,
          service: textServiceState.service_name,
          model_status: textServiceState.model_status
        };
        renderUi();
      }
    }

    async function attemptIdentityReferenceGenerate() {
      if (currentIdentityRequest?.phase === "running") {
        return;
      }

      const readiness = await fetchIdentityVerfuegbarkeit({ forceFresh: true });
      const readinessView = getIdentityVerfuegbarkeitView();
      if (!readiness || !readinessView.ready) {
        currentIdentityRequest = {
          phase: "error",
          request_token: null,
          error_type: "api_error",
          blocker: readinessView.blocker || "identity_not_ready",
          message: formatImageGenerationErrorMessage(readinessView.blocker || "identity_not_ready", {
            fallback: "Der Referenzpfad ist gerade nicht bereit."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      if (!hasUsableIdentityReferenceImage()) {
        currentIdentityRequest = {
          phase: "error",
          request_token: null,
          error_type: "invalid_request",
          blocker: "missing_reference_image",
          message: "Das Referenzbild fehlt noch.",
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      const prompt = identityPromptEl.value.trim();
      if (!prompt) {
        currentIdentityRequest = {
          phase: "error",
          request_token: null,
          error_type: "invalid_request",
          blocker: "empty_prompt",
          message: "Bitte gib zuerst einen Wunsch ein.",
          result_id: null,
          output_file: null
        };
        renderUi();
        return;
      }

      clearIdentityResult();
      const requestToken = `identity-request-${String(++currentIdentityRequestCounter).padStart(6, "0")}`;
      currentIdentityRequest = {
        phase: "running",
        request_token: requestToken,
        started_at_utc: new Date().toISOString(),
        error_type: null,
        blocker: null,
        message: null,
        result_id: null,
        output_file: null
      };
      renderUi();

      try {
        const healthPayload = healthState.payload || await fetchHealth({ forceFresh: true });
        const forcedBasicCheckpoint = basicIdentityMode ? getCurrentIdentitySingleImageStyleConfig().checkpoint_mode : "";
        const checkpoint = isNonEmptyString(forcedBasicCheckpoint)
          ? forcedBasicCheckpoint
          : (isNonEmptyString(healthPayload?.selected_checkpoint) ? healthPayload.selected_checkpoint.trim() : "");
        const response = await fetch("/identity-reference/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            checkpoint,
            reference_image_id: activeIdentityReferenceImage.image_id
          })
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isIdentityRequestRelevant(requestToken)) {
          return;
        }

        if (response.ok && payload && payload.status === "ok" && isNonEmptyString(payload.output_file)) {
          setIdentityResult(payload);
          currentIdentityRequest = {
            phase: "success",
            request_token: null,
            error_type: null,
            blocker: null,
            message: null,
            result_id: isNonEmptyString(payload.result_id) ? payload.result_id.trim() : null,
            output_file: payload.output_file.trim()
          };
          await fetchResults({ showLoading: false });
          renderUi();
          return;
        }

        currentIdentityRequest = {
          phase: "error",
          request_token: null,
          error_type: isNonEmptyString(payload?.error_type) ? payload.error_type.trim() : "api_error",
          blocker: isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_reference_http_${response.status}`,
          message: formatImageGenerationErrorMessage(
            isNonEmptyString(payload?.blocker) ? payload.blocker.trim() : `identity_reference_http_${response.status}`,
            { fallback: "Der Referenzpfad konnte gerade nicht abgeschlossen werden." }
          ),
          result_id: null,
          output_file: null
        };
        renderUi();
      } catch (error) {
        if (!isIdentityRequestRelevant(requestToken)) {
          return;
        }

        currentIdentityRequest = {
          phase: "error",
          request_token: null,
          error_type: "api_error",
          blocker: error instanceof Error ? error.message : String(error),
          message: formatImageGenerationErrorMessage(error instanceof Error ? error.message : String(error), {
            fallback: "Der Referenzpfad konnte gerade nicht abgeschlossen werden."
          }),
          result_id: null,
          output_file: null
        };
        renderUi();
      }
    }

    async function attemptGenerateWithPreflight() {
      const generateControl = computeGenerateEnabled({
        health_state: deriveHealthState(),
        current_request: currentRequest ? {
          phase: currentRequest.phase
        } : null
      });

      if (!generateControl.enabled) {
        const blocker = generateControl.reason || "health_not_ready";
        if (blocker !== "preflight_in_progress" && blocker !== "render_in_progress") {
          clearTransientLocalNotices("blocked_attempt");
          setTransientClientPrecheckError(
            blocker === "empty_prompt" || blocker === "invalid_mode" ? "invalid_request" : "client_precheck",
            blocker,
            {
              message: blocker === "empty_prompt" || blocker === "invalid_mode"
                ? formatUiCause(blocker)
                : `Vorabpruefung fehlgeschlagen | ${formatUiCause(blocker)}`
            }
          );
          renderUi();
        }
        return;
      }

      clearTransientLocalNotices("new_attempt");
      const prompt = promptEl.value.trim();
      if (!prompt) {
        setTransientClientPrecheckError("invalid_request", "empty_prompt");
        renderUi();
        return;
      }
      const negativePrompt = isNonEmptyString(negativePromptEl?.value) ? negativePromptEl.value.trim() : "";
      if (negativePrompt.length > NEGATIVE_PROMPT_MAX_LENGTH) {
        setTransientClientPrecheckError("invalid_request", "negative_prompt_too_long");
        renderUi();
        return;
      }

      const mode = modeEl.value.trim().toLowerCase();
      if (!VALID_MODES.has(mode)) {
        setTransientClientPrecheckError("invalid_request", "invalid_mode");
        renderUi();
        return;
      }

      const forcedBasicCheckpoint = isV11BasicImageTask() ? getCurrentBasicImageStyleConfig().checkpoint_mode : null;
      const effectiveMode = forcedBasicCheckpoint ? "sdxl" : mode;
      const clientRequestId = beginCurrentRequest(effectiveMode, "preflight");

      const preflightHealth = await fetchHealth({ forceFresh: true });
      const preflightView = resolveHealthView();
      if (!currentRequest || currentRequest.client_request_id !== clientRequestId) {
        rememberSettledRequestId(clientRequestId);
        return;
      }

      if (!preflightHealth || preflightView.state !== "ready") {
        settleCurrentRequest(clientRequestId);
        setTransientClientPrecheckError(
          "client_precheck",
          preflightView.cause || "health_not_ready",
          {
            message: `Vorabpruefung fehlgeschlagen | ${formatUiCause(preflightView.cause || "health_not_ready")}`
          }
        );
        renderUi();
        return;
      }

      updateCurrentRequest(clientRequestId, { phase: "running" });
      persist_interrupted_request(currentRequest);
      renderUi();

      const body = { prompt, mode: effectiveMode };
      // Add task_id for clarity and debugging (especially for image modes)
      if (isV7BasicModeActive() && BASIC_IMAGE_TASK_IDS.includes(currentV7BasicTask)) {
        body.task_id = currentV7BasicTask;
      }
      if (negativePrompt) {
        body.negative_prompt = negativePrompt;
      }
      const checkpoint = forcedBasicCheckpoint || checkpointEl.value.trim();
      if (checkpoint) {
        body.checkpoint = checkpoint;
      }
      if (shouldUseInputImage()) {
        body.use_input_image = true;
        body.input_image_id = activeInputImage.image_id;
        body.denoise_strength = normalizeDenoiseStrength(denoiseStrengthEl.value, getActiveDenoiseMax());
      }
      if (shouldUseInpainting()) {
        body.use_inpainting = true;
        body.mask_image_id = activeMaskImage.image_id;
      }

      try {
        const response = await fetch("/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (!isResponseRelevant(clientRequestId)) {
          logIgnoredGenerateResponse(clientRequestId, "response_not_relevant");
          return;
        }

        if (!payload || typeof payload !== "object") {
          clearTransientBusyNotice("invalid_response");
          setTransientRequestError("api_error", "invalid_generate_response", null, {
            message: formatImageGenerationErrorMessage("invalid_generate_response", {
              fallback: "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden."
            })
          });
          return;
        }

        updateCurrentRequest(clientRequestId, { request_id: payload.request_id ?? null });
        renderUi();

        if (payload.status === "ok" && payload.output_file) {
          handleGenerateSuccess(payload);
          void fetchResults({ showLoading: false });
        } else {
          handleGenerateError(payload);
        }
      } catch (error) {
        if (!isResponseRelevant(clientRequestId)) {
          logIgnoredGenerateResponse(clientRequestId, "error_not_relevant");
          return;
        }

        setTransientRequestError(
          "api_error",
          error instanceof Error ? error.message : String(error),
          null,
          {
            message: formatImageGenerationErrorMessage(error instanceof Error ? error.message : String(error), {
              fallback: "Die Bild-Erstellung konnte gerade nicht abgeschlossen werden."
            })
          }
        );
        clearTransientBusyNotice("request_exception");
      } finally {
        const activeClientRequestId = getActiveClientRequestId();
        if (!isResponseRelevant(clientRequestId, activeClientRequestId)) {
          rememberSettledRequestId(clientRequestId);
          logIgnoredGenerateResponse(clientRequestId, "finalize_not_relevant");
          return;
        }

        settleCurrentRequest(clientRequestId);
        await fetchHealth({ forceFresh: true });
        renderUi();
      }
    }

    const interruptedRequestNotice = consume_interrupted_request();
    if (interruptedRequestNotice) {
      setTransientInfoNotice(interruptedRequestNotice);
    }
    inputFileEl.addEventListener("change", handleInputFileSelection);
    guidedModeBasicEl.addEventListener("click", () => {
      setV7ViewMode("basic");
    });
    guidedModeExpertEl.addEventListener("click", () => {
      setV7ViewMode("expert");
    });
    basicTaskOpenExpertEl.addEventListener("click", () => {
      const action = isNonEmptyString(basicTaskOpenExpertEl.dataset.action)
        ? basicTaskOpenExpertEl.dataset.action.trim().toLowerCase()
        : "open_expert";
      if (action === "switch_task") {
        const targetTaskId = isNonEmptyString(basicTaskOpenExpertEl.dataset.targetTask)
          ? basicTaskOpenExpertEl.dataset.targetTask.trim()
          : "";
        if (targetTaskId && V7_TASK_CONFIG_BY_ID[targetTaskId]) {
          setV7BasicTask(targetTaskId);
          return;
        }
      }
      setV7ViewMode("expert");
    });
    V7_TASK_CONFIG.forEach((config) => {
      guidedTaskButtonEls[config.id].addEventListener("click", () => {
        setV7BasicTask(config.id);
      });
    });
    basicImageStylePhotoEl.addEventListener("click", () => {
      setBasicImageStyle("photo");
    });
    basicImageStyleAnimeEl.addEventListener("click", () => {
      setBasicImageStyle("anime");
    });
    identitySingleStylePhotoEl.addEventListener("click", () => {
      setIdentitySingleImageStyle("photo");
    });
    identitySingleStyleAnimeEl.addEventListener("click", () => {
      setIdentitySingleImageStyle("anime");
    });
    identityReferenceFileEl.addEventListener("change", handleIdentityReferenceFileSelection);
    multiReferenceFileEl.addEventListener("change", handleMultiReferenceFileSelection);
    IDENTITY_TRANSFER_ROLE_CONFIG.forEach((config) => {
      identityTransferRoleViews[config.role].fileEl.addEventListener("change", (event) => {
        handleIdentityTransferFileSelection(config.role, event);
      });
      identityTransferRoleViews[config.role].uploadEl.addEventListener("click", () => {
        void attemptUploadIdentityTransferRole(config.role);
      });
      identityTransferRoleViews[config.role].resetEl.addEventListener("click", () => {
        void resetIdentityTransferRole(config.role);
      });
    });
    maskFileEl.addEventListener("change", handleMaskFileSelection);
    pasteTargetEl.addEventListener("click", () => {
      pasteTargetEl.focus();
    });
    modeEl.addEventListener("change", renderUi);
    useInputImageEl.addEventListener("change", renderUi);
    useInpaintingEl.addEventListener("change", renderUi);
    denoiseStrengthEl.addEventListener("change", () => {
      denoiseStrengthEl.value = normalizeDenoiseStrength(denoiseStrengthEl.value, getActiveDenoiseMax()).toFixed(2);
      renderUi();
    });
    maskToolBrushEl.addEventListener("click", () => {
      setMaskEditorTool("brush");
    });
    maskToolEraserEl.addEventListener("click", () => {
      setMaskEditorTool("eraser");
    });
    maskBrushSizeEl.addEventListener("input", handleMaskBrushSizeChange);
    maskEditorClearEl.addEventListener("click", resetMaskEditorDrawing);
    maskEditorSaveEl.addEventListener("click", () => {
      void saveMaskEditorDrawing();
    });
    maskEditorOverlayEl.addEventListener("pointerdown", beginMaskEditorStroke);
    maskEditorOverlayEl.addEventListener("pointermove", continueMaskEditorStroke);
    maskEditorOverlayEl.addEventListener("pointerup", endMaskEditorStroke);
    maskEditorOverlayEl.addEventListener("pointercancel", endMaskEditorStroke);
    maskEditorOverlayEl.addEventListener("pointerleave", endMaskEditorStroke);
    window.addEventListener("paste", (event) => {
      void handlePasteEvent(event);
    }, true);
    uploadImageEl.addEventListener("click", attemptUploadImage);
    uploadIdentityReferenceEl.addEventListener("click", attemptUploadIdentityReference);
    uploadMultiReferenceEl.addEventListener("click", () => {
      void attemptUploadMultiReference();
    });
    uploadMaskEl.addEventListener("click", attemptUploadMask);
    resetInputImageEl.addEventListener("click", resetUploadedInputImage);
    resetIdentityReferenceEl.addEventListener("click", resetIdentityReferenceImage);
    resetAllMultiReferenceEl.addEventListener("click", () => {
      void resetAllMultiReferences();
    });
    resetAllIdentityTransferEl.addEventListener("click", () => {
      void resetAllIdentityTransferRoles();
    });
    resetMultiReferenceSlotEls.slice(1).forEach((button, index) => {
      button.addEventListener("click", () => {
        void resetMultiReferenceSlot(index + 1);
      });
    });
    resetMaskImageEl.addEventListener("click", resetUploadedMaskImage);
    generateEl.addEventListener("click", attemptGenerateWithPreflight);
    identityGenerateEl.addEventListener("click", () => {
      void attemptIdentityReferenceGenerate();
    });
    multiReferenceGenerateEl.addEventListener("click", () => {
      void attemptIdentityMultiReferenceGenerate();
    });
    identityTransferGenerateEl.addEventListener("click", () => {
      void attemptIdentityTransferGenerate();
    });
    identityTransferMaskHybridGenerateEl.addEventListener("click", () => {
      void attemptIdentityTransferMaskHybridGenerate();
    });
    textServiceBasicSendEl.addEventListener("click", () => {
      void attemptTextServiceBasicPrompt();
    });
    textChatNewEl.addEventListener("click", () => {
      void createTextChat();
    });
    textChatRenameEl.addEventListener("click", () => {
      void renameActiveTextChat();
    });
    textChatClearEl.addEventListener("click", () => {
      void clearActiveTextChat();
    });
    textWorkModeWritingEl.addEventListener("click", () => {
      setTextWorkMode("writing");
    });
    textWorkModeRewriteEl.addEventListener("click", () => {
      setTextWorkMode("rewrite");
    });
    textWorkModeImageEl.addEventListener("click", () => {
      setTextWorkMode("image_prompt");
    });
    textServiceBasicApplyImagePromptEl.addEventListener("click", () => {
      applyTextServiceBasicResponseToImagePrompt(getTextServiceBasicApplyTargetTaskId());
    });
    if (negativePromptEl instanceof HTMLTextAreaElement) {
      negativePromptEl.addEventListener("input", () => {
        persistBasicTaskNegativePromptDraft(currentV7BasicTask);
      });
    }
    if (useStandardNegativePromptEl instanceof HTMLInputElement) {
      useStandardNegativePromptEl.addEventListener("change", () => {
        if (!BASIC_IMAGE_TASK_IDS.includes(currentV7BasicTask)) {
          return;
        }
        setBasicTaskStandardNegativePromptEnabled(currentV7BasicTask, useStandardNegativePromptEl.checked);
        syncBasicTaskNegativePrompt(currentV7BasicTask, isV7BasicModeActive());
        renderNegativePromptGuidance(currentV7BasicTask, isV7BasicModeActive());
        renderUi();
      });
    }
    if (textBodyClearEl) {
      textBodyClearEl.addEventListener("click", () => {
        if (textBodyEl) {
          textBodyEl.value = "";
          saveTextBodyDraft("");
        }
      });
    }
    if (textBodyInsertEl) {
      textBodyInsertEl.addEventListener("click", () => {
        const response = textServiceBasicPromptState.response_text;
        if (!isNonEmptyString(response) || !textBodyEl) {
          return;
        }
        const current = textBodyEl.value;
        textBodyEl.value = current ? `${current}\n\n${response.trim()}` : response.trim();
        saveTextBodyDraft(textBodyEl.value);
        renderUi();
      });
    }
    if (textBodyReplaceEl) {
      textBodyReplaceEl.addEventListener("click", () => {
        const response = textServiceBasicPromptState.response_text;
        if (!isNonEmptyString(response) || !textBodyEl) {
          return;
        }
        textBodyEl.value = response.trim();
        saveTextBodyDraft(textBodyEl.value);
        renderUi();
      });
    }
    if (textBodyEl) {
      textBodyEl.addEventListener("input", () => {
        saveTextBodyDraft(textBodyEl.value);
        if (sceneState.active_scene_id) {
          scheduleSaveScene();
        }
      });
      textBodyEl.addEventListener("selectionchange", () => {
        if (normalizeTextWorkMode(currentTextWorkMode) === "image_prompt") {
          renderUi();
        }
      });
      textBodyEl.addEventListener("mouseup", () => {
        if (normalizeTextWorkMode(currentTextWorkMode) === "image_prompt") {
          renderUi();
        }
      });
      textBodyEl.addEventListener("keyup", () => {
        if (normalizeTextWorkMode(currentTextWorkMode) === "image_prompt") {
          renderUi();
        }
      });
    }
    if (textToImageGoEl) {
      textToImageGoEl.addEventListener("click", () => {
        const negPrompt = textImageNegativePromptEl ? textImageNegativePromptEl.value.trim() : "";
        if (negPrompt && negativePromptEl) {
          negativePromptEl.value = negPrompt;
        }
        applyTextServiceBasicResponseToImagePrompt("create");
      });
    }
    if (textServiceBasicApplyImagePromptEl) {
      const originalHandler = textServiceBasicApplyImagePromptEl.onclick;
      textServiceBasicApplyImagePromptEl.addEventListener("click", () => {
        const negPrompt = textImageNegativePromptEl ? textImageNegativePromptEl.value.trim() : "";
        if (negPrompt && negativePromptEl) {
          negativePromptEl.value = negPrompt;
        }
      });
    }
    if (sceneNewEl) {
      sceneNewEl.addEventListener("click", () => {
        const defaultTitle = `Szene ${(sceneState.scenes || []).length + 1}`;
        const body = textBodyEl ? textBodyEl.value : "";
        void createScene(defaultTitle, body);
      });
    }
    if (sceneSaveEl) {
      sceneSaveEl.addEventListener("click", () => {
        if (!sceneState.active_scene_id) {
          const defaultTitle = `Szene 1`;
          const body = textBodyEl ? textBodyEl.value : "";
          void createScene(defaultTitle, body);
          return;
        }
        const title = sceneTitleEl ? sceneTitleEl.value.trim() : null;
        const body = textBodyEl ? textBodyEl.value : "";
        const updates = { body };
        if (title) updates.title = title;
        void saveScene(sceneState.active_scene_id, updates);
      });
    }
    if (sceneDeleteEl) {
      sceneDeleteEl.addEventListener("click", () => {
        if (!sceneState.active_scene_id) return;
        if (!window.confirm(`Szene "${sceneState.active_scene ? sceneState.active_scene.title : ""}" loeschen?`)) return;
        void deleteScene(sceneState.active_scene_id);
      });
    }

    /* --- OVERFLOW MENU FUNCTIONALITY --- */
    const textActionsMoreEl = document.getElementById("text-actions-more");
    const textActionsMenuEl = document.getElementById("text-actions-menu");

    if (textActionsMoreEl && textActionsMenuEl) {
      // Toggle overflow menu
      textActionsMoreEl.addEventListener("click", (e) => {
        e.stopPropagation();
        const isHidden = textActionsMenuEl.hasAttribute("hidden");
        if (isHidden) {
          textActionsMenuEl.removeAttribute("hidden");
          textActionsMoreEl.classList.add("active");
        } else {
          textActionsMenuEl.setAttribute("hidden", "");
          textActionsMoreEl.classList.remove("active");
        }
      });

      // Close menu when clicking outside
      document.addEventListener("click", () => {
        if (!textActionsMenuEl.hasAttribute("hidden")) {
          textActionsMenuEl.setAttribute("hidden", "");
          textActionsMoreEl.classList.remove("active");
        }
      });

      // Close menu when clicking inside menu (action was taken)
      textActionsMenuEl.addEventListener("click", () => {
        setTimeout(() => {
          textActionsMenuEl.setAttribute("hidden", "");
          textActionsMoreEl.classList.remove("active");
        }, 50);
      });
    }

    if (sceneToggleListEl) {
      sceneToggleListEl.addEventListener("click", () => {
        sceneListOpen = !sceneListOpen;
        renderUi();
      });
    }
    if (sceneListEl) {
      sceneListEl.addEventListener("click", (event) => {
        const item = event.target.closest("[data-scene-id]");
        if (!item) return;
        const sceneId = item.dataset.sceneId;
        if (sceneId && sceneId !== sceneState.active_scene_id) {
          void activateScene(sceneId);
        }
      });
    }
    if (sceneTitleEl) {
      sceneTitleEl.addEventListener("blur", () => {
        if (!sceneState.active_scene_id) return;
        const title = sceneTitleEl.value.trim();
        if (!title) {
          sceneTitleEl.value = sceneState.active_scene ? sceneState.active_scene.title : "";
          return;
        }
        if (sceneState.active_scene && title !== sceneState.active_scene.title) {
          void saveScene(sceneState.active_scene_id, { title });
        }
      });
    }
    if (sceneResultsRefreshEl) {
      sceneResultsRefreshEl.addEventListener("click", () => {
        if (isNonEmptyString(sceneState.active_scene_id)) {
          void fetchSceneResults(sceneState.active_scene_id, { showLoading: true });
        }
      });
    }
    if (sceneExportEl) {
      sceneExportEl.addEventListener("click", () => {
        if (isNonEmptyString(sceneState.active_scene_id)) {
          void requestSceneExport(sceneState.active_scene_id);
        }
      });
    }
    textServiceBasicCopyEl.addEventListener("click", () => {
      void attemptCopyTextResponse("basic");
    });
    textServiceSendEl.addEventListener("click", () => {
      void attemptTextServicePromptTest();
    });
    textServiceTestCopyEl.addEventListener("click", () => {
      void attemptCopyTextResponse("test");
    });
    resultsRefreshEl.addEventListener("click", () => {
      void fetchResults();
    });
    resultsPreviewPrevEl.addEventListener("click", () => {
      openAdjacentResultsPreview(-1);
    });
    resultsPreviewNextEl.addEventListener("click", () => {
      openAdjacentResultsPreview(1);
    });
    resultsPreviewLoadInputEl.addEventListener("click", () => {
      if (!isNonEmptyString(resultsPreviewState.result_id)) {
        return;
      }
      void loadResultAsInputImage(resultsPreviewState.result_id, { closePreview: true });
    });
    resultsPreviewDeleteEl.addEventListener("click", () => {
      if (!isNonEmptyString(resultsPreviewState.result_id)) {
        return;
      }
      void requestResultDelete(resultsPreviewState.result_id, {
        closePreview: true,
        fileName: resultsPreviewState.file_name
      });
    });
    resultsPreviewCloseEl.addEventListener("click", () => {
      closeResultsPreview();
    });
    resultsPreviewModalEl.addEventListener("click", (event) => {
      if (event.target === resultsPreviewModalEl) {
        closeResultsPreview();
      }
    });
    Object.keys(speechInputControllers).forEach((key) => {
      speechInputControllers[key].buttonEl.addEventListener("click", () => {
        toggleSpeechInput(key);
      });
    });
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && resultsPreviewState.open) {
        closeResultsPreview();
        return;
      }
      if (resultsPreviewState.open && event.key === "ArrowLeft") {
        event.preventDefault();
        openAdjacentResultsPreview(-1);
        return;
      }
      if (resultsPreviewState.open && event.key === "ArrowRight") {
        event.preventDefault();
        openAdjacentResultsPreview(1);
      }
    });
    window.addEventListener("beforeunload", () => {
      stopActiveSpeechInput({ clear_feedback: true });
      if (currentRequest && currentRequest.phase === "running") {
        persist_interrupted_request(currentRequest);
      }
    });
    clearCurrentInputImage({ clearNotice: false });
    clearCurrentIdentityReferenceImage({ clearNotice: false });
    clearCurrentMaskImage({ clearNotice: false });
    restoreV7NavigationState();
    speechUsageState = loadSpeechUsageState();
    resetSelectedMultiReferenceFile();
    IDENTITY_TRANSFER_ROLE_CONFIG.forEach((config) => {
      resetSelectedIdentityTransferFile(config.role);
    });
    clearImage();
    void (async () => {
      await fetchScenes();
      if (textBodyEl) {
        if (sceneState.active_scene) {
          textBodyEl.value = sceneState.active_scene.body || "";
          saveTextBodyDraft(textBodyEl.value);
          if (sceneTitleEl) sceneTitleEl.value = sceneState.active_scene.title || "";
        } else {
          const savedDraft = loadTextBodyDraft();
          if (savedDraft) textBodyEl.value = savedDraft;
        }
      }
      renderUi();
    })();
    renderUi();
    void fetchHealth();
    void fetchSpeechStatus();
    void fetchMultiReferenceStatus();
    void fetchMultiReferenceRuntimeVerfuegbarkeit();
    void fetchIdentityTransferStatus();
    void fetchIdentityTransferRuntimeVerfuegbarkeit();
    void fetchIdentityTransferMaskHybridRuntimeVerfuegbarkeit();
    void fetchTextChats();
    void fetchResults();
    scheduleHealthPoll();
  




