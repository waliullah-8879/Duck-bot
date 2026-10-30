# Bird Daily Video Bot

Makes one short vertical Urdu video per day about ducks, geese, doves, starlings, and forest birds, then posts it to your Facebook Page.

**Pipeline:** pick topic → write script (Claude) → voiceover (edge-tts, free) → stock footage (Pixabay, free) → assemble with ffmpeg (1080x1920 + captions) → upload to Facebook Page.

## 1. Setup (local test)

```bash
sudo apt install ffmpeg        # or: brew install ffmpeg / choco install ffmpeg
pip install -r requirements.txt
cp .env.example .env           # then fill in the keys
python main.py --dry-run       # builds output/<title>.mp4, does NOT post
```

## 2. Keys you need

| Key | Where | Cost |
|---|---|---|
| `PIXABAY_API_KEY` | https://pixabay.com/api/ | Free |
| `FB_PAGE_ID`, `FB_PAGE_TOKEN` | Meta for Developers (below) | Free |
| `ANTHROPIC_API_KEY` (optional) | https://console.anthropic.com | Pay per use, very small (about one short call a day) |

### Facebook Page token
1. Go to https://developers.facebook.com → create an app (type: Business).
2. Add the Pages API. In Graph API Explorer, request permissions `pages_show_list`, `pages_manage_posts`, `pages_read_engagement` (and `publish_video` if offered).
3. Generate a User token, exchange it for a long-lived one, then call `GET /me/accounts` to get the **Page access token** and **Page ID**.
4. Use a Page token from a long-lived user token so it does not expire in an hour. You must be an admin of the Page.
5. Your app may need Meta App Review before it can post to a Page that is not your own test Page. In Development mode it works for Pages you administer.

## 3. Run it every day (free)

1. Push this folder to a **private** GitHub repo.
2. Repo → Settings → Secrets and variables → Actions → add `PIXABAY_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`, `ANTHROPIC_API_KEY`.
3. The workflow in `.github/workflows/daily.yml` runs daily (edit the cron line to change the time) and you can also trigger it manually from the Actions tab.

## 4. Customize
- **Topics:** edit `topics.py`. Rotation stays within ducks, geese, doves, starlings, and forest birds, and avoids repeats.
- **Voice:** the default is Pakistani Urdu (`ur-PK-AsadNeural`). Set `TTS_VOICE` to another Urdu voice if preferred (run `edge-tts --list-voices`).
- **Length / style:** edit the prompt in `script_gen.py`.

## Things to know
- **Language and footage:** narration is generated in Urdu, and footage searches are limited to the selected bird subject.
- **Footage source:** Pixabay search responses are cached for 24 hours as required by its API terms, and the post description credits Pixabay.
- **Repetitive content:** Facebook can reduce reach for fully automated, low-effort pages. Review the first videos, add your own clips/photos, and keep the facts accurate.
- **Reels:** this uses the standard video endpoint. Facebook Reels use a separate multi-step upload API if you want to switch later.
