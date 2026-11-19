#!/usr/bin/env python3
"""
Git Commit Auto Message - MVP
Generate Conventional Commits messages from a git diff using Google Gemini AI.
"""

import argparse
import os
import subprocess
import sys

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


def load_prompt_template():
    """Load the prompt template from the prompts folder."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "prompt_template.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {prompt_path}")
        sys.exit(1)


def get_git_diff(staged_only=False):
    """Collect the current git diff from the repository."""
    if staged_only:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()

    staged = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        check=False,
    )
    unstaged = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        check=False,
    )
    return f"{staged.stdout}\n{unstaged.stdout}".strip()


def read_diff_from_file(path):
    """Read a diff from a text file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: Diff file not found at {path}")
        sys.exit(1)


def get_recent_commits(limit=5):
    """Fetch recent commit subjects to help match repository style."""
    result = subprocess.run(
        ["git", "log", f"-{limit}", "--pretty=format:%s"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def generate_commit_message(diff, recent_commits=""):
    """Use Google Gemini to propose a Conventional Commits message."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    prompt_template = load_prompt_template()
    prompt = prompt_template.format(
        diff=diff,
        recent_commits=recent_commits or "No recent commits available.",
    )

    try:
        print("\nGenerating commit message with AI...")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a Conventional Commits message from a git diff."
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Path to a saved diff file instead of running git diff",
    )
    parser.add_argument(
        "-s",
        "--staged",
        action="store_true",
        help="Use only staged changes (git diff --staged)",
    )
    args = parser.parse_args()

    print("Git Commit Auto Message")
    print("=" * 50)

    if args.file:
        diff = read_diff_from_file(args.file)
    else:
        diff = get_git_diff(staged_only=args.staged)

    if not diff:
        print("No changes found. Stage files or provide a diff file with --file.")
        sys.exit(1)

    recent_commits = get_recent_commits()
    commit_message = generate_commit_message(diff, recent_commits)

    print("\n" + "=" * 50)
    print("SUGGESTED COMMIT MESSAGE")
    print("=" * 50)
    print(commit_message)
    print("=" * 50)


if __name__ == "__main__":
    main()
