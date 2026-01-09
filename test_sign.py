import datetime
from volcenginesdkcore.signv4 import SignerV4
from volcenginesdkcore.configuration import Configuration
from volcenginesdkcore.rest import RESTClientObject

class MockRequest:
    def __init__(self, method, url, headers, body):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.path = "/api/v2/asr"
        self.host = "openspeech.bytedance.com"

class MockCredentials:
    def __init__(self, ak, sk, region, service):
        self.ak = ak
        self.sk = sk
        self.region = region
        self.service = service

def test_sign():
    # Inspect Signature
    import inspect
    print("Sign Signature:", inspect.signature(SignerV4.sign))
    
    # ... (rest commented out to avoid error for now)
    return
    
    ak = "TEST_AK"
    sk = "TEST_SK"
    region = "cn-north-1"
    
    # SignerV4 __init__ arguments are fuzzy, let's look at signature again
    # (self, /, *args, **kwargs)
    # Usually it doesn't take args in init, but uses them in sign?
    # Or init takes config?
    signer = SignerV4()
    
    headers = {
        "Host": "openspeech.bytedance.com",
        "X-Date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    }
    
    req = MockRequest("GET", "https://openspeech.bytedance.com/api/v2/asr", headers, None)
    creds = MockCredentials(ak, sk, region, "asr") # Service name usually 'asr'
    
    try:
        # sign(self, request, credentials)
        # It mutates the request.headers
        signer.sign(req, creds)
        print("Signed Headers:", req.headers)
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sign()
