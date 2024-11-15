#!/usr/bin/python3

import os
import dotenv
from atlassian import Confluence
from dotenv import load_dotenv
from markdownify import MarkdownConverter
from inconfluential import AtlassianConverter

def main():
    # Load the environment variables.
    load_dotenv()

    # Define local variables from environment.
    confluence_instance = os.getenv("CONFLUENCE_INSTANCE")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_API_KEY")
    export_destination = os.getenv('EXPORT_DESTINATION')

    space_key = input("Enter the Space Key of the space you will be pulling a page from: ")
    page_title = input("Enter the title of the page you want to pull for testing: ")

    # Connect to Confluence
    confluence = Confluence(url=confluence_instance, username=username, password=password)

    # Fetch the page by title
    page_id = confluence.get_page_id(space_key, page_title)
    if not page_id:
        print(f"Page '{page_title}' not found in space '{space_key}'.")
        return

    # Retrieve the full page content
    page = confluence.get_page_by_id(page_id, expand="body.storage,version")
    markdown_content = AtlassianConverter().convert(page['body']['storage']['value'])

    # Define filename and write to .md file
    filename = f"{export_destination}/{page_title.replace('/', '_')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"Page '{page_title}' downloaded and saved as '{filename}'.")

if __name__ == '__main__':
    main()
