import aiohttp

GLOT_LANG_MAP = {
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
    Sends raw source code to the Glot.io open public execution sandbox.
    """
    glot_lang = GLOT_LANG_MAP.get(syntax)

    if not glot_lang:
        return f"Error: The file extension type `.{syntax}` does not support compilation pipelines."

    raw_source = "\n".join(raw_lines)
    
    # Glot.io expects a structural JSON layout tracking file properties
    payload = {
        "files": [
            {
                "name": f"main.{syntax}",
                "content": raw_source
            }
        ]
    }

    # Bypasses local verification checks to resolve host configuration handshakes smoothly
    ssl_context = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(connector=ssl_context) as web_client:
            # Pushing execution request directly through Glot's open runner service
            url = f"https://glot.io{glot_lang}/latest"
            
            async with web_client.post(url, json=payload) as api_response:
                if api_response.status == 200:
                    result_data = await api_response.json()
                    
                    stdout = result_data.get("stdout", "")
                    stderr = result_data.get("stderr", "")
                    error = result_data.get("error", "")
                    
                    # Combine output metrics safely
                    console_log = ""
                    if stdout:
                        console_log += stdout
                    if stderr:
                        console_log += stderr
                    if error:
                        console_log += f"Execution Error: {error}"
                        
                    if not console_log:
                        return "Process executed successfully with no output returned."

                    return console_log[:1900]
                else:
                    return f"Error: Sandbox compiler engine returned unexpected status code {api_response.status}."
    except Exception as e:
        return f"Runtime execution connection failed: {str(e)}"
