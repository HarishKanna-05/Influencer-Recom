import os
import json
import time
import re
import datetime
from typing import Dict, List, Any, Optional, Tuple
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from wordcloud import WordCloud
import requests
from dotenv import load_dotenv
import googleapiclient.discovery
import googleapiclient.errors

# Load environment variables
load_dotenv()

# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Initialize YouTube API client if key is available
youtube = None
if YOUTUBE_API_KEY:
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

class SocialMediaTrendAnalyzer:
    """
    A class to analyze trends across different social media platforms.
    Currently supports YouTube and Instagram.
    """
    
    def __init__(self, region_code="IN", language="ta"):
        """
        Initialize the trend analyzer.
        
        Args:
            region_code: The region code to analyze trends for (default: IN for India)
            language: The language to analyze trends for (default: ta for Tamil)
        """
        self.region_code = region_code
        self.language = language
        self.youtube_trends = {}
        self.instagram_trends = {}
        
        # Create output directory if it doesn't exist
        os.makedirs("trend_reports", exist_ok=True)
    
    def get_youtube_trending_videos(self, category_id=None, max_results=50):
        """
        Get trending videos from YouTube.
        
        Args:
            category_id: The category ID to filter by (optional)
            max_results: Maximum number of results to return
            
        Returns:
            List of trending videos
        """
        if not youtube:
            print("YouTube API key not found. Skipping YouTube trend analysis.")
            return []
        
        try:
            # Build the request
            request_params = {
                "part": "snippet,contentDetails,statistics",
                "chart": "mostPopular",
                "regionCode": self.region_code,
                "maxResults": max_results,
                "relevanceLanguage": self.language
            }
            
            if category_id:
                request_params["videoCategoryId"] = category_id
            
            request = youtube.videos().list(**request_params)
            response = request.execute()
            
            # Process and return the results
            videos = []
            for item in response.get("items", []):
                video = {
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "channelTitle": item["snippet"]["channelTitle"],
                    "publishedAt": item["snippet"]["publishedAt"],
                    "viewCount": int(item["statistics"].get("viewCount", 0)),
                    "likeCount": int(item["statistics"].get("likeCount", 0)),
                    "commentCount": int(item["statistics"].get("commentCount", 0)),
                    "tags": item["snippet"].get("tags", []),
                    "categoryId": item["snippet"]["categoryId"],
                    "thumbnailUrl": item["snippet"]["thumbnails"]["high"]["url"],
                    "url": f"https://www.youtube.com/watch?v={item['id']}"
                }
                videos.append(video)
            
            return videos
        
        except googleapiclient.errors.HttpError as e:
            print(f"YouTube API error: {e}")
            return []
        
        except Exception as e:
            print(f"Error getting YouTube trending videos: {e}")
            return []
    
    def get_youtube_trending_music(self, max_results=30):
        """
        Get trending music videos from YouTube.
        Music category ID is typically 10.
        
        Args:
            max_results: Maximum number of results to return
            
        Returns:
            List of trending music videos
        """
        return self.get_youtube_trending_videos(category_id="10", max_results=max_results)
    
    def extract_hashtags_from_youtube(self, videos):
        """
        Extract hashtags from YouTube video titles and descriptions.
        
        Args:
            videos: List of YouTube video data
            
        Returns:
            Counter object with hashtag frequencies
        """
        hashtags = []
        
        for video in videos:
            # Extract hashtags from title
            title_tags = re.findall(r'#\w+', video["title"])
            hashtags.extend([tag.lower() for tag in title_tags])
            
            # Extract hashtags from tags
            for tag in video.get("tags", []):
                if tag.startswith("#"):
                    hashtags.append(tag.lower())
        
        return Counter(hashtags)
    
    def extract_trending_keywords(self, videos, min_count=2):
        """
        Extract trending keywords from video titles.
        
        Args:
            videos: List of YouTube video data
            min_count: Minimum count to consider a keyword trending
            
        Returns:
            Counter object with keyword frequencies
        """
        # Common words to exclude
        stop_words = set([
            "the", "and", "a", "to", "of", "in", "is", "you", "that", "it", "he",
            "was", "for", "on", "are", "with", "as", "his", "they", "at", "be",
            "this", "have", "from", "or", "one", "had", "by", "word", "but", "not",
            "what", "all", "were", "we", "when", "your", "can", "said", "there",
            "use", "an", "each", "which", "she", "do", "how", "their", "if", "will",
            "up", "other", "about", "out", "many", "then", "them", "these", "so",
            "some", "her", "would", "make", "like", "him", "into", "time", "has",
            "look", "two", "more", "write", "go", "see", "number", "no", "way",
            "could", "people", "my", "than", "first", "water", "been", "call",
            "who", "oil", "its", "now", "find", "long", "down", "day", "did", "get",
            "come", "made", "may", "part", "over", "new", "sound", "take", "only",
            "little", "work", "know", "place", "year", "live", "me", "back", "give",
            "most", "very", "after", "thing", "our", "just", "name", "good",
            "sentence", "man", "think", "say", "great", "where", "help", "through",
            "much", "before", "line", "right", "too", "mean", "old", "any", "same",
            "tell", "boy", "follow", "came", "want", "show", "also", "around",
            "form", "three", "small", "set", "put", "end", "does", "another",
            "well", "large", "must", "big", "even", "such", "because", "turn",
            "here", "why", "ask", "went", "men", "read", "need", "land", "different",
            "home", "us", "move", "try", "kind", "hand", "picture", "again", "change",
            "off", "play", "spell", "air", "away", "animal", "house", "point", "page",
            "letter", "mother", "answer", "found", "study", "still", "learn", "should",
            "america", "world"
        ])
        
        # Extract all words from titles
        all_words = []
        for video in videos:
            # Remove special characters and split into words
            words = re.sub(r'[^\w\s]', ' ', video["title"].lower()).split()
            # Filter out stop words and short words
            filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
            all_words.extend(filtered_words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        
        # Filter to words that appear at least min_count times
        trending_keywords = {word: count for word, count in word_counts.items() if count >= min_count}
        
        return Counter(trending_keywords)
    
    def analyze_youtube_trends(self):
        """
        Analyze trending content on YouTube.
        """
        print("Analyzing YouTube trends...")
        
        # Get trending videos
        trending_videos = self.get_youtube_trending_videos(max_results=50)
        if not trending_videos:
            print("No trending videos found.")
            return
        
        # Get trending music videos
        trending_music = self.get_youtube_trending_music(max_results=30)
        
        # Extract hashtags
        hashtags = self.extract_hashtags_from_youtube(trending_videos)
        
        # Extract trending keywords
        keywords = self.extract_trending_keywords(trending_videos)
        
        # Store the results
        self.youtube_trends = {
            "trending_videos": trending_videos,
            "trending_music": trending_music,
            "trending_hashtags": dict(hashtags.most_common(20)),
            "trending_keywords": dict(keywords.most_common(30)),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        print(f"Found {len(trending_videos)} trending videos and {len(trending_music)} trending music videos.")
        print(f"Top hashtags: {', '.join(list(self.youtube_trends['trending_hashtags'].keys())[:5])}")
    
    def analyze_instagram_trends(self):
        """
        Analyze trending content on Instagram.
        Requires Instagram Graph API access token.
        """
        if not INSTAGRAM_ACCESS_TOKEN:
            print("Instagram access token not found. Skipping Instagram trend analysis.")
            return
            
        print("Analyzing Instagram trends...")
        
        try:
            # Get trending hashtags from Instagram
            # Note: This requires Instagram Graph API access
            # This is a simplified implementation
            hashtags = self.get_instagram_trending_hashtags()
            
            # Get trending reels
            reels = self.get_instagram_trending_reels()
            
            # Store the results
            self.instagram_trends = {
                "trending_hashtags": hashtags,
                "trending_reels": reels,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            print(f"Found {len(hashtags)} trending hashtags and {len(reels)} trending reels on Instagram.")
            
        except Exception as e:
            print(f"Error analyzing Instagram trends: {e}")
    
    def get_instagram_trending_hashtags(self, limit=20):
        """
        Get trending hashtags from Instagram.
        
        Args:
            limit: Maximum number of hashtags to return
            
        Returns:
            Dictionary of hashtags and their counts
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Instagram Graph API
        # to get trending hashtags
        
        # For now, return an empty dictionary
        return {}
    
    def get_instagram_trending_reels(self, limit=20):
        """
        Get trending reels from Instagram.
        
        Args:
            limit: Maximum number of reels to return
            
        Returns:
            List of trending reels
        """
        # This is a placeholder implementation
        # In a real implementation, you would use the Instagram Graph API
        # to get trending reels
        
        # For now, return an empty list
        return []
    
    def analyze_all_platforms(self):
        """
        Analyze trends across all supported platforms.
        """
        self.analyze_youtube_trends()
        self.analyze_instagram_trends()
    
    def generate_youtube_report(self, output_format="json"):
        """
        Generate a report of YouTube trends.
        
        Args:
            output_format: Format of the output report (json, csv, or html)
        """
        if not self.youtube_trends:
            print("No YouTube trends data available. Run analyze_youtube_trends() first.")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save trending videos to file
        if output_format == "json":
            with open(f"trend_reports/youtube_trends_{timestamp}.json", "w", encoding="utf-8") as f:
                json.dump(self.youtube_trends, f, ensure_ascii=False, indent=2)
            print(f"YouTube trends saved to trend_reports/youtube_trends_{timestamp}.json")
        
        elif output_format == "csv":
            # Convert trending videos to DataFrame
            videos_df = pd.DataFrame(self.youtube_trends["trending_videos"])
            videos_df.to_csv(f"trend_reports/youtube_trending_videos_{timestamp}.csv", index=False)
            
            # Convert trending music to DataFrame
            music_df = pd.DataFrame(self.youtube_trends["trending_music"])
            music_df.to_csv(f"trend_reports/youtube_trending_music_{timestamp}.csv", index=False)
            
            # Convert hashtags to DataFrame
            hashtags_df = pd.DataFrame(list(self.youtube_trends["trending_hashtags"].items()), 
                                      columns=["hashtag", "count"])
            hashtags_df.to_csv(f"trend_reports/youtube_trending_hashtags_{timestamp}.csv", index=False)
            
            # Convert keywords to DataFrame
            keywords_df = pd.DataFrame(list(self.youtube_trends["trending_keywords"].items()), 
                                      columns=["keyword", "count"])
            keywords_df.to_csv(f"trend_reports/youtube_trending_keywords_{timestamp}.csv", index=False)
            
            print(f"YouTube trends saved to CSV files in trend_reports/ directory")
        
        elif output_format == "html":
            # Create a simple HTML report
            html_content = f"""
            <html>
            <head>
                <title>YouTube Trends Report - {timestamp}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2 {{ color: #cc0000; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    .video-card {{ border: 1px solid #ddd; margin: 10px; padding: 10px; border-radius: 5px; }}
                    .video-thumbnail {{ width: 120px; height: 90px; object-fit: cover; }}
                </style>
            </head>
            <body>
                <h1>YouTube Trends Report</h1>
                <p>Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                
                <h2>Top Trending Hashtags</h2>
                <table>
                    <tr><th>Hashtag</th><th>Count</th></tr>
            """
            
            # Add hashtags
            for hashtag, count in self.youtube_trends["trending_hashtags"].items():
                html_content += f"<tr><td>{hashtag}</td><td>{count}</td></tr>"
            
            html_content += """
                </table>
                
                <h2>Top Trending Keywords</h2>
                <table>
                    <tr><th>Keyword</th><th>Count</th></tr>
            """
            
            # Add keywords
            for keyword, count in self.youtube_trends["trending_keywords"].items():
                html_content += f"<tr><td>{keyword}</td><td>{count}</td></tr>"
            
            html_content += """
                </table>
                
                <h2>Trending Music Videos</h2>
            """
            
            # Add music videos
            for video in self.youtube_trends["trending_music"][:10]:  # Show top 10
                html_content += f"""
                <div class="video-card">
                    <img src="{video['thumbnailUrl']}" class="video-thumbnail" align="left" style="margin-right: 10px;">
                    <h3><a href="{video['url']}" target="_blank">{video['title']}</a></h3>
                    <p>Channel: {video['channelTitle']}</p>
                    <p>Views: {video['viewCount']:,} | Likes: {video['likeCount']:,} | Comments: {video['commentCount']:,}</p>
                    <div style="clear: both;"></div>
                </div>
                """
            
            html_content += """
                <h2>Trending Videos</h2>
            """
            
            # Add trending videos
            for video in self.youtube_trends["trending_videos"][:10]:  # Show top 10
                html_content += f"""
                <div class="video-card">
                    <img src="{video['thumbnailUrl']}" class="video-thumbnail" align="left" style="margin-right: 10px;">
                    <h3><a href="{video['url']}" target="_blank">{video['title']}</a></h3>
                    <p>Channel: {video['channelTitle']}</p>
                    <p>Views: {video['viewCount']:,} | Likes: {video['likeCount']:,} | Comments: {video['commentCount']:,}</p>
                    <div style="clear: both;"></div>
                </div>
                """
            
            html_content += """
            </body>
            </html>
            """
            
            with open(f"trend_reports/youtube_trends_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"YouTube trends saved to trend_reports/youtube_trends_{timestamp}.html")
    
    def generate_instagram_report(self, output_format="json"):
        """
        Generate a report of Instagram trends.
        
        Args:
            output_format: Format of the output report (json, csv, or html)
        """
        if not self.instagram_trends:
            print("No Instagram trends data available. Run analyze_instagram_trends() first.")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save Instagram trends to file
        if output_format == "json":
            with open(f"trend_reports/instagram_trends_{timestamp}.json", "w", encoding="utf-8") as f:
                json.dump(self.instagram_trends, f, ensure_ascii=False, indent=2)
            print(f"Instagram trends saved to trend_reports/instagram_trends_{timestamp}.json")
        
        elif output_format == "csv":
            # Convert hashtags to DataFrame
            if self.instagram_trends.get("trending_hashtags"):
                hashtags_df = pd.DataFrame(list(self.instagram_trends["trending_hashtags"].items()), 
                                          columns=["hashtag", "count"])
                hashtags_df.to_csv(f"trend_reports/instagram_trending_hashtags_{timestamp}.csv", index=False)
            
            # Convert reels to DataFrame
            if self.instagram_trends.get("trending_reels"):
                reels_df = pd.DataFrame(self.instagram_trends["trending_reels"])
                reels_df.to_csv(f"trend_reports/instagram_trending_reels_{timestamp}.csv", index=False)
            
            print(f"Instagram trends saved to CSV files in trend_reports/ directory")
        
        elif output_format == "html":
            # Create a simple HTML report
            html_content = f"""
            <html>
            <head>
                <title>Instagram Trends Report - {timestamp}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2 {{ color: #e1306c; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    .reel-card {{ border: 1px solid #ddd; margin: 10px; padding: 10px; border-radius: 5px; }}
                    .reel-thumbnail {{ width: 120px; height: 120px; object-fit: cover; }}
                </style>
            </head>
            <body>
                <h1>Instagram Trends Report</h1>
                <p>Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                
                <h2>Top Trending Hashtags</h2>
                <table>
                    <tr><th>Hashtag</th><th>Count</th></tr>
            """
            
            # Add hashtags
            for hashtag, count in self.instagram_trends.get("trending_hashtags", {}).items():
                html_content += f"<tr><td>{hashtag}</td><td>{count}</td></tr>"
            
            html_content += """
                </table>
                
                <h2>Trending Reels</h2>
            """
            
            # Add reels (placeholder for now)
            html_content += """
                <p>Instagram API access required to display trending reels.</p>
            """
            
            html_content += """
            </body>
            </html>
            """
            
            with open(f"trend_reports/instagram_trends_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"Instagram trends saved to trend_reports/instagram_trends_{timestamp}.html")
    
    def visualize_youtube_trends(self):
        """
        Create visualizations of YouTube trends.
        """
        if not self.youtube_trends:
            print("No YouTube trends data available. Run analyze_youtube_trends() first.")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up the plotting style
        plt.style.use('ggplot')
        sns.set_palette("viridis")
        
        # Create directory for visualizations
        os.makedirs("trend_reports/visualizations", exist_ok=True)
        
        # 1. Visualize top hashtags
        plt.figure(figsize=(12, 6))
        hashtags = list(self.youtube_trends["trending_hashtags"].keys())[:15]
        counts = list(self.youtube_trends["trending_hashtags"].values())[:15]
        
        sns.barplot(x=counts, y=hashtags)
        plt.title("Top 15 Trending Hashtags on YouTube", fontsize=16)
        plt.xlabel("Frequency", fontsize=12)
        plt.ylabel("Hashtags", fontsize=12)
        plt.tight_layout()
        plt.savefig(f"trend_reports/visualizations/top_hashtags_{timestamp}.png")
        plt.close()
        
        # 2. Visualize top keywords
        plt.figure(figsize=(12, 6))
        keywords = list(self.youtube_trends["trending_keywords"].keys())[:15]
        counts = list(self.youtube_trends["trending_keywords"].values())[:15]
        
        sns.barplot(x=counts, y=keywords)
        plt.title("Top 15 Trending Keywords on YouTube", fontsize=16)
        plt.xlabel("Frequency", fontsize=12)
        plt.ylabel("Keywords", fontsize=12)
        plt.tight_layout()
        plt.savefig(f"trend_reports/visualizations/top_keywords_{timestamp}.png")
        plt.close()
        
        # 3. Create a word cloud of trending keywords
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            colormap='viridis',
            max_words=100
        ).generate_from_frequencies(self.youtube_trends["trending_keywords"])
        
        plt.figure(figsize=(16, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title("Trending Keywords Word Cloud", fontsize=20)
        plt.tight_layout()
        plt.savefig(f"trend_reports/visualizations/keywords_wordcloud_{timestamp}.png")
        plt.close()
        
        # 4. Visualize view counts of top trending videos
        plt.figure(figsize=(14, 7))
        top_videos = sorted(self.youtube_trends["trending_videos"], 
                           key=lambda x: x["viewCount"], 
                           reverse=True)[:10]
        
        if top_videos:
            video_titles = [video["title"][:30] + "..." if len(video["title"]) > 30 else video["title"] 
                           for video in top_videos]
            view_counts = [video["viewCount"] for video in top_videos]
            
            sns.barplot(x=view_counts, y=video_titles)
            plt.title("Top 10 Trending Videos by View Count", fontsize=16)
            plt.xlabel("View Count", fontsize=12)
            plt.ylabel("Video Title", fontsize=12)
            plt.ticklabel_format(style='plain', axis='x')
            plt.tight_layout()
            plt.savefig(f"trend_reports/visualizations/top_videos_views_{timestamp}.png")
            plt.close()
        
        # 5. Visualize engagement (likes/views ratio) of top trending videos
        plt.figure(figsize=(14, 7))
        if top_videos:
            for video in top_videos:
                video["engagement_ratio"] = (video["likeCount"] / video["viewCount"]) * 100 if video["viewCount"] > 0 else 0
            
            video_titles = [video["title"][:30] + "..." if len(video["title"]) > 30 else video["title"] 
                           for video in top_videos]
            engagement_ratios = [video["engagement_ratio"] for video in top_videos]
            
            sns.barplot(x=engagement_ratios, y=video_titles)
            plt.title("Top 10 Trending Videos by Engagement Rate (Likes/Views)", fontsize=16)
            plt.xlabel("Engagement Rate (%)", fontsize=12)
            plt.ylabel("Video Title", fontsize=12)
            plt.tight_layout()
            plt.savefig(f"trend_reports/visualizations/top_videos_engagement_{timestamp}.png")
            plt.close()
        
        print(f"Visualizations saved to trend_reports/visualizations/ directory")
    
    def visualize_instagram_trends(self):
        """
        Create visualizations of Instagram trends.
        """
        if not self.instagram_trends or not self.instagram_trends.get("trending_hashtags"):
            print("No Instagram trends data available. Run analyze_instagram_trends() first.")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up the plotting style
        plt.style.use('ggplot')
        sns.set_palette("magma")
        
        # Create directory for visualizations
        os.makedirs("trend_reports/visualizations", exist_ok=True)
        
        # Visualize top hashtags
        plt.figure(figsize=(12, 6))
        hashtags = list(self.instagram_trends["trending_hashtags"].keys())[:15]
        counts = list(self.instagram_trends["trending_hashtags"].values())[:15]
        
        if hashtags and counts:
            sns.barplot(x=counts, y=hashtags)
            plt.title("Top 15 Trending Hashtags on Instagram", fontsize=16)
            plt.xlabel("Frequency", fontsize=12)
            plt.ylabel("Hashtags", fontsize=12)
            plt.tight_layout()
            plt.savefig(f"trend_reports/visualizations/instagram_top_hashtags_{timestamp}.png")
            plt.close()
        
        # Create a word cloud of trending hashtags
        if self.instagram_trends["trending_hashtags"]:
            wordcloud = WordCloud(
                width=800, 
                height=400, 
                background_color='white',
                colormap='magma',
                max_words=100
            ).generate_from_frequencies(self.instagram_trends["trending_hashtags"])
            
            plt.figure(figsize=(16, 8))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title("Trending Instagram Hashtags Word Cloud", fontsize=20)
            plt.tight_layout()
            plt.savefig(f"trend_reports/visualizations/instagram_hashtags_wordcloud_{timestamp}.png")
            plt.close()
        
        print(f"Instagram visualizations saved to trend_reports/visualizations/ directory")

def main():
    parser = argparse.ArgumentParser(description="Social Media Trend Analyzer")
    parser.add_argument("--platform", choices=["youtube", "instagram", "all"], 
                        default="all", help="Platform to analyze")
    parser.add_argument("--region", default="IN", help="Region code (default: IN for India)")
    parser.add_argument("--language", default="ta", help="Language code (default: ta for Tamil)")
    parser.add_argument("--output", choices=["json", "csv", "html"], default="json", 
                        help="Output format for reports")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    
    args = parser.parse_args()
    
    # Create the trend analyzer
    analyzer = SocialMediaTrendAnalyzer(region_code=args.region, language=args.language)
    
    # Analyze trends based on the selected platform
    if args.platform == "youtube" or args.platform == "all":
        analyzer.analyze_youtube_trends()
        analyzer.generate_youtube_report(output_format=args.output)
        if args.visualize:
            analyzer.visualize_youtube_trends()
    
    if args.platform == "instagram" or args.platform == "all":
        analyzer.analyze_instagram_trends()
        analyzer.generate_instagram_report(output_format=args.output)
        if args.visualize:
            analyzer.visualize_instagram_trends()
    
    print("\nTrend analysis complete!")

if __name__ == "__main__":
    main()