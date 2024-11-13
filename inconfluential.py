#!/usr/bin/python3
import datetime
import logging
import os
import subprocess
import time

from atlassian import Confluence
from atlassian.errors import ApiError
from dotenv import load_dotenv
from markdownify import MarkdownConverter
from tqdm import tqdm



class AtlassianConverter(MarkdownConverter):
    """
    Converts Confluence HTML content to Markdown, handling Confluence-specific macros.

    This class extends `MarkdownConverter` to handle Confluence-specific elements such as
    `<ac:structured-macro>`, `<ac:parameter>`, and `<ac:plain-text-body>`, converting them
    to Markdown-compatible syntax or removing unnecessary Confluence-specific markup.
    """

    def __init__(self, **options):
        super().__init__(**options)
        setattr(self, 'convert_ac:structured-macro', self.convert_ac_structured_macro)
        setattr(self, 'convert_ac:parameter', self.convert_ac_parameter)
        setattr(self, 'convert_ac:plain-text-body', self.convert_ac_plain_text_body)

    def convert_ac_structured_macro(self, el, text, convert_as_inline):
        return text

    def convert_ac_parameter(self, el, text, convert_as_inline):
        if el.attrs['ac:name'] == 'title':
            return self.convert_h4(el, text, convert_as_inline)
        return ''

    def convert_ac_plain_text_body(self, el, text, convert_as_inline):
        if el.parent.attrs['ac:name'] == 'code':
            return self.convert_p(el, self.convert_code(el, text, convert_as_inline), convert_as_inline)
        else:
            return self.convert_p(el, text, convert_as_inline)


def fetch_pages_and_save(confluence, space, destination, git_root, batch_size=100, max_retries=5):
    """
    Fetch all pages from a Confluence space and save them as Markdown files.
    Retries requests on rate limiting (HTTP 429) with exponential backoff.

    Args:
        confluence (Confluence): Confluence client instance.
        space (str): Key of the Confluence space.
        destination (str): Directory to save Markdown files.
        batch_size (int): Number of pages to fetch per API call.
        max_retries (int): Maximum consecutive retries on rate limiting.

    Returns:
        bool: True if any pages were updated, False otherwise.
    """
    import math
    from tqdm import tqdm

    page_count = 0
    retry_count = 0
    more_pages = True  # Flag to indicate whether more pages are available
    changes_made = False

    os.makedirs(destination, exist_ok=True)

    logging.info(f"\n\tConfiguration Variables: \n"
                 f"\t\tPages per Batch: {batch_size}\n"
                 f"\t\tMax Retries: {max_retries}\n")

    # Get total number of pages to set total for tqdm
    try:
        cql = f'space = \"{space}\" AND type = \"page\"'
        cql_result = confluence.cql(cql, limit=1)
        total_pages = cql_result.get('totalSize', 0)
        total_batches = math.ceil(total_pages / batch_size)
    except Exception as e:
        logging.error(f"Failed to retrieve total page count: {e}")
        total_batches = None  # Unknown total

    with tqdm(total=total_batches, desc=f"Processing space \'{space}\'", unit='batch') as pbar_batches:
        while more_pages:
            logging.info("Batch found.")
            try:
                # Fetch a batch of pages
                logging.info(f"Pulling next batch of {batch_size}... ")
                pages = confluence.get_all_pages_from_space(space, start=page_count, limit=batch_size)

                if pages:
                    logging.info("Pulled.\n")

                    # Process each individual page with progress bar
                    with tqdm(total=len(pages), desc="Processing batch", unit='page', leave=False) as pbar_pages:
                        for page in pages:
                            page_id = page['id']
                            page_title = page['title']
                            logging.info(f"Processing page: \'{page_title}\' (ID: {page_id})")

                            try:
                                page_data = confluence.get_page_by_id(page_id, expand="body.storage,version")

                                account_id = page_data['version']['by'].get('accountId', 'unknown')
                                display_name = page_data['version']['by'].get('displayName', 'Unknown User')
                                timestamp = page_data['version'].get('when', 'unknown time')

                                author_data = {
                                    "Account ID": account_id,
                                    "Author Name": display_name,
                                    "Last Updated": timestamp
                                }

                                markdown = (str(author_data))+"\n"+AtlassianConverter().convert(page_data['body']['storage']['value'])
                                filename = os.path.join(destination, f"{page_title.replace('/', '_')}.md")
                                logging.info(f"\tPage: \'{page_title}\' converted to markdown. Writing...")

                                try:
                                    # Attempt to write the file only if there are changes
                                    if write_if_changed(filename, markdown):
                                        # Pass the git_root (export_destination) to stage_file
                                        stage_file(git_root, filename)
                                        changes_made = True
                                    else:
                                        logging.info(f"\tPage: Skipping git add for \'{filename}\' as no changes were made.")
                                except Exception as e:
                                    logging.error(f"\tPage: Writing failed! \'{filename}\' will not be written: {e}")

                            except ApiError as e:
                                tqdm.write(f"Page: Failed to retrieve page \'{page_title}\': {e}")
                                logging.warning(f"\tPage: Failed to retrieve page \'{page_title}\': {e}\n")
                            except Exception as e:
                                logging.warning(f"Unknown error occurred while processing \"{page_title}\": {e}\n")

                            pbar_pages.update(1)  # Update page progress bar

                    # Move to the next batch of pages
                    page_count += batch_size
                    pbar_batches.update(1)  # Update batch progress bar

                else:
                    more_pages = False  # No more pages to process; exit loop
                    logging.info("\n\t\tNOTE: All reachable pages have been obtained.\n")

                retry_count = 0  # Reset retry count on a successful fetch

            except ApiError as e:
                # Handle rate limiting
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', '1'))
                    print(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    retry_count += 1
                    logging.warning(f"\t\t\tWARNING: You are getting rate-limited (retry_count={retry_count}).\n")
                    if retry_count >= max_retries:
                        logging.critical("Aborting due to repeated rate-limit errors in rapid succession.")
                        raise Exception("Max retries exceeded due to rate limiting.")
                    continue  # Retry the fetch attempt
                else:
                    logging.error(f"Error fetching pages from space \'{space}\': {e}\n")
                    break  # Stop on non-rate-limiting errors

    return changes_made



def write_if_changed(filename, new_content):
    """
    Writes new content to a file only if it differs from the existing content.

    Args:
        filename (str): Path of the file to write.
        new_content (str): The new content to potentially write to the file.

    Returns:
        bool: True if the file was updated, False if no changes were made.
    """
    try:
        # Check if the file already exists
        if os.path.exists(filename):
            # Read the existing content
            with open(filename, 'r') as f:
                existing_content = f.read()

            # Compare with the new content; if identical, skip writing
            if existing_content == new_content:
                logging.info(f"\tGit: No changes detected in \'{filename}\'; skipping write.")
                return False  # No update necessary

        # If the file doesn't exist or content has changed, write new content
        with open(filename, 'w') as f:
            f.write(new_content)
        logging.info(f"\tGit: Changes detected; \'{filename}\' has been updated.")
        return True  # File was written/updated

    except Exception as e:
        logging.error(f"\tGit: Error while writing to \'{filename}\': {e}")
        return False  # In case of error, assume no update was made


def ensure_git_repo(git_root):
    """
    Checks if the specified folder is a Git repository.
    If not, initializes it as a Git repository.

    Args:
        git_root (str): The directory path to check or initialize as a Git repository.
    """
    try:
        # Check if .git folder exists, indicating a Git repository
        if not os.path.isdir(os.path.join(git_root, '.git')):
            logging.info(f"Initializing Git repository in \'{git_root}\'")
            result = subprocess.run(["git", "init"], cwd=git_root, check=True, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                logging.error(f"Git init failed for \'{git_root}\': {result.stderr}")

            logging.info("Git repository initialized.")
        else:
            logging.info(f"\'{git_root}\' is already a Git repository.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to initialize Git repository: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while checking Git repository status: {e}")


def stage_file(git_root, filename):
    """
    Adds the specified file to git staging area.

    Args:
        git_root (str): Path to the root of the git repository.
        filename (str): The file to add to staging area.
    """
    try:
        # Ensure the file path is an absolute path
        filepath = os.path.abspath(filename)

        # Add the file to Git
        result = subprocess.run(["git", "add", filepath], cwd=git_root, check=True, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logging.error(f"Git add failed for \'{filename}\': {result.stderr}")

        logging.info(f"Successfully added \'{filename}\' to git staging area")

    except subprocess.CalledProcessError as e:
        logging.error(f"Git add failed for \'{filename}\': {e}")
    except Exception as e:
        logging.error(f"Unknown error occurred while adding \'{filename}\': {e}")


def commit_all_changes(git_root):
    """
    Commits all staged changes in the git repository at destination.

    Args:
        destination (str): Path to the git repository.
    """
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Updated {current_time}"

        result = subprocess.run(["git", "commit", "-m", message], cwd=git_root, check=True, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logging.error(f"Git commit failed for {current_time}: {result.stderr}")

        logging.info(f"Successfully committed changes with message: {message}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Git commit failed: {e}")
    except Exception as e:
        logging.error(f"Unknown error occurred during git commit: {e}")


def set_logging_rules(filename='inconfluential.dev.log', min_level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s'):
    # Configure logging
    logging.basicConfig(
        filename=filename,  # Log file name
        level=min_level,  # Minimum log level to capture
        format=format  # Log message format
    )


def main():
    """
    Runs the primary logic of inconfluential.

    `inconfluential` is not intended to be run as a command-line tool. All information required should be stored in
    the local `.env` file.

    :return:
        None
    """

    print("""
    
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::                                                                  ::
::                                                                  ::
::   _                        __ _                  _   _       _   ::
::  (_)                      / _| |                | | (_)     | |  ::
::   _ _ __   ___ ___  _ __ | |_| |_   _  ___ _ __ | |_ _  __ _| |  ::
::  | | '_ \\ / __/ _ \\| '_ \\|  _| | | | |/ _ | '_ \\| __| |/ _` | |  ::
::  | | | | | (_| (_) | | | | | | | |_| |  __| | | | |_| | (_| | |  ::
::  |_|_| |_|\\___\\___/|_| |_|_| |_|\\__,_|\\___|_| |_|\\__|_|\\__,_|_|  ::
::                                                                  ::
::                                                                  ::
::                  by @dinjou, working proof v0.1                  ::
::                                                                  ::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    """)

    set_logging_rules('inconfluential.log', logging.INFO)

    # Load the environment variables.
    load_dotenv()

    # Define local variables from environment.
    confluence_instance = os.getenv("CONFLUENCE_INSTANCE")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_API_KEY")
    space_keys = [key.strip() for key in os.getenv("CONFLUENCE_SPACE").split(',')]  # Confluence space keys as a list
    export_destination = os.getenv('EXPORT_DESTINATION')

    # Print keys to `.gitignore`'d log to test functionality.
    logging.info(f"--------------------------------------------------------------------------\n"
                 f"Now running `inconfluential.py` @ {datetime.datetime.now()}\n"
                 f"\tEnvironment Variables loaded: \n"
                 f"\t\tCONFLUENCE_USERNAME={username}\n"
                 f"\t\tCONFLUENCE_API_KEY={'***' if password else 'Not Set'}\n"
                 f"\t\tCONFLUENCE_SPACE={space_keys}\n"
                 f"\t\tCONFLUENCE_INSTANCE={confluence_instance}\n"
                 f"\t\tEXPORT_DESTINATION={export_destination}\n")

    # Ensure the git repository is initialized at export_destination
    os.makedirs(export_destination, exist_ok=True)
    ensure_git_repo(export_destination)

    # Initialize changes_made to False
    changes_made = False

    # Initialize Confluence client
    try:
        confluence = Confluence(url=confluence_instance, username=username, password=password)

        # Loop over each space key
        for space_key in space_keys:
            # Set the destination for this space
            space_destination = os.path.join(export_destination, space_key)
            # Fetch and save all pages for this space
            space_changes_made = fetch_pages_and_save(confluence, space_key, space_destination, export_destination)
            if space_changes_made:
                changes_made = True

        # After all spaces have been processed, commit changes if any
        if changes_made:
            commit_all_changes(export_destination)

    except Exception as e:
        logging.error(f'Error occurred while exporting pages from Confluence.\n{e}')
        print("Unable to obtain requested pages from Confluence. Please see the logs for more information.")
        exit(1)

    if changes_made:
        print("\n--------------------------------------------------------\nChanges have been pulled from your wiki.")
    else:
        print("\n--------------------------------------------------------\nNo changes have been pulled from your wiki.")
    print("Thank you for using inconfluential. Goodbye.\n--------------------------------------------------------\n\n")


if __name__ == '__main__':
    main()
