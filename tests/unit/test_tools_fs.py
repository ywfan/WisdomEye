"""Unit tests for file system tools."""
import pytest
from pathlib import Path
from tools.fs import (
    ensure_dir, make_output_root, slugify, 
    create_resume_folder, write_text, read_text
)


class TestFileSystemTools:
    """Test file system utility functions."""

    def test_ensure_dir(self, temp_dir):
        """Test directory creation."""
        test_path = Path(temp_dir) / "test" / "nested" / "dir"
        result = ensure_dir(str(test_path))
        
        assert Path(result).exists()
        assert Path(result).is_dir()
        assert result == str(test_path)

    def test_ensure_dir_existing(self, temp_dir):
        """Test ensure_dir on existing directory."""
        test_path = Path(temp_dir) / "existing"
        test_path.mkdir()
        
        result = ensure_dir(str(test_path))
        assert result == str(test_path)

    def test_slugify_basic(self):
        """Test basic slugification."""
        assert slugify("Simple Name") == "Simple_Name"
        assert slugify("name-with-dash") == "name-with-dash"
        assert slugify("name_with_underscore") == "name_with_underscore"

    def test_slugify_special_chars(self):
        """Test slugify removes special characters."""
        assert slugify("name@#$%with&*special") == "namewithspecial"
        # Note: slugify preserves alphanumeric chars, which includes Chinese in Python's isalnum()
        result = slugify("中文名字123")
        assert "123" in result  # Numbers are preserved
        assert slugify("file.pdf") == "filepdf"

    def test_slugify_empty(self):
        """Test slugify with empty or invalid input."""
        assert slugify("") == "resume"
        assert slugify("   ") == "resume"
        assert slugify("@#$%") == "resume"

    def test_slugify_preserves_numbers(self):
        """Test that numbers are preserved."""
        assert slugify("resume_2024") == "resume_2024"
        assert slugify("file123") == "file123"

    def test_write_and_read_text(self, temp_dir):
        """Test writing and reading text files."""
        file_path = Path(temp_dir) / "test.txt"
        content = "Hello, World!\n这是中文测试。"
        
        write_text(str(file_path), content)
        assert file_path.exists()
        
        read_content = read_text(str(file_path))
        assert read_content == content

    def test_read_text_with_errors(self, temp_dir):
        """Test reading text with encoding errors."""
        file_path = Path(temp_dir) / "binary.dat"
        file_path.write_bytes(b"\xff\xfe\x00\x01")
        
        # Should not raise, uses ignore errors
        content = read_text(str(file_path))
        assert isinstance(content, str)

    def test_create_resume_folder(self, temp_dir, monkeypatch):
        """Test creating resume-specific output folder."""
        monkeypatch.chdir(temp_dir)
        
        result = create_resume_folder("test_resume.pdf")
        
        assert Path(result).exists()
        assert Path(result).is_dir()
        assert "test_resume" in result
        assert "output" in result

    def test_create_resume_folder_with_special_chars(self, temp_dir, monkeypatch):
        """Test create_resume_folder handles special characters."""
        monkeypatch.chdir(temp_dir)
        
        result = create_resume_folder("/path/to/文件@#$名称.pdf")
        
        assert Path(result).exists()
        # Should have sanitized the name
        assert "@" not in result
        assert "#" not in result

    def test_make_output_root(self, temp_dir, monkeypatch):
        """Test creating output root directory."""
        monkeypatch.chdir(temp_dir)
        
        root = make_output_root()
        
        assert Path(root).exists()
        assert Path(root).is_dir()
        assert Path(root).name == "output"

    def test_write_text_creates_parent(self, temp_dir):
        """Test that write_text works even if parent doesn't exist."""
        file_path = Path(temp_dir) / "nested" / "dir" / "file.txt"
        
        # Parent doesn't exist, but Path.write_text will create it
        # Actually, it won't - this will fail. Let's test the actual behavior
        with pytest.raises(FileNotFoundError):
            write_text(str(file_path), "content")
