import requests
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class IGAPIError(Exception):
    """Custom exception for IG API errors"""
    pass

class IGClient:
    def __init__(self, api_key, username, password):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.base_url = "https://demo-api.ig.com/gateway/deal"
        self.session = requests.Session()
        self.account_id = None
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None

    def login(self):
        """Authenticate with the IG API"""
        headers = {
            "X-IG-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json; charset=UTF-8",
            "Version": "3"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/session",
                headers=headers,
                json={"identifier": self.username, "password": self.password}
            )

            if response.status_code == 200:
                response_data = response.json()
                self.account_id = response_data.get('accountId')
                oauth_token = response_data.get('oauthToken', {})
                self.access_token = oauth_token.get('access_token')
                self.refresh_token = oauth_token.get('refresh_token')
                expires_in = int(oauth_token.get('expires_in', 0))
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                logger.info("Successfully authenticated with IG API")
                return True
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid credentials")
                raise IGAPIError("Invalid credentials provided")
            else:
                logger.error(f"Authentication failed with status code: {response.status_code}")
                raise IGAPIError("Failed to authenticate with IG API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during authentication: {str(e)}")
            raise IGAPIError("Network error occurred while connecting to IG API")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise IGAPIError("An unexpected error occurred during authentication")

    def refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False

        headers = {
            "X-IG-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json; charset=UTF-8",
            "Version": "1"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/session/refresh-token",
                headers=headers,
                json={"refresh_token": self.refresh_token}
            )

            if response.status_code == 200:
                response_data = response.json()
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
                expires_in = int(response_data.get('expires_in', 0))
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                logger.info("Successfully refreshed access token")
                return True
            else:
                logger.error(f"Failed to refresh token: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False

    def ensure_token_valid(self):
        """Ensure the access token is valid, refresh if needed"""
        if not self.token_expiry or not self.access_token:
            raise IGAPIError("No valid session - needs new login")

        # Refresh if token expires in less than 15 seconds
        if datetime.now() + timedelta(seconds=15) >= self.token_expiry:
            logger.info("Token expiring soon, attempting refresh...")
            success = self.refresh_access_token()
            if not success:
                self.access_token = None
                self.refresh_token = None
                self.token_expiry = None
                raise IGAPIError("Session expired - needs new login")
            
    def get_positions(self):
        """Fetch current positions"""
        try:
            self.ensure_token_valid()
            if not self.access_token:
                raise IGAPIError("Not authenticated - please log in first")

            headers = {
                "X-IG-API-KEY": self.api_key,
                "Authorization": f"Bearer {self.access_token}",
                "IG-ACCOUNT-ID": self.account_id,
                "Content-Type": "application/json",
                "Accept": "application/json; charset=UTF-8",
                "Version": "1"
            }

            response = self.session.get(
                f"{self.base_url}/positions",
                headers=headers
            )

            if response.status_code == 200:
                logger.info("Successfully fetched positions")
                return response.json()
            elif response.status_code == 401:
                # Clear tokens and raise error
                self.access_token = None
                self.refresh_token = None
                self.token_expiry = None
                raise IGAPIError("Session expired - needs new login")
            else:
                logger.error(f"Failed to fetch positions: HTTP {response.status_code}")
                raise IGAPIError("Failed to fetch positions from IG API")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching positions: {str(e)}")
            raise IGAPIError("Network error occurred while fetching positions")
        except Exception as e:
            logger.error(f"Unexpected error while fetching positions: {str(e)}")
            raise IGAPIError("An unexpected error occurred while fetching positions")
        
    def get_market_details(self, epic):
        """
        Fetch details for a specific market by its epic code

        Args:
            epic: The epic identifier for the market

        Returns:
            dict: Market details including current price, underlying info, etc.
        """
        self.ensure_token_valid()
        if not self.access_token:
            logger.error("Attempted to fetch market details without being logged in")
            raise IGAPIError("Not authenticated - please log in first")

        headers = {
            "X-IG-API-KEY": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "IG-ACCOUNT-ID": self.account_id,
            "Content-Type": "application/json",
            "Accept": "application/json; charset=UTF-8",
            "Version": "3"
        }

        try:
            response = self.session.get(
                f"{self.base_url}/markets/{epic}",
                headers=headers
            )

            if response.status_code == 200:
                logger.info("Successfully fetched market details")
                return response.json()
            elif response.status_code == 401:
                logger.error("Token expired or invalid")
                raise IGAPIError("Session expired - please log in again")
            else:
                logger.error(f"Failed to fetch market details: HTTP {response.status_code}")
                raise IGAPIError(f"Failed to fetch market details from IG API: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching market details: {str(e)}")
            raise IGAPIError("Network error occurred while fetching market details")
        except Exception as e:
            logger.error(f"Unexpected error while fetching market details: {str(e)}")
            raise IGAPIError("An unexpected error occurred while fetching market details")