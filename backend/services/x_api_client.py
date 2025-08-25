import os
from typing import List

import requests
from models.schemas.x_api import Tweet, UserInfo


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
            followers=data.get("followers", 0),
            following=data.get("following", 0),
        )

    def get_last_tweets(self, handle: str, num_tweets: int = 20) -> List[Tweet]:
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
        all_tweets = []
        cursor = ""

        # Paginate through results to get requested number of tweets
        while len(all_tweets) < num_tweets:
            url = f"{self.base_url}/twitter/user/last_tweets"
            params = {
                "userName": handle,
                "cursor": cursor,
                "includeReplies": True,
            }

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            result = response.json()
            if result.get("status") != "success":
                raise Exception(f"API error: {result.get('message', 'Unknown error')}")

            tweets = result.get("tweets", [])
            if not tweets:
                break

            for tweet_data in tweets:
                if len(all_tweets) >= num_tweets:
                    break

                all_tweets.append(Tweet.from_api_response(tweet_data))

            # Check if there are more pages
            if not result.get("has_next_page", False):
                break

            cursor = result.get("next_cursor", "")
            if not cursor:
                break

        return all_tweets[:num_tweets]

    def get_tweet_by_ids(self, tweet_ids: List[str]) -> List[Tweet]:
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
        return [Tweet.from_api_response(tweet_data) for tweet_data in tweets]
