#!/usr/bin/env python3

import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def load_prompt(template_path: Path) -> str:
    try:
        logger.info(f"Loading prompt from: {template_path}")
        return template_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {template_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading prompt file: {e}")
        raise


def fetch_headlines(api_key: str, limit: int = 10) -> list[dict]:
    try:
        logger.info(f"Fetching {limit} headlines from NewsAPI")
        response = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "country": "us",
                "pageSize": limit,
            },
            headers={"X-Api-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Retrieved {len(articles)} articles")
        return articles
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching headlines from NewsAPI: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching headlines: {e}")
        raise


def condense_news(
    client: genai.Client,
    model_name: str,
    prompt_template: str,
    article: dict,
    max_words: int,
) -> str:
    try:
        title = article.get("title", "")
        logger.debug(f"Condensing article: {title[:50]}...")
        prompt = prompt_template.format(
            max_words=max_words,
            title=title,
            description=article.get("description", ""),
            content=article.get("content", ""),
            url=article.get("url", ""),
            source=article.get("source", {}).get("name", ""),
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        text = getattr(response, "text", "")
        condensed = (text or "").strip()
        if not condensed:
            logger.warning(f"Empty response from Gemini for article: {title[:50]}...")
        return condensed
    except Exception as e:
        logger.error(f"Error condensing article '{article.get('title', 'Unknown')[:50]}...': {e}")
        raise


def main() -> None:
    try:
        logger.info("Starting 20Words aggregator")
        base_dir = Path(__file__).parent
        load_dotenv(base_dir / ".env")

        news_api_key = os.getenv("NEWS_API_KEY")
        if not news_api_key:
            logger.error("Missing NEWS_API_KEY in environment")
            raise RuntimeError("Missing NEWS_API_KEY in environment.")

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.error("Missing GEMINI_API_KEY in environment")
            raise RuntimeError("Missing GEMINI_API_KEY in environment.")

        max_words = int(os.getenv("MAX_WORDS", "20"))
        logger.info(f"Max words per article: {max_words}")
        
        prompt_file_path = os.getenv("PROMPT_FILE_PATH", "prompts/prompt_template.txt")
        prompt_path = base_dir / prompt_file_path if not Path(prompt_file_path).is_absolute() else Path(prompt_file_path)
        prompt_template = load_prompt(prompt_path)
        
        client = genai.Client(api_key=gemini_api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        logger.info(f"Using Gemini model: {model_name}")

        articles = fetch_headlines(news_api_key)
        if not articles:
            logger.warning("No articles retrieved")
            return

        for i, article in enumerate(articles, 1):
            try:
                condensed = condense_news(
                    client, model_name, prompt_template, article, max_words
                )
                print(f"- {condensed}")
            except Exception as e:
                logger.error(f"Failed to process article {i}: {e}")
                continue

        logger.info("News aggregation completed")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()

