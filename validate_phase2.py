import time
import os
import urllib.request
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from PIL import Image
import io

import torch
from core.image.detector import UnivFDDetector, analyze_image_univfd
from core.risk import calculate_image_authenticity

def measure_time(func, *args, **kwargs):
    start = time.time()
    res = func(*args, **kwargs)
    end = time.time()
    return res, end - start

def print_memory():
    if not PSUTIL_AVAILABLE:
        return 0.0
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / (1024 * 1024)

def run_validation():
    print("=== CLAIMSHIELD AI: PHASE 2 VALIDATION ===")
    
    # Check Hardware
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n[RESOURCE CHECK]")
    print(f"Device used for inference: {device}")
    
    checkpoint_path = "fc_weights.pth"
    if os.path.exists(checkpoint_path):
        size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
        print(f"fc_weights.pth size: {size_mb:.2f} MB")
        
    print(f"Initial Memory Usage: {print_memory():.2f} MB")
    
    print("\n[PERFORMANCE: LOADING MODEL]")
    start_load = time.time()
    detector = UnivFDDetector.get_instance()
    load_time = time.time() - start_load
    print(f"Model initialization/loading time: {load_time:.2f} seconds")
    print(f"Post-load Memory Usage: {print_memory():.2f} MB")

    # Images
    images = {}
    
    # 1. Real Image (Download from Wikipedia)
    real_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/2012_Honda_Civic_LX_sedan_--_04-20-2011.jpg/800px-2012_Honda_Civic_LX_sedan_--_04-20-2011.jpg"
    try:
        real_bytes = urllib.request.urlopen(real_url, timeout=10).read()
        images["real_photo.jpg"] = real_bytes
    except Exception:
        # Fallback to local red square if download fails
        img = Image.new("RGB", (800, 600), color="blue")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        images["real_photo.jpg"] = img_byte_arr.getvalue()
        
    # 2. AI Image
    import sys
    ai_path = os.environ.get("AI_IMAGE_PATH")
    if not ai_path and len(sys.argv) > 1:
        ai_path = sys.argv[1]

    if ai_path and os.path.exists(ai_path):
        with open(ai_path, "rb") as f:
            images["ai_generated.jpg"] = f.read()
    else:
        print("\nWARNING: AI_IMAGE_PATH not set or file not found. Skipping AI-image test.")
        print("Please provide the path via AI_IMAGE_PATH environment variable or as a CLI argument.\n")
            
    # 3. Corrupt Image
    images["corrupt.jpg"] = b"This is not a valid image file."
    
    # 4. Empty Input
    images["empty.jpg"] = b""
    
    print("\n[REAL IMAGE TEST & FAILURE TESTS]")
    first_inference = True
    
    for filename, img_bytes in images.items():
        print(f"\n--- Testing: {filename} ---")
        
        dim = "N/A"
        if img_bytes:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                dim = f"{img.width}x{img.height}"
            except:
                pass
                
        print(f"Dimensions: {dim}")
        print(f"Size: {len(img_bytes)} bytes")
        
        start_inf = time.time()
        signal, success = analyze_image_univfd(img_bytes)
        inf_time = time.time() - start_inf
        
        if first_inference and img_bytes and success:
            print(f"First inference time: {inf_time:.2f} seconds")
            first_inference = False
        elif img_bytes and success:
            print(f"Subsequent inference time: {inf_time:.2f} seconds")
            
        if success:
            signals = [signal] if signal else []
            score = calculate_image_authenticity(signals)
            
            print(f"Success: {success}")
            print(f"Signal Generated: {signal.name}")
            print(f"Predicted Class: {signal.severity}")
            if signal.severity == "HIGH":
                print(f"AI-generation likelihood: {signal.confidence:.4f}")
            else:
                print(f"Model confidence (Authentic): {signal.confidence:.4f}")
                
            print(f"Image Authenticity Score: {score}")
            print(f"Message: {signal.message}")
        else:
            print(f"Success: {success}")
            print("Failed gracefully. No fabricated prediction.")
            
if __name__ == "__main__":
    run_validation()
