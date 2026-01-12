# Bluesky Post Deleter

A Python script to selectively delete old posts from your Bluesky account based on age and engagement metrics.

## Features

- **Age-based deletion**: Delete posts older than a specified number of days
- **Engagement protection**: Automatically preserve posts with high likes or reposts
- **Flexible thresholds**: Keep posts if they have enough likes OR reposts (configurable)
- **Dry-run mode**: Preview what would be deleted before making any changes
- **Seamless workflow**: After dry-run, proceed directly to deletion without re-entering details
- **Comprehensive logging**: Track all deletions with timestamps and post details
- **Interactive prompts**: Easy-to-use command-line interface
- **Multi-account support**: No stored credentials - works with any Bluesky account

## How It Works

The script keeps a post if **ANY** of the following conditions are true:
- Post is newer than the age threshold
- Post has at least the minimum number of likes (if likes threshold > 0)
- Post has at least the minimum number of reposts (if reposts threshold > 0)

Posts are only deleted if they fail **ALL** conditions (old AND low engagement).

### Disabling Engagement Protection

You can disable likes or reposts protection by entering `0`:
- Enter `0` for likes → Only age and reposts matter
- Enter `0` for reposts → Only age and likes matter
- Enter `0` for both → Pure time-based deletion (all old posts deleted regardless of engagement)

## Installation

### Prerequisites

- Python 3.8 or higher
- A Bluesky account
- An app password (see setup instructions below)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/bsky-deleter.git
cd bsky-deleter
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Generate an App Password

**Important**: Never use your main Bluesky password with this script!

1. Go to your Bluesky settings: https://bsky.app/settings/app-passwords
2. Click "Add App Password"
3. Give it a name (e.g., "Post Deleter")
4. Copy the generated password
5. Use this app password when running the script

## Usage

Run the script:
```bash
python delete_posts.py
```

The script will interactively prompt you for:
1. **Username**: Your Bluesky handle (e.g., `user.bsky.social`)
2. **App Password**: The app password you generated (input will be visible for easy pasting)
3. **Days threshold**: Delete posts older than this many days (e.g., `30`)
4. **Minimum likes**: Keep posts with at least this many likes (e.g., `5`, or `0` to ignore)
5. **Minimum reposts**: Keep posts with at least this many reposts (e.g., `2`, or `0` to ignore)
6. **Dry-run mode**: Choose whether to preview only or actually delete

### Example Session

```
=== Bluesky Authentication ===
Note: Use an app password, not your main account password!
Generate one at: https://bsky.app/settings/app-passwords

Enter your Bluesky username (e.g., user.bsky.social): alice.bsky.social
Enter your app password (visible): abcd-efgh-ijkl-mnop

=== Deletion Parameters ===
Delete posts older than how many days? (e.g., 30): 90
Keep posts with at least this many likes (0 = ignore likes): 10
Keep posts with at least this many reposts (0 = ignore reposts): 0
  → Reposts will be ignored (posts won't be protected by reposts)

Dry-run mode? (preview only, no deletions) [Y/n]: y

================================================================================
DELETION CRITERIA SUMMARY:
  • Posts older than 90 days will be considered for deletion
  • Posts will be KEPT if they have:
    - At least 10 likes
================================================================================

Authenticating...
✓ Successfully authenticated as alice.bsky.social

Fetching your posts...
✓ Fetched 247 posts

=== Deletion Preview ===
Total posts to delete: 83

Showing 5 sample posts:
--------------------------------------------------------------------------------

1. Age: 125 days | Likes: 2 | Reposts: 0
   Text: Just setting up my Bluesky account!
   URI: at://did:plc:example123/app.bsky.feed.post/3k7example

...

✓ Dry-run mode: No posts were actually deleted.

================================================================================

Proceed with actual deletion using these same settings? [y/N]: y

⚠️  WARNING: This action is IRREVERSIBLE! ⚠️
Are you absolutely sure you want to delete these posts?
Type 'DELETE' (in all caps) to confirm: DELETE

Deleting posts...
Progress: 10/83 posts deleted
Progress: 20/83 posts deleted
...
Progress: 83/83 posts deleted

✓ Deletion complete!
  Successfully deleted: 83

✓ Log saved to: logs/
```

> **Tip**: After a dry-run preview, you'll be offered the option to proceed with actual deletion without re-entering your credentials and parameters.

## Safety Features

- **App password required**: Protects your main account credentials
- **Dry-run by default**: Preview deletions before committing
- **Explicit confirmation**: Requires typing "DELETE" to proceed with actual deletions
- **Comprehensive logging**: Every action is logged with timestamps
- **Engagement protection**: High-engagement posts are automatically preserved
- **Rate limiting**: 0.5s delay between deletions with automatic retry on rate limit errors
- **Exponential backoff**: Automatically retries failed deletions with increasing delays

## Rate Limiting

The script implements intelligent rate limiting to avoid hitting Bluesky's API limits:

- **0.5 second delay** between each deletion
- **Automatic retry** if a rate limit error occurs (up to 3 attempts)
- **Exponential backoff** (5s, 10s, 20s) for retries
- **Progress updates** every 10 deletions

If you're deleting many posts, the script will take its time to ensure reliable completion.

## Logs

All operations are logged to the `logs/` directory with timestamps:
- Dry-run logs: `logs/dry-run-YYYY-MM-DD-HHMMSS.log`
- Deletion logs: `logs/deletion-YYYY-MM-DD-HHMMSS.log`

Each log includes:
- Post URIs
- Post text previews
- Age and engagement metrics
- Success/failure status
- Rate limit warnings and retries

## ⚠️ Important Warnings

- **Deletions are IRREVERSIBLE**: Once deleted, posts cannot be recovered
- **Test with dry-run first**: Always run in dry-run mode before actual deletion
- **Review the preview carefully**: Check the sample posts to ensure your filters are correct
- **Start conservative**: Use higher thresholds initially, then adjust if needed
- **Check your logs**: Review the log files to understand what will be deleted

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is provided as-is. The authors are not responsible for any data loss or account issues. Use at your own risk and always test with dry-run mode first.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Remember**: Always use an app password, never your main account password!
