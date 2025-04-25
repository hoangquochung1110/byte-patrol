# Code Review Buddy

A CLI tool to analyze code changes and provide AI-powered feedback.

## Project Structure

```
code-review-buddy/
├── main.py                  # Entry point
├── git_handler/             # Git integration
│   ├── __init__.py
│   ├── diff_parser.py       # Parse git diff output
│   └── file_extractor.py    # Extract file contents
├── code_analyzer/           # Code analysis
│   ├── __init__.py
│   ├── ai_connector.py      # AI API integration
│   └── feedback.py          # Process and structure feedback
├── ui/                      # Terminal UI
│   ├── __init__.py
│   ├── formatter.py         # Format output
│   └── display.py           # Display in terminal
├── config/                  # Configuration
│   ├── __init__.py
│   └── settings.py          # User settings
└── tests/                   # Tests
    └── test_main.py         # Tests for main entry
```

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Testing

```bash
pytest