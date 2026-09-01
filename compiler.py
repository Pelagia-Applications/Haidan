import aiohttp

# Mapping file extensions to Piston engine language identifiers
PISTON_LANG_MAP = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "cpp": "cpp",
    "c": "c",
    "java": "java",
    "cs": "csharp",
    "rs": "rust",
    "go": "go",
    "sh": "bash"
}

async def execute_source_code(syntax: str, raw_lines: list) -> str:
    """
    Sends raw source code to an open public execution sandbox.
    Bypasses local SSL checking to ensure Render connects without certificate blocks.
    """
    piston_lang = PISTON_LANG_MAP.get(syntax)

    if not piston_lang:
        return f"Error: The file extension type `.{syntax}` does not support execution."

    raw_source = "\n".join(raw_lines)
    payload = {
        "language": piston_lang,
        "version": "*",
        "files": [{"content": raw_source}]
    }

    # Disables strict SSL validation handshakes to clear hosting verification errors
    ssl_context = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(connector=ssl_context) as web_client:
            # Routing via EngineerMan's public unauthenticated sandbox executor cluster
            url = "https://engineer-man.org"
            
            async with web_client.post(url, json=payload) as api_response:
                if api_response.status == 200:
                    result_data = await api_response.json()
                    run_output = result_data.get("run", {})
                    stdout = run_output.get("stdout", "")
                    stderr = run_output.get("stderr", "")
                    
                    console_log = stdout if stdout else stderr
                    if not console_log:
                        return "Process executed successfully with no output returned."

                    return console_log[:1900]
                else:
                    return f"Error: Sandbox compiler engine returned unexpected status code {api_response.status}."
    except Exception as e:
        return f"Runtime execution connection failed: {str(e)}"
