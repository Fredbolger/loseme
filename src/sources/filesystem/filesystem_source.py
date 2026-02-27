import os
from pathlib import Path
from typing import List, Optional, Callable, Mapping
import hashlib
from datetime import datetime
from src.sources.filesystem.filesystem_model import FilesystemIndexingScope 
from src.sources.base.models import IngestionSource, Document, OpenDescriptor, DocumentPart
from src.core.ids import make_logical_document_part_id, make_source_instance_id
from storage.metadata_db.document import get_document_by_id
from src.sources.base.registry import extractor_registry, ExtractorRegistry, ingestion_source_registry
from src.sources.base.docker_path_translation import host_path_to_container, container_path_to_host
from fnmatch import fnmatch
import logging
import os
import warnings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

device_id = os.environ.get("LOSEME_DEVICE_ID", os.uname().nodename)

if device_id is None:
    raise ValueError("LOSEME_DEVICE_ID environment variable is not set.")

def is_running_in_docker():
    return os.path.exists("/.dockerenv")

suffix_command_dict = {
    '.txt': 'vim',
    '.md': 'vim',
    '.pdf': 'xdg-open',
    '.docx': 'xdg-open',
    '.xlsx': 'xdg-open',
    '.pptx': 'xdg-open',
    '.fallback': 'cat',
}

class FilesystemIngestionSource(IngestionSource):
    _extractor_registry = extractor_registry

    def __init__(self, 
                 scope: FilesystemIndexingScope,
                 should_stop: Optional[Callable[[], bool]] = None,
                 update_if_changed_after: Optional[datetime] = None
                 ):
        super().__init__(scope = scope, should_stop=should_stop, update_if_changed_after=update_if_changed_after)
        self.scope = scope
        self.should_stop = should_stop
        logger.debug(f"Initialized FilesystemIngestionSource with scope: {self.scope.serialize()}")
        logger.debug(f"Extractor registry contains: {list(self.extractor_registry.list_extractors())}")

    def _walk_files(self):
        """
        Walk through all files in scope.directories.
        Returns (root, path) tuples, sorted for stable resumable indexing.
        """
        all_files = []

        # Check if self.scope.directories is actually a file
        scope_directories = self.scope.directories

        if is_running_in_docker():
            logger.debug("Running in Docker, translating scope directories to host paths for file walking")
            scope_directories = [host_path_to_container(str(dir)) for dir in self.scope.directories]
            logger.debug(f"Translated scope directories: {scope_directories}")
        
        #if len(self.scope.directories) == 1 and self.scope.directories[0].is_file():
        if len(scope_directories) == 1 and Path(scope_directories[0]).is_file():
            #root = self.scope.directories[0].parent
            root = Path(scope_directories[0]).parent
            #path = self.scope.directories[0]
            path = Path(scope_directories[0])
            #all_files.append((root, path))
            all_files.append((root, path))
            return all_files
            
        #for directory in self.scope.directories:
        for directory in scope_directories:
            root = Path(directory)
            for path in root.rglob("*"):
                if path.is_file():
                    all_files.append((root, path))

        return sorted(all_files, key=lambda x: str(x[1]))
    
    @property
    def extractor_registry(self) -> ExtractorRegistry:
        return self._extractor_registry

    def iter_documents(self) -> List[Document]:
        """ 
        Iterate over documents in the scope. This should not simply recycle list_documents()
        but actually yield documents one by one for memory efficiency.
        """
        scope_directories = self.scope.directories
        
        if is_running_in_docker():
            logger.debug("Running in Docker, translating scope directories to host paths for document iteration")
            scope_directories = [host_path_to_container(str(dir)) for dir in self.scope.directories]
            logger.debug(f"Translated scope directories: {scope_directories}")

        for docker_root_path, root_path in zip(scope_directories, self.scope.directories):
            logger.debug(f"Walking through directory: {docker_root_path}")
            docker_root = Path(docker_root_path)
            root = Path(root_path)
            for docker_path in docker_root.rglob("*"):
                logger.debug(f"Processing path: {docker_path}")
                if self.should_stop():
                    logger.info("Stop requested, terminating filesystem ingestion source.")
                    break

                if docker_path.is_file():
                    logger.debug(f"Found file: {docker_path}")
                    rel_path = docker_path.relative_to(docker_root).as_posix()
                    
                    if self.scope.exclude_patterns and any(
                        fnmatch(rel_path, pattern) for pattern in self.scope.exclude_patterns
                    ):
                        continue

                    if self.scope.include_patterns and not any(
                        fnmatch(rel_path, pattern) for pattern in self.scope.include_patterns
                    ):
                        continue
                    
                    extracted = self.extractor_registry.extract(docker_path)
                    
                    if extracted is None:
                        logger.warning(f"No suitable extractor found for file: {docker_path}, skipping.")
                        continue
                    logger.debug(f"Extracted content from {docker_path} with content type {extracted.content_types[0]}")

                    document_checksum = hashlib.sha256(
                           extracted.text().strip().encode("utf-8")
                           ).hexdigest()

                    source_instance_id = make_source_instance_id(
                            source_type="filesystem",
                            source_path=container_path_to_host(str(docker_path)),
                            device_id=device_id,
                    )
                    doc_id = make_logical_document_part_id(
                            source_instance_id=source_instance_id,
                            unit_locator=extracted.unit_locators[0]
                    )
                    extracted_metadata = extracted.metadata[0]
                    document = Document(
                        id=doc_id,
                        source_type="filesystem",
                        source_id=source_instance_id,
                        device_id=device_id,
                        source_path=str(container_path_to_host(str(docker_path))),
                        checksum=document_checksum,
                        created_at=datetime.fromtimestamp(docker_path.stat().st_ctime),
                        updated_at=datetime.fromtimestamp(docker_path.stat().st_mtime),
                        metadata={
                            **extracted_metadata,
                            "relative_path": rel_path,
                            "size": docker_path.stat().st_size,
                        },
                    )
                    
                    document.add_part(DocumentPart(
                                        document_part_id=doc_id,
                                        text=extracted.text(),
                                        source_type="filesystem",
                                        checksum=document_checksum,
                                        device_id=device_id,
                                        source_path=str(container_path_to_host(str(docker_path))),
                                        source_instance_id=source_instance_id,
                                        #unit_locator=f"filesystem:{path}",
                                        unit_locator=f"filesystem:{container_path_to_host(str(docker_path))}",
                                        content_type=extracted.content_types[0],
                                        extractor_name=extracted.extractor_names[0],
                                        extractor_version=extracted.extractor_versions[0],
                                        metadata_json=extracted.metadata[0],
                                        created_at=document.created_at,
                                        updated_at=document.updated_at,
                                        )
                    )
            
                    yield document
    
    def extract_by_document_id(self,
                             document_id: str
                               ) -> Optional[Document]:
        """
        Extract a single document's content with all its parts by its document ID.
        Args:
            document_id: The unique identifier of the document to extract.
        Returns:
            The extracted Document object, or None if extraction fails.
        """

        try:
            doc_record = get_document_by_id(document_id)
            logger.debug(f"Retrieved document record for ID {document_id}: {doc_record}")

            if doc_record is None:
                raise ValueError(f"Document with ID {document_id} not found in metadata database.")
                return None

            source_path = Path(doc_record["source_path"])
            extracted = self.extractor_registry.extract(source_path)
            if extracted is None:
                raise ValueError(f"No suitable extractor found for file: {source_path}")
                return None
            document_checksum = hashlib.sha256(
                   extracted.text.strip().encode("utf-8")
                   ).hexdigest()

            metadata = doc_record.get("metadat_json", {})

            return Document(
                id=document_id,
                source_type="filesystem",
                source_id=doc_record["source_instance_id"],
                device_id=doc_record["device_id"],
                source_path=str(source_path),
                texts=extracted.texts,
                unit_locators=extracted.unit_locators,
                content_types=extracted.content_types,
                extractor_names=extracted.extractor_names,
                extractor_versions=extracted.extractor_versions,
                checksum=document_checksum,
                created_at=datetime.fromtimestamp(source_path.stat().st_ctime),
                updated_at=datetime.fromtimestamp(source_path.stat().st_mtime),
                metadata={
                    **metadata,
                    "relative_path": os.path.relpath(source_path, LOSEME_DATA_DIR),
                    "size": source_path.stat().st_size,
                },
            )
            
        except Exception as e:
            logger.error(f"Error extracting document {document_id}: {e}")
            return None
    
    def get_open_descriptor(self, document_part: dict) -> OpenDescriptor:
        source_path = document_part["source_path"]
        device_id = document_part["device_id"]
        
        suffix = Path(source_path).suffix.lower()
        if suffix in suffix_command_dict:
            os_command = suffix_command_dict[suffix]
        else:
            os_command = suffix_command_dict['.fallback']

        return OpenDescriptor(
            source_type="filesystem",
            target=source_path,   # always relative
            extra={
                "device_id": device_id,
            },
            os_command=os_command
        )

ingestion_source_registry.register_source("filesystem", FilesystemIngestionSource)
