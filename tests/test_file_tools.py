import pytest
from tools.file_tools import create_file

def test_create_file_success(tmp_path):
    # setup path
    # Menggunakan rujukan lokasi test di dalam variabel tmp_path
    file_path = tmp_path / "test_file.txt"
    content = "Hello, testing!"
    
    # Panggil modul create_file menggunakan rujukan lokasi test tersebut
    result = create_file.invoke({"file_path": str(file_path), "content": content})
    
    # Assert untuk memastikan fungsionalitas tepat
    assert "✅ Created new file" in result
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == content
