#!/usr/bin/env python3
"""
Test script to verify the ddgs library works correctly with our updated fetch_webpage_summary function
"""
import sys
import os

# Add the agent_scratchpad directory to the path so we can import the tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from tool import fetch_webpage_summary


def test_fetch_webpage_summary():
    print("Testing fetch_webpage_summary function...")

    # Test with a simple search query
    result = fetch_webpage_summary("Python programming")
    print(f"Search result for 'Python programming':\n{result}")
    print("\n" + "="*50 + "\n")

    # Test with a URL
    result = fetch_webpage_summary("https://python.org")
    print(f"Search result for 'https://python.org':\n{result}")
    print("\n" + "="*50 + "\n")

    # Test with a domain query
    result = fetch_webpage_summary("openai")
    print(f"Search result for 'openai':\n{result}")


if __name__ == "__main__":
    test_fetch_webpage_summary()

