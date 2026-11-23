from deepface import DeepFace

id_path = "id_card.jpg"
live_path = "live_capture.jpg"

try:
    result = DeepFace.verify(img1_path=id_path, img2_path=live_path)
    print("\n✅ Verification Result:")
    print(result)
    if result["verified"]:
        print("Access Granted — proceed to voting!")
    else:
        print("Access Denied — face does not match.")
except Exception as e:
    print("❌ Error:", e)
