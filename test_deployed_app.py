import requests
import time

url = "https://leon4gr45-openoperator.hf.space/health"

def test_health():
    print(f"Testing health endpoint: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_health()
