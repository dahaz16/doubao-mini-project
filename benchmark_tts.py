import requests
import time
import sys

def benchmark_tts(text):
    url = f"http://192.168.3.73:8000/tts/stream?text={text}"
    print(f"Benchmarking: {url}")
    
    start_time = time.time()
    try:
        with requests.get(url, stream=True, timeout=10) as r:
            first_byte_time = None
            total_bytes = 0
            for chunk in r.iter_content(chunk_size=1):
                if first_byte_time is None:
                    first_byte_time = time.time() - start_time
                    print(f"Time to first byte (TTFB): {first_byte_time:.3f}s")
                total_bytes += len(chunk)
            
            total_time = time.time() - start_time
            print(f"Total time: {total_time:.3f}s")
            print(f"Total bytes: {total_bytes}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    t = "你好呀，很高兴见到你。"
    if len(sys.argv) > 1:
        t = sys.argv[1]
    benchmark_tts(t)
