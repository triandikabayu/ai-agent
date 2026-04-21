"""
File Tools — read, write, append, edit, and list files on the local filesystem.
Unrestricted access to any path on the system.
"""

import os
import shutil
from pathlib import Path
from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file from the local filesystem.
    Use this to inspect source code, config files, documentation, or any text file.

    Args:
        file_path: Absolute or relative path to the file to read.
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return f"Error: File not found: {path}"

        if not path.is_file():
            return f"Error: Not a file: {path}"

        # Check file size (limit to 100KB for context management)
        size = path.stat().st_size
        if size > 100_000:
            return (
                f"Error: File too large ({size:,} bytes). "
                f"Maximum readable size is 100KB."
            )

        content = path.read_text(encoding="utf-8", errors="replace")
        line_count = content.count("\n") + 1

        return (
            f"--- {path} ({line_count} lines, {size:,} bytes) ---\n\n"
            f"{content}"
        )

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def create_file(file_path: str, content: str) -> str:
    """Create a new file with the given content. 
    Fails safely if the file already exists to prevent accidental overwrites.
    
    Args:
        file_path: Path to the new file.
        content: The initial content of the file.
    """
    try:
        path = Path(file_path).resolve()
        
        if path.exists():
            return f"Error: File already exists at {path}. Use `edit_file` or `write_file` with overwrite=True to modify it."
            
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        size = path.stat().st_size
        
        return f"✅ Created new file {path} ({size:,} bytes)."
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"


@tool
def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """Write content to a file. Creates the file and parent directories if they don't exist.
    WARNING: By default, this will fail if the file exists to prevent destructive overwriting.
    When editing code, prefer `edit_file`. Only use `overwrite=True` if you explicitly intend to replace the entire file.

    Args:
        file_path: Absolute or relative path for the file to write.
        content: The full content to write to the file.
        overwrite: Set to True to allow overwriting an existing file.
    """
    try:
        path = Path(file_path).resolve()

        if path.exists() and not overwrite:
            return f"Error: {path} already exists. To overwrite it, you must pass overwrite=True, or use edit_file to modify specific lines."

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        size = path.stat().st_size

        return f"✅ Written {size:,} bytes to {path}"

    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def edit_file(file_path: str, target_text: str, replacement_text: str) -> str:
    """Replace a specific block of text in a file with new text. 
    Use this to surgically edit existing files without rewriting the entire file.
    Make sure `target_text` exactly matches the existing text in the file.
    
    Args:
        file_path: Path to the file to edit.
        target_text: Exact string to find and replace.
        replacement_text: The new string that will replace the target text.
    """
    try:
        path = Path(file_path).resolve()
        
        if not path.exists():
            return f"Error: File not found: {path}"
            
        content = path.read_text(encoding="utf-8")
        
        if target_text not in content:
            return "Error: Could not find `target_text` inside the file. Ensure the target text matches exactly, including whitespace and line breaks."
            
        # Create a backup before editing
        try:
            backup_path = path.with_suffix(".bak")
            shutil.copy2(path, backup_path)
        except Exception:
            return "Error: Gagal melakukan operasi backup sebelum mengedit file."
            
        new_content = content.replace(target_text, replacement_text, 1)
        path.write_text(new_content, encoding="utf-8")
        
        return f"✅ Successfully replaced text snippet in {path}."
        
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error editing file: {str(e)}"


@tool
def append_to_file(file_path: str, content: str) -> str:
    """Append text to the end of a file. Good for logs, appending configuration, or chat histories.
    
    Args:
        file_path: Path to the file.
        content: Text to append to the end of the file.
    """
    try:
        path = Path(file_path).resolve()
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # open in append mode
        with open(path, "a", encoding="utf-8") as f:
            if not content.startswith("\n"):
                f.write("\n")
            f.write(content)
            
        return f"✅ Appended content to {path}."
        
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error appending to file: {str(e)}"


@tool
def list_directory(directory_path: str = ".", show_hidden: bool = False) -> str:
    """List the contents of a directory showing files and subdirectories.
    Use this to explore project structure, find files, or understand a codebase layout.

    Args:
        directory_path: Path to the directory to list. Defaults to current directory.
        show_hidden: Whether to include hidden files (starting with dot).
    """
    try:
        path = Path(directory_path).resolve()

        if not path.exists():
            return f"Error: Directory not found: {path}"

        if not path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        dirs = []
        files = []

        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue

            if entry.is_dir():
                # Count immediate children
                try:
                    child_count = sum(1 for _ in entry.iterdir())
                except PermissionError:
                    child_count = "?"
                dirs.append(f"  📁 {entry.name}/ ({child_count} items)")
            else:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                files.append(f"  📄 {entry.name} ({size_str})")

        output = [f"📂 {path}\n"]
        if dirs:
            output.append("Directories:")
            output.extend(dirs)
        if files:
            output.append("\nFiles:")
            output.extend(files)

        if not dirs and not files:
            output.append("  (empty directory)")

        total = len(dirs) + len(files)
        output.append(f"\n  Total: {len(dirs)} dirs, {len(files)} files")

        return "\n".join(output)

    except PermissionError:
        return f"Error: Permission denied: {directory_path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"
