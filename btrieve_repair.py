#!/usr/bin/env python3
"""
Btrieve File Repair Tool

This tool analyzes Btrieve files for corruption, parses DDF schemas, rebuilds indexes, and extracts data.
It performs checks on file structure and provides repair suggestions.

Usage: python3 btrieve_repair.py <file_path> [options]

Options:
  --repair          Attempt to repair by rebuilding (requires BUTIL)
  --rebuild-indexes Rebuild indexes (requires BUTIL)
  --dump [format]   Extract contents to format: csv (default), sqlite, sql
  --parse-ddf       Parse and display DDF schemas
"""

import os
import sys
import struct
import argparse
import csv
import sqlite3
import logging

BLOCK_SIZE = 256

# Add the btrieve library to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'btrieve'))

# Import DDF parsers
from ddf_parsers import get_tables_ddf, get_fields_ddf

from btrieve.blocks import (
    FileControlRecordFactory,
    PageAllocationTableFactory,
    DataPageFactory,
    PointerTypes
)
from btrieve.records import (
    FieldFactory,
    TableFactory
)

def scan_directory(directory_path, log_file):
    """
    Scan the directory for Btrieve files, identify them, and log info.
    """
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)

    tables = get_tables(directory_path)
    fields = get_fields(directory_path)

    table_dict = {table.id: table for table in tables}

    logging.info("Scanning directory: %s", directory_path)
    logging.info("=" * 50)

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                try:
                    result = analyze_file(file_path, extract_records=False, silent=True)
                    if result:
                        fcr, _ = result
                        # Identify type from DDF
                        table_info = None
                        for table in tables:
                            if table.location and os.path.basename(file_path).upper() == table.location.upper():
                                table_info = table
                                break
                        if table_info:
                            logging.info("File: %s", file_path)
                            logging.info("  Type: Btrieve Table - %s", table_info.name)
                            logging.info("  Page Size: %d", fcr.page_size)
                            logging.info("  Record Size: %d", fcr.record_size)
                            logging.info("  Total Records: %d", fcr.total_records)
                            if str(table_info.id) in fields:
                                logging.info("  Fields:")
                                for field in fields[str(table_info.id)]:
                                    logging.info("    %s - Type: %s, Size: %d", field.name, field.data_type, field.size)
                            logging.info("")
                        else:
                            logging.info("File: %s - Btrieve file, but no DDF entry found", file_path)
                    else:
                        logging.info("File: %s - Not a Btrieve file", file_path)
                except Exception as e:
                    logging.info("Error processing %s: %s", file_path, e)

def total_pat_pages(file_size, page_size):
    return (file_size + 130 * page_size) // (130 * page_size)

def pat_offset(pat_number, page_size):
    return (128 * pat_number + 2) * page_size

def raw_records(file_path):
    data_file_size = os.path.getsize(file_path)
    records = []
    with open(file_path, "rb") as data:
        block_1 = data.read(BLOCK_SIZE)
        block_2 = data.read(BLOCK_SIZE)
        fcr = FileControlRecordFactory.from_blocks(block_1, block_2)
        pat_pages = total_pat_pages(data_file_size, fcr.page_size)
        for pat_count in range(int(pat_pages)):
            offset = pat_offset(pat_count, fcr.page_size)
            if offset >= data_file_size:
                continue
            data.seek(offset)
            pat = PageAllocationTableFactory.from_blocks(
                data.read(fcr.page_size), 
                data.read(fcr.page_size)
            )
            for pointer in pat.pointers:
                if pointer[0] == PointerTypes.DATA:
                    data.seek(pointer[1] * fcr.page_size)
                    data_page = data.read(fcr.page_size)
                    page = DataPageFactory.from_fcr_and_block(fcr, data_page)
                    records += page.records
    return records

def find_ddf_file(folder, base_names):
    """
    Find DDF file in the folder, checking multiple possible names and extensions.
    """
    for base in base_names:
        for ext in ['.DDF', '.ddf', '.DAT', '.dat', '.txt']:
            # Try exact match
            path = os.path.join(folder, base + ext)
            if os.path.exists(path):
                return path
            # Try with .original extension
            path = os.path.join(folder, base + '.original' + ext)
            if os.path.exists(path):
                return path
            # Try case variations
            for case_base in [base.lower(), base.upper(), base.capitalize()]:
                path = os.path.join(folder, case_base + ext)
                if os.path.exists(path):
                    return path
                path = os.path.join(folder, case_base + '.original' + ext)
                if os.path.exists(path):
                    return path
    return None

def get_fields(folder):
    """
    Get field definitions from DDF files using proper DDF parsing.
    """
    try:
        return get_fields_ddf(folder)
    except Exception as e:
        print(f"Warning: Error parsing field DDF files: {e}")
        return {}

def get_tables(folder):
    """
    Get table definitions from DDF files using proper DDF parsing.
    """
    try:
        return get_tables_ddf(folder)
    except Exception as e:
        print(f"Warning: Error parsing table DDF files: {e}")
        return []

def parse_ddf(folder):
    tables = get_tables(folder)
    fields = get_fields(folder)
    print("\nDDF Schema Information:")
    print("=" * 40)
    for table in tables:
        print(f"Table: {table.name} (ID: {table.id})")
        if str(table.id) in fields:
            print("  Fields:")
            for field in fields[str(table.id)]:
                print(f"    {field.name} - Type: {field.data_type}, Offset: {field.offset}, Size: {field.size}")
        print()

def dump_to_csv(records, fields, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if fields:
            writer.writerow([f.name for f in fields])
            for record in records:
                # Assuming fixed length, parse based on fields
                row = []
                offset = 0
                for field in fields:
                    value = record[offset:offset + field.size].decode('latin-1').rstrip('\x00')
                    row.append(value)
                    offset += field.size
                writer.writerow(row)
        else:
            writer.writerow(['Raw Data'])
            for record in records:
                writer.writerow([record.hex()])

def dump_to_sqlite(records, fields, table_name, db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    if fields:
        columns = ', '.join([f"{f.name} TEXT" for f in fields])
        c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
        for record in records:
            offset = 0
            values = []
            for field in fields:
                value = record[offset:offset + field.size].decode('latin-1').rstrip('\x00')
                values.append(value)
                offset += field.size
            placeholders = ', '.join(['?'] * len(values))
            c.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    else:
        c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (data BLOB)")
        for record in records:
            c.execute(f"INSERT INTO {table_name} VALUES (?)", (record,))
    conn.commit()
    conn.close()

def dump_to_sql(records, fields, table_name, output_file):
    with open(output_file, 'w') as sqlfile:
        if fields:
            columns = ', '.join([f.name for f in fields])
            sqlfile.write(f"CREATE TABLE {table_name} ({', '.join([f'{f.name} TEXT' for f in fields])});\n")
            for record in records:
                offset = 0
                values = []
                for field in fields:
                    value = record[offset:offset + field.size].decode('latin-1').rstrip('\x00').replace("'", "''")
                    values.append(f"'{value}'")
                    offset += field.size
                sqlfile.write(f"INSERT INTO {table_name} ({columns}) VALUES ({', '.join(values)});\n")
        else:
            sqlfile.write(f"CREATE TABLE {table_name} (data BLOB);\n")
            for record in records:
                sqlfile.write(f"INSERT INTO {table_name} VALUES (X'{record.hex()}');\n")

def analyze_fcr(block1, block2):
    """
    Analyze File Control Record from two blocks.
    """
    # Basic FCR structure (simplified from Centurix)
    # Magic at 0: 'FC'
    magic = block1[0:2]
    if magic != b'FC':
        return None, "Invalid magic"

    # Page size at offset 4 (little endian short)
    page_size = struct.unpack('<H', block1[4:6])[0]

    # Record size at 6
    record_size = struct.unpack('<H', block1[6:8])[0]

    # Total records at 8
    total_records = struct.unpack('<L', block1[8:12])[0]

    return {
        'magic': magic,
        'page_size': page_size,
        'record_size': record_size,
        'total_records': total_records
    }, None

def analyze_file(file_path, extract_records=False, silent=False):
    """
    Analyze the Btrieve file for corruption and structure.
    Optionally extract records.
    """
    if not os.path.exists(file_path):
        if not silent:
            print("Error: File does not exist.")
        return None

    file_size = os.path.getsize(file_path)
    if not silent:
        print(f"File Size: {file_size} bytes")

    try:
        with open(file_path, "rb") as data:
            block_1 = data.read(BLOCK_SIZE)
            block_2 = data.read(BLOCK_SIZE)
            if len(block_1) < BLOCK_SIZE or len(block_2) < BLOCK_SIZE:
                if not silent:
                    print("Error: File too small to contain FCR.")
                return None

            fcr = FileControlRecordFactory.from_blocks(block_1, block_2)
            if not silent:
                print(f"Magic: {fcr.magic}")
            if fcr.magic != b'FC':
                if not silent:
                    print("Error: Invalid FCR magic. Not a valid Btrieve file.")
                return None

            if not silent:
                print(f"Page Size: {fcr.page_size}")
                print(f"Record Size: {fcr.record_size}")
                print(f"Total Records: {fcr.total_records}")

            if file_size % fcr.page_size != 0:
                if not silent:
                    print("Warning: File size not multiple of page size. Possible corruption.")

            pat_pages = total_pat_pages(file_size, fcr.page_size)
            if not silent:
                print(f"PAT Pages: {pat_pages}")

            records = []
            if extract_records:
                records = raw_records(file_path)
                if not silent:
                    print(f"Extracted Records: {len(records)}")
                    if len(records) != fcr.total_records:
                        print(f"Warning: Record count mismatch. FCR: {fcr.total_records}, Extracted: {len(records)}")

            return fcr, records

    except Exception as e:
        if not silent:
            print(f"Error analyzing file: {e}")
        return None

def check_ddf(folder):
    """
    Check DDF files for schema information.
    """
    ddf_bases = ['FILE', 'file', 'files', 'FIELD', 'field', 'fields', 'INDEX', 'index', 'indexes']
    found_files = []
    for base in ddf_bases:
        path = find_ddf_file(folder, [base])
        if path:
            found_files.append(os.path.basename(path))
    for ddf in found_files:
        print(f"Found DDF: {ddf}")
        # Could parse further, but for now just note presence

def suggest_repair(file_path, issues):
    """
    Suggest repair methods based on issues found.
    """
    if issues:
        print("\nRepair Suggestions:")
        print("1. Use Pervasive BUTIL tool if available:")
        print(f"   butil -stat {file_path}")
        print(f"   butil -rebuild {file_path} repaired.btr")
        print("2. If BUTIL not available, consider migrating to a modern database.")
        print("3. Backup the file before any operations.")
    else:
        print("No major issues detected. File appears healthy.")

def main():
    parser = argparse.ArgumentParser(description="Btrieve File Repair Tool")
    parser.add_argument('file_path', help='Path to the Btrieve file or directory')
    parser.add_argument('--repair', action='store_true', help='Attempt repair by rebuilding (requires BUTIL)')
    parser.add_argument('--rebuild-indexes', action='store_true', help='Rebuild indexes (requires BUTIL)')
    parser.add_argument('--parse-ddf', action='store_true', help='Parse and display DDF schemas')
    parser.add_argument('--dump', nargs='?', const='csv', choices=['csv', 'sqlite', 'sql'], help='Extract contents to format (default: csv)')
    parser.add_argument('--log', default='info.log', help='Log file for directory scan (default: info.log)')

    args = parser.parse_args()

    if os.path.isdir(args.file_path):
        scan_directory(args.file_path, args.log)
        if args.parse_ddf:
            parse_ddf(args.file_path)
        return

    print("Btrieve File Repair Tool")
    print("=" * 30)

    extract_records = args.dump or args.rebuild_indexes
    result = analyze_file(args.file_path, extract_records=extract_records, silent=False)
    if not result:
        return

    fcr, records = result

    issues = []
    if fcr.magic != b'FC':
        issues.append("Invalid FCR")

    folder = os.path.dirname(args.file_path) or '.'

    if args.parse_ddf:
        parse_ddf(folder)

    if args.dump:
        table_name = os.path.splitext(os.path.basename(args.file_path))[0]
        fields = get_fields(folder).get(str(fcr.total_records if hasattr(fcr, 'total_records') else 0), [])  # Approximate
        if args.dump == 'csv':
            output_file = f"{table_name}.csv"
            dump_to_csv(records, fields, output_file)
            print(f"Data dumped to {output_file}")
        elif args.dump == 'sqlite':
            output_file = f"{table_name}.db"
            dump_to_sqlite(records, fields, table_name, output_file)
            print(f"Data dumped to {output_file}")
        elif args.dump == 'sql':
            output_file = f"{table_name}.sql"
            dump_to_sql(records, fields, table_name, output_file)
            print(f"Data dumped to {output_file}")

    if args.repair or args.rebuild_indexes:
        print("\nRepair/Index Rebuild:")
        print("Using BUTIL:")
        if args.repair:
            print(f"  butil -rebuild {args.file_path} repaired.btr")
        if args.rebuild_indexes:
            print(f"  butil -rebuild {args.file_path} rebuilt.btr")

    if issues:
        print("\nIssues Found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nSuggestions:")
        print("1. Backup the file.")
        print("2. Use BUTIL for repair.")
    else:
        print("No major issues detected.")

if __name__ == "__main__":
    main()