#!/usr/bin/env python3
"""
Bluesky Post Deleter
A script to selectively delete old posts from a Bluesky account based on age and engagement.
"""

import getpass
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from atproto import Client, models


def setup_logging(dry_run=False):
    """Set up logging to file and console."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    mode = "dry-run" if dry_run else "deletion"
    log_file = logs_dir / f"{mode}-{timestamp}.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def get_credentials():
    """Prompt user for Bluesky credentials."""
    print("\n=== Bluesky Authentication ===")
    print("Note: Use an app password, not your main account password!")
    print("Generate one at: https://bsky.app/settings/app-passwords\n")

    username = input("Enter your Bluesky username (e.g., user.bsky.social): ").strip()

    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)

    password = input("Enter your app password (visible): ").strip()

    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    return username, password


def get_parameters():
    """Prompt user for deletion parameters."""
    print("\n=== Deletion Parameters ===")

    # Get days threshold
    while True:
        try:
            days = input("Delete posts older than how many days? (e.g., 30): ").strip()
            days = int(days)
            if days < 0:
                print("Error: Days must be a positive number.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Get minimum likes threshold
    while True:
        try:
            min_likes = input("Keep posts with at least this many likes (0 = ignore likes): ").strip()
            min_likes = int(min_likes)
            if min_likes < 0:
                print("Error: Likes must be a positive number or 0.")
                continue
            if min_likes == 0:
                print("  → Likes will be ignored (posts won't be protected by likes)")
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Get minimum reposts threshold
    while True:
        try:
            min_reposts = input("Keep posts with at least this many reposts (0 = ignore reposts): ").strip()
            min_reposts = int(min_reposts)
            if min_reposts < 0:
                print("Error: Reposts must be a positive number or 0.")
                continue
            if min_reposts == 0:
                print("  → Reposts will be ignored (posts won't be protected by reposts)")
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Get keep images preference
    while True:
        keep_images_input = input("\nKeep posts that have images? [Y/n]: ").strip().lower()
        if keep_images_input in ['', 'y', 'yes']:
            keep_images = True
            print("  → Posts with images will be kept")
            break
        elif keep_images_input in ['n', 'no']:
            keep_images = False
            print("  → Posts with images will NOT be protected")
            break
        else:
            print("Error: Please enter 'y' or 'n'.")

    # Get dry-run mode
    while True:
        dry_run_input = input("\nDry-run mode? (preview only, no deletions) [Y/n]: ").strip().lower()
        if dry_run_input in ['', 'y', 'yes']:
            dry_run = True
            break
        elif dry_run_input in ['n', 'no']:
            dry_run = False
            break
        else:
            print("Error: Please enter 'y' or 'n'.")

    # Show summary
    print("\n" + "=" * 80)
    print("DELETION CRITERIA SUMMARY:")
    print(f"  • Posts older than {days} days will be considered for deletion")
    if min_likes > 0 or min_reposts > 0 or keep_images:
        print("  • Posts will be KEPT if they have:")
        if min_likes > 0:
            print(f"    - At least {min_likes} likes")
        if min_reposts > 0:
            print(f"    - At least {min_reposts} reposts")
        if keep_images:
            print(f"    - Images attached")
    else:
        print("  • No engagement protection (all old posts will be deleted)")
    print("=" * 80)

    return days, min_likes, min_reposts, keep_images, dry_run


def authenticate(username, password):
    """Authenticate with Bluesky API."""
    print("\nAuthenticating...")
    try:
        client = Client()
        client.login(username, password)
        print(f"✓ Successfully authenticated as {username}")
        return client
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}\n")
        print("Common issues:")
        print("  1. Make sure you're using an APP PASSWORD, not your main account password")
        print("     Generate one at: https://bsky.app/settings/app-passwords")
        print("  2. Verify your username is correct (e.g., user.bsky.social)")
        print("  3. Check for typos in your username or password")
        print("  4. Ensure the app password hasn't been revoked")
        sys.exit(1)


def fetch_posts(client, logger):
    """Fetch all posts from the authenticated user."""
    print("\nFetching your posts...")
    logger.info("Starting to fetch user posts")

    posts = []
    cursor = None

    try:
        while True:
            # Fetch a batch of posts
            response = client.app.bsky.feed.get_author_feed(
                params={'actor': client.me.did, 'limit': 100, 'cursor': cursor}
            )

            # Extract posts from feed
            for feed_item in response.feed:
                if feed_item.post.author.did == client.me.did:  # Only our own posts
                    posts.append(feed_item.post)

            # Check if there are more posts
            if not response.cursor:
                break
            cursor = response.cursor

        print(f"✓ Fetched {len(posts)} posts")
        logger.info(f"Fetched {len(posts)} total posts")
        return posts

    except Exception as e:
        print(f"✗ Error fetching posts: {e}")
        logger.error(f"Error fetching posts: {e}")
        sys.exit(1)


def filter_posts(posts, days_threshold, min_likes, min_reposts, keep_images, logger):
    """Filter posts to determine which should be deleted."""
    likes_criteria = f"likes >= {min_likes}" if min_likes > 0 else "likes ignored"
    reposts_criteria = f"reposts >= {min_reposts}" if min_reposts > 0 else "reposts ignored"
    images_criteria = "keep posts with images" if keep_images else "images not protected"
    logger.info(f"Filtering criteria: age > {days_threshold} days, {likes_criteria}, {reposts_criteria}, {images_criteria}")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    posts_to_delete = []
    posts_to_keep = []

    for post in posts:
        # Parse post creation date
        try:
            created_at = datetime.fromisoformat(post.record.created_at.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Could not parse date for post {post.uri}: {e}")
            continue

        # Get engagement metrics
        like_count = post.like_count or 0
        repost_count = post.repost_count or 0

        # Check if post has images
        has_images = False
        if hasattr(post.record, 'embed') and post.record.embed:
            # Check for images in embed (could be images or external links with images)
            embed_type = post.record.embed.py_type if hasattr(post.record.embed, 'py_type') else str(type(post.record.embed))
            if 'images' in embed_type.lower() or (hasattr(post.record.embed, 'images') and post.record.embed.images):
                has_images = True

        # Calculate age
        age_days = (datetime.now(timezone.utc) - created_at).days

        # Filtering logic: Keep if ANY of these conditions are true
        # Delete if ALL conditions are false (old AND low engagement)
        # Note: 0 threshold means "ignore this criterion"
        keep_reasons = []

        if age_days <= days_threshold:
            keep_reasons.append("recent")
        if min_likes > 0 and like_count >= min_likes:
            keep_reasons.append(f"{like_count} likes")
        if min_reposts > 0 and repost_count >= min_reposts:
            keep_reasons.append(f"{repost_count} reposts")
        if keep_images and has_images:
            keep_reasons.append("has images")

        if keep_reasons:
            posts_to_keep.append({
                'post': post,
                'age_days': age_days,
                'likes': like_count,
                'reposts': repost_count,
                'reasons': keep_reasons
            })
        else:
            posts_to_delete.append({
                'post': post,
                'age_days': age_days,
                'likes': like_count,
                'reposts': repost_count
            })

    logger.info(f"Posts to keep: {len(posts_to_keep)}, Posts to delete: {len(posts_to_delete)}")

    return posts_to_delete, posts_to_keep


def preview_deletions(posts_to_delete, logger):
    """Show a preview of posts that will be deleted."""
    print(f"\n=== Deletion Preview ===")
    print(f"Total posts to delete: {len(posts_to_delete)}")

    if len(posts_to_delete) == 0:
        print("No posts match the deletion criteria!")
        return

    # Show first 5 posts as sample
    sample_size = min(5, len(posts_to_delete))
    print(f"\nShowing {sample_size} sample posts:")
    print("-" * 80)

    for i, item in enumerate(posts_to_delete[:sample_size], 1):
        post = item['post']
        text = post.record.text[:100] + "..." if len(post.record.text) > 100 else post.record.text

        print(f"\n{i}. Age: {item['age_days']} days | Likes: {item['likes']} | Reposts: {item['reposts']}")
        print(f"   Text: {text}")
        print(f"   URI: {post.uri}")

        logger.info(f"Will delete: {post.uri} | Age: {item['age_days']}d | Likes: {item['likes']} | Reposts: {item['reposts']}")

    if len(posts_to_delete) > sample_size:
        print(f"\n... and {len(posts_to_delete) - sample_size} more posts")

    print("-" * 80)


def confirm_deletion():
    """Ask user to confirm deletion."""
    print("\n⚠️  WARNING: This action is IRREVERSIBLE! ⚠️")
    print("Are you absolutely sure you want to delete these posts?")

    while True:
        confirm = input("Type 'DELETE' (in all caps) to confirm: ").strip()
        if confirm == 'DELETE':
            return True
        elif confirm.lower() in ['n', 'no', 'cancel', 'exit']:
            return False
        else:
            print("Invalid input. Type 'DELETE' to confirm or 'no' to cancel.")


def delete_posts(client, posts_to_delete, logger, dry_run=False):
    """Delete the selected posts."""
    if dry_run:
        print("\n✓ Dry-run mode: No posts were actually deleted.")
        logger.info("Dry-run completed - no posts deleted")
        return

    print("\nDeleting posts...")
    print("(Rate limiting: ~0.5s delay between deletions)")
    deleted_count = 0
    failed_count = 0

    for i, item in enumerate(posts_to_delete, 1):
        post = item['post']

        # Try deletion with retry logic for rate limits
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                # Parse the post URI: at://did:plc:abc123/app.bsky.feed.post/record_key
                uri_parts = post.uri.split('/')
                record_key = uri_parts[-1]  # Get the record key (rkey)

                # Delete the post using the correct API method
                client.com.atproto.repo.delete_record(
                    data={
                        'repo': client.me.did,
                        'collection': 'app.bsky.feed.post',
                        'rkey': record_key
                    }
                )
                deleted_count += 1

                # Log the full text of the deleted post
                full_text = post.record.text
                logger.info(f"Deleted {i}/{len(posts_to_delete)}: {post.uri} | {full_text}")

                # Progress indicator
                if i % 10 == 0 or i == len(posts_to_delete):
                    print(f"Progress: {i}/{len(posts_to_delete)} posts deleted")

                # Success - break out of retry loop
                break

            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit error
                if 'rate' in error_str.lower() or '429' in error_str:
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit for {post.uri}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        print(f"⚠ Rate limit hit, waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        failed_count += 1
                        full_text = post.record.text
                        logger.error(f"Rate limit exceeded for {post.uri} after {max_retries} attempts | {full_text}")
                        print(f"✗ Failed to delete post {i} after {max_retries} attempts (rate limit)")
                        break
                else:
                    # Non-rate-limit error
                    failed_count += 1
                    full_text = post.record.text
                    logger.error(f"Failed to delete {post.uri}: {e} | {full_text}")
                    print(f"✗ Failed to delete post {i}: {e}")
                    break

        # Rate limiting: small delay between deletions to avoid hitting limits
        if i < len(posts_to_delete):  # Don't delay after the last post
            time.sleep(0.5)

    print(f"\n✓ Deletion complete!")
    print(f"  Successfully deleted: {deleted_count}")
    if failed_count > 0:
        print(f"  Failed: {failed_count}")

    logger.info(f"Deletion complete: {deleted_count} deleted, {failed_count} failed")


def main():
    """Main function."""
    print("=" * 80)
    print("Bluesky Post Deleter")
    print("Selectively delete old posts based on age and engagement")
    print("=" * 80)

    # Get credentials
    username, password = get_credentials()

    # Get parameters
    days, min_likes, min_reposts, keep_images, dry_run = get_parameters()

    # Set up logging
    logger = setup_logging(dry_run)
    logger.info("=" * 80)
    logger.info("Starting Bluesky Post Deleter")
    logger.info(f"User: {username}")
    logger.info(f"Parameters: days={days}, min_likes={min_likes}, min_reposts={min_reposts}, keep_images={keep_images}, dry_run={dry_run}")

    # Authenticate
    client = authenticate(username, password)

    # Fetch posts
    posts = fetch_posts(client, logger)

    if len(posts) == 0:
        print("No posts found!")
        logger.info("No posts found for this account")
        return

    # Filter posts
    posts_to_delete, posts_to_keep = filter_posts(posts, days, min_likes, min_reposts, keep_images, logger)

    # Preview deletions
    preview_deletions(posts_to_delete, logger)

    if len(posts_to_delete) == 0:
        return

    # Confirm deletion (if not dry-run)
    if not dry_run:
        print("\n" + "=" * 80)
        proceed = input("\nYou chose to skip dry-run mode. Proceed with ACTUAL DELETION? [y/N]: ").strip().lower()

        if proceed not in ['y', 'yes']:
            print("\n✓ Deletion cancelled.")
            logger.info("User cancelled deletion")
            return

        if not confirm_deletion():
            print("\n✓ Deletion cancelled.")
            logger.info("User cancelled deletion")
            return

    # Delete posts
    delete_posts(client, posts_to_delete, logger, dry_run)

    # If it was a dry-run, offer to proceed with actual deletion
    if dry_run and len(posts_to_delete) > 0:
        print("\n" + "=" * 80)
        proceed = input("\nProceed with actual deletion using these same settings? [y/N]: ").strip().lower()

        if proceed in ['y', 'yes']:
            # Set up new logger for actual deletion
            logger = setup_logging(dry_run=False)
            logger.info("=" * 80)
            logger.info("Proceeding with actual deletion after dry-run")
            logger.info(f"User: {username}")
            logger.info(f"Parameters: days={days}, min_likes={min_likes}, min_reposts={min_reposts}, keep_images={keep_images}")

            # Confirm deletion
            if not confirm_deletion():
                print("\n✓ Deletion cancelled.")
                logger.info("User cancelled deletion")
            else:
                # Perform actual deletion
                delete_posts(client, posts_to_delete, logger, dry_run=False)

            logger.info("=" * 80)
        else:
            print("\n✓ Actual deletion skipped.")

    print(f"\n✓ Log saved to: logs/")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
