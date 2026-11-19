#!/usr/bin/env python3
"""
Route Optimizer - MVP
A simple command-line tool to optimize travel routes using Google Gemini AI.
"""

import os
import sys
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

def load_prompt_template():
    """Load the prompt template from the prompts folder."""
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'prompt_template.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {prompt_path}")
        sys.exit(1)

def get_max_addresses():
    """Read the maximum number of addresses from environment variables."""
    value = os.getenv('MAX_ADDRESSES')
    if not value:
        print("Error: MAX_ADDRESSES not found in environment variables.")
        sys.exit(1)
    try:
        max_addresses = int(value)
        if max_addresses < 1:
            raise ValueError
        return max_addresses
    except ValueError:
        print("Error: MAX_ADDRESSES must be a positive integer.")
        sys.exit(1)

def get_addresses():
    """Collect addresses from user input."""
    max_addresses = get_max_addresses()
    addresses = []
    print("Route Optimizer")
    print("=" * 50)
    print("Enter addresses one by one. The first address is the starting point.")
    print("Press Enter with an empty line to finish.")
    print(f"You can enter up to {max_addresses} addresses.")
    print()
    
    while True:
        address = input(f"Address {len(addresses) + 1} (or press Enter to finish): ").strip()
        if not address:
            if len(addresses) == 0:
                print("Please enter at least one address.")
                continue
            break
        addresses.append(address)
        if len(addresses) >= max_addresses:
            print(f"Maximum of {max_addresses} addresses reached.")
            break
    
    return addresses

def return_to_starting_point():
    """Ask user if they want to return to the starting point."""
    while True:
        response = input("\nDo you want to return to the starting point? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'.")

def optimize_route(addresses, return_to_start=False):
    """Use Google Gemini to optimize the route."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    # Load prompt template
    prompt_template = load_prompt_template()
    
    # Prepare addresses string
    addresses_str = '\n'.join([f"{i+1}. {addr}" for i, addr in enumerate(addresses)])
    
    # Determine starting point (first address)
    starting_point = addresses[0] if addresses else ""
    
    # Format the prompt
    prompt = prompt_template.format(
        addresses=addresses_str,
        starting_point=starting_point,
        return_to_start="Yes" if return_to_start else "No"
    )
    
    try:
        print("\nOptimizing route with AI...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)

def main():
    """Main function to run the route optimizer."""
    # Collect addresses
    addresses = get_addresses()
    
    # Ask about return preference
    return_to_start = return_to_starting_point()
    
    # Optimize route
    optimized_route = optimize_route(addresses, return_to_start)
    
    # Display results
    print("\n" + "=" * 50)
    print("OPTIMIZED ROUTE")
    print("=" * 50)
    print(optimized_route)
    print("=" * 50)

if __name__ == "__main__":
    main()
