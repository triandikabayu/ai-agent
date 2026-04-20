"""
Code Runner Tool — execute shell commands and utility tools.
"""

import subprocess
from datetime import datetime
from langchain_core.tools import tool
from config.settings import CODE_RUNNER_TIMEOUT


@tool
def get_current_datetime() -> str:
    """Get the current date and time. Use this when the user asks about
    the current time, date, day of the week, or anything time-related.
    """
    now = datetime.now()
    return (
        f"📅 Current Date & Time:\n"
        f"  Date: {now.strftime('%A, %B %d, %Y')}\n"
        f"  Time: {now.strftime('%H:%M:%S')}\n"
        f"  ISO: {now.isoformat()}"
    )


@tool
def run_command(command: str, working_directory: str = None) -> str:
    """Execute a shell command and return its output.
    Use this to run build commands, install packages, run scripts, check versions,
    or any other command-line operation.

    Args:
        command: The shell command to execute.
        working_directory: Optional directory to run the command in. Defaults to current directory.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=CODE_RUNNER_TIMEOUT,
            cwd=working_directory,
        )

        output_parts = []

        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        if result.returncode != 0:
            output_parts.insert(0, f"⚠️ Command exited with code {result.returncode}")
        else:
            output_parts.insert(0, "✅ Command completed successfully")

        output = "\n\n".join(output_parts)

        # Truncate very long output
        if len(output) > 5000:
            output = output[:5000] + "\n\n... [Output truncated]"

        return output

    except subprocess.TimeoutExpired:
        return (
            f"⚠️ Command timed out after {CODE_RUNNER_TIMEOUT} seconds.\n"
            f"Command: {command}"
        )
    except FileNotFoundError:
        return f"Error: Command not found or invalid: {command}"
    except Exception as e:
        return f"Error running command: {str(e)}"
