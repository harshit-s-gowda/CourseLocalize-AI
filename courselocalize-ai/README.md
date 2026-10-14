# CourseLocalize AI

CourseLocalize AI is a Streamlit prototype for translating English technical
course material into Kannada, Hindi, Tamil, and Telugu. It uses AI4Bharat
IndicTrans2, preserves code and selected terminology, retains Markdown
structure, and stores successful jobs in a local JSON history file.

## Features

- Paste lesson text or upload UTF-8 TXT, Markdown, or text-based PDF files.
- Translate from English into Kannada, Hindi, Tamil, or Telugu.
- Use the official AI4Bharat IndicTrans2 English-to-Indic distilled model.
- Keep fenced code, inline code, URLs, file paths, common identifiers, and
  configured technical terms unchanged.
- Add preferred target-language terms or preservation rules in the editable
  terminology dictionary.
- Preserve Markdown headings, list markers, paragraph order, tables, and code
  blocks.
- Review original and localized text side by side and download Markdown or TXT.
- Reopen successful jobs from local JSON history, or clear history.
- Run BLEU and chrF++ comparisons only when a reference translation is supplied.
- Run automated checks for missing output, structure, code blocks, and
  protected placeholders.

## Technology

- Python 3.11+
- Streamlit
- AI4Bharat IndicTrans2 via Hugging Face Transformers and IndicTransToolkit
- PyMuPDF for selectable text in PDFs
- JSON files for terminology and local history
- SacreBLEU for BLEU and chrF++ metrics
- Python `unittest` for automated tests

## Folder structure

```text
courselocalize-ai/
├── app.py
├── config.py
├── requirements.txt
├── requirements-model.txt
├── README.md
├── .streamlit/
│   └── config.toml
├── data/
│   ├── history.json
│   ├── sample_lesson.md
│   └── terminology.json
├── modules/
│   ├── file_processor.py
│   ├── history_manager.py
│   ├── quality_evaluator.py
│   ├── structure_preserver.py
│   ├── terminology.py
│   └── translator.py
└── tests/
    ├── test_file_processor.py
    ├── test_history_manager.py
    ├── test_quality_evaluator.py
    ├── test_structure_preserver.py
    ├── test_terminology.py
    └── test_translator.py
```

## Run locally

Install Python 3.11 or newer. From the repository root:

```bash
cd courselocalize-ai
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 5000
```

The base requirements start the interface, PDF extraction, and reference-based
evaluation. Translation is intentionally not replaced by sample or fabricated
output: configure the local model or a compatible real translation endpoint
before using the Localize Content action.

## Set up local IndicTrans2 inference

The app's local inference path follows the AI4Bharat Hugging Face model-card
example and the IndicTransToolkit processor. It uses the 200M distilled model:

```text
ai4bharat/indictrans2-en-indic-dist-200M
```

Install the additional model dependencies:

```bash
python -m pip install -r requirements-model.txt
```

The model repository may require you to sign in to Hugging Face and accept its
access conditions before downloading. If model access is gated, provide your
authorized Hugging Face token through your operating system's secret manager or
Replit Secrets using `HF_TOKEN` (or `HUGGINGFACEHUB_API_TOKEN`). Do not put a
token in source code, `config.py`, or a committed file.

PyTorch and the model weights can use several gigabytes of memory and disk.
CPU inference is supported but may be slow. The application does not require a
GPU, and it does not download model weights until the first translation attempt.

The official model language codes used by the app are:

| Language | Code |
| --- | --- |
| English | `eng_Latn` |
| Kannada | `kan_Knda` |
| Hindi | `hin_Deva` |
| Tamil | `tam_Taml` |
| Telugu | `tel_Telu` |

Official references:

- [IndicTrans2 repository and inference interface](https://github.com/AI4Bharat/IndicTrans2)
- [English-to-Indic distilled model card](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M)
- [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit)

## Alternative translation endpoint

If the model cannot run locally, point the app at a real IndicTrans2-compatible
HTTP endpoint by setting `INDICTRANS2_ENDPOINT_URL`. An optional bearer token
can be supplied as `HF_TOKEN` or `HUGGINGFACEHUB_API_TOKEN`. Configure both
values through Replit Secrets or a local environment/secret manager; never
commit credentials.

The endpoint must accept a JSON POST in this form:

```json
{
  "inputs": "The lesson sentence to translate.",
  "parameters": {
    "src_lang": "eng_Latn",
    "tgt_lang": "hin_Deva"
  }
}
```

It must return a Hugging Face-style response containing `translation_text` or
`generated_text`, for example:

```json
[
  {
    "translation_text": "अनुवादित वाक्य।"
  }
]
```

The endpoint is responsible for running IndicTrans2 inference and any required
IndicProcessor preprocessing/postprocessing. The app reports endpoint errors
instead of claiming a translation succeeded.

## Configure technical terms

Open **Terminology** in the app to edit the JSON dictionary. Each entry uses:

- `term`: the source-language term to match.
- `mode`: `preserve` to keep it unchanged, or `translate` to let IndicTrans2
  translate it.
- `translations`: optional preferred values keyed by target code. A preferred
  target value is restored exactly instead of being translated.

Example:

```json
{
  "term": "Database",
  "mode": "translate",
  "translations": {
    "hin_Deva": "डेटाबेस"
  }
}
```

The shipped dictionary preserves API, Python, SQL, and HTML; generic terms such
as Function, Variable, Database, Algorithm, Machine Learning, and Artificial
Intelligence are left for the translation model unless a preferred value is
configured.

## Run tests

```bash
cd courselocalize-ai
python -m unittest discover -s tests -v
```

Tests cover file validation and extraction, code and placeholder preservation,
terminology rules, model failure handling, output bytes, structure checks, and
local history.

## Storage and privacy

- Uploaded files are processed in memory and are not copied into a separate
  uploads directory.
- Successful jobs save the original lesson and translation to
  `data/history.json` so they can be reopened. Failed jobs save only the file
  name, target language, date, and status.
- Clear saved jobs from the History page. This action permanently removes the
  local JSON history.
- `data/history.json` is excluded from Git to avoid committing course content.
- Uploaded program code is treated only as text; the app never executes it.
- Files are limited to 5 MB and documents to 50,000 characters.

## Limitations

- PDF support extracts selectable text only; scanned PDFs need OCR first.
- Translating structured Markdown line by line can make wording less natural
  across adjacent lines. Review the output before using it in a course.
- The app stops and reports an error if a protected placeholder is missing,
  duplicated, or changed.
- A model download, gated model access, limited RAM, or a disconnected endpoint
  can prevent translation. The app does not silently switch to mock output.
- BLEU and chrF++ require a human-verified reference in the target language.
  Short or differently formatted samples can produce misleading metric scores;
  automated scores are not human evaluation.

## Example demonstration

1. Open the Localization Workspace.
2. Click **Load sample lesson** to load an English lesson with a Python code
   block, a list, and a table.
3. Select a target language and click **Localize Content**.
4. Review the original, translation, and structure checks.
5. Download the output as Markdown or TXT, or open the saved job from History.

The demo requires working IndicTrans2 model access or a configured endpoint.

## Future improvements

- Add OCR for scanned PDFs.
- Add an optional human review workflow and editable corrections.
- Evaluate against an approved parallel dataset such as IN22 rather than a
  single reference sentence.
- Add sentence-level progress and glossary import/export formats.
