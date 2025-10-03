import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = os.path.join(os.path.dirname(__file__), "sample_texts.json")


def run_tests():
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])

    for sample in samples:
        print(f"\n=== Running Test {sample['id']} ===")

        input_text = sample.get("input_text", "")
        image_path = sample.get("input_image_path", "")
        use_image = sample.get("use_image", None)  # optional explicit choice

        # Decide which input to send
        if use_image is True and image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                resp = requests.post(f"{BASE_URL}/api/process", files={"file": f}, json={"use_image": True})
        elif input_text:
            resp = requests.post(f"{BASE_URL}/api/process", json={"text": input_text, "use_image": False})
        elif image_path and os.path.exists(image_path):
            # fallback to image if text missing
            with open(image_path, "rb") as f:
                resp = requests.post(f"{BASE_URL}/api/process", files={"file": f})
        else:
            print("No valid input for this sample, skipping...")
            continue

        try:
            final_result = resp.json()
        except Exception as e:
            print("Final JSON decode error:", e)
            print("Raw response:", resp.text)
            continue

        print("Final Output:", json.dumps(final_result, indent=2))


if __name__ == "__main__":
    run_tests()
