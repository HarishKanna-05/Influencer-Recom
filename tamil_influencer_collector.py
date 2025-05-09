import os
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient

# Add this class to handle datetime serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("YouTube API key not found. Please add it to your .env file as YOUTUBE_API_KEY=your_key_here")

# Initialize YouTube API client
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

# Initialize MongoDB client
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["tamil_influencers"]
influencers_collection = db["influencers"]

# Create indexes for faster queries
influencers_collection.create_index([("channelId", pymongo.ASCENDING)], unique=True)
influencers_collection.create_index([("categories", pymongo.ASCENDING)])
influencers_collection.create_index([("subscriberCount", pymongo.DESCENDING)])

# Tamil categories to search for
CATEGORIES = [
    "Tamil comedy",
    # "Tamil cooking",
    "Tamil tech",
    # "Tamil beauty",
    "Tamil fashion",
    # "Tamil gaming",
     "Tamil education",
    # "Tamil music",
     "Tamil movies",
    # "Tamil vlogs",
    # "Tamil fitness",
    # "Tamil travel",
    # "Tamil lifestyle",
    #  "Tamil business",
    # "Tamil motivation"
]

def search_channels(category: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for YouTube channels based on a category.
    
    Args:
        category: The category to search for
        max_results: Maximum number of results to return (default: 10 to limit API usage)
        
    Returns:
        List of channel items
    """
    try:
        print(f"Searching for channels in category: {category}")
        request = youtube.search().list(
            part="snippet",
            q=category,
            type="channel",
            relevanceLanguage="ta",  # Tamil language code
            maxResults=max_results,
            order="viewCount"  # Order by view count to get popular channels first
        )
        response = request.execute()
        
        print(f"Found {len(response.get('items', []))} channels for category: {category}")
        return response.get("items", [])
    
    except googleapiclient.errors.HttpError as e:
        error_details = json.loads(e.content)
        print(f"YouTube API error: {error_details.get('error', {}).get('message', 'Unknown error')}")
        
        if "quota" in str(e).lower():
            print("API quota exceeded. Waiting for 1 hour before retrying...")
            time.sleep(3600)  # Wait for 1 hour
            return search_channels(category, max_results)
        
        return []
    
    except Exception as e:
        print(f"Error searching channels for {category}: {str(e)}")
        return []

def get_channel_details(channel_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a YouTube channel.
    
    Args:
        channel_id: The ID of the channel
        
    Returns:
        Channel details or None if not found
    """
    try:
        request = youtube.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings",
            id=channel_id
        )
        response = request.execute()
        
        if not response.get("items"):
            return None
        
        return response["items"][0]
    
    except googleapiclient.errors.HttpError as e:
        error_details = json.loads(e.content)
        print(f"YouTube API error: {error_details.get('error', {}).get('message', 'Unknown error')}")
        
        if "quota" in str(e).lower():
            print("API quota exceeded. Waiting for 1 hour before retrying...")
            time.sleep(3600)  # Wait for 1 hour
            return get_channel_details(channel_id)
        
        return None
    
    except Exception as e:
        print(f"Error getting channel details for {channel_id}: {str(e)}")
        return None

def calculate_engagement_rate(channel_id: str) -> Tuple[float, int]:
    """
    Calculate engagement rate and average views per video for a channel.
    
    Args:
        channel_id: The ID of the channel
        
    Returns:
        Tuple of (engagement_rate, avg_views_per_video)
    """
    try:
        # Get channel's recent videos
        videos_request = youtube.search().list(
            part="id",
            channelId=channel_id,
            order="date",
            type="video",
            maxResults=10
        )
        videos_response = videos_request.execute()
        
        if not videos_response.get("items"):
            return 0.0, 0
        
        video_ids = [item["id"]["videoId"] for item in videos_response["items"]]
        
        # Get video statistics
        video_stats_request = youtube.videos().list(
            part="statistics",
            id=",".join(video_ids)
        )
        video_stats_response = video_stats_request.execute()
        
        # Calculate average engagement
        total_likes = 0
        total_comments = 0
        total_views = 0
        
        for video in video_stats_response.get("items", []):
            stats = video.get("statistics", {})
            total_likes += int(stats.get("likeCount", 0))
            total_comments += int(stats.get("commentCount", 0))
            total_views += int(stats.get("viewCount", 0))
        
        video_count = len(video_stats_response.get("items", []))
        
        if video_count == 0 or total_views == 0:
            return 0.0, 0
        
        avg_views = total_views / video_count
        
        # Engagement rate = (likes + comments) / views * 100
        engagement_rate = ((total_likes + total_comments) / total_views) * 100
        
        return round(engagement_rate, 2), round(avg_views)
    
    except googleapiclient.errors.HttpError as e:
        error_details = json.loads(e.content)
        print(f"YouTube API error: {error_details.get('error', {}).get('message', 'Unknown error')}")
        
        if "quota" in str(e).lower():
            print("API quota exceeded. Waiting for 1 hour before retrying...")  # Wait for 1 hour
            return calculate_engagement_rate(channel_id)
        
        return 0.0, 0
    
    except Exception as e:
        print(f"Error calculating engagement for {channel_id}: {str(e)}")
        return 0.0, 0

def extract_contact_info(description: str) -> Dict[str, Optional[str]]:
    """
    Extract contact information from channel description.
    
    Args:
        description: Channel description text
        
    Returns:
        Dictionary with contact information
    """
    contact_info = {
        "email": None,
        "phone": None,
        "instagram": None,
        "twitter": None,
        "facebook": None,
        "business_email": None
    }
    
    # Extract email addresses
    email_regex = r'[\w.-]+@[\w.-]+\.\w+'
    emails = re.findall(email_regex, description)
    
    if emails:
        contact_info["email"] = emails[0]
        
        # Check for business email specifically
        business_email_patterns = [
            r'business\s*email\s*[:-]?\s*([\w.-]+@[\w.-]+\.\w+)',
            r'for\s*business\s*[:-]?\s*([\w.-]+@[\w.-]+\.\w+)',
            r'business\s*inquiries\s*[:-]?\s*([\w.-]+@[\w.-]+\.\w+)'
        ]
        
        for pattern in business_email_patterns:
            business_match = re.search(pattern, description, re.IGNORECASE)
            if business_match:
                contact_info["business_email"] = business_match.group(1)
                break
    
    # Extract phone numbers (basic pattern)
    phone_regex = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_regex, description)
    if phones:
        contact_info["phone"] = phones[0]
    
    # Extract social media handles
    instagram_regex = r'instagram\.com/([A-Za-z0-9_.-]+)'
    instagram_match = re.search(instagram_regex, description, re.IGNORECASE)
    if instagram_match:
        contact_info["instagram"] = instagram_match.group(1)
    
    twitter_regex = r'twitter\.com/([A-Za-z0-9_.-]+)'
    twitter_match = re.search(twitter_regex, description, re.IGNORECASE)
    if twitter_match:
        contact_info["twitter"] = twitter_match.group(1)
    
    facebook_regex = r'facebook\.com/([A-Za-z0-9_.-]+)'
    facebook_match = re.search(facebook_regex, description, re.IGNORECASE)
    if facebook_match:
        contact_info["facebook"] = facebook_match.group(1)
    
    return contact_info

def is_tamil_content(channel_details: Dict[str, Any]) -> bool:
    """
    Check if a channel contains Tamil content.
    
    Args:
        channel_details: Channel details from YouTube API
        
    Returns:
        True if the channel likely contains Tamil content
    """
    snippet = channel_details.get("snippet", {})
    title = snippet.get("title", "").lower()
    description = snippet.get("description", "").lower()
    
    # Check for Tamil keywords
    tamil_keywords = ["tamil", "தமிழ்", "தமிழ"]
    
    for keyword in tamil_keywords:
        if keyword in title or keyword in description:
            return True
    
    # Check for Tamil Unicode characters
    tamil_unicode_pattern = r'[\u0B80-\u0BFF]'
    if re.search(tamil_unicode_pattern, title) or re.search(tamil_unicode_pattern, description):
        return True
    
    # Check country
    if channel_details.get("brandingSettings", {}).get("channel", {}).get("country") == "IN":
        # If from India, check for more Tamil indicators
        if "chennai" in description or "tamil nadu" in description:
            return True
    
    return False

def collect_influencer_data():
    """
    Main function to collect Tamil YouTube influencer data.
    Limited to top 10 influencers per category to manage API quota.
    """
    print("Starting Tamil YouTube influencer data collection (top 10 per category)...")
    
    for category in CATEGORIES:
        print(f"\nProcessing category: {category}")
        
        # Search for top 10 channels in this category
        channels = search_channels(category, max_results=10)
        
        for channel in channels:
            channel_id = channel["id"]["channelId"]
            
            # Check if we already have this channel
            existing_channel = influencers_collection.find_one({"channelId": channel_id})
            
            if existing_channel:
                print(f"Channel {channel['snippet']['title']} already exists, updating categories...")
                
                # Update existing channel with new category if needed
                if category not in existing_channel.get("categories", []):
                    influencers_collection.update_one(
                        {"channelId": channel_id},
                        {"$addToSet": {"categories": category},
                         "$set": {"lastUpdated": datetime.now()}}
                    )
                continue
            
            # Get detailed channel information
            channel_details = get_channel_details(channel_id)
            
            if not channel_details:
                print(f"Could not get details for channel {channel['snippet']['title']}")
                continue
            
            # Check if the channel contains Tamil content
            if not is_tamil_content(channel_details):
                print(f"Skipping non-Tamil channel: {channel_details['snippet']['title']}")
                continue
            
            # Calculate engagement metrics
            engagement_rate, avg_views = calculate_engagement_rate(channel_id)
            
            # Extract contact information from description
            description = channel_details["snippet"]["description"]
            contact_info = extract_contact_info(description)
            
            # Create new influencer record
            influencer = {
                "channelId": channel_id,
                "channelTitle": channel_details["snippet"]["title"],
                "description": description,
                "thumbnailUrl": channel_details["snippet"]["thumbnails"]["high"]["url"],
                "subscriberCount": int(channel_details["statistics"].get("subscriberCount", 0)),
                "videoCount": int(channel_details["statistics"].get("videoCount", 0)),
                "viewCount": int(channel_details["statistics"].get("viewCount", 0)),
                "categories": [category],
                "contactEmail": contact_info["email"],
                "businessEmail": contact_info["business_email"],
                "contactPhone": contact_info["phone"],
                "socialLinks": {
                    "instagram": contact_info["instagram"],
                    "twitter": contact_info["twitter"],
                    "facebook": contact_info["facebook"]
                },
                "language": "Tamil",
                "engagementRate": engagement_rate,
                "avgViewsPerVideo": avg_views,
                "createdAt": datetime.now(),
                "lastUpdated": datetime.now()
            }
            
            # Save to database
            try:
                influencers_collection.insert_one(influencer)
                print(f"Saved influencer: {channel_details['snippet']['title']}")
            except pymongo.errors.DuplicateKeyError:
                print(f"Duplicate channel ID: {channel_id}")
            
            # Respect YouTube API quota limits with a delay
            time.sleep(1)
    
    print("\nData collection complete!")

def get_influencers_by_category(categories=None, min_subscribers=0, limit=100):
    """
    Get influencers filtered by categories and minimum subscribers.
    
    Args:
        categories: List of categories to filter by
        min_subscribers: Minimum number of subscribers
        limit: Maximum number of results to return
        
    Returns:
        List of influencer documents
    """
    query = {"subscriberCount": {"$gte": min_subscribers}}
    
    if categories:
        query["categories"] = {"$in": categories if isinstance(categories, list) else [categories]}
    
    influencers = list(
        influencers_collection.find(
            query,
            {"_id": 0}  # Exclude MongoDB _id field
        )
        .sort("subscriberCount", pymongo.DESCENDING)
        .limit(limit)
    )
    
    return influencers

def export_to_json(filename="tamil_influencers.json"):
    """
    Export all influencers to a JSON file.
    
    Args:
        filename: Name of the output file
    """
    influencers = list(influencers_collection.find({}, {"_id": 0}))
    
    # Convert datetime objects to strings
    for influencer in influencers:
        if "createdAt" in influencer:
            influencer["createdAt"] = influencer["createdAt"].isoformat()
        if "lastUpdated" in influencer:
            influencer["lastUpdated"] = influencer["lastUpdated"].isoformat()
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(influencers, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    
    print(f"Exported {len(influencers)} influencers to {filename}")

def get_top_influencers_by_category(limit=10):
    """
    Get the top influencers for each category.
    
    Args:
        limit: Maximum number of influencers per category
        
    Returns:
        Dictionary with categories as keys and lists of influencers as values
    """
    result = {}
    
    for category in CATEGORIES:
        influencers = list(
            influencers_collection.find(
                {"categories": category},
                {"_id": 0}
            )
            .sort("subscriberCount", pymongo.DESCENDING)
            .limit(limit)
        )
        
        # Convert datetime objects to strings
        for influencer in influencers:
            if "createdAt" in influencer:
                influencer["createdAt"] = influencer["createdAt"].isoformat()
            if "lastUpdated" in influencer:
                influencer["lastUpdated"] = influencer["lastUpdated"].isoformat()
        
        result[category] = influencers
    
    return result

def export_top_influencers(filename="top_tamil_influencers.json", limit=10):
    """
    Export top influencers from each category to a JSON file.
    
    Args:
        filename: Name of the output file
        limit: Maximum number of influencers per category
    """
    top_influencers = get_top_influencers_by_category(limit=limit)
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(top_influencers, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    
    total_count = sum(len(influencers) for influencers in top_influencers.values())
    print(f"Exported top {limit} influencers from each category (total: {total_count}) to {filename}")

def print_stats():
    """
    Print statistics about the collected data.
    """
    total_influencers = influencers_collection.count_documents({})
    
    print(f"\n=== Tamil YouTube Influencer Database Stats ===")
    print(f"Total influencers: {total_influencers}")
    
    # Stats by category
    print("\nInfluencers by category:")
    for category in CATEGORIES:
        count = influencers_collection.count_documents({"categories": category})
        print(f"  {category}: {count}")
    
    # Stats by subscriber count
    print("\nInfluencers by subscriber count:")
    print(f"  1M+: {influencers_collection.count_documents({'subscriberCount': {'$gte': 1000000}})}")
    print(f"  500K-1M: {influencers_collection.count_documents({'subscriberCount': {'$gte': 500000, '$lt': 1000000}})}")
    print(f"  100K-500K: {influencers_collection.count_documents({'subscriberCount': {'$gte': 100000, '$lt': 500000}})}")
    print(f"  50K-100K: {influencers_collection.count_documents({'subscriberCount': {'$gte': 50000, '$lt': 100000}})}")
    print(f"  10K-50K: {influencers_collection.count_documents({'subscriberCount': {'$gte': 10000, '$lt': 50000}})}")
    print(f"  <10K: {influencers_collection.count_documents({'subscriberCount': {'$lt': 10000}})}")
    
    # Contact information stats
    with_email = influencers_collection.count_documents({"contactEmail": {"$ne": None}})
    with_business_email = influencers_collection.count_documents({"businessEmail": {"$ne": None}})
    with_phone = influencers_collection.count_documents({"contactPhone": {"$ne": None}})
    with_instagram = influencers_collection.count_documents({"socialLinks.instagram": {"$ne": None}})
    
    print("\nContact information availability:")
    if total_influencers > 0:
        print(f"  With email: {with_email} ({round(with_email/total_influencers*100, 1)}%)")
        print(f"  With business email: {with_business_email} ({round(with_business_email/total_influencers*100, 1)}%)")
        print(f"  With phone: {with_phone} ({round(with_phone/total_influencers*100, 1)}%)")
        print(f"  With Instagram: {with_instagram} ({round(with_instagram/total_influencers*100, 1)}%)")
    else:
        print("  No influencers in database yet. Run the collection process first.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Tamil YouTube Influencer Data Collection Tool")
    parser.add_argument("--collect", action="store_true", help="Collect new influencer data")
    parser.add_argument("--export", action="store_true", help="Export data to JSON file")
    parser.add_argument("--export-top", action="store_true", help="Export top influencers from each category")
    parser.add_argument("--stats", action="store_true", help="Print database statistics")
    parser.add_argument("--category", help="Filter by specific category when exporting")
    parser.add_argument("--min-subscribers", type=int, default=0, help="Minimum subscriber count when exporting")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of results per category")
    
    args = parser.parse_args()
    
    if args.collect:
        collect_influencer_data()
    
    if args.export:
        categories = [args.category] if args.category else None
        influencers = get_influencers_by_category(
            categories=categories,
            min_subscribers=args.min_subscribers,
            limit=10000  # High limit to get all matching influencers
        )
        
        filename = f"tamil_influencers"
        if args.category:
            filename += f"_{args.category.replace(' ', '_').lower()}"
        if args.min_subscribers > 0:
            filename += f"_min{args.min_subscribers}"
        filename += ".json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(influencers, f, ensure_ascii=False, indent=2,cls=DateTimeEncoder)
        
        print(f"Exported {len(influencers)} influencers to {filename}")
    
    if args.export_top:
        export_top_influencers(limit=args.limit)
    
    if args.stats:
        print_stats()
    
    # If no arguments provided, show help