import os
from typing import List

import requests

from models.schemas.x_api import TweetInfo, UserInfo


class XApiClient:
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.base_url = "https://api.twitterapi.io"
        self.headers = {"X-API-Key": self.api_key}

    def get_user_info(self, handle: str) -> UserInfo:
        """Get user information by handle/username.

        Args:
            handle: Twitter username (without @)

        Returns:
            UserInfo model with user details

        Raises:
            requests.HTTPError: If API request fails
            Exception: If API returns error status
        """
        url = f"{self.base_url}/twitter/user/info"
        params = {"userName": handle}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        result = response.json()
        if result.get("status") != "success":
            raise Exception(f"API error: {result.get('message', 'Unknown error')}")

        data = result.get("data", {})

        # Map API response fields to our model
        return UserInfo(
            username=data.get("userName"),
            name=data.get("name"),
            description=data.get("description"),
            location=data.get("location"),
            num_followers=data.get("followers", 0),
            num_following=data.get("following", 0),
        )

    def get_last_tweets(self, handle: str, num_tweets: int = 20) -> List[TweetInfo]:
        """Get the last tweets from a user.

        Args:
            handle: Twitter username (without @)
            num_tweets: Number of tweets to retrieve (default 20)

        Returns:
            List of Tweet models

        Raises:
            requests.HTTPError: If API request fails
            Exception: If API returns error status
        """

        all_tweets: List[TweetInfo] = []
        cursor = ""
        page_count = 0

        # Paginate through results to get requested number of tweets
        while len(all_tweets) < num_tweets:
            page_count += 1
            url = f"{self.base_url}/twitter/user/last_tweets"
            # Start with minimal params like the working curl command
            params = {
                "userName": handle,
                "cursor": cursor,
                "includeReplies": False,
            }
            # Only add cursor if we have one (for pagination)
            if cursor:
                params["cursor"] = cursor

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            result = response.json()

            if result.get("status") != "success":
                raise Exception(f"API error: {result.get('message', 'Unknown error')}")

            # Check if tweets are in data.tweets (nested) or directly in tweets
            if "data" in result and "tweets" in result["data"]:
                tweets = result["data"]["tweets"]
            else:
                tweets = result.get("tweets", [])

            if not tweets:
                break

            for tweet_data in tweets:
                if len(all_tweets) >= num_tweets:
                    break

                all_tweets.append(TweetInfo.from_api_response(tweet_data))

            # Check if there are more pages
            has_next = result.get("has_next_page", False)

            if not has_next:
                break

            cursor = result.get("next_cursor", "")
            if not cursor:
                break

        return all_tweets[:num_tweets]

    def get_tweet_by_ids(self, tweet_ids: List[str]) -> List[TweetInfo]:
        """Get tweets by their IDs.

        Args:
            tweet_ids: List of tweet IDs to retrieve

        Returns:
            List of Tweet models

        Raises:
            requests.HTTPError: If API request fails
            Exception: If API returns error status
        """
        if not tweet_ids:
            return []

        url = f"{self.base_url}/twitter/tweets"
        params = {"tweet_ids": ",".join(tweet_ids)}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        result = response.json()
        if result.get("status") != "success":
            raise Exception(f"API error: {result.get('message', 'Unknown error')}")

        tweets = result.get("tweets", [])
        return [TweetInfo.from_api_response(tweet_data) for tweet_data in tweets]
