from pathlib import Path
from src.core.ids import make_logical_document_part_id, make_source_instance_id, make_chunk_id

def test_document_id_is_deterministic():
    textcontent = "hello world"
    file_path = Path("/tmp/file.txt")
    source_instance_id = make_source_instance_id("filesystem", "dev1", file_path)
    a = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator=f"filesystem:{file_path}")
    b = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator=f"filesystem:{file_path}")
    assert a == b


def test_document_id_changes_with_device():
    device_id_1 = "dev1"
    device_id_2 = "dev2"
    source_type = "filesystem"
    source_path = Path("/tmp/file.txt")
    a = make_source_instance_id(source_type, device_id_1, source_path)
    b = make_source_instance_id(source_type, device_id_2, source_path)
    assert a != b


def test_chunk_id_changes_with_checksum():
    textcontent = "hello world"
    file_path = Path("/tmp/file.txt")
    source_instance_id = make_source_instance_id("filesystem", "dev1", file_path)
    doc_id = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator=f"filesystem:{file_path}")
    a = make_chunk_id(doc_id, "abc", 0)
    b = make_chunk_id(doc_id, "def", 0)
    assert a != b

def test_chunk_id_changes_with_index():
    textcontent = "hello world"
    source_instance_id = make_source_instance_id("filesystem", "dev1", Path("/tmp/file.txt"))
    doc_id = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator=f"filesystem:/tmp/file.txt")
    a = make_chunk_id(doc_id, "abc", 0)
    b = make_chunk_id(doc_id, "abc", 1)
    assert a != b

def test_symlink_resolves_to_same_source_id(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("hello")

    link = tmp_path / "link.txt"
    link.symlink_to(real)
    
    a = make_source_instance_id("filesystem", "dev1", real.resolve())
    b = make_source_instance_id("filesystem", "dev1", link.resolve())
    assert a == b

