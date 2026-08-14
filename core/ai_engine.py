import streamlit as st
import google.generativeai as genai
import json
import re

def initialize_gemini() -> None:
    """Initialize Google Generative AI with API key from Streamlit secrets."""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in Streamlit secrets")
        
        genai.configure(api_key=api_key)
        print("Gemini AI initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
        raise

def _clean_json_response(response_text: str) -> str:
    """Clean Gemini response to extract pure JSON."""
    # Remove markdown code fences
    response_text = re.sub(r'`json\s*', '', response_text)
    response_text = re.sub(r'`\s*', '', response_text)
    
    # Remove any leading/trailing whitespace
    response_text = response_text.strip()
    
    # Sometimes Gemini adds non-JSON text, try to find JSON object
    if '{' in response_text and '}' in response_text:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        response_text = response_text[start_idx:end_idx]
    
    return response_text

def generate_problem(difficulty: str) -> dict:
    """
    Generate a competitive programming problem using Gemini.
    
    Args:
        difficulty: Problem difficulty (easy, medium, hard)
    
    Returns:
        Dictionary with problem data including title, description, 
        constraints, starter_code, and test_cases
    """
    try:
        prompt = f"""You are a competitive programming puzzle generator.

Generate a random {difficulty}-level coding problem.

Output exactly as a JSON object using this format:

{{
  "title": "String",
  "description": "String",
  "constraints": ["String"],
  "starter_code": "def solve(input_var):\n    pass",
  "test_cases": [
    {{
      "input": [args],
      "expected_output": value
    }}
  ]
}}

Generate exactly 3 test cases.

Do not include Markdown formatting.
Do not include `json.
Return only the JSON object."""
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean the response
        cleaned_response = _clean_json_response(response.text)
        
        # Parse JSON
        problem_data = json.loads(cleaned_response)
        
        # Validate structure
        required_keys = ['title', 'description', 'constraints', 'starter_code', 'test_cases']
        if not all(key in problem_data for key in required_keys):
            raise ValueError(f"Invalid response format. Missing keys: {required_keys}")
        
        if len(problem_data['test_cases']) != 3:
            print(f"Warning: Expected 3 test cases, got {len(problem_data['test_cases'])}")
        
        return problem_data
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini response: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
        raise ValueError("Failed to parse Gemini JSON response")
    except Exception as e:
        print(f"Error generating problem: {e}")
        raise

def review_code(title: str, user_code: str) -> dict:
    """
    Review submitted code using Gemini AI referee.
    
    Args:
        title: Problem title
        user_code: Submitted Python code
    
    Returns:
        Dictionary with review data including time_complexity, 
        space_complexity, roast_review, and ai_bonus_score
    """
    try:
        prompt = f"""You are a strict competitive programming code reviewer.

Review the following Python solution for a problem titled:
"{title}"

Evaluate the code for:

1. Time complexity using Big-O notation.
2. Space complexity using Big-O notation.
3. Edge cases.
4. General correctness concerns.
5. Code quality and style.

Provide a witty, slightly roasting review of the code style.

Return exactly this JSON format:

{{
  "time_complexity": "O(...)",
  "space_complexity": "O(...)",
  "roast_review": "String",
  "ai_bonus_score": 0
}}

The ai_bonus_score must be an integer from 0 to 10 based on efficiency and code quality.

Do not include Markdown formatting.
Do not include `json.
Return only the JSON object.

Problem title:
{title}

Submitted code:
{user_code}"""
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Clean the response
        cleaned_response = _clean_json_response(response.text)
        
        # Parse JSON
        review_data = json.loads(cleaned_response)
        
        # Validate structure and score range
        required_keys = ['time_complexity', 'space_complexity', 'roast_review', 'ai_bonus_score']
        if not all(key in review_data for key in required_keys):
            raise ValueError(f"Invalid review format. Missing keys: {required_keys}")
        
        score = review_data['ai_bonus_score']
        if not isinstance(score, int) or score < 0 or score > 10:
            print(f"Warning: AI bonus score {score} is outside 0-10 range, clamping to 5")
            review_data['ai_bonus_score'] = 5
        
        return review_data
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini review response: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
        raise ValueError("Failed to parse Gemini JSON response")
    except Exception as e:
        print(f"Error reviewing code: {e}")
        raise

if __name__ == "__main__":
    # Test the module
    try:
        # Note: This won't work without actual API keys
        print("AI Engine Module - Testing interface")
        print("initialize_gemini(): OK (requires secrets)")
        print("generate_problem('easy'): Returns dict with problem data")
        print("review_code('Test Problem', 'def solve(x): return x*x'): Returns review dict")
    except Exception as e:
        print(f"Test error: {e}")
