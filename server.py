
#!/usr/bin/env python3
"""
MCP Server for Byteflow API

This server provides tools to interact with the Byteflow API,
starting with a health check endpoint.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
import httpx
from pydantic import BaseModel, Field, ConfigDict
from fastmcp import FastMCP # Corrected import: FastMCP is directly from fastmcp

# Initialize IMMEDIATELY after imports
mcp = FastMCP("byteflow_mcp")

API_BASE_URL = "https://apidoc.byteflow.bot"
CHARACTER_LIMIT = 25000

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"

class ByteflowGetHealthInput(BaseModel):
    """Input parameters for checking the Byteflow API health."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format for the health status."
    )

async def _make_api_request(endpoint: str, method: str = "GET", **kwargs) -> dict:
    """Reusable function for all API calls."""
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.request(
            method,
            endpoint,
            timeout=30.0,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

def _handle_api_error(e: Exception) -> str:
    """Consistent error formatting."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return "Error: Resource not found."
        elif e.response.status_code == 403:
            return "Error: Permission denied."
        elif e.response.status_code == 401:
            return "Error: Authentication failed."
        elif e.response.status_code == 429:
            return "Error: Rate limit exceeded."
        # Ensure response.text is handled if it's not JSON or empty
        try:
            error_detail = e.response.json()
        except httpx.ReadError: # Catches if response is not valid JSON
            error_detail = e.response.text
        return f"Error: API request failed with status {e.response.status_code}: {error_detail}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out."
    elif isinstance(e, httpx.RequestError): # Catch other httpx request errors like ConnectError
        return f"Error: Network request failed: {e}"
    return f"Error: {type(e).__name__}: {e}"

@mcp.tool(
    name="byteflow_get_health",
    annotations={
        "title": "Get Byteflow API Health Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def byteflow_get_health(params: ByteflowGetHealthInput) -> str:
    """Checks the current operational status of the Byteflow API.

    Args:
        params (ByteflowGetHealthInput): Validated input parameters.
            - response_format (ResponseFormat): Desired output format (Markdown or JSON).

    Returns:
        str: The health status of the Byteflow API.

        Markdown format:
        - "Byteflow API Status: UP"
        - "Byteflow API Status: DOWN (Error details...)"

        JSON format:
        {
            "status": "UP"
        }
        or
        {
            "error": "Error message"
        }

    Examples:
        - Use case 1: Check if the Byteflow API is operational.
          `byteflow_get_health()`
        - Use case 2: Get the health status in JSON format.
          `byteflow_get_health(response_format="json")`

    Error Handling:
        - All exceptions caught via _handle_api_error, returning a descriptive error message.
        - HTTP status errors (e.g., 500) will be reported.
    """
    try:
        response_data = await _make_api_request("api/health", method="GET")
        status = response_data.get("status", "UNKNOWN")

        if params.response_format == ResponseFormat.JSON:
            # Return a string representation of the dictionary for JSON output
            return str({"status": status})
        else:
            output = f"Byteflow API Status: {status}"
            if len(output) > CHARACTER_LIMIT:
                output = output[:CHARACTER_LIMIT - 3] + "..."
            return output
    except Exception as e:
        error_message = _handle_api_error(e)
        if params.response_format == ResponseFormat.JSON:
            # Return a string representation of the dictionary for JSON error output
            return str({"error": error_message})
        else:
            output = f"Byteflow API Status: Error - {error_message}"
            if len(output) > CHARACTER_LIMIT:
                output = output[:CHARACTER_LIMIT - 3] + "..."
            return output

if __name__ == "__main__":
    mcp.run()
