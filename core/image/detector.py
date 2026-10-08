import torch
import torch.nn as nn
from PIL import Image
import io
import logging
from typing import Tuple, Optional
from core.types import Signal

try:
    from transformers import CLIPProcessor, CLIPModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnivFDDetector:
    _instance = None
    
    @classmethod
    def get_instance(cls, fc_weights_path: str = "fc_weights.pth"):
        if cls._instance is None or not getattr(cls._instance, 'is_loaded', False):
            cls._instance = cls(fc_weights_path)
        return cls._instance

    def __init__(self, fc_weights_path: str = "fc_weights.pth"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers library is not available.")
            return
            
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(self.device)
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
            
            self.fc = nn.Linear(768, 1).to(self.device)
            state_dict = torch.load(fc_weights_path, map_location=self.device, weights_only=True)
            self.fc.load_state_dict(state_dict)
            self.fc.eval()
            self.model.eval()
            self.is_loaded = True
        except Exception as e:
            logger.error(f"Error loading UnivFD model: {e}")

    @torch.no_grad()
    def predict(self, image_bytes: bytes) -> Tuple[Optional[Signal], bool]:
        if not image_bytes or not self.is_loaded:
            return None, False
            
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            image_features = self.model.get_image_features(pixel_values=inputs.pixel_values)
            if hasattr(image_features, 'image_embeds'):
                image_features = image_features.image_embeds
            elif hasattr(image_features, 'pooler_output'):
                image_features = image_features.pooler_output
            elif not isinstance(image_features, torch.Tensor):
                image_features = image_features[1] if isinstance(image_features, tuple) else image_features

            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
            logits = self.fc(image_features)
            prob = torch.sigmoid(logits).item()
            
            # UniversalFakeDetect typical convention: positive = fake
            is_fake = prob > 0.5
            
            # Score conversion: 100 is authentic, 0 is fake
            # Higher synthetic probability -> lower authenticity score
            score = 100 - int(prob * 100)
            
            if is_fake:
                return Signal(
                    name="UNIVFD_AI_DETECTION",
                    severity="HIGH",
                    score=score,
                    message="Model indicates high likelihood of AI generation or manipulation.",
                    confidence=prob
                ), True
            else:
                return Signal(
                    name="UNIVFD_AI_DETECTION",
                    severity="LOW",
                    score=score,
                    message="Image appears authentic based on UnivFD analysis.",
                    confidence=1.0 - prob
                ), True
                
        except Exception as e:
            logger.error(f"UnivFD inference failed: {e}")
            return None, False

# Interface function maintaining stability
def analyze_image_univfd(image_bytes: bytes) -> Tuple[Optional[Signal], bool]:
    detector = UnivFDDetector.get_instance()
    return detector.predict(image_bytes)
