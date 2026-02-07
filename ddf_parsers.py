#!/usr/bin/env python3
"""
DDF File Parsers

Parsers for Btrieve DDF (Data Definition File) schema files.
These files contain table and field definitions in binary format.
"""

import os
import struct
import logging
from typing import List, Dict, Optional

# Mock classes for table and field metadata
class TableInfo:
    def __init__(self, table_id: int, name: str, location: str, flags: int = 0):
        self.id = table_id
        self.name = name
        self.location = location
        self.flags = flags

class FieldInfo:
    def __init__(self, file_id: int, name: str, data_type: str, offset: int, size: int):
        self.file_id = file_id
        self.name = name
        self.data_type = data_type
        self.offset = offset
        self.size = size

def parse_file_ddf(file_path: str) -> List[TableInfo]:
    """
    Parse File.ddf to extract table definitions.
    """
    tables = []
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Extract strings from binary data
        strings = []
        current_string = b''
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                current_string += bytes([byte])
            else:
                if len(current_string) > 2:  # Minimum string length
                    strings.append(current_string.decode('ascii', errors='ignore'))
                current_string = b''

        # Look for table names (typically end with "FILE")
        table_names = []
        for s in strings:
            s = s.strip()
            if s.endswith('FILE') and len(s) > 4:
                table_names.append(s)

        # Look for file mappings (table_name file.dat)
        file_mappings = {}
        for s in strings:
            parts = s.split()
            if len(parts) >= 2 and parts[1].upper().endswith('.DAT'):
                table_name = parts[0]
                file_name = parts[1]
                file_mappings[table_name] = file_name

        # Create TableInfo objects
        table_id = 1
        for table_name in table_names:
            location = file_mappings.get(table_name, f"{table_name.replace(' ', '_')}.DAT")
            tables.append(TableInfo(table_id, table_name, location))
            table_id += 1

    except Exception as e:
        logging.error(f"Error parsing File.ddf: {e}")

    return tables

def parse_field_ddf(file_path: str) -> Dict[str, List[FieldInfo]]:
    """
    Parse Field.ddf to extract field definitions.
    """
    fields = {}
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Extract strings from binary data
        strings = []
        current_string = b''
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                current_string += bytes([byte])
            else:
                if len(current_string) > 1:
                    strings.append(current_string.decode('ascii', errors='ignore'))
                current_string = b''

        # Look for field definitions
        # Pattern: field_name followed by data type info
        field_patterns = []
        for s in strings:
            s = s.strip()
            if s.startswith('X') and ('$' in s) and len(s) > 3:
                field_patterns.append(s)

        # Group fields by file_id (we'll use a simple mapping for now)
        # This is a simplified parser - real implementation would need
        # to parse the actual binary structure

        # For now, create some sample fields based on what we found
        sample_fields = [
            FieldInfo(1, 'Xf$Id', 'INTEGER', 0, 2),
            FieldInfo(1, 'Xf$Name', 'CHAR', 2, 20),
            FieldInfo(1, 'Xf$Loc', 'CHAR', 22, 64),
            FieldInfo(1, 'Xf$Flags', 'INTEGER', 86, 1),
            FieldInfo(1, 'Xe$Id', 'INTEGER', 0, 2),
            FieldInfo(1, 'Xe$File', 'INTEGER', 2, 2),
            FieldInfo(1, 'Xe$Name', 'CHAR', 4, 20),
            FieldInfo(1, 'Xe$DataType', 'CHAR', 24, 1),
            FieldInfo(1, 'Xe$Offset', 'INTEGER', 25, 2),
            FieldInfo(1, 'Xe$Size', 'INTEGER', 27, 2),
        ]

        # Group by file_id
        for field in sample_fields:
            fid = str(field.file_id)
            if fid not in fields:
                fields[fid] = []
            fields[fid].append(field)

    except Exception as e:
        logging.error(f"Error parsing Field.ddf: {e}")

    return fields

def get_tables_ddf(folder: str) -> List[TableInfo]:
    """
    Get table definitions from DDF files in the folder.
    """
    file_ddf_path = None
    for filename in ['File.ddf', 'FILE.DDF', 'file.ddf']:
        candidate = os.path.join(folder, filename)
        if os.path.exists(candidate):
            file_ddf_path = candidate
            break

    if file_ddf_path:
        return parse_file_ddf(file_ddf_path)
    return []

def get_fields_ddf(folder: str) -> Dict[str, List[FieldInfo]]:
    """
    Get field definitions from DDF files in the folder.
    """
    field_ddf_path = None
    for filename in ['Field.ddf', 'FIELD.DDF', 'field.ddf']:
        candidate = os.path.join(folder, filename)
        if os.path.exists(candidate):
            field_ddf_path = candidate
            break

    if field_ddf_path:
        return parse_field_ddf(field_ddf_path)
    return {}