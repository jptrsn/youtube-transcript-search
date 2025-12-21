import hmac
import hashlib
import secrets
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from backend.models import Channel, WebSubSubscription, Video
from backend.config import WEBSUB_CALLBACK_URL, WEBSUB_SECRET
import logging

logger = logging.getLogger(__name__)

WEBSUB_HUB_URL = "https://pubsubhubbub.appspot.com/subscribe"
YOUTUBE_FEED_TEMPLATE = "https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"


class WebSubService:
    def __init__(self, db: Session):
        self.db = db

    def subscribe_to_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Subscribe to a YouTube channel's WebSub feed.

        Args:
            channel_id: YouTube channel ID (e.g., UCxxx)

        Returns:
            Dictionary with subscription status
        """
        try:
            # Get channel from database
            channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()

            if not channel:
                raise ValueError(f"Channel {channel_id} not found in database")

            # Check if already subscribed
            existing_sub = self.db.query(WebSubSubscription).filter(
                WebSubSubscription.channel_id == channel.id
            ).first()

            if existing_sub and existing_sub.status == 'active':
                return {
                    'success': True,
                    'message': 'Already subscribed',
                    'subscription': self._subscription_to_dict(existing_sub)
                }

            # Generate tokens
            verify_token = secrets.token_urlsafe(32)
            secret = WEBSUB_SECRET
            topic_url = YOUTUBE_FEED_TEMPLATE.format(channel_id=channel_id)

            # Prepare subscription request
            data = {
                'hub.mode': 'subscribe',
                'hub.topic': topic_url,
                'hub.callback': WEBSUB_CALLBACK_URL,
                'hub.verify': 'async',
                'hub.verify_token': verify_token,
                'hub.secret': secret,
                'hub.lease_seconds': '432000'  # 5 days
            }

            # Send subscription request to hub
            logger.info(f"Subscribing to channel {channel_id} at hub")
            response = requests.post(WEBSUB_HUB_URL, data=data, timeout=10)
            response.raise_for_status()

            # Create or update subscription record
            if existing_sub:
                existing_sub.verify_token = verify_token
                existing_sub.secret = secret
                existing_sub.topic_url = topic_url
                existing_sub.callback_url = WEBSUB_CALLBACK_URL
                existing_sub.status = 'pending'
                existing_sub.last_error = None
                existing_sub.updated_at = datetime.utcnow()
                subscription = existing_sub
            else:
                subscription = WebSubSubscription(
                    channel_id=channel.id,
                    topic_url=topic_url,
                    callback_url=WEBSUB_CALLBACK_URL,
                    verify_token=verify_token,
                    secret=secret,
                    status='pending',
                    created_at=datetime.utcnow()
                )
                self.db.add(subscription)

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(f"Subscription request sent for channel {channel_id}, status: pending")

            return {
                'success': True,
                'message': 'Subscription request sent, pending verification',
                'subscription': self._subscription_to_dict(subscription)
            }

        except requests.RequestException as e:
            logger.error(f"Failed to subscribe to channel {channel_id}: {e}")
            if existing_sub:
                existing_sub.status = 'failed'
                existing_sub.last_error = str(e)
                self.db.commit()
            raise Exception(f"Failed to subscribe: {str(e)}")

    def unsubscribe_from_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Unsubscribe from a YouTube channel's WebSub feed.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with unsubscription status
        """
        try:
            # Get channel from database
            channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()

            if not channel:
                raise ValueError(f"Channel {channel_id} not found in database")

            # Get subscription
            subscription = self.db.query(WebSubSubscription).filter(
                WebSubSubscription.channel_id == channel.id
            ).first()

            if not subscription:
                return {
                    'success': True,
                    'message': 'Not subscribed to this channel'
                }

            # Prepare unsubscription request
            data = {
                'hub.mode': 'unsubscribe',
                'hub.topic': subscription.topic_url,
                'hub.callback': WEBSUB_CALLBACK_URL,
                'hub.verify': 'async',
                'hub.verify_token': subscription.verify_token
            }

            # Send unsubscription request to hub
            logger.info(f"Unsubscribing from channel {channel_id}")
            response = requests.post(WEBSUB_HUB_URL, data=data, timeout=10)
            response.raise_for_status()

            # Delete subscription record
            self.db.delete(subscription)
            self.db.commit()

            logger.info(f"Unsubscribed from channel {channel_id}")

            return {
                'success': True,
                'message': 'Unsubscribed successfully'
            }

        except requests.RequestException as e:
            logger.error(f"Failed to unsubscribe from channel {channel_id}: {e}")
            raise Exception(f"Failed to unsubscribe: {str(e)}")

    def verify_subscription(self, mode: str, topic: str, challenge: str, verify_token: str,
                          lease_seconds: Optional[int] = None) -> tuple[bool, Optional[str]]:
        """
        Verify a subscription request from the WebSub hub.

        Args:
            mode: 'subscribe' or 'unsubscribe'
            topic: The topic URL being verified
            challenge: The challenge string from the hub
            verify_token: The verify token from the hub
            lease_seconds: Subscription lease duration (for subscribe only)

        Returns:
            Tuple of (success: bool, challenge: str or None)
        """
        try:
            # Find subscription by topic and verify_token
            subscription = self.db.query(WebSubSubscription).filter(
                WebSubSubscription.topic_url == topic,
                WebSubSubscription.verify_token == verify_token
            ).first()

            if not subscription:
                logger.warning(f"Verification failed: No matching subscription for topic {topic}")
                return False, None

            if mode == 'subscribe':
                # Update subscription as active
                subscription.status = 'active'
                subscription.subscribed_at = datetime.utcnow()
                subscription.lease_seconds = lease_seconds
                if lease_seconds:
                    subscription.expires_at = datetime.utcnow() + timedelta(seconds=lease_seconds)
                subscription.updated_at = datetime.utcnow()
                self.db.commit()

                logger.info(f"Subscription verified and activated for channel {subscription.channel.channel_id}")

            elif mode == 'unsubscribe':
                # Subscription will be deleted separately
                logger.info(f"Unsubscription verified for channel {subscription.channel.channel_id}")

            return True, challenge

        except Exception as e:
            logger.error(f"Error during verification: {e}")
            return False, None

    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify HMAC signature from WebSub hub.

        Args:
            payload: Raw request body
            signature: Signature from X-Hub-Signature header
            secret: Shared secret

        Returns:
            True if signature is valid
        """
        if not signature:
            return False

        try:
            # Signature format: sha1=<hex_digest> or sha256=<hex_digest>
            algorithm, expected_signature = signature.split('=', 1)

            if algorithm == 'sha1':
                hash_func = hashlib.sha1
            elif algorithm == 'sha256':
                hash_func = hashlib.sha256
            else:
                logger.warning(f"Unknown signature algorithm: {algorithm}")
                return False

            # Compute HMAC
            computed_hmac = hmac.new(
                secret.encode('utf-8'),
                payload,
                hash_func
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(computed_hmac, expected_signature)

        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False

    def process_notification(self, payload: bytes, signature: Optional[str] = None) -> Dict[str, Any]:
      """
      Process a WebSub notification (video upload/update).

      Args:
          payload: Raw Atom feed XML
          signature: Optional HMAC signature for verification

      Returns:
          Dictionary with processing results
      """
      try:
          # Parse Atom feed
          feed = feedparser.parse(payload)

          if not feed.entries:
              logger.warning("Received notification with no entries")
              return {'success': False, 'message': 'No entries in feed'}

          # Get the entry (should be only one)
          entry = feed.entries[0]

          # Extract data from Atom feed
          video_id = entry.get('yt_videoid')
          channel_id = entry.get('yt_channelid')

          if not video_id or not channel_id:
              logger.warning("Missing video_id or channel_id in notification")
              return {'success': False, 'message': 'Missing required fields'}

          logger.info(f"Received notification for video {video_id} on channel {channel_id}")

          # Get channel from database
          channel = self.db.query(Channel).filter(
              Channel.channel_id == channel_id
          ).first()

          if not channel:
              logger.warning(f"Channel {channel_id} not found in database")
              return {'success': False, 'message': 'Channel not in database'}

          # Update subscription's last notification time
          subscription = self.db.query(WebSubSubscription).filter(
              WebSubSubscription.channel_id == channel.id
          ).first()

          if subscription:
              subscription.last_notification_at = datetime.utcnow()
              self.db.commit()

          # Check if video already exists
          existing_video = self.db.query(Video).filter(
              Video.video_id == video_id
          ).first()

          if existing_video:
              logger.info(f"Video {video_id} already exists in database")
              return {
                  'success': True,
                  'message': 'Video already exists',
                  'video_id': video_id,
                  'action': 'exists'
              }

          # Fetch full video details from YouTube API
          from backend.youtube_client import YouTubeClient
          yt_client = YouTubeClient()

          try:
              video_details = yt_client.get_video_details(video_id)

              if not video_details:
                  logger.error(f"Could not fetch video details for {video_id}")
                  # Fall back to basic info from notification
                  video_details = {
                      'video_id': video_id,
                      'title': entry.get('title', 'Untitled'),
                      'description': '',
                      'published_at': entry.get('published', datetime.utcnow().isoformat()),
                      'thumbnail_url': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                  }
          except Exception as e:
              logger.error(f"Error fetching video details for {video_id}: {e}")
              # Fall back to basic info from notification
              video_details = {
                  'video_id': video_id,
                  'title': entry.get('title', 'Untitled'),
                  'description': '',
                  'published_at': entry.get('published', datetime.utcnow().isoformat()),
                  'thumbnail_url': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
              }

          # Parse published date
          published_at = None
          if video_details.get('published_at'):
              try:
                  published_at = datetime.fromisoformat(video_details['published_at'].replace('Z', '+00:00'))
              except:
                  published_at = datetime.utcnow()

          # Create new video entry
          new_video = Video(
              channel_id=channel.id,
              video_id=video_id,
              title=video_details.get('title', 'Untitled'),
              description=video_details.get('description', ''),
              published_at=published_at or datetime.utcnow(),
              thumbnail_url=video_details.get('thumbnail_url', f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
              created_at=datetime.utcnow()
          )

          self.db.add(new_video)
          self.db.commit()

          logger.info(f"Created new video {video_id} for channel {channel_id}")

          return {
              'success': True,
              'message': 'New video added',
              'video_id': video_id,
              'title': new_video.title,
              'action': 'created'
          }

      except Exception as e:
          logger.error(f"Error processing notification: {e}", exc_info=True)
          return {'success': False, 'message': f'Error: {str(e)}'}

    def renew_expiring_subscriptions(self, hours_before_expiry: int = 24) -> Dict[str, Any]:
        """
        Renew subscriptions that are expiring soon.

        Args:
            hours_before_expiry: Renew subscriptions expiring within this many hours

        Returns:
            Dictionary with renewal statistics
        """
        try:
            threshold = datetime.utcnow() + timedelta(hours=hours_before_expiry)

            # Find subscriptions expiring soon
            expiring_subs = self.db.query(WebSubSubscription).filter(
                WebSubSubscription.status == 'active',
                WebSubSubscription.expires_at <= threshold
            ).all()

            renewed = 0
            failed = 0

            for sub in expiring_subs:
                try:
                    channel = sub.channel
                    logger.info(f"Renewing subscription for channel {channel.channel_id}")

                    # Resubscribe (which will update the expiry)
                    self.subscribe_to_channel(channel.channel_id)
                    renewed += 1

                except Exception as e:
                    logger.error(f"Failed to renew subscription for channel {channel.channel_id}: {e}")
                    failed += 1

            return {
                'success': True,
                'total_expiring': len(expiring_subs),
                'renewed': renewed,
                'failed': failed
            }

        except Exception as e:
            logger.error(f"Error renewing subscriptions: {e}")
            return {'success': False, 'message': str(e)}

    def get_subscription_status(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription status for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with subscription info or None
        """
        channel = self.db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

        if not channel:
            return None

        subscription = self.db.query(WebSubSubscription).filter(
            WebSubSubscription.channel_id == channel.id
        ).first()

        if not subscription:
            return None

        return self._subscription_to_dict(subscription)

    def list_all_subscriptions(self) -> list[Dict[str, Any]]:
        """
        List all WebSub subscriptions.

        Returns:
            List of subscription dictionaries
        """
        subscriptions = self.db.query(WebSubSubscription).all()
        return [self._subscription_to_dict(sub) for sub in subscriptions]

    def _subscription_to_dict(self, subscription: WebSubSubscription) -> Dict[str, Any]:
        """Convert subscription model to dictionary."""
        return {
            'id': subscription.id,
            'channel_id': subscription.channel.channel_id,
            'channel_name': subscription.channel.channel_name,
            'status': subscription.status,
            'subscribed_at': subscription.subscribed_at.isoformat() if subscription.subscribed_at else None,
            'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
            'lease_seconds': subscription.lease_seconds,
            'last_notification_at': subscription.last_notification_at.isoformat() if subscription.last_notification_at else None,
            'last_error': subscription.last_error
        }