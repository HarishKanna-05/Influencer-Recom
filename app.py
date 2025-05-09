import streamlit as st
import json
import os
import re
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from wordcloud import WordCloud
import requests
from dotenv import load_dotenv
import googleapiclient.discovery
import googleapiclient.errors
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

# Import your existing modules
from tamil_influencer_collector import (
    get_influencers_by_category,
    CATEGORIES,
    calculate_engagement_rate,
    is_tamil_content,
    extract_contact_info
)

from social_media_trend_analyzer import SocialMediaTrendAnalyzer

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Influencer Marketing Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF5A5F;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #484848;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .influencer-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
        border-left: 5px solid #FF5A5F;
    }
    .metric-container {
        background-color: #f0f0f0;
        border-radius: 5px;
        padding: 10px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #FF5A5F;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #484848;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Gemini LLM
def get_gemini_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not found in .env file. Please add it as GEMINI_API_KEY=your_key_here")
        return None
    
    return ChatGoogleGenerativeAI(
        model='gemini-2.5-pro-exp-03-25',
        api_key=SecretStr(api_key)
    )

# Load influencer data from JSON file
def load_influencer_data():
    try:
        with open("tamil_influencers.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Function to analyze website and generate marketing strategy
def analyze_website(url, llm):
    if not llm:
        return "Error: Gemini API not initialized. Please check your API key."
    
    try:
        prompt = f"""
        Analyze this website: {url}
        
        Please provide a comprehensive marketing strategy report with the following sections:
        
        1. Website Overview:
           - Main products/services offered
           - Brand identity and theme
           - Target audience demographics
        
        2. Marketing Strategy Recommendations:
           - Content marketing approach
           - Social media platforms to focus on
           - Types of influencers that would be most effective
           - Content themes and ideas that would resonate with the audience
           - Recommended campaign types (awareness, engagement, conversion)
        
        3. Influencer Marketing Strategy:
           - Ideal influencer categories for this brand
           - Recommended content formats (videos, reels, posts)
           - Collaboration ideas
           - KPIs to track for measuring success
        
        Format the response in markdown with clear sections and bullet points.
        """
        
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Error analyzing website: {str(e)}"

# Function to get trending hashtags and keywords
def get_trending_data():
    analyzer = SocialMediaTrendAnalyzer(region_code="IN", language="ta")
    analyzer.analyze_youtube_trends()
    
    if not analyzer.youtube_trends:
        return None
    
    return {
        "hashtags": analyzer.youtube_trends.get("trending_hashtags", {}),
        "keywords": analyzer.youtube_trends.get("trending_keywords", {})
    }

# Function to display influencer card
def display_influencer_card(influencer):
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.image(
            influencer.get("thumbnailUrl", "https://via.placeholder.com/150"),
            width=150
        )
    
    with col2:
        st.markdown(f"### {influencer.get('channelTitle', 'Unknown Channel')}")
        st.markdown(f"**Subscribers:** {influencer.get('subscriberCount', 0):,}")
        st.markdown(f"**Engagement Rate:** {influencer.get('engagementRate', 0)}%")
        st.markdown(f"**Avg. Views:** {influencer.get('avgViewsPerVideo', 0):,}")
        
        # Contact info
        contact_info = []
        if influencer.get("businessEmail"):
            contact_info.append(f"📧 **Business Email:** {influencer.get('businessEmail')}")
        elif influencer.get("contactEmail"):
            contact_info.append(f"📧 **Email:** {influencer.get('contactEmail')}")
        
        social_links = influencer.get("socialLinks", {})
        if social_links.get("instagram"):
            contact_info.append(f"📸 **Instagram:** {social_links.get('instagram')}")
        if social_links.get("twitter"):
            contact_info.append(f"🐦 **Twitter:** {social_links.get('twitter')}")
        
        if contact_info:
            st.markdown("\n".join(contact_info))
        
        st.markdown(f"[View Channel](https://www.youtube.com/channel/{influencer.get('channelId')})")

# Main app
def main():
    st.markdown("<h1 class='main-header'>Influencer Marketing Assistant</h1>", unsafe_allow_html=True)
    
    # Initialize session state
    if 'marketing_strategy' not in st.session_state:
        st.session_state.marketing_strategy = None
    if 'selected_categories' not in st.session_state:
        st.session_state.selected_categories = []
    if 'influencers' not in st.session_state:
        st.session_state.influencers = []
    if 'trending_data' not in st.session_state:
        st.session_state.trending_data = None
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Configuration")
        
        # Website analysis
        st.markdown("#### Website Analysis")
        website_url = st.text_input("Enter website URL to analyze", "https://www.rajalakshmi.org")
        analyze_button = st.button("Analyze Website")
        
        st.markdown("---")
        
        # Influencer categories
        st.markdown("#### Influencer Categories")
        selected_categories = st.multiselect(
            "Select categories",
            options=CATEGORIES,
            default=[]
        )
        
        min_subscribers = st.slider(
            "Minimum Subscribers",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000,
            format="%d"
        )
        
        find_influencers_button = st.button("Find Influencers")
        
        st.markdown("---")
        
        # Trend analysis
        st.markdown("#### Trend Analysis")
        analyze_trends_button = st.button("Analyze Current Trends")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["Marketing Strategy", "Influencer Recommendations", "Trend Analysis"])
    
    # Initialize Gemini LLM
    llm = get_gemini_llm()
    
    # In the main function, modify the website analysis handler
    # Handle website analysis
    if analyze_button:
        with st.spinner("Analyzing website and generating marketing strategy..."):
            st.session_state.marketing_strategy = analyze_website(website_url, llm)
            
            # Extract recommended categories from the marketing strategy
            if st.session_state.marketing_strategy:
                recommended_categories = extract_recommended_categories(st.session_state.marketing_strategy)
                st.session_state.selected_categories = recommended_categories
                
                # Automatically find influencers based on the recommended categories
                with st.spinner("Finding relevant influencers based on website analysis..."):
                    all_influencers = load_influencer_data()
                    
                    filtered_influencers = []
                    for influencer in all_influencers:
                        if any(category in influencer.get("categories", []) for category in recommended_categories) and \
                           influencer.get("subscriberCount", 0) >= min_subscribers:
                            filtered_influencers.append(influencer)
                    
                    # Sort by subscriber count
                    filtered_influencers.sort(key=lambda x: x.get("subscriberCount", 0), reverse=True)
                    
                    st.session_state.influencers = filtered_influencers[:50]  # Limit to top 50
    
    # Handle influencer search
    if find_influencers_button:
        st.session_state.selected_categories = selected_categories
        with st.spinner("Finding relevant influencers..."):
            # Load influencers from JSON file
            all_influencers = load_influencer_data()
            
            # Filter by selected categories and minimum subscribers
            if selected_categories:
                filtered_influencers = []
                for influencer in all_influencers:
                    if any(category in influencer.get("categories", []) for category in selected_categories) and \
                       influencer.get("subscriberCount", 0) >= min_subscribers:
                        filtered_influencers.append(influencer)
            else:
                filtered_influencers = [inf for inf in all_influencers if inf.get("subscriberCount", 0) >= min_subscribers]
            
            # Sort by subscriber count
            filtered_influencers.sort(key=lambda x: x.get("subscriberCount", 0), reverse=True)
            
            st.session_state.influencers = filtered_influencers[:50]  # Limit to top 50
    
    # Handle trend analysis
    if analyze_trends_button:
        with st.spinner("Analyzing current trends..."):
            st.session_state.trending_data = get_trending_data()
    
    # Tab 1: Marketing Strategy
    with tab1:
        if st.session_state.marketing_strategy:
            st.markdown(st.session_state.marketing_strategy)
        else:
            st.info("Enter a website URL and click 'Analyze Website' to generate a marketing strategy.")
    
    # Tab 2: Influencer Recommendations
    with tab2:
        if st.session_state.influencers:
            st.markdown(f"### Found {len(st.session_state.influencers)} Influencers")
            
            # Group influencers by category
            if st.session_state.selected_categories:
                for category in st.session_state.selected_categories:
                    category_influencers = [inf for inf in st.session_state.influencers 
                                          if category in inf.get("categories", [])]
                    
                    if category_influencers:
                        st.markdown(f"<h3 class='sub-header'>{category}</h3>", unsafe_allow_html=True)
                        
                        for influencer in category_influencers[:5]:  # Show top 5 per category
                            with st.container():
                                st.markdown("<div class='influencer-card'>", unsafe_allow_html=True)
                                display_influencer_card(influencer)
                                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Show all influencers if no category selected
                for influencer in st.session_state.influencers[:10]:  # Show top 10
                    with st.container():
                        st.markdown("<div class='influencer-card'>", unsafe_allow_html=True)
                        display_influencer_card(influencer)
                        st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Select categories and click 'Find Influencers' to see recommendations.")
    
    # Tab 3: Trend Analysis
    with tab3:
        if st.session_state.trending_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Trending Hashtags")
                hashtags = st.session_state.trending_data.get("hashtags", {})
                if hashtags:
                    # Create hashtag word cloud
                    try:
                        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(hashtags)
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"Error generating word cloud: {str(e)}")
                    
                    # Show hashtag table
                    hashtag_df = pd.DataFrame(list(hashtags.items()), columns=["Hashtag", "Count"])
                    hashtag_df = hashtag_df.sort_values(by="Count", ascending=False).head(10)
                    st.table(hashtag_df)
                else:
                    st.info("No trending hashtags found.")
            
            with col2:
                st.markdown("### Trending Keywords")
                keywords = st.session_state.trending_data.get("keywords", {})
                if keywords:
                    # Create keyword word cloud
                    try:
                        wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(keywords)
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"Error generating word cloud: {str(e)}")
                    
                    # Show keyword table
                    keyword_df = pd.DataFrame(list(keywords.items()), columns=["Keyword", "Count"])
                    keyword_df = keyword_df.sort_values(by="Count", ascending=False).head(10)
                    st.table(keyword_df)
                else:
                    st.info("No trending keywords found.")
        else:
            st.info("Click 'Analyze Current Trends' to see trending hashtags and keywords.")

# Add this function after the analyze_website function
def extract_recommended_categories(marketing_strategy):
    """Extract recommended influencer categories from the marketing strategy"""
    if not marketing_strategy:
        return []
    
    # Look for influencer categories in the marketing strategy text
    categories = []
    for category in CATEGORIES:
        # Remove "Tamil " prefix for matching
        category_keyword = category.replace("Tamil ", "").lower()
        if category_keyword in marketing_strategy.lower():
            categories.append(category)
    
    # If no categories found, try to match broader terms
    if not categories:
        category_mapping = {
            "tech": "Tamil tech",
            "education": "Tamil education",
            "movie": "Tamil movies",
            "film": "Tamil movies",
            "cinema": "Tamil movies",
            "beauty": "Tamil beauty",
            "fashion": "Tamil fashion",
            "style": "Tamil fashion",
            "gaming": "Tamil gaming",
            "game": "Tamil gaming",
            "music": "Tamil music",
            "song": "Tamil music",
            "cook": "Tamil cooking",
            "food": "Tamil cooking",
            "recipe": "Tamil cooking",
            "comedy": "Tamil comedy",
            "funny": "Tamil comedy",
            "humor": "Tamil comedy",
            "vlog": "Tamil vlogs",
            "lifestyle": "Tamil lifestyle",
            "fitness": "Tamil fitness",
            "workout": "Tamil fitness",
            "exercise": "Tamil fitness",
            "travel": "Tamil travel",
            "tourism": "Tamil travel",
            "business": "Tamil business",
            "entrepreneur": "Tamil business",
            "motivation": "Tamil motivation",
            "inspire": "Tamil motivation"
        }
        
        for keyword, category in category_mapping.items():
            if keyword in marketing_strategy.lower() and category in CATEGORIES:
                categories.append(category)
    
    return list(set(categories))  # Remove duplicates

if __name__ == "__main__":
    main()