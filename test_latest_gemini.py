#!/usr/bin/env python3
"""
Test script to verify the latest Gemini model is working correctly
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

# Load environment variables
load_dotenv()

def test_gemini_models():
    """Test different Gemini models to see which ones work"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return
    
    # List of models to test (latest ones first)
    models_to_test = [
        "gemini-2.5-flash",      # Latest recommended model
        "gemini-2.5-pro",        # Most powerful thinking model
        "gemini-2.0-flash",      # Next generation features
        "gemini-1.5-flash",      # Fallback option
        "gemini-1.5-pro"         # Fallback option
    ]
    
    test_prompt = "Hello! Can you respond with 'Model working correctly' to confirm this model is functioning?"
    
    print("🧪 Testing Gemini Models...")
    print("=" * 50)
    
    working_models = []
    
    for model_name in models_to_test:
        try:
            print(f"\n🔍 Testing {model_name}...")
            
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                api_key=SecretStr(api_key),
                temperature=0.3,
                max_tokens=100
            )
            
            response = llm.invoke(test_prompt)
            print(f"✅ {model_name}: {response.content[:100]}...")
            working_models.append(model_name)
            
        except Exception as e:
            print(f"❌ {model_name}: {str(e)}")
    
    print("\n" + "=" * 50)
    print("📊 RESULTS SUMMARY:")
    print("=" * 50)
    
    if working_models:
        print(f"✅ Working models ({len(working_models)}):")
        for i, model in enumerate(working_models, 1):
            print(f"   {i}. {model}")
        
        print(f"\n🎯 RECOMMENDED: Use '{working_models[0]}' (latest working model)")
        
        # Test a more complex query with the best model
        print(f"\n🚀 Testing complex query with {working_models[0]}...")
        try:
            llm = ChatGoogleGenerativeAI(
                model=working_models[0],
                api_key=SecretStr(api_key),
                temperature=0.7
            )
            
            complex_prompt = """
            Analyze this scenario and provide a brief marketing strategy:
            A Tamil educational technology company wants to reach young students.
            What type of content and influencers would be most effective?
            """
            
            response = llm.invoke(complex_prompt)
            print(f"✅ Complex query successful!")
            print(f"📝 Response preview: {response.content[:200]}...")
            
        except Exception as e:
            print(f"❌ Complex query failed: {str(e)}")
    
    else:
        print("❌ No models are working. Please check your API key and internet connection.")
    
    return working_models

def update_env_with_working_model():
    """Update .env file with the recommended model"""
    working_models = test_gemini_models()
    
    if working_models:
        recommended_model = working_models[0]
        print(f"\n💡 Your app is now configured to use: {recommended_model}")
        print("✨ This is the latest stable Gemini model available!")
    else:
        print("\n⚠️  Please check your GEMINI_API_KEY in the .env file.")

if __name__ == "__main__":
    update_env_with_working_model()
