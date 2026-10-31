![Banner](banner.png)

# dso-html-comment-remover
A command-line tool that removes HTML comments from files or directories. Can be configured to remove specific types of comments or all comments, preventing information leakage through forgotten debugging notes or server-side code. - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## How it works
The tool parses each file with an HTML parser and rebuilds it without the comment nodes. Ordinary text, tags, scripts, and the doctype are kept as they were. A comment closed with the `--!>` form is removed like any other comment. A comment that never closes is treated as ending at the end of the line it starts on, so one broken comment cannot swallow the rest of the page.

Each run reports how many comments were removed per file and in total. A run that removes nothing exits with a non-zero status and a plain "Nothing was removed" line, and an empty directory is reported the same way. If any file fails to process, for example because its bytes do not match the encoding in use, the run exits with status 1.

## Install
`git clone https://github.com/ShadowStrikeHQ/dso-html-comment-remover`

## Usage
`./dso-html-comment-remover [params]`

## Parameters
- `-h`: Show help message and exit
- `-r`: Process directories recursively.
- `-s`: Remove only comments containing this string (case-sensitive).
- `-o`: Output directory for processed files. If not specified, files are overwritten in place.
- `-e`: Specify the encoding of the input files (e.g., utf-8, latin-1). If not specified, attempts to auto-detect.

All comments are removed by default, so there is no separate flag for removing all of them.

## License
Copyright (c) ShadowStrikeHQ
