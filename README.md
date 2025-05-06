# Byte Patrol

![Byte Patrol](https://static.ssan.me/byte-patrol.jpeg)

A GitHub App that provides AI-powered code review assistance through pull request comments. Using Google's Gemini family of LLMs, Byte Patrol offers thoughtful and automated code reviews based on user-defined commands.

## Overview

Byte Patrol is a GitHub App that integrates directly into your pull request workflow. It analyzes code changes and provides detailed feedback through PR comments, helping teams maintain code quality and consistency.

### Key Features

- **Command-Based Reviews**: Trigger code reviews using predefined commands in PR comments
- **Flexible Analysis**: Get feedback on any aspect of your code through natural language commands
- **AI-Powered**: Leverages Google's Gemini family of LLMs for intelligent code analysis
- **Automated Workflow**: Seamlessly integrates with GitHub's pull request process
- **Customizable Feedback**: Request specific types of analysis through natural language commands

### How It Works

1. Install the Byte Patrol GitHub App on your repository
2. Create a pull request as usual
3. Use predefined commands in PR comments to request code reviews
4. Receive detailed, AI-powered feedback directly in your PR

## Usage

### Setup

1. Subscribe your repository to the Byte Patrol GitHub App
   - Visit the [Byte Patrol App page](https://github.com/apps/byte-patrol)
   - Click "Install App"
   - Select the repositories you want to enable Byte Patrol for

### Requesting Code Reviews

1. Open a Pull Request in your repository
2. Navigate to the "Conversation" tab
3. Add a comment using the following command format:
   ```
   @byte-patrol review --areas "<kind-of-feedback>" --style "<concise>"
   ```

#### Command Parameters

- `--areas`: Specify the type of feedback you want (e.g., "security", "performance", "readability", "best-practices")
- `--style`: Choose the feedback style (e.g., "concise", "detailed", "educational")

#### Example Commands

```
@byte-patrol review --areas "security,performance" --style "concise"
@byte-patrol review --areas "readability,best-practices" --style "detailed"
@byte-patrol review --areas "all" --style "educational"
```

The bot will analyze your PR and respond with a detailed review comment based on your specified parameters.

## Project Structure

```
byte-patrol/
├── src/                    # Source code
│   ├── byte_patrol/       # Main package
│   │   ├── cli.py         # Command-line interface
│   │   ├── config.py      # Configuration management
│   │   ├── request_counter.py  # API request tracking
│   │   ├── prompt_engine/ # AI prompt management
│   │   └── utils/         # Utility functions
│   └── api/               # API related code
│       ├── server.py      # FastAPI server setup
│       ├── models.py      # Data models and schemas
│       ├── config.py      # API configuration
│       ├── constants.py   # API constants
│       ├── services/      # Business logic services
│       │   ├── github.py      # GitHub integration
│       │   └── code_review.py # Code review service
│       ├── routes/        # API endpoints
│       │   └── webhooks.py    # Webhook handlers
│       └── middleware/    # Request/response middleware
├── tests/                 # Test suite
├── pyproject.toml         # Project metadata and dependencies
├── setup.cfg             # Additional project configuration
├── .env.example          # Example environment variables
└── INSTALL.md            # Detailed installation instructions
```

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows
```

2. Install dependencies:
```bash
pip install -e .
```

For detailed installation instructions, please refer to [INSTALL.md](INSTALL.md).

## Usage

```bash
byte-patrol --help
```

## Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

## Configuration

Copy `.env.example` to `.env` and configure your environment variables:
```bash
cp src/byte_patrol/.env.example src/byte_patrol/.env
```