import sys, requests, pathlib

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
IMG = sys.argv[2] if len(sys.argv) > 2 else "sample.jpg"

def main():
    print("== Health ==")
    r = requests.get(f"{BASE}/grafologia/health", timeout=20)
    print(r.status_code, r.text)

    print("\n== Analizar ==")
    with open(IMG, "rb") as f:
        r = requests.post(f"{BASE}/grafologia/analizar", files={"file": f}, timeout=60)
    print(r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)

    print("\n== Informe PDF ==")
    with open(IMG, "rb") as f:
        r = requests.post(f"{BASE}/grafologia/informe_pdf", files={"file": f}, timeout=120)
    out = pathlib.Path("grafo.pdf")
    out.write_bytes(r.content)
    print("PDF guardado:", out.resolve())

if __name__ == "__main__":
    main()
