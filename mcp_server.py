from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("qa-agent")


@mcp.tool()
def generate_test_cases(scenario: str):

    return f"""
Generate:

1. Positive cases
2. Negative cases
3. Edge cases
4. Boundary cases

Scenario:
{scenario}
"""


@mcp.tool()
def run_tests():

    result = subprocess.run(
        ["pytest", "-v"],
        capture_output=True,
        text=True
    )

    return result.stdout


if __name__ == "__main__":
    mcp.run()