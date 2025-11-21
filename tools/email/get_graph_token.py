import os
import json
import msal
from dotenv import load_dotenv

load_dotenv()
TOKEN_CACHE_PATH = os.getenv("OUTLOOK_TOKEN_PATH")


def _get_ms_access_token():
    CLIENT_ID = os.getenv("OUTLOOK_API")
    AUTHORITY = "https://login.microsoftonline.com/consumers"
    SCOPES = ["Mail.Read"]

    # ---- load or create token cache ----
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )

    # ---- try silent token first ----
    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    # ---- if no valid token, do device code flow ----
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to create device flow: {flow}")

        print("Go to:", flow["verification_uri"])
        print("Code:", flow["user_code"])
        input("Press Enter here AFTER signing in and accepting...\n")

        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Failed to acquire token: {json.dumps(result, indent=2)}")

    # ---- persist cache if changed ----
    if cache.has_state_changed:
        with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(cache.serialize())

    return result["access_token"]
