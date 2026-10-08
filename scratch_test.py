import torch
import torch.nn as nn
from PIL import Image
import io
from transformers import CLIPProcessor, CLIPModel

device = "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

fc = nn.Linear(768, 1).to(device)
state_dict = torch.load("fc_weights.pth", map_location=device)
fc.load_state_dict(state_dict)
fc.eval()
model.eval()

image = Image.new("RGB", (224, 224), color="red")
inputs = processor(images=image, return_tensors="pt").to(device)

with torch.no_grad():
    image_features = model.get_image_features(**inputs)
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    logits = fc(image_features)
    prob = torch.sigmoid(logits).item()

print("PROB:", prob)
