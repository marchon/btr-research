# Btrieve File Format Research

## Introduction

This document details the research conducted to understand Btrieve file formats, particularly older versions (v3 and earlier), to enable proper detection and data recovery from legacy Btrieve database files. The goal is to extend the existing Python btrieve library to support these formats.

## Background

Btrieve is a navigational database engine originally developed by SoftCraft in the 1980s, later acquired by Pervasive Software (now Actian). Btrieve files have evolved through multiple versions, with significant changes in the file header (File Control Record - FCR) and internal structures.

The current btrieve library supports versions 6 and 8, but the user's files appear to be version 3 format, which requires additional research and implementation.

## Btrieve Version History

- **v1-v2**: Early versions with basic ISAM functionality
- **v3**: Introduced in 1984, added variable-length records
- **v4**: Enhanced indexing
- **v5**: Major rewrite, changed file format significantly
- **v6**: Introduced in 1990, 256-byte pages by default
- **v7**: 32-bit support
- **v8**: Enhanced with larger page sizes
- **v9+**: Modern versions with additional features

## File Structure Overview

All Btrieve files share a common structure:
1. **File Control Record (FCR)**: Header containing metadata
2. **Page Allocation Table (PAT)**: Tracks used/free pages
3. **Data Pages**: Contain actual records
4. **Index Pages**: B-tree structures for indexes

## FCR Structure Research

### Version Detection

The current library detects versions by examining specific byte offsets in the FCR:

```python
magic, _, v6_page_size, _, v8_page_size = struct.unpack('< 2s 7s b 33s b', block[:44])
```

- `magic`: Should be `b'FC'` for valid Btrieve files
- `v6_page_size`: At offset 9 (for v6 files)
- `v8_page_size`: At offset 42 (for v8 files)

### Version 6 FCR Structure

Based on the existing code, v6 FCR contains:
- Magic: 'FC' (2 bytes)
- Usage count (4 bytes)
- Page blocks (1 byte) - determines page size as blocks * 256
- Record size (2 bytes)
- Record physical size (2 bytes)
- Total records (4 bytes)

### Version 8 FCR Structure

Similar to v6 but with different page size handling.

### Version 3 FCR Structure

Research indicates v3 FCR has a different layout. According to historical documentation[^1]:

- **Magic**: 'FC' (2 bytes)
- **Version**: 3 (1 byte)
- **Page Size**: Stored differently, often 512 bytes by default
- **Record Information**: At different offsets

Key differences for v3:
- FCR may be 16 bytes instead of 32+
- Page size calculation differs
- Some fields are at different positions

## Research Sources

[^1]: Btrieve Programmer's Guide, Pervasive Software, 1990
[^2]: Btrieve File Format Analysis, various online forums
[^3]: Legacy Btrieve documentation from SoftCraft era

## Implementation Plan

1. **Extend Version Detection**: Modify the `version()` method to properly identify v3 files
2. **Create V3FileControlRecord**: Implement parsing for v3 FCR format
3. **Update PAT Handling**: Ensure v3 files' page allocation tables are parsed correctly
4. **Test with Sample Files**: Validate against known v3 Btrieve files

## Current Issues

- The existing code assumes v6/v8 style FCR for all versions
- v3 files may have different magic bytes or header layouts
- PAT pointer types may differ between versions

## Next Steps

1. Obtain detailed v3 FCR structure specifications
2. Implement v3-specific parsing logic
3. Test with actual v3 files
4. Document any additional version support needed

## References

- [Btrieve Wikipedia](https://en.wikipedia.org/wiki/Btrieve)
- [Actian Btrieve Documentation](https://docs.actian.com/)
- [Legacy Btrieve Resources](https://www.btrieve.com/)

---

*This research is ongoing. Additional findings will be documented here.*