from deepface import DeepFace
result = DeepFace.verify(img1_path="id_card.jpg", img2_path="live_capture.jpg")
print(result)
