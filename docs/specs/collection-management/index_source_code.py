#!/usr/bin/env python3
"""
Source Code Indexer for Weaviate
Indexes source code files from a local directory into the SRC_ENTERPRISE__ collection
"""

import os
import asyncio
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
import argparse
from datetime import datetime

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.config import Tokenization
import weaviate.classes as wvc

# Common source code extensions
SOURCE_EXTENSIONS = {
    # Web
    '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass', '.less',
    '.vue', '.svelte', '.astro',
    # Python
    '.py', '.pyx', '.pyi', '.ipynb',
    # Java/JVM
    '.java', '.kt', '.scala', '.groovy', '.clj',
    # C/C++/C#
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.cs',
    # Go
    '.go',
    # Rust
    '.rs',
    # Ruby
    '.rb', '.erb',
    # PHP
    '.php',
    # Swift/Objective-C
    '.swift', '.m', '.mm',
    # Shell
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    # Config
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.xml', '.env', '.properties',
    # Documentation
    '.md', '.rst', '.txt', '.adoc',
    # SQL
    '.sql',
    # Docker
    'Dockerfile', '.dockerfile',
    # Build files
    'Makefile', 'CMakeLists.txt', 'package.json', 'pom.xml', 'build.gradle',
    'Cargo.toml', 'go.mod', 'requirements.txt', 'Gemfile', 'composer.json'
}

# Directories to skip
SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
    'build', 'dist', 'target', '.next', '.nuxt', '.svelte-kit',
    '.pytest_cache', '.mypy_cache', '.tox', 'coverage', '.coverage',
    '.idea', '.vscode', '.vs', '*.egg-info'
}

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    '.exe', '.dll', '.so', '.dylib', '.a', '.o', '.obj',
    '.class', '.jar', '.war', '.ear',
    '.pyc', '.pyo', '.pyd',
    '.wasm', '.wat',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp',
    '.mp3', '.mp4', '.avi', '.mov', '.wmv',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.db', '.sqlite', '.sqlite3'
}


def should_index_file(file_path: Path) -> bool:
    """Determine if a file should be indexed"""
    # Skip binary files
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    
    # Skip hidden files (except .env, .gitignore, etc.)
    if file_path.name.startswith('.') and file_path.suffix not in SOURCE_EXTENSIONS:
        return False
    
    # Check if it's a source code file
    if file_path.suffix.lower() in SOURCE_EXTENSIONS:
        return True
    
    # Check for special files without extensions
    if file_path.name in SOURCE_EXTENSIONS:
        return True
    
    # Check for common config/build files
    special_files = {'Dockerfile', 'Makefile', 'README', 'LICENSE', 'CHANGELOG'}
    if file_path.name in special_files:
        return True
    
    return False


def get_language_from_extension(file_path: Path) -> str:
    """Get programming language from file extension"""
    ext_to_lang = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.jsx': 'JavaScript',
        '.ts': 'TypeScript', 
        '.tsx': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.sh': 'Shell',
        '.sql': 'SQL',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.xml': 'XML',
        '.md': 'Markdown',
        '.toml': 'TOML',
    }
    return ext_to_lang.get(file_path.suffix.lower(), 'Unknown')


async def create_or_update_schema(client: weaviate.Client):
    """Create or update the SRC_ENTERPRISE__ collection schema"""
    collection_name = "SRC_ENTERPRISE__"
    
    # Check if collection exists
    if client.collections.exists(collection_name):
        print(f"Collection {collection_name} already exists")
        return client.collections.get(collection_name)
    
    # Create collection with schema
    collection = client.collections.create(
        name=collection_name,
        properties=[
            Property(
                name="file_path",
                data_type=DataType.TEXT,
                description="Full path to the source file",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="file_name", 
                data_type=DataType.TEXT,
                description="Name of the file",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="directory",
                data_type=DataType.TEXT,
                description="Directory containing the file",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="content",
                data_type=DataType.TEXT,
                description="Source code content",
                tokenization=Tokenization.WORD
            ),
            Property(
                name="language",
                data_type=DataType.TEXT,
                description="Programming language",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="extension",
                data_type=DataType.TEXT,
                description="File extension",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="size_bytes",
                data_type=DataType.INT,
                description="File size in bytes"
            ),
            Property(
                name="line_count",
                data_type=DataType.INT,
                description="Number of lines in the file"
            ),
            Property(
                name="last_modified",
                data_type=DataType.DATE,
                description="Last modification timestamp"
            ),
            Property(
                name="content_hash",
                data_type=DataType.TEXT,
                description="SHA256 hash of file content",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="project_root",
                data_type=DataType.TEXT,
                description="Root directory of the project",
                tokenization=Tokenization.FIELD
            ),
            Property(
                name="relative_path",
                data_type=DataType.TEXT,
                description="Path relative to project root",
                tokenization=Tokenization.FIELD
            ),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small",
            vectorize_collection_name=False,
        ),
        replication_config=Configure.replication(factor=1)
    )
    
    print(f"Created collection {collection_name} with schema")
    return collection


async def index_file(file_path: Path, project_root: Path, collection, batch_objects: List[Dict]) -> bool:
    """Index a single source code file"""
    try:
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except:
                print(f"  ⚠️  Skipping {file_path} - encoding error")
                return False
        
        # Get file metadata
        stat = file_path.stat()
        relative_path = file_path.relative_to(project_root)
        
        # Create object for Weaviate
        obj = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "directory": str(file_path.parent),
            "content": content,
            "language": get_language_from_extension(file_path),
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "line_count": content.count('\n') + 1,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "project_root": str(project_root),
            "relative_path": str(relative_path),
        }
        
        batch_objects.append(obj)
        return True
        
    except Exception as e:
        print(f"  ❌ Error indexing {file_path}: {e}")
        return False


async def index_directory(directory: str, client: weaviate.Client, batch_size: int = 100):
    """Index all source code files in a directory"""
    project_root = Path(directory).resolve()
    
    if not project_root.exists():
        print(f"❌ Directory {project_root} does not exist")
        return
    
    print(f"📁 Indexing source code from: {project_root}")
    
    # Create or get collection
    collection = await create_or_update_schema(client)
    
    # Collect all files to index
    files_to_index = []
    for root, dirs, files in os.walk(project_root):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        root_path = Path(root)
        for file in files:
            file_path = root_path / file
            if should_index_file(file_path):
                files_to_index.append(file_path)
    
    print(f"📊 Found {len(files_to_index)} files to index")
    
    # Index files in batches
    indexed = 0
    failed = 0
    batch_objects = []
    
    for i, file_path in enumerate(files_to_index, 1):
        success = await index_file(file_path, project_root, collection, batch_objects)
        
        if success:
            indexed += 1
        else:
            failed += 1
        
        # Process batch when full or at the end
        if len(batch_objects) >= batch_size or i == len(files_to_index):
            if batch_objects:
                try:
                    # Insert batch into Weaviate
                    collection.data.insert_many(batch_objects)
                    print(f"  ✅ Indexed batch of {len(batch_objects)} files ({i}/{len(files_to_index)})")
                    batch_objects = []
                except Exception as e:
                    print(f"  ❌ Error inserting batch: {e}")
                    failed += len(batch_objects)
                    batch_objects = []
    
    print(f"\n✨ Indexing complete!")
    print(f"  ✅ Successfully indexed: {indexed} files")
    if failed > 0:
        print(f"  ⚠️  Failed to index: {failed} files")
    
    # Verify collection
    count = collection.aggregate.over_all(total_count=True)
    print(f"  📚 Total documents in collection: {count.total_count}")


async def main():
    parser = argparse.ArgumentParser(description='Index source code into Weaviate')
    parser.add_argument('directory', help='Directory containing source code to index')
    parser.add_argument('--url', default='http://localhost:8080', help='Weaviate URL')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for indexing')
    parser.add_argument('--api-key', help='Weaviate API key (if needed)')
    
    args = parser.parse_args()
    
    # Connect to Weaviate
    if args.api_key:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=args.url,
            auth_credentials=weaviate.auth.AuthApiKey(args.api_key)
        )
    else:
        # Local/anonymous connection
        client = weaviate.connect_to_local(
            host=args.url.replace('http://', '').replace('https://', '').split(':')[0],
            port=int(args.url.split(':')[-1]) if ':' in args.url else 8080
        )
    
    try:
        with client:
            await index_directory(args.directory, client, args.batch_size)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())