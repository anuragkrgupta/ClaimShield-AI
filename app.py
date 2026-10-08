import streamlit as st
from PIL import Image

from core.image.detector import analyze_image_mock
from core.risk import calculate_image_authenticity

st.set_page_config(page_title="ClaimShield AI", page_icon="🛡️")

st.title("ClaimShield AI 🛡️")
st.subheader("Insurance Claim Evidence Analysis")

st.warning("⚠️ MOCK MODE: The AI image detector is currently running in mock mode.")
st.markdown("Hint: Upload an image with 'fake', 'synthetic', or 'manipulated' in the filename to test the suspicious flow. Use 'fail' or 'error' to test failure.")

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
        with st.spinner("Running MOCK AI Image Detector..."):
            image_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
            
            signal, success = analyze_image_mock(image_bytes, filename)
            
            if not success:
                st.error("❌ MOCK DETECTOR UNAVAILABLE / FAILED.")
                st.info("The detector failed to process the image. The analysis cannot be completed.")
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
                    st.write(f"**Reason:** {s.message}")
                    if s.confidence:
                        st.write(f"**Confidence:** {s.confidence:.2f}")
