# ClaimShield AI

ClaimShield AI is an insurance-agnostic digital evidence authenticity and fraud detection system designed to analyze insurance claim files (images and documents), detect potential AI generation and digital tampering, compute explainable risk scores, and aid human claim investigators.

## Current Implementation Status

* **Phase 1 (Minimal Scaffold):** Implemented core data structures (`Signal` in `core/types.py`), initial risk calculation (`calculate_image_authenticity` in `core/risk.py`), and baseline unit tests with mocks.
* **Phase 2 (UnivFD Integration):** Integrated UniversalFakeDetect (`UnivFDDetector` in `core/image/detector.py`) using a pretrained CLIP ViT-L/14 backbone and custom classification head (`fc_weights.pth`). Single-image analysis is operational in the Streamlit UI (`app.py`).
* **Phase 3 (Forensic Evaluation):** Completed forensic evaluation of reference methods; Error Level Analysis (ELA) and reference noise analysis were rejected for the generic natural-image pipeline due to reliability limitations. Recapture detection (Moiré / JPEG-blockiness) remains a proposed candidate awaiting implementation and validation.
* **Planned Capabilities:** Document tampering & OCR, basic date/amount claim consistency checks (P0), multi-tier risk engine fusion, and full multi-evidence claim workflow UI.

## Setup and Installation

### Prerequisites
* Python 3.10+
* Virtual environment (recommended)

### Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note on Model Weights:** The classifier weights (`fc_weights.pth`) are required for live UnivFD inference. The CLIP ViT-L/14 backbone will be automatically downloaded by HuggingFace Transformers on initial run if not already cached.

## Running the Application

Launch the Streamlit web interface:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`. Upload an image (JPG, JPEG, PNG) and click **Analyze Image** to inspect the UnivFD detection output and Image Authenticity Score.

## Running Tests and Validation

### Automated Unit Tests
To run the automated test suite (isolated to ClaimShield tests):
```bash
python -m pytest tests/test_pipeline.py
```
*(Tests currently cover mocked detector responses and risk score calculation logic).*

### Live Model Validation
To validate live UnivFD model initialization, resource usage, and inference:
```bash
python validate_phase2.py
```
To validate against a specific AI-generated image:
```bash
python validate_phase2.py path/to/ai_image.jpg
```
*(or set the `AI_IMAGE_PATH` environment variable).*