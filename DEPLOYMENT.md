# Deployment Guide for Streamlit Cloud

## Prerequisites
- GitHub account
- Streamlit Cloud account (free at share.streamlit.io)

## Files Required for Streamlit Cloud

### 1. `packages.txt`
This file tells Streamlit Cloud to install Chromium browser and driver:
```
chromium
chromium-driver
```

### 2. `.streamlit/config.toml`
Configuration for Streamlit settings (already included)

### 3. `requirements.txt`
Python dependencies (already included)

## Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add Streamlit Cloud support"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your repository
   - Set main file path: `app.py`
   - Click "Deploy"

3. **First Use on Cloud**
   - Click "Send" button
   - Wait for QR code to appear in the app
   - Scan QR code with your WhatsApp mobile app
   - Messages will start sending

## Important Notes

### QR Code Scanning
- On Streamlit Cloud, you need to scan the QR code **every time** you use the app
- The Chrome profile doesn't persist between sessions
- The QR code will appear directly in the Streamlit interface

### Limitations
- Each session requires fresh WhatsApp login (QR scan)
- Rate limiting: WhatsApp may block if you send too many messages too quickly
- Cloud sessions have timeout limits

### Best Practices
- Test with a small batch first (5-10 contacts)
- Use inter-message delay of at least 5 seconds
- Don't send identical messages to avoid spam detection
- Use personalization variables like {name}

## Troubleshooting

### "WebDriver unexpectedly exited" Error
- Fixed by the `packages.txt` file
- Ensure Chromium is installed on cloud

### QR Code Not Appearing
- Wait 10-15 seconds after clicking Send
- Refresh the page if stuck
- Check app logs for errors

### Messages Not Sending
- Verify phone numbers include country code
- Check CSV format matches requirements
- Ensure WhatsApp Web is not blocked in your region

## Local Development

To run locally:
```bash
streamlit run app.py
```

Local mode will:
- Open Chrome window (not headless)
- Use persistent Chrome profile
- Keep you logged in between sessions
