from typing import List
from core.types import Signal

def calculate_image_authenticity(signals: List[Signal]) -> int:
    """
    Calculates the Image Authenticity Score (0-100).
    Higher is more authentic.
    """
    if not signals:
        return 100  # Default to authentic if no signals
        
    # Find the AI detection signal
    ai_signal = next((s for s in signals if s.name == "AI_IMAGE_DETECTION_MOCK"), None)
    
    if ai_signal:
        return ai_signal.score
        
    return 100
