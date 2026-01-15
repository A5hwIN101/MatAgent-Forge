import requests

response = requests.post(
    "http://localhost:8000/api/analyze",
    json={"material_name": "NaCl"},
    stream=True
)

for chunk in response.iter_content(decode_unicode=True):
    if chunk:
        print(chunk, end="", flush=True)