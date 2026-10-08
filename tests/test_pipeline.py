import pytest
from core.types import Signal
from core.image.detector import analyze_image_mock
from core.risk import calculate_image_authenticity

def test_mock_detector_authentic():
    image_bytes = b"dummy_data"
    signal, success = analyze_image_mock(image_bytes, "real_accident.jpg")
    
    assert success is True
    assert signal is not None
    assert signal.severity == "LOW"
    assert signal.score > 80

def test_mock_detector_suspicious():
    image_bytes = b"dummy_data"
    signal, success = analyze_image_mock(image_bytes, "fake_accident.jpg")
    
    assert success is True
    assert signal is not None
    assert signal.severity == "HIGH"
    assert signal.score < 50

def test_mock_detector_failure():
    image_bytes = b"dummy_data"
    signal, success = analyze_image_mock(image_bytes, "fail.jpg")
    
    assert success is False
    assert signal is None

def test_mock_detector_empty_bytes():
    signal, success = analyze_image_mock(b"", "test.jpg")
    
    assert success is False
    assert signal is None

def test_risk_score_calculation():
    signals = [
        Signal(
            name="AI_IMAGE_DETECTION_MOCK",
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
