from browser_use_sdk.v3 import AsyncBrowserUse


def get_browseruse_client() -> AsyncBrowserUse:
    return AsyncBrowserUse()