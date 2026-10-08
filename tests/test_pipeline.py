import pytest
from unittest.mock import patch, MagicMock
from core.types import Signal
from core.image.detector import analyze_image_univfd, UnivFDDetector
from core.risk import calculate_image_authenticity
from PIL import Image
import io

def create_test_image_bytes():
    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

@pytest.fixture(autouse=True)
def mock_detector_init():
    with patch.object(UnivFDDetector, '__init__', return_value=None):
        yield

@patch.object(UnivFDDetector, 'predict')
def test_mock_detector_authentic(mock_predict):
    mock_predict.return_value = (Signal(
        name="UNIVFD_AI_DETECTION",
        severity="LOW",
        score=95,
        message="Authentic",
        confidence=0.9
    ), True)
    
    image_bytes = create_test_image_bytes()
    # Force instance reset for test isolation
    UnivFDDetector._instance = None
    signal, success = analyze_image_univfd(image_bytes)
    
    assert success is True
    assert signal is not None
    assert signal.severity == "LOW"
    assert signal.score > 80

@patch.object(UnivFDDetector, 'predict')
def test_mock_detector_suspicious(mock_predict):
    mock_predict.return_value = (Signal(
        name="UNIVFD_AI_DETECTION",
        severity="HIGH",
        score=20,
        message="Fake",
        confidence=0.95
    ), True)
    
    image_bytes = create_test_image_bytes()
    UnivFDDetector._instance = None
    signal, success = analyze_image_univfd(image_bytes)
    
    assert success is True
    assert signal is not None
    assert signal.severity == "HIGH"
    assert signal.score < 50

@patch.object(UnivFDDetector, 'predict')
def test_mock_detector_failure(mock_predict):
    mock_predict.return_value = (None, False)
    
    image_bytes = create_test_image_bytes()
    UnivFDDetector._instance = None
    signal, success = analyze_image_univfd(image_bytes)
    
    assert success is False
    assert signal is None

def test_mock_detector_empty_bytes():
    UnivFDDetector._instance = None
    with patch.object(UnivFDDetector, 'predict', return_value=(None, False)):
        signal, success = analyze_image_univfd(b"")
        assert success is False
        assert signal is None

def test_risk_score_calculation():
    signals = [
        Signal(
            name="UNIVFD_AI_DETECTION",
            severity="HIGH",
            score=15,
            message="Test",
            confidence=0.99
        )
    ]
    
    score = calculate_image_authenticity(signals)
    assert score == 15

def test_risk_score_no_signals():
    score = calculate_image_authenticity([])
    assert score == 100
