# Videos to Odysee

Selenium RPA script to log in to [Odysee](https://odysee.com) and upload videos via the web interface. Automates the signin flow at https://odysee.com/$/signin and the upload flow at https://odysee.com/$/upload.

**Disclaimer:** This project is not affiliated with Odysee or LBRY. Use at your own risk. Odysee is moving away from the LBRY protocol; this tool may become obsolete.

## Requirements

- **Python 3.8+**
- **Chrome** (or Chromium) — Selenium uses ChromeDriver
- **selenium**, **webdriver-manager**, **python-dotenv** — `pip install -r requirements.txt`

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure credentials. Either:

   - **Option A:** Copy `.env.example` to `.env` and fill in your email and password:
     ```bash
     cp .env.example .env
     # Edit .env with your ODYSEE_EMAIL and ODYSEE_PASSWORD
     ```

   - **Option B:** Set environment variables before running:
     ```bash
     export ODYSEE_EMAIL="your@email.com"
     export ODYSEE_PASSWORD="your_password"
     ```

   **Never commit `.env` or hardcode credentials.**

3. For uploads:
   - Create a `videos/` folder in the project root and place your `.mp4` (or `.webm`, `.mkv`, `.mov`, `.avi`) files there.
   - Place `thumb.jpg` in the project root — it will be used as the thumbnail for all uploads.

## Usage

### Login only

```bash
python odysee_login.py
```

### Login and upload

```bash
python odysee_login.py --upload
```

This logs in, navigates to the upload page, and uploads each video in `videos/` one by one, using `thumb.jpg` as the thumbnail for all.

### Arguments

| Argument | Description |
|----------|-------------|
| `--no-headless` | Show browser window (default is headless) |
| `--keep-open` | Keep browser open after completion (useful for debugging) |
| `--timeout N` | Wait timeout in seconds (default: 15) |
| `--upload` | After login, upload videos from `videos/` |
| `--videos-dir PATH` | Folder containing videos (default: `videos/` in project) |
| `--thumbnail PATH` | Thumbnail image path (default: `thumb.jpg` in project) |

### Examples

```bash
# Login only
python odysee_login.py

# Login and upload all videos from videos/
python odysee_login.py --upload

# Upload from a custom folder with custom thumbnail
python odysee_login.py --upload --videos-dir /path/to/my/videos --thumbnail /path/to/thumb.jpg

# Headless upload
python odysee_login.py --upload --headless

# Keep browser open after upload
python odysee_login.py --upload --keep-open
```

## Flow

### Login

1. Opens https://odysee.com/$/signin
2. Fills email, clicks "Log In"
3. Fills password, clicks "Continue"
4. Waits for redirect to https://odysee.com/

### Upload (when `--upload` is used)

1. Navigates to https://odysee.com/$/upload
2. For each video in `videos/`:
   - Selects the video file
   - Clicks Upload (for the video)
   - Selects `thumb.jpg` as thumbnail
   - Clicks Upload (for the thumbnail)
   - Marks the sync toggle
   - Clicks Confirm
   - Waits for upload to complete
   - Navigates to `/$/upload` for the next video
3. Prints the number of successfully uploaded videos

## Building a Windows .exe (for non-technical users)

To distribute the script as a standalone executable for Windows users who don't have Python:

1. On a **Windows** machine with Python installed, run:
   ```batch
   build.bat
   ```

2. The executable will be created in `dist/odysee_upload.exe`.

3. Copy the entire `dist/` folder to the end user. They need to add:
   - `.env` (rename from `.env.example`, fill in ODYSEE_EMAIL and ODYSEE_PASSWORD)
   - `thumb.jpg`
   - `videos/` folder with their `.mp4` files

4. The user double-clicks `Rodar_Upload.bat` to run the upload.

See `INSTRUCOES_UTILIZADOR.txt` for end-user instructions in Portuguese.
