"""
Hardened OpenAI client with proper retry logic, timeouts, and SSL configuration.
"""
import certifi
import httpx
import os
from openai import AsyncOpenAI


def make_async_client() -> AsyncOpenAI:
    """
    Create a hardened AsyncOpenAI client with:
    - Proper retry logic
    - Extended timeouts
    - SSL certificate verification
    - HTTP/2 disabled (avoids macOS TLS edge cases)
    """
    transport = httpx.AsyncHTTPTransport(retries=3)
    
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=15.0, read=60.0, write=60.0, pool=60.0),
        transport=transport,
        verify=certifi.where(),
        proxies=None,
        http2=False,  # avoids macOS TLS edge cases
    )
    
    # Ensure SSL certs are available
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    
    return AsyncOpenAI(http_client=http_client, max_retries=2)

