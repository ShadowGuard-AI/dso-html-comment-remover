#!/usr/bin/env python3

import argparse
import os
import re
import logging
import chardet  # dependency
import sys


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Removes HTML comments from files or directories.")
    parser.add_argument("path", help="Path to the file or directory to process.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directories recursively.")
    parser.add_argument("-s", "--specific", help="Remove only comments containing this string (case-sensitive).")
    parser.add_argument("-a", "--all", action="store_true", help="Remove all HTML comments (default).")
    parser.add_argument("-o", "--output", help="Output directory for processed files. If not specified, files are overwritten in place.")
    parser.add_argument("-e", "--encoding", help="Specify the encoding of the input files (e.g., utf-8, latin-1). If not specified, attempts to auto-detect.")
    return parser


def remove_html_comments(content, specific_string=None):
    """
    Removes HTML comments from a string.

    Args:
        content (str): The string to process.
        specific_string (str, optional): If specified, only comments containing this string will be removed. Defaults to None.

    Returns:
        str: The string with HTML comments removed.
    """
    try:
        if specific_string:
            # Remove only comments containing the specific string
            pattern = re.compile(r"<!--.*?{}.*?-->".format(re.escape(specific_string)), re.DOTALL)
        else:
            # Remove all HTML comments
            pattern = re.compile(r"<!--.*?-->", re.DOTALL)

        return pattern.sub("", content)
    except Exception as e:
        logging.error(f"Error removing comments: {e}")
        return content  # Return original content on error


def process_file(file_path, specific_string=None, output_dir=None, encoding=None):
    """
    Processes a single file, removing HTML comments.

    Args:
        file_path (str): The path to the file to process.
        specific_string (str, optional): If specified, only comments containing this string will be removed. Defaults to None.
        output_dir (str, optional): The output directory for the processed file. If None, the file is overwritten in place. Defaults to None.
        encoding (str, optional): The encoding of the file. If None, attempts to auto-detect. Defaults to None.
    """
    try:
        # Determine encoding if not provided
        if not encoding:
            with open(file_path, 'rb') as f:
                rawdata = f.read()
                result = chardet.detect(rawdata)
                encoding = result['encoding']
                if not encoding:
                    logging.warning(f"Could not detect encoding for {file_path}.  Defaulting to utf-8.")
                    encoding = 'utf-8'
                else:
                    logging.info(f"Detected encoding: {encoding} for file {file_path}")


        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        # Sanitize data by removing HTML comments
        sanitized_content = remove_html_comments(content, specific_string)

        if output_dir:
            output_path = os.path.join(output_dir, os.path.basename(file_path))
        else:
            output_path = file_path

        with open(output_path, "w", encoding=encoding) as f:
            f.write(sanitized_content)

        logging.info(f"Processed file: {file_path}")

    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")


def process_directory(dir_path, recursive=False, specific_string=None, output_dir=None, encoding=None):
    """
    Processes a directory, removing HTML comments from files within it.

    Args:
        dir_path (str): The path to the directory to process.
        recursive (bool, optional): Whether to process the directory recursively. Defaults to False.
        specific_string (str, optional): If specified, only comments containing this string will be removed. Defaults to None.
        output_dir (str, optional): The output directory for the processed files. If None, files are overwritten in place. Defaults to None.
        encoding (str, optional): The encoding of the files. If None, attempts to auto-detect. Defaults to None.
    """
    try:
        for root, _, files in os.walk(dir_path):
            if output_dir:
                output_subdir = os.path.join(output_dir, os.path.relpath(root, dir_path))
                os.makedirs(output_subdir, exist_ok=True)
            else:
                output_subdir = None

            for file in files:
                if file.endswith((".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".tpl")): # Common HTML-like file extensions to consider
                    file_path = os.path.join(root, file)
                    process_file(file_path, specific_string, output_subdir, encoding)

            if not recursive:
                break  # Only process the top-level directory
    except Exception as e:
        logging.error(f"Error processing directory {dir_path}: {e}")



def main():
    """
    Main function to execute the script.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    path = args.path
    recursive = args.recursive
    specific_string = args.specific
    output_dir = args.output
    encoding = args.encoding

    # Validate input
    if not os.path.exists(path):
        logging.error(f"Error: Path '{path}' does not exist.")
        sys.exit(1)

    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
        except OSError as e:
             logging.error(f"Error creating output directory {output_dir}: {e}")
             sys.exit(1)

    if os.path.isfile(path):
        process_file(path, specific_string, output_dir, encoding)
    elif os.path.isdir(path):
        process_directory(path, recursive, specific_string, output_dir, encoding)
    else:
        logging.error(f"Error: Invalid path type: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
Usage Examples:

1. Remove all HTML comments from a single file:
   dso-html-comment-remover myfile.html

2. Remove all HTML comments from a directory recursively:
   dso-html-comment-remover mydirectory -r

3. Remove only comments containing the string "DEBUG" from a file:
   dso-html-comment-remover myfile.html -s DEBUG

4. Remove comments from a directory and save the output to a new directory:
   dso-html-comment-remover mydirectory -r -o output_directory

5. Specify the encoding of the input files:
   dso-html-comment-remover myfile.html -e latin-1

6. Help message
   dso-html-comment-remover -h

"""