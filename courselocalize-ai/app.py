import json
from pathlib import Path
import re
import uuid

import streamlit as st

from config import (
    APP_DIR,
    DATA_DIR,
    HISTORY_PATH,
    LANGUAGES,
    MAX_DOCUMENT_CHARS,
    MAX_UPLOAD_BYTES,
)
from modules.file_processor import (
    ContentError,
    download_bytes,
    extract_text,
    validate_pasted_text,
)
from modules.history_manager import (
    add_history_item,
    clear_history,
    load_history,
)
from modules.quality_evaluator import check_translation, evaluate_reference
from modules.structure_preserver import (
    PlaceholderError,
    translate_markdown_document,
)
from modules.terminology import (
    load_terminology,
    save_terminology,
    validate_terminology,
)
from modules.translator import TranslationError, translate_many


st.set_page_config(
    page_title="CourseLocalize AI",
    page_icon="🌐",
    layout="wide",
)

PAGES = [
    "Home",
    "Localization Workspace",
    "Translation Results",
    "History",
    "Terminology",
    "About Project",
]


def go_to_workspace() -> None:
    st.session_state["navigation"] = "Localization Workspace"


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem or "localized-course"
    return re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-") or "localized-course"


def _preserved_terms(
    source: str,
    terminology: list[dict[str, object]],
) -> list[str]:
    terms = []
    for entry in terminology:
        term = entry.get("term")
        if (
            entry.get("mode") == "preserve"
            and isinstance(term, str)
            and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", source, re.IGNORECASE)
        ):
            terms.append(term)
    return terms


def render_downloads(record: dict[str, object]) -> None:
    translated = str(record.get("translated", ""))
    stem = _safe_stem(str(record.get("source_filename", "localized-course")))
    language = _safe_stem(str(record.get("target_language", "translation")))
    col_md, col_txt = st.columns(2)
    with col_md:
        st.download_button(
            "Download Markdown",
            data=download_bytes(translated),
            file_name=f"{stem}-{language}.md",
            mime="text/markdown",
            key=f"download-md-{record.get('id', uuid.uuid4())}",
            use_container_width=True,
        )
    with col_txt:
        st.download_button(
            "Download TXT",
            data=download_bytes(translated),
            file_name=f"{stem}-{language}.txt",
            mime="text/plain",
            key=f"download-txt-{record.get('id', uuid.uuid4())}",
            use_container_width=True,
        )


def render_result(record: dict[str, object], include_evaluation: bool = True) -> None:
    if record.get("status") != "success":
        st.warning(
            "This localization job did not complete. No source or translation "
            "content was saved for failed jobs."
        )
        return

    source = str(record.get("original", ""))
    translated = str(record.get("translated", ""))
    target_language = str(record.get("target_language", ""))
    st.caption(
        f"Source: {record.get('source_filename', 'Pasted content')} · "
        f"Target language: {target_language}"
    )

    checks = check_translation(source, translated)
    if checks.warnings:
        st.warning(
            "Some structure checks need review: " + " ".join(checks.warnings)
        )
    else:
        st.success("The content and Markdown structure checks passed.")

    with st.expander("Localization checks", expanded=False):
        for label, passed in checks.checks.items():
            (st.success if passed else st.warning)(
                f"{'Passed' if passed else 'Review'} — {label}"
            )

    try:
        terminology = load_terminology()
        protected = _preserved_terms(source, terminology)
    except ValueError:
        protected = []
    if protected:
        st.info("Protected technical terms: " + ", ".join(protected))

    original_column, translated_column = st.columns(2)
    with original_column:
        st.subheader("Original · English")
        st.text_area(
            "Original course content",
            value=source,
            height=360,
            disabled=True,
            key=f"original-{record.get('id', 'current')}",
            label_visibility="collapsed",
        )
    with translated_column:
        st.subheader(f"Localized · {target_language}")
        st.text_area(
            "Localized course content",
            value=translated,
            height=360,
            disabled=True,
            key=f"translated-{record.get('id', 'current')}",
            label_visibility="collapsed",
        )
    render_downloads(record)

    if include_evaluation:
        with st.expander("Optional BLEU and chrF++ evaluation"):
            st.caption(
                "Upload a human-verified reference translation in the selected "
                "target language. Scores are calculated only from that reference; "
                "they are not a substitute for human review."
            )
            reference_file = st.file_uploader(
                "Reference translation (TXT or Markdown)",
                type=["txt", "md"],
                key=f"reference-{record.get('id', 'current')}",
            )
            if st.button(
                "Evaluate against reference",
                key=f"evaluate-{record.get('id', 'current')}",
                disabled=reference_file is None,
            ):
                try:
                    reference = extract_text(
                        reference_file.name,
                        reference_file.getvalue(),
                    )
                    scores = evaluate_reference(translated, reference)
                    score_col1, score_col2 = st.columns(2)
                    score_col1.metric("BLEU", f"{scores['BLEU']:.2f}")
                    score_col2.metric("chrF++", f"{scores['chrF++']:.2f}")
                    st.caption(
                        "These automatic scores compare this result with the "
                        "uploaded reference and can vary with text length and "
                        "formatting."
                    )
                except (ContentError, RuntimeError, ValueError) as exc:
                    st.error(str(exc))


def render_home() -> None:
    st.title("CourseLocalize AI")
    st.subheader("Learn technical skills in your preferred language.")
    st.write(
        "Localize English course material into Indian languages while keeping "
        "code, technical identifiers, and lesson structure intact."
    )
    language_text = " · ".join(LANGUAGES)
    st.markdown(f"**Supported languages:** {language_text}")
    st.button(
        "Start Localization",
        type="primary",
        on_click=go_to_workspace,
        use_container_width=False,
    )

    st.divider()
    st.subheader("Built for technical learning")
    feature_columns = st.columns(3)
    features = [
        (
            "Multilingual Translation",
            "Translate English learning content into Kannada, Hindi, Tamil, "
            "or Telugu with AI4Bharat IndicTrans2.",
        ),
        (
            "Technical Term Preservation",
            "Protect code, identifiers, and terms you choose to keep unchanged.",
        ),
        (
            "Course Structure Preservation",
            "Keep headings, lists, paragraphs, tables, and code blocks organized.",
        ),
    ]
    for column, (title, description) in zip(feature_columns, features):
        with column:
            with st.container(border=True):
                st.subheader(title)
                st.write(description)

    st.subheader("A clear four-step workflow")
    workflow_columns = st.columns(4)
    for column, step in zip(
        workflow_columns,
        ["Upload or paste", "Translate", "Review", "Download"],
    ):
        with column:
            with st.container(border=True):
                st.markdown(f"**{step}**")


def _load_sample() -> str:
    return (DATA_DIR / "sample_lesson.md").read_text(encoding="utf-8")


def render_workspace() -> None:
    st.title("Localization Workspace")
    st.write(
        "Upload an English lesson or paste its content. Markdown headings, lists, "
        "tables, inline code, and fenced code blocks are handled separately."
    )
    st.caption(
        "Files are limited to 5 MB. Successful jobs save their source and result "
        "in local history so you can reopen them; use History to remove saved jobs."
    )

    if st.button("Load sample lesson", key="load-sample"):
        st.session_state["pasted_course_text"] = _load_sample()

    input_method = st.radio(
        "Choose how to provide course content",
        ["Paste text", "Upload a file"],
        horizontal=True,
        key="input-method",
    )
    source_filename = "Pasted lesson.md"
    source_text = ""
    upload = None
    if input_method == "Paste text":
        source_text = st.text_area(
            "English course content",
            key="pasted_course_text",
            height=260,
            placeholder=(
                "Paste lesson text or Markdown here. You can also load the sample "
                "lesson above."
            ),
        )
    else:
        upload = st.file_uploader(
            "Upload a TXT, Markdown, or text-based PDF",
            type=["txt", "md", "pdf"],
            key="course-file",
        )
        if upload is not None:
            source_filename = upload.name
            st.caption(f"Selected file: **{upload.name}**")
            if upload.size > MAX_UPLOAD_BYTES:
                st.error("The file is larger than the 5 MB upload limit.")
            else:
                try:
                    source_text = extract_text(upload.name, upload.getvalue())
                except ContentError as exc:
                    st.error(str(exc))

    source_language = st.selectbox(
        "Source language",
        ["English"],
        disabled=True,
    )
    target_language = st.selectbox(
        "Target language",
        list(LANGUAGES),
        key="target-language",
    )
    st.caption(f"Source language: {source_language}")

    if st.button(
        "Localize Content",
        type="primary",
        use_container_width=True,
        key="localize-content",
    ):
        st.session_state["last_result"] = None
        progress = st.progress(0, text="Validating course content…")
        status = st.status("Preparing localization…", expanded=True)
        try:
            if input_method == "Upload a file":
                if upload is None:
                    raise ContentError("Choose a file before starting localization.")
                source_text = extract_text(upload.name, upload.getvalue())
                source_filename = upload.name
            else:
                source_text = validate_pasted_text(source_text)
                source_filename = "Pasted lesson.md"
            if len(source_text) > MAX_DOCUMENT_CHARS:
                raise ContentError(
                    "This prototype accepts up to 50,000 characters per lesson."
                )

            status.update(
                label="Protecting code, terminology, and lesson structure…",
                state="running",
            )
            terminology = load_terminology()
            progress.progress(0.08, text="Preparing text segments…")

            def update_progress(completed: int, total: int) -> None:
                fraction = 0.1 + 0.82 * (completed / max(total, 1))
                progress.progress(
                    min(fraction, 0.94),
                    text=f"Translating segment {completed} of {total}…",
                )

            translated, _vault = translate_markdown_document(
                source_text,
                LANGUAGES[target_language],
                terminology,
                lambda segments: translate_many(
                    segments,
                    LANGUAGES[target_language],
                    progress_callback=update_progress,
                ),
            )
            quality = check_translation(source_text, translated)
            status.update(
                label="Checking placeholders and course structure…",
                state="running",
            )
            if not quality.checks["Output is not empty"]:
                raise ValueError("The translation returned empty output.")
            if not quality.checks["Code blocks are unchanged"]:
                raise PlaceholderError(
                    "A code block changed during translation. The result was not saved."
                )

            try:
                history_record = add_history_item(
                    source_filename=source_filename,
                    target_language=target_language,
                    status="success",
                    original=source_text,
                    translated=translated,
                    warnings=quality.warnings,
                    path=HISTORY_PATH,
                )
            except (OSError, ValueError) as history_error:
                history_record = {
                    "id": f"current-{uuid.uuid4()}",
                    "source_filename": source_filename,
                    "target_language": target_language,
                    "status": "success",
                    "original": source_text,
                    "translated": translated,
                    "warnings": quality.warnings,
                }
                st.warning(
                    "The translation completed, but local history could not be "
                    f"saved: {history_error}"
                )
            st.session_state["last_result"] = history_record
            progress.progress(1.0, text="Localization complete.")
            status.update(label="Localization complete.", state="complete")
            st.success(
                "Translation completed. Review it below or open Translation Results."
            )
        except (
            ContentError,
            TranslationError,
            PlaceholderError,
            ValueError,
            RuntimeError,
        ) as exc:
            status.update(label="Localization did not complete.", state="error")
            progress.empty()
            st.session_state["last_result"] = None
            st.error(str(exc))
            try:
                add_history_item(
                    source_filename=source_filename,
                    target_language=target_language,
                    status="failed",
                    path=HISTORY_PATH,
                )
            except (OSError, ValueError):
                pass

    result = st.session_state.get("last_result")
    if result:
        st.divider()
        st.subheader("Translation Results")
        render_result(result)


def render_results_page() -> None:
    st.title("Translation Results")
    result = st.session_state.get("last_result")
    if not result:
        st.info(
            "No result is open. Localize a lesson or choose a completed job from "
            "History."
        )
        return
    render_result(result)


def render_history() -> None:
    st.title("History")
    st.caption(
        "Successful jobs store both the original lesson and its translation in "
        "the local JSON history file. Failed jobs store only their file name, "
        "language, date, and status."
    )
    try:
        items = load_history(HISTORY_PATH)
    except ValueError as exc:
        st.error(str(exc))
        return

    if not items:
        st.info("No localization jobs have been saved yet.")
        return

    for item in items:
        created = str(item.get("created_at", ""))
        with st.container(border=True):
            col_file, col_language, col_date, col_status = st.columns(
                [3, 1.3, 2, 1]
            )
            col_file.write(str(item.get("source_filename", "Unknown file")))
            col_language.write(str(item.get("target_language", "Unknown")))
            col_date.write(created.replace("T", " ").split(".")[0])
            status = str(item.get("status", "unknown")).title()
            if status == "Success":
                col_status.success(status)
            else:
                col_status.error(status)

    successful_items = [item for item in items if item.get("status") == "success"]
    if successful_items:
        st.subheader("Reopen a previous result")
        selected_id = st.selectbox(
            "Saved localization",
            options=[str(item.get("id")) for item in successful_items],
            format_func=lambda item_id: next(
                (
                    f"{item.get('source_filename')} → {item.get('target_language')} "
                    f"({str(item.get('created_at', '')).replace('T', ' ')[:16]})"
                    for item in successful_items
                    if str(item.get("id")) == item_id
                ),
                item_id,
            ),
            key="history-selection",
        )
        selected = next(
            item for item in successful_items if str(item.get("id")) == selected_id
        )
        st.session_state["last_result"] = selected
        render_result(selected, include_evaluation=False)

    st.divider()
    confirm_clear = st.checkbox(
        "I understand this permanently deletes all saved local history."
    )
    if st.button(
        "Clear history",
        disabled=not confirm_clear,
        type="secondary",
    ):
        try:
            clear_history(HISTORY_PATH)
            st.session_state["last_result"] = None
            st.success("Local history was cleared.")
            st.rerun()
        except (OSError, ValueError) as exc:
            st.error(f"Could not clear history: {exc}")


def render_terminology() -> None:
    st.title("Terminology Dictionary")
    st.write(
        "Choose which terms remain unchanged and add preferred translations. "
        "Terms with mode `translate` and no preferred target translation are "
        "left for IndicTrans2 to translate."
    )
    st.caption(
        "Use one JSON array of objects. Each object needs `term` and `mode`; "
        "`mode` is `preserve` or `translate`. Add target-code values under "
        "`translations` when you want a preferred translation."
    )
    try:
        current = load_terminology()
    except ValueError as exc:
        st.error(str(exc))
        return
    editor_value = st.text_area(
        "Edit terminology JSON",
        value=json.dumps(current, ensure_ascii=False, indent=2),
        height=420,
        key="terminology-json",
    )
    st.markdown(
        "Target codes: `kan_Knda` (Kannada), `hin_Deva` (Hindi), "
        "`tam_Taml` (Tamil), `tel_Telu` (Telugu)."
    )
    if st.button("Save terminology dictionary", type="primary"):
        try:
            parsed = json.loads(editor_value)
            saved = save_terminology(validate_terminology(parsed))
            st.success(f"Saved {len(saved)} terminology entries.")
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            st.error(f"Dictionary was not saved: {exc}")


def render_about() -> None:
    st.title("About Project")
    st.write(
        "CourseLocalize AI explores how English technical course content can be "
        "made more accessible in Indian languages without losing essential code "
        "or educational structure."
    )
    st.subheader("Problem statement")
    st.write(
        "Students often learn technical subjects from English materials even "
        "when they understand concepts more comfortably in another language. "
        "Direct translation can damage programming syntax, terminology, and "
        "lesson structure."
    )
    st.subheader("Project modules")
    modules = [
        "Content Processing",
        "Context and Terminology Handling",
        "Multilingual Translation",
        "Course Structure Preservation",
        "Quality Evaluation",
    ]
    module_columns = st.columns(3)
    for index, module in enumerate(modules):
        with module_columns[index % len(module_columns)]:
            with st.container(border=True):
                st.write(f"**{index + 1}. {module}**")

    st.subheader("Technology stack")
    st.write(
        "Python, Streamlit, AI4Bharat IndicTrans2, Hugging Face Transformers, "
        "IndicTransToolkit, PyMuPDF, local JSON history, BLEU, and chrF++."
    )
    st.write(
        "The app does not train a model or substitute fake translations. If the "
        "local model is unavailable, configure a compatible translation "
        "endpoint or install the documented IndicTrans2 dependencies."
    )
    st.markdown(
        "References: [AI4Bharat IndicTrans2](https://github.com/AI4Bharat/IndicTrans2) "
        "· [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit) "
        "· [IndicTrans2 model card](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M)"
    )


st.sidebar.title("CourseLocalize AI")
st.sidebar.caption("Technical courses, in your preferred language.")
page = st.sidebar.radio("Navigate", PAGES, key="navigation")
st.sidebar.divider()
st.sidebar.caption("English → Kannada · Hindi · Tamil · Telugu")

if page == "Home":
    render_home()
elif page == "Localization Workspace":
    render_workspace()
elif page == "Translation Results":
    render_results_page()
elif page == "History":
    render_history()
elif page == "Terminology":
    render_terminology()
else:
    render_about()
