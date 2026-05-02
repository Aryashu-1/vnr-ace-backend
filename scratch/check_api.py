
import requests
import json

def check():
    try:
        response = requests.get("http://localhost:8000/api/v1/data/students")
        if response.status_code == 200:
            data = response.json()
            print(f"Total students returned: {len(data)}")
            if len(data) > 0:
                print("First student data sample:")
                print(json.dumps(data[0], indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    check()
