# Btrieve Repair Tool

A Python-based tool to analyze, repair, and extract data from Btrieve database files.

## Features

- Analyzes Btrieve file structure (FCR, PAT, data pages)
- Detects common corruption issues
- Parses DDF files for schema information (tables, fields)
- Rebuilds indexes and repairs files (via BUTIL)
- Extracts file contents to CSV, SQLite, or SQL formats

## Requirements

- Python 3.10+
- Click library (installed automatically)

## Installation

1. Clone this repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the tool: `python3 btrieve_repair.py <file_path> [options]`

## Usage

Analyze a file:
```bash
python3 btrieve_repair.py path/to/your/file.btr
```

Scan a directory for Btrieve files:
```bash
python3 btrieve_repair.py /path/to/directory
```

Parse DDF schemas:
```bash
python3 btrieve_repair.py path/to/your/file.btr --parse-ddf
```

Extract data to CSV (default):
```bash
python3 btrieve_repair.py path/to/your/file.btr --dump
```

Repair file:
```bash
python3 btrieve_repair.py path/to/your/file.btr --repair
```

## Directory Scanning

When a directory is provided, the tool:
- Recursively scans all files
- Identifies Btrieve files by FCR magic
- Matches files to DDF entries for table names and schemas
- Logs detailed information to console and `info.log`
- Includes file type, page/record info, and field definitions

## Output Format

The tool provides structured output with sections for file analysis, schema information, and suggestions. For data dumps, it creates files in the current directory with the table name as prefix.

## Limitations

- Repair and index rebuild require Pervasive BUTIL tool
- Data extraction assumes fixed-length records and basic field parsing
- Tested with V6/V8 Btrieve files

## License

Based on Centurix Btrieve library (MIT-like).# btr-research
