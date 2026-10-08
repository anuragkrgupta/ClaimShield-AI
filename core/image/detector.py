from typing import Tuple, Optional
from core.types import Signal

def analyze_image_mock(image_bytes: bytes, filename: str = "") -> Tuple[Optional[Signal], bool]:
    """
    Mock AI Image Detector.
    Returns a (Signal, success_flag) tuple.
    In a real implementation, this would run a deepfake detection model.
    """
    if not image_bytes:
        return None, False
        
    name_lower = filename.lower()
    
    # Simulate a detector failure/unavailability
    if "fail" in name_lower or "error" in name_lower:
        return None, False
    
    # Simulate a suspicious/manipulated image detection
    if "fake" in name_lower or "manipulated" in name_lower or "synthetic" in name_lower:
        return Signal(
            name="AI_IMAGE_DETECTION_MOCK",
            severity="HIGH",
            score=15, # 15/100 authenticity
            message="MOCK: High probability of AI generation or manipulation detected.",
            confidence=0.95
        ), True
        
    # Simulate an authentic image
    return Signal(
        name="AI_IMAGE_DETECTION_MOCK",
        severity="LOW",
        score=92, # 92/100 authenticity
        message="MOCK: Image appears authentic. No obvious manipulation detected.",
        confidence=0.88
    ), True
