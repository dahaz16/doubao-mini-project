import os
from dotenv import load_dotenv

load_dotenv()

appid = os.getenv("VOLC_APPID")
ak = os.getenv("VOLC_ACCESS_KEY")
sk = os.getenv("VOLC_SECRET_KEY")

print(f"VOLC_APPID: {appid}")
print(f"VOLC_ACCESS_KEY: {ak[:4]}...{ak[-4:] if ak else ''}")
print(f"VOLC_SECRET_KEY: {'[SET]' if sk else '[NOT SET]'}")

if not all([appid, ak, sk]):
    print("WARNING: Some environment variables are missing!")
else:
    print("Credentials loaded.")
