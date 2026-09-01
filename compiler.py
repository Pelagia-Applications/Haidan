import aiohttp

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
    Returns the console output string (stdout, stderr, or error messaging).
    """
    piston_lang = PISTON_LANG_MAP.get(syntax)

    if not piston_lang:
        return f"Error: The file extension type `.{syntax}` does not support compilation pipelines."

    raw_source = "\n".join(raw_lines)
    payload = {
        "language": piston_lang,
        "version": "*",
        "files": [{"content": raw_source}]
    }

    try:
        async with aiohttp.ClientSession() as web_client:
            # Swapping to a fully open public community Piston router endpoint
            async with web_client.post("https://api.emkc.org/api/v2/piston/execute", json=payload) as api_response:
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
                    return f"Error: Compiler container engine returned unexpected code {api_response.status}."
    except Exception as e:
        return f"Runtime execution connection failed: {str(e)}"
