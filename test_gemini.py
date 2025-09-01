#!/usr/bin/env python3
"""
Test script to verify that the Gemini API is working with the latest model.
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

# Load environment variables
load_dotenv()

def test_gemini_models():
    """Test different Gemini models to find the latest available ones."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return False
    
    # List of Gemini models to test (from latest to older)
    models_to_test = [
        "gemini-1.5-pro-002",      # Latest stable
        "gemini-1.5-pro-001",      # Previous version
        "gemini-1.5-pro",          # Base model
        "gemini-1.5-flash-002",    # Latest flash
        "gemini-1.5-flash-001",    # Previous flash
        "gemini-1.5-flash",        # Base flash
        "gemini-pro"               # Legacy model
    ]
    
    working_models = []
    
    for model_name in models_to_test:
        try:
            print(f"Testing model: {model_name}...")
            
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                api_key=SecretStr(api_key),
                temperature=0.1
            )
            
            # Simple test prompt
            response = llm.invoke("Hello! Please respond with just 'Working' if you can see this message.")
            
            if response and response.content:
                print(f"✅ {model_name}: {response.content.strip()}")
                working_models.append(model_name)
            else:
                print(f"❌ {model_name}: No response received")
                
        except Exception as e:
            print(f"❌ {model_name}: {str(e)}")
    
    print(f"\n📊 Summary:")
    print(f"Working models: {len(working_models)}")
    for model in working_models:
        print(f"  ✅ {model}")
    
    if working_models:
        print(f"\n🎯 Recommended model to use: {working_models[0]}")
        return working_models[0]
    else:
        print("❌ No working models found. Please check your API key.")
        return None

if __name__ == "__main__":
    print("🔍 Testing Gemini Models...")
    print("=" * 50)
    
    best_model = test_gemini_models()
    
    if best_model:
        print(f"\n🚀 Your code should use: {best_model}")
        print("\nThe app.py and main.py files have been updated to use the latest working model.")
    else:
        print("\n❌ Please check your GEMINI_API_KEY in the .env file.")
