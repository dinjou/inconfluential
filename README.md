# Inconfluential

Inconfluential is a Python script designed to export pages from one or more Atlassian Confluence spaces into Markdown files. It organizes these files into a directory structure and maintains a Git repository to track changes over time. This allows for easy version control, offline access, and integration with other tools that consume Markdown files.

## Features

- **Batch Processing**: Efficiently fetches pages in batches to handle large Confluence spaces.
- **Multiple Spaces**: Supports exporting pages from multiple Confluence spaces specified in the configuration.
- **Markdown Conversion**: Converts Confluence pages (HTML content) into Markdown format.
- **Git Integration**: Automatically adds and commits changes to a Git repository, preserving the history of changes.
- **Progress Indicators**: Provides visual progress bars for batch and page processing using `tqdm`.
- **Error Handling**: Robust error handling for API requests, rate limiting, and file operations.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Logging](#logging)
- [Acknowledgments](#acknowledgments)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- **Python 3.13+**: The script is compatible with Python version 3.13 and above.
- **Atlassian Confluence**: Access to one or more Confluence spaces with API credentials.
- **Git**: Git should be installed on your system to enable version control features.
- **Poetry**: Used for dependency management and packaging.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/inconfluential.git
   cd inconfluential
   ```

2. **Install Poetry**

   If you don't have Poetry installed, you can install it using one of the following methods:
   
   #### scoop.sh (powershell)
   ```bash
   scoop install poetry
   ```
   
   #### brew (macOS)
   ```bash
   brew install poetry
   ```

   #### bash
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

   Or refer to the [Poetry documentation](https://python-poetry.org/docs/#installation) for other installation methods.

3. **Install Dependencies**

   ```bash
   poetry install
   ```

   This command will create a virtual environment and install all the required dependencies specified in `pyproject.toml`.

## Configuration

Inconfluential uses a `.env` file to manage configuration variables. Create a `.env` file in the root directory of the project.

### **`.env` File Format**

```ini
# Atlassian Confluence Configuration
CONFLUENCE_INSTANCE=https://your-confluence-instance.atlassian.net
CONFLUENCE_USERNAME=your.email@example.com
CONFLUENCE_API_KEY=your_confluence_api_token
CONFLUENCE_SPACE=SPACEKEY1, SPACEKEY2  # Comma-separated list of space keys

# Export Configuration
EXPORT_DESTINATION=/path/to/export/destination
```

### **Obtaining an API Token**

1. Log in to your Atlassian account.
2. Navigate to [Atlassian API Tokens](https://id.atlassian.com/manage/api-tokens).
3. Click **Create API token**, label it, and copy the generated token.
4. Use this token as the value for `CONFLUENCE_API_KEY` in your `.env` file.

### **Environment Variables Explained**

- **CONFLUENCE_INSTANCE**: The base URL of your Confluence instance.
- **CONFLUENCE_USERNAME**: Your Confluence username (usually your email).
- **CONFLUENCE_API_KEY**: The API token generated from your Atlassian account.
- **CONFLUENCE_SPACE**: A comma-separated list of Confluence space keys to export.
- **EXPORT_DESTINATION**: The directory where the Markdown files and Git repository will be stored.

## Usage

Run the script using Poetry:

```bash
poetry run python inconfluential.py
```

### **What Happens When You Run the Script**

1. **Environment Loading**: The script loads configuration variables from the `.env` file.
2. **Logging Setup**: Initializes logging to output to `inconfluential.log`.
3. **Git Repository Initialization**: Ensures that the `EXPORT_DESTINATION` directory is a Git repository. If not, it initializes one.
4. **Confluence Connection**: Establishes a connection to the Confluence instance using the provided credentials.
5. **Space Processing**: Iterates over each space key specified in `CONFLUENCE_SPACE`.
6. **Page Fetching and Conversion**:
   - Fetches pages in batches.
   - Converts each page from HTML to Markdown using LukeLR's `AtlassianConverter`.
   - Writes the Markdown files to the appropriate directory. Authors and publication date are written to the first line of the file.
7. **Git Operations**:
   - Adds changed files to the Git staging area.
   - Commits changes with a message like `Updated YYYY-MM-DD HH:MM:SS`.
8. **Progress Indicators**: Displays progress bars for batches and pages using `tqdm`.

### **Notes**

- The script is intended to be configured through the `.env` file and run without arguments.
- Ensure that the `EXPORT_DESTINATION` path can be written to and that read access secured properly.
- Ensure that 

## Logging

- All logs are written to `inconfluential.log` in the project root directory.
- The log includes timestamps, log levels, and messages for debugging and audit purposes.
- Sensitive information like API keys is masked in the logs.
- Options for `min_level` include the standard `logging.DEBUG`, `logging.INFO`, `logging.WARNING`, `logging.ERROR`, and `logging.CRITICAL`.

## Acknowledgments

- **[LukeLR's Gitfluence](https://codeberg.org/LukeLR/gitfluence)**: The `AtlassianConverter` class used in this project is directly sourced from LukeLR's `gitfluence`. This was pivotal in designing the approach to converting Confluence pages to Markdown. Special thanks to LukeLR for their contribution to the community.

- **[Atlassian Python API](https://atlassian-python-api.readthedocs.io/)**: For providing a convenient way to interact with Confluence.

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the Repository**

   Click on the "Fork" button at the top right of the repository page.

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**

4. **Commit Your Changes**

   ```bash
   git commit -am 'Add some feature'
   ```

5. **Push to the Branch**

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**

   Navigate to your forked repository and click on "New pull request".

## License

This project is licensed under the GNU Affero General Public License (v3).

### **Common Issues**

- **Authentication Errors**: If you receive authentication errors, double-check your `CONFLUENCE_USERNAME` and `CONFLUENCE_API_KEY` in the `.env` file.
- **Permission Denied**: Ensure you have the necessary permissions to read from Confluence spaces and write to the `EXPORT_DESTINATION` directory.
- **Git Errors**: Make sure Git is installed and properly configured on your system.
- **Poetry Issues**: If you encounter issues with Poetry, refer to the [Poetry documentation](https://python-poetry.org/docs/).

### **Contact**

If you encounter any issues or have questions, feel free to open an issue on the GitHub repository or contact the maintainer at [your.email@example.com](mailto:your.email@example.com).

---

**Disclaimer**: This tool is provided as-is without any guarantees. Use it responsibly and ensure compliance with your organization's policies regarding data export and version control.