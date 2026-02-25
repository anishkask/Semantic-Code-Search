"""
AST-aware code chunker for semantic code search.

This module implements intelligent chunking of Python code along AST boundaries,
preserving semantic structure and metadata for vector embedding and retrieval.
"""

import ast
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Union, Dict, Any

# Configure logging for error messages
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def parse_file(file_path: Path) -> Optional[ast.Module]:
    """
    Parse a Python file and return its Abstract Syntax Tree.
    
    This is the foundation function - all other chunking operations depend on
    successfully parsing the source code into an AST. We use Python's built-in
    `ast.parse()` which handles the lexing and parsing for us.
    
    Args:
        file_path: Path to the Python file to parse
        
    Returns:
        ast.Module node representing the parsed file, or None if parsing fails
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        SyntaxError: If the file contains invalid Python syntax
        
    Example:
        >>> tree = parse_file(Path("example.py"))
        >>> isinstance(tree, ast.Module)
        True
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # ast.parse() returns an ast.Module node (the root of the AST)
        # We pass the filename for better error messages
        tree = ast.parse(source_code, filename=str(file_path))
        return tree
        
    except FileNotFoundError:
        # Re-raise with clearer message
        raise FileNotFoundError(f"File not found: {file_path}")
    except SyntaxError as e:
        # Re-raise to let caller handle (we'll catch these later in traversal)
        raise SyntaxError(f"Syntax error in {file_path}: {e}")


def traverse_ast(tree: ast.Module) -> List[Tuple[str, str, int]]:
    """
    Traverse the AST and identify top-level functions, classes, and methods.
    
    This function manually walks the AST (not using ast.walk()) and tracks parent
    context to distinguish:
    - Module-level functions (functions at the top level)
    - Classes (class definitions at the top level)
    - Methods (functions inside class bodies)
    
    Nested functions are NOT chunked separately - they stay inside their parent chunk.
    Module-level code (imports, assignments) is skipped.
    
    Args:
        tree: The AST Module node to traverse
        
    Returns:
        List of tuples: (name, node_type, line_number)
        - name: The name of the function/class/method
        - node_type: One of "function", "class", or "method"
        - line_number: The line number where the node is defined
        
    Example:
        >>> tree = parse_file(Path("example.py"))
        >>> nodes = traverse_ast(tree)
        >>> for name, node_type, line_num in nodes:
        ...     print(f"{name} ({node_type}) at line {line_num}")
    """
    results: List[Tuple[str, str, int]] = []
    parent_stack: List[ast.AST] = []  # Track parent nodes during traversal
    
    def visit_node(node: ast.AST) -> None:
        """Recursively visit AST nodes, tracking parent context."""
        # Check if this is a top-level function or class
        if isinstance(node, ast.FunctionDef):
            # Determine if this is a method, nested function, or module-level function
            if parent_stack and isinstance(parent_stack[-1], ast.ClassDef):
                # Function inside a class = method
                node_type = "method"
                results.append((node.name, node_type, node.lineno))
            elif parent_stack and isinstance(parent_stack[-1], ast.FunctionDef):
                # Function inside a function = nested function (skip adding to results)
                # But still need to traverse its body
                node_type = None
            else:
                # Function at module level = module-level function
                node_type = "function"
                results.append((node.name, node_type, node.lineno))
            
            # Push this function onto the stack and traverse its body
            # (even nested functions need their bodies traversed)
            parent_stack.append(node)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
            parent_stack.pop()
            
        elif isinstance(node, ast.ClassDef):
            # Class definition at module level
            results.append((node.name, "class", node.lineno))
            
            # Push this class onto the stack and traverse its body
            parent_stack.append(node)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
            parent_stack.pop()
            
        else:
            # For other nodes, just traverse children without tracking
            # (we skip module-level code like imports, assignments)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
    
    # Start traversal from the module body
    for node in tree.body:
        visit_node(node)
    
    return results


def extract_source(node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef], 
                   source: str) -> str:
    """
    Extract the complete source code for a node, including decorators.
    
    This function handles decorators that appear above function/class definitions.
    Since ast.get_source_segment() only extracts from the node's starting position
    (the 'def' or 'class' keyword), we need to manually include decorators that
    appear before the definition.
    
    Args:
        node: The AST node to extract (FunctionDef, AsyncFunctionDef, or ClassDef)
        source: The original source code string
        
    Returns:
        The complete source code including decorators, or just the node if extraction fails
        
    Example:
        >>> source = '@decorator\\ndef func(): pass'
        >>> tree = ast.parse(source)
        >>> func_node = tree.body[0]
        >>> extract_source(func_node, source)
        '@decorator\\ndef func(): pass'
    """
    # Get the node's source segment (without decorators)
    node_source = ast.get_source_segment(source, node)
    if node_source is None:
        # Fallback: return empty string if extraction fails
        return ""
    
    # Check if node has decorators
    if not hasattr(node, 'decorator_list') or not node.decorator_list:
        # No decorators, return just the node source
        return node_source
    
    # Find the starting line of the first decorator
    # All decorators should be on consecutive lines above the node
    source_lines = source.splitlines(keepends=True)
    
    # Get the minimum line number among all decorators
    # Line numbers in AST are 1-indexed, but list indices are 0-indexed
    first_decorator_line = min(dec.lineno for dec in node.decorator_list)
    node_start_line = node.lineno
    
    # Extract decorator lines (from first decorator line to line before node)
    # We subtract 1 because lineno is 1-indexed but list indices are 0-indexed
    decorator_start_idx = first_decorator_line - 1
    node_start_idx = node_start_line - 1
    
    # Extract decorator lines
    decorator_source = ''.join(source_lines[decorator_start_idx:node_start_idx])
    
    # Combine decorators with node source
    return decorator_source + node_source


# Threshold for replacing large class chunks with header-only (class def, docstring, attributes)
_CLASS_HEADER_THRESHOLD = 10_000


def _extract_class_header(node: ast.ClassDef, source: str) -> str:
    """
    Extract class definition, docstring, and attribute assignments only.
    Skips method bodies (they are separate chunks). Used for large classes
    to keep chunk size manageable without losing retrievable information.
    """
    source_lines = source.splitlines(keepends=True)
    parts: List[str] = []

    # Decorators (if any)
    if hasattr(node, "decorator_list") and node.decorator_list:
        first_dec = min(dec.lineno for dec in node.decorator_list)
        decorator_source = "".join(source_lines[first_dec - 1 : node.lineno - 1])
        parts.append(decorator_source)

    # Class definition line(s): from node.lineno to the line before first body stmt
    if node.body:
        end_line = node.body[0].lineno
        class_def = "".join(source_lines[node.lineno - 1 : end_line - 1])
    else:
        class_def = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
    parts.append(class_def)

    # Docstring and attribute assignments only (skip methods)
    def _is_docstring(val: ast.AST) -> bool:
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return True
        # ast.Str exists in Python < 3.8 for string literals
        if getattr(ast, "Str", None) and isinstance(val, ast.Str):
            return True
        return False

    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(stmt, ast.Expr) and _is_docstring(stmt.value):
            seg = ast.get_source_segment(source, stmt)
            if seg:
                parts.append(seg)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            seg = ast.get_source_segment(source, stmt)
            if seg:
                parts.append(seg)

    return "".join(parts)


def _traverse_with_nodes(tree: ast.Module) -> List[Tuple[Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef], str, str]]:
    """
    Traverse the AST and return nodes with their type and parent class.
    
    This is an internal helper function that returns actual AST nodes along with
    their metadata, used by build_chunks_from_file.
    
    Args:
        tree: The AST Module node to traverse
        
    Returns:
        List of tuples: (node, node_type, parent_class_name)
        - node: The AST node (FunctionDef, AsyncFunctionDef, or ClassDef)
        - node_type: One of "function", "class", or "method"
        - parent_class_name: Name of parent class if method, empty string otherwise
    """
    results: List[Tuple[Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef], str, str]] = []
    parent_stack: List[ast.AST] = []  # Track parent nodes during traversal
    
    def visit_node(node: ast.AST) -> None:
        """Recursively visit AST nodes, tracking parent context."""
        # Check if this is a top-level function or class
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine if this is a method, nested function, or module-level function
            if parent_stack and isinstance(parent_stack[-1], ast.ClassDef):
                # Function inside a class = method
                node_type = "method"
                parent_class_name = parent_stack[-1].name
                results.append((node, node_type, parent_class_name))
            elif parent_stack and isinstance(parent_stack[-1], (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Function inside a function = nested function (skip adding to results)
                # But still need to traverse its body
                pass
            else:
                # Function at module level = module-level function
                node_type = "function"
                results.append((node, node_type, ""))
            
            # Push this function onto the stack and traverse its body
            # (even nested functions need their bodies traversed)
            parent_stack.append(node)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
            parent_stack.pop()
            
        elif isinstance(node, ast.ClassDef):
            # Class definition at module level
            results.append((node, "class", ""))
            
            # Push this class onto the stack and traverse its body
            parent_stack.append(node)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
            parent_stack.pop()
            
        else:
            # For other nodes, just traverse children without tracking
            # (we skip module-level code like imports, assignments)
            for child in ast.iter_child_nodes(node):
                visit_node(child)
    
    # Start traversal from the module body
    for node in tree.body:
        visit_node(node)
    
    return results


def build_chunks_from_file(file_path: Path, repo_root: Path) -> List[Dict[str, Any]]:
    """
    Build complete chunk objects from a Python file.
    
    This function combines parsing, traversal, and source extraction to produce
    a list of chunk dictionaries with all required metadata fields.
    
    Args:
        file_path: Path to the Python file to process
        repo_root: Root directory of the repository (for relative paths)
        
    Returns:
        List of chunk dictionaries, each containing:
        - id: Unique identifier (filepath + "::" + name)
        - name: Function/class/method name
        - type: "function", "class", or "method"
        - source: Complete source code including decorators
        - file_path: Relative path from repo_root
        - start_line: First decorator line if decorated, else def/class line
        - end_line: Last line of the node
        - parent_class: Parent class name if method, empty string otherwise
        
    Example:
        >>> chunks = build_chunks_from_file(Path("app.py"), Path("."))
        >>> len(chunks) > 0
        True
    """
    # Parse the file
    tree = parse_file(file_path)
    if tree is None:
        return []
    
    # Read source code
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Get relative path from repo_root
    try:
        relative_path = str(file_path.relative_to(repo_root))
    except ValueError:
        # If file_path is not relative to repo_root, use absolute path
        relative_path = str(file_path)
    
    # Traverse AST to get nodes with metadata
    nodes_with_metadata = _traverse_with_nodes(tree)
    
    chunks: List[Dict[str, Any]] = []
    
    for node, node_type, parent_class_name in nodes_with_metadata:
        # Extract source code including decorators
        source = extract_source(node, source_code)

        # For large classes: replace with header-only (def, docstring, attributes)
        # to avoid truncation during embedding; methods are separate chunks
        if node_type == "class" and len(source) > _CLASS_HEADER_THRESHOLD:
            source = _extract_class_header(node, source_code)
        
        # Determine start_line: first decorator line if decorated, else node's lineno
        if hasattr(node, 'decorator_list') and node.decorator_list:
            start_line = min(dec.lineno for dec in node.decorator_list)
        else:
            start_line = node.lineno
        
        # Get end_line from node's end_lineno
        # end_lineno is available in Python 3.8+
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            end_line = node.end_lineno
        else:
            # Fallback: count lines in source
            end_line = start_line + source.count('\n')
        
        # Generate unique ID: include parent class for methods, and line number to
        # avoid collisions (e.g. overloaded locate_app, multiple App classes)
        if node_type == "method" and parent_class_name:
            chunk_id = f"{relative_path}::{parent_class_name}.{node.name}:{start_line}"
        else:
            chunk_id = f"{relative_path}::{node.name}:{start_line}"
        
        # Build chunk dictionary
        chunk = {
            "id": chunk_id,
            "name": node.name,
            "type": node_type,
            "source": source,
            "file_path": relative_path,
            "start_line": start_line,
            "end_line": end_line,
            "parent_class": parent_class_name
        }
        
        chunks.append(chunk)
    
    return chunks


def build_chunks_from_repo(repo_root: Path) -> List[Dict[str, Any]]:
    """
    Walk an entire directory tree and build chunks from all Python files.
    
    This function recursively walks through the repository directory, finds all
    .py files, processes each one with build_chunks_from_file(), and collects
    all chunks into a single list. Files that fail to parse are skipped gracefully
    with error logging.
    
    Args:
        repo_root: Root directory of the repository to process
        
    Returns:
        List of all chunk dictionaries from all Python files in the repository
        
    Example:
        >>> chunks = build_chunks_from_repo(Path("flask"))
        >>> len(chunks) > 0
        True
    """
    all_chunks: List[Dict[str, Any]] = []
    repo_root = Path(repo_root).resolve()
    
    # Walk through all .py files in the repository
    for py_file in repo_root.rglob("*.py"):
        try:
            # Process the file
            file_chunks = build_chunks_from_file(py_file, repo_root)
            all_chunks.extend(file_chunks)
        except FileNotFoundError as e:
            logger.warning(f"Skipping {py_file}: {e}")
            continue
        except SyntaxError as e:
            logger.warning(f"Skipping {py_file} due to syntax error: {e}")
            continue
        except Exception as e:
            logger.warning(f"Skipping {py_file} due to error: {e}")
            continue
    
    return all_chunks


def print_chunk_summary(chunks: List[Dict[str, Any]]) -> None:
    """
    Print a summary of the chunk collection.
    
    This function analyzes the chunk list and prints:
    - Total number of chunks
    - Breakdown by type (function/class/method)
    - Average chunk length in tokens (approximate: split by whitespace)
    - Top 5 largest chunks by line count
    
    Args:
        chunks: List of chunk dictionaries to summarize
        
    Example:
        >>> chunks = build_chunks_from_repo(Path("flask"))
        >>> print_chunk_summary(chunks)
    """
    if not chunks:
        print("No chunks to summarize.")
        return
    
    total_chunks = len(chunks)
    
    # Breakdown by type
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk.get("type", "unknown")
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
    
    # Calculate average chunk length in tokens
    total_tokens = 0
    for chunk in chunks:
        source = chunk.get("source", "")
        tokens = len(source.split())  # Approximate: split by whitespace
        total_tokens += tokens
    avg_tokens = total_tokens / total_chunks if total_chunks > 0 else 0
    
    # Find top 5 largest chunks by line count
    chunks_with_line_count = []
    for chunk in chunks:
        start_line = chunk.get("start_line", 0)
        end_line = chunk.get("end_line", 0)
        line_count = end_line - start_line + 1
        chunks_with_line_count.append((chunk, line_count))
    
    # Sort by line count (descending) and take top 5
    chunks_with_line_count.sort(key=lambda x: x[1], reverse=True)
    top_5_chunks = chunks_with_line_count[:5]
    
    # Print summary
    print("=" * 80)
    print("CHUNK SUMMARY")
    print("=" * 80)
    print(f"\nTotal chunks: {total_chunks}")
    
    print(f"\nBreakdown by type:")
    for chunk_type in sorted(type_counts.keys()):
        count = type_counts[chunk_type]
        percentage = (count / total_chunks * 100) if total_chunks > 0 else 0
        print(f"  {chunk_type:12s}: {count:5d} ({percentage:5.1f}%)")
    
    print(f"\nAverage chunk length: {avg_tokens:.1f} tokens")
    
    print(f"\nTop 5 largest chunks by line count:")
    for i, (chunk, line_count) in enumerate(top_5_chunks, 1):
        chunk_id = chunk.get("id", "unknown")
        chunk_name = chunk.get("name", "unknown")
        chunk_type = chunk.get("type", "unknown")
        file_path = chunk.get("file_path", "unknown")
        start_line = chunk.get("start_line", 0)
        end_line = chunk.get("end_line", 0)
        print(f"  {i}. {chunk_id}")
        print(f"     Type: {chunk_type}, Lines: {line_count} ({start_line}-{end_line}), File: {file_path}")
    
    print("=" * 80)
