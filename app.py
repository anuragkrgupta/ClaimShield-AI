import streamlit as st
from PIL import Image

from core.image.detector import analyze_image_univfd
from core.risk import calculate_image_authenticity

st.set_page_config(page_title="ClaimShield AI", page_icon="🛡️")

st.title("ClaimShield AI 🛡️")
st.subheader("Insurance Claim Evidence Analysis")

st.info("ℹ️ DETECTOR: UnivFD / UniversalFakeDetect integrated.")

uploaded_file = st.file_uploader("Upload an image (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Display the image
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Evidence", use_container_width=True)
    except Exception:
        st.error("Could not read the uploaded image. Please ensure it is a valid image file.")
        st.stop()
        
    if st.button("Analyze Image"):
        with st.spinner("Running UnivFD AI Image Detector..."):
            image_bytes = uploaded_file.getvalue()
            
            signal, success = analyze_image_univfd(image_bytes)
            
            if not success:
                st.error("❌ ANALYSIS UNAVAILABLE")
                st.info("The model failed to process the image or weights are missing. The analysis cannot be completed.")
            else:
                signals = [signal] if signal else []
                score = calculate_image_authenticity(signals)
                
                st.markdown("### Analysis Results")
                
                # Display Score
                if score >= 70:
                    st.success(f"**Image Authenticity Score: {score} / 100**")
                elif score >= 40:
                    st.warning(f"**Image Authenticity Score: {score} / 100**")
                else:
                    st.error(f"**Image Authenticity Score: {score} / 100**")
                    
                st.markdown("#### Evidence & Reasons")
                for s in signals:
                    severity_icon = "🔴" if s.severity in ["HIGH", "CRITICAL"] else "🟡" if s.severity == "MEDIUM" else "🟢"
                    st.markdown(f"{severity_icon} **{s.name}**")
                    
                    if s.confidence is not None:
                        # Displaying AI-generation likelihood or model confidence
                        if s.severity in ["HIGH", "CRITICAL"]:
                            st.write(f"**AI-generation likelihood:** {s.confidence * 100:.1f}%")
                        else:
                            # It's authentic, confidence is the confidence of being authentic
                            st.write(f"**Model confidence (Authentic):** {s.confidence * 100:.1f}%")
                            
                    st.write(f"**Reason:** {s.message}")
