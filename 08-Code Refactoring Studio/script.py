#!/usr/bin/env python3
"""
AI Code Refactoring Studio - MVP
Analyze Python code with AST, read files via MCP, and get refactoring suggestions from Gemini.
"""

import argparse
import ast
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
import google.generativeai as genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

load_dotenv()


@dataclass
class CodeIssue:
    type: str
    severity: str
    location: str
    message: str


class ASTAnalyzer(ast.NodeVisitor):
    """Traverse the AST and collect code smell issues."""

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        param_count = len(node.args.args)
        if param_count > 5:
            self.issues.append(CodeIssue(
                type="parameters",
                severity="medium",
                location=f"line {node.lineno}",
                message=f"Function '{node.name}' has {param_count} parameters (recommended max: 5)",
            ))

        func_lines = node.end_lineno - node.lineno + 1
        if func_lines > 50:
            self.issues.append(CodeIssue(
                type="size",
                severity="high" if func_lines > 100 else "medium",
                location=f"lines {node.lineno}-{node.end_lineno}",
                message=f"Function '{node.name}' is {func_lines} lines long (recommended max: 50)",
            ))

        complexity = _calculate_complexity(node)
        if complexity > 10:
            self.issues.append(CodeIssue(
                type="complexity",
                severity="high" if complexity > 20 else "medium",
                location=f"line {node.lineno}",
                message=f"Function '{node.name}' has cyclomatic complexity {complexity} (recommended max: 10)",
            ))

        max_nesting = _max_nesting_depth(node)
        if max_nesting > 4:
            self.issues.append(CodeIssue(
                type="nesting",
                severity="high" if max_nesting > 6 else "medium",
                location=f"line {node.lineno}",
                message=f"Function '{node.name}' has nesting depth {max_nesting} (recommended max: 4)",
            ))

        self.generic_visit(node)


def _calculate_complexity(node: ast.AST) -> int:
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            complexity += 1
    return complexity


def _max_nesting_depth(node: ast.AST) -> int:
    def depth(n: ast.AST, current: int = 0) -> int:
        max_d = current
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                max_d = max(max_d, depth(child, current + 1))
            else:
                max_d = max(max_d, depth(child, current))
        return max_d

    return depth(node, 0)


def analyze_code(code: str, filename: str = "<string>") -> List[CodeIssue]:
    tree = ast.parse(code, filename=filename)
    analyzer = ASTAnalyzer()
    analyzer.visit(tree)
    return analyzer.issues


def load_prompt_template() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "refactoring_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {prompt_path}")
        sys.exit(1)


async def read_file_via_mcp(filepath: str) -> str:
    """Read a file through the MCP filesystem server."""
    root = os.getenv("MCP_FILESYSTEM_ROOT", os.path.dirname(os.path.abspath(__file__)))
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", root],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("read_text_file", arguments={"path": filepath})
            if result.isError:
                raise RuntimeError(result.content[0].text)
            if not result.content or not isinstance(result.content[0], TextContent):
                raise RuntimeError("Unexpected MCP response: expected text content")
            return result.content[0].text


def format_issues_summary(issues: List[CodeIssue]) -> str:
    return "\n".join(
        f"{i + 1}. [{issue.severity.upper()}] {issue.type.upper()}: {issue.message} ({issue.location})"
        for i, issue in enumerate(issues)
    )


def generate_suggestions(code: str, issues: List[CodeIssue]) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    prompt_template = load_prompt_template()
    prompt = prompt_template.format(
        issues_summary=format_issues_summary(issues),
        code=code,
    )

    try:
        print("\nGenerating refactoring suggestions with AI...")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)


def print_issues(issues: List[CodeIssue]) -> None:
    if not issues:
        print("No issues found. Code looks good.")
        return

    print(f"Found {len(issues)} issue(s):\n")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. [{issue.severity.upper()}] {issue.type.upper()}: {issue.message}")
        print(f"   Location: {issue.location}")
    print()


async def run_analysis(filepath: str) -> None:
    print("AI Code Refactoring Studio")
    print("=" * 50)
    print(f"Analyzing: {filepath}")
    print("=" * 50)

    try:
        code = await read_file_via_mcp(filepath)
    except Exception as e:
        print(f"Error reading file via MCP: {e}")
        sys.exit(1)

    try:
        issues = analyze_code(code, filename=filepath)
    except SyntaxError as e:
        print(f"Error: Syntax error in Python file: {e}")
        sys.exit(1)

    print()
    print_issues(issues)

    if not issues:
        return

    suggestions = generate_suggestions(code, issues)

    print("=" * 50)
    print("REFACTORING SUGGESTIONS")
    print("=" * 50)
    print(suggestions)
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Python code with AST + MCP and get AI refactoring suggestions."
    )
    parser.add_argument("file", help="Python file to analyze (path relative to MCP root)")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' does not exist.")
        sys.exit(1)

    asyncio.run(run_analysis(args.file))


if __name__ == "__main__":
    main()
