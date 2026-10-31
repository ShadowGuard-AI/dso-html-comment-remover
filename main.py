#!/usr/bin/env python3

import argparse
import os
import logging
import chardet  # dependency
import sys
from html.parser import HTMLParser


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
    parser.add_argument("-o", "--output", help="Output directory for processed files. If not specified, files are overwritten in place.")
    parser.add_argument("-e", "--encoding", help="Specify the encoding of the input files (e.g., utf-8, latin-1). If not specified, attempts to auto-detect.")
    return parser


class _CommentStripper(HTMLParser):
    """
    Rebuilds the document from parser events, dropping comment nodes.

    Start tags are copied from the original tag text, so attributes keep
    their original spelling and quoting. End tags are rebuilt from the
    tag name, so an end tag written in upper case comes back lower case.
    """

    def __init__(self, specific_string=None):
        super().__init__(convert_charrefs=False)
        self.specific_string = specific_string
        self.parts = []
        self.removed = 0

    def _drop(self, data):
        if self.specific_string is None:
            return True
        return self.specific_string in data

    def handle_comment(self, data):
        if self._drop(data):
            self.removed += 1
        else:
            self.parts.append("<!--" + data + "-->")

    def handle_decl(self, decl):
        self.parts.append("<!" + decl + ">")

    def unknown_decl(self, data):
        self.parts.append("<![" + data + "]>")

    def handle_pi(self, data):
        self.parts.append("<?" + data + ">")

    def handle_starttag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append("</" + tag + ">")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append("&" + name + ";")

    def handle_charref(self, name):
        self.parts.append("&#" + name + ";")


def _drop_unterminated_comments(content, specific_string=None):
    """
    Drops comments that never close before the next comment opens or
    before the end of the file.

    A parser reads everything after an unterminated "<!--" as one long
    comment, so a single broken comment would swallow the rest of the
    page. Here such a comment is treated as ending at the end of the
    line it starts on, and only that line fragment is dropped. Returns
    a (content, dropped_count) pair.
    """
    out = []
    dropped = 0
    i = 0
    n = len(content)
    while True:
        start = content.find("<!--", i)
        if start == -1:
            out.append(content[i:])
            break
        closes = [c for c in (content.find("-->", start + 4),
                              content.find("--!>", start + 4)) if c != -1]
        close = min(closes) if closes else -1
        nxt = content.find("<!--", start + 4)
        if close != -1 and (nxt == -1 or close < nxt):
            end = close + (4 if content.startswith("--!>", close) else 3)
            out.append(content[i:end])
            i = end
            continue
        # Unterminated: the comment runs to the end of its own line.
        eol = content.find("\n", start)
        if eol == -1:
            eol = n
        fragment = content[start:eol]
        out.append(content[i:start])
        if specific_string is None or specific_string in fragment:
            dropped += 1
        else:
            out.append(fragment)
        i = eol
    return "".join(out), dropped


def remove_html_comments(content, specific_string=None):
    """
    Removes HTML comments from a string using an HTML parser pass.

    Args:
        content (str): The string to process.
        specific_string (str, optional): If specified, only comments containing this string will be removed. Defaults to None.

    Returns:
        tuple: (the string with HTML comments removed, the number of comments removed)
    """
    content, dropped = _drop_unterminated_comments(content, specific_string)
    stripper = _CommentStripper(specific_string)
    stripper.feed(content)
    stripper.close()
    return "".join(stripper.parts), dropped + stripper.removed


def process_file(file_path, specific_string=None, output_dir=None, encoding=None):
    """
    Processes a single file, removing HTML comments.

    Args:
        file_path (str): The path to the file to process.
        specific_string (str, optional): If specified, only comments containing this string will be removed. Defaults to None.
        output_dir (str, optional): The output directory for the processed file. If None, the file is overwritten in place. Defaults to None.
        encoding (str, optional): The encoding of the file. If None, attempts to auto-detect. Defaults to None.

    Returns:
        int: The number of comments removed, or None when the file failed.
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
        sanitized_content, removed = remove_html_comments(content, specific_string)

        if output_dir:
            output_path = os.path.join(output_dir, os.path.basename(file_path))
        else:
            output_path = file_path

        with open(output_path, "w", encoding=encoding) as f:
            f.write(sanitized_content)

        logging.info(f"Processed file: {file_path} ({removed} comment(s) removed)")
        return removed

    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        return None


def process_directory(dir_path, recursive=False, specific_string=None, output_dir=None, encoding=None):
    """
    Processes a directory, removing HTML comments from files within it.

    Returns:
        tuple: (total comments removed, number of files that failed)
    """
    total_removed = 0
    failures = 0
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
                    removed = process_file(file_path, specific_string, output_subdir, encoding)
                    if removed is None:
                        failures += 1
                    else:
                        total_removed += removed

            if not recursive:
                break  # Only process the top-level directory
    except Exception as e:
        logging.error(f"Error processing directory {dir_path}: {e}")
        failures += 1
    return total_removed, failures



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
        removed = process_file(path, specific_string, output_dir, encoding)
        if removed is None:
            sys.exit(1)
        total_removed, failures = removed, 0
    elif os.path.isdir(path):
        total_removed, failures = process_directory(path, recursive, specific_string, output_dir, encoding)
    else:
        logging.error(f"Error: Invalid path type: {path}")
        sys.exit(1)

    if failures:
        logging.error(f"{failures} file(s) failed to process.")
        sys.exit(1)

    logging.info(f"Total comments removed: {total_removed}")
    if total_removed == 0:
        logging.error("Nothing was removed: no matching HTML comments found.")
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
