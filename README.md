<a href="http://zuko.pro/">
    <img src="https://github.com/user-attachments/assets/9fb5d9ef-bc78-4552-88e0-a053a5e923a8" alt="Z-Logo"
         title="Halu Universe" align="right" />
</a>
# ffpm

# :fire: FFPM — Firefox Profile Manager :fire:

Simple Firefox Profile Manager, including Import/Export  
**Special Feature:** Monitor directory changes before/after actions.

## Description

**ffpm** is a Python-based tool for managing Firefox profiles. It allows you to import/export profiles and monitor directory changes before or after running actions—ideal for troubleshooting, backups, and tracking modifications.

## Features

- List Firefox profiles
- Import and export profiles
- Monitor directory changes before/after actions
- Simple command-line interface

## Installation & Usage

### Recommended: Use Pre-Built Binaries

For most users, download the latest pre-built binary from the [Releases page](https://github.com/7pvd/ffpm/releases).  
No Python setup is required—just download and run the binary appropriate for your platform.
Built binaries was tested and confirmed working on Windows 10 & ~Debian 11~.

### Development: Run from Source

For development or testing only:

```bash
git clone https://github.com/7pvd/ffpm.git
cd ffpm
pip install typer watchdog nuitka
python ffpm.py [OPTIONS]
```

## Available Commands

- List profiles:
  ```bash
  ffpm list
  ```
  
- Clean cache from a profile:
  ```bash
  ffpm clean <name>
  ```
- Export a profile:
  ```bash
  ffpm export <profile_name> --output <optional_output_path>
  ```
- Import a profile:
  ```bash
  ffpm import <zip_path> --name <optional_name>
  ```
- Monitor directory changes:
  ```bash
  ffpm monitor <directory_path>
  ```

## Requirements (for development)

- Python 3.x
- [See requirements.txt for dependencies]

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

GPL v3

## Acknowledgements

Inspired by the need for easy Firefox profile management and monitoring.
