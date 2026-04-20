# AURASUTRA - Desktop WhatsApp Sender

## ⚠️ IMPORTANT: This App Works ONLY on Your Local Computer

**Why it won't work on Streamlit Cloud or any web hosting:**
- WhatsApp Web actively blocks automated/headless browsers
- Cloud servers can't display real browser windows for QR code scanning
- WhatsApp requires a persistent browser session with your login
- The error "WhatsApp works with Google Chrome 85+" means WhatsApp detected automation

**Solution:** Run this app locally on your computer using the Desktop App.

---

## 🖥️ Desktop App (Recommended)

### Requirements
- Windows 10/11 or macOS or Linux
- Python 3.8+
- Google Chrome browser installed

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the desktop app:**
   ```bash
   python desktop_app.py
   ```

### First Time Setup
1. The app will open a Chrome browser window
2. WhatsApp Web will load and show a QR code
3. Open WhatsApp on your phone → Settings → Linked Devices → Link a Device
4. Scan the QR code
5. Once logged in, you can start sending messages

### Features
- ✅ Persistent login (scan QR code only once)
- ✅ Visual GUI with progress tracking
- ✅ Upload CSV/Excel contacts
- ✅ Customizable message templates with placeholders
- ✅ Export send reports to CSV
- ✅ Configurable delays to avoid rate limiting

---

## 📱 How to Use

### 1. Prepare Your Contacts File
Create a CSV or Excel file with these columns:
- `mobile` - Phone number (with or without country code)
- `name` - Contact name
- `clinic_name` - Business name
- `location` - City/area

Example:
```csv
mobile,name,clinic_name,location
9876543210,Dr. Sharma,City Clinic,Mumbai
+919123456789,Dr. Patel,Health Center,Delhi
```

### 2. Write Your Message Template
Use placeholders that match your column names:
```
Hi {name},

I came across {clinic_name} in {location} and wanted to reach out.

We help clinics grow through digital marketing. Would love to connect!

— Aurasutra Team
```

### 3. Configure Settings
- **Country Code**: Auto-prepends to 10-digit numbers
- **Wait Time**: Seconds to wait for each chat to load (30 recommended)
- **Delay Between Messages**: Pause between sends (5+ seconds recommended)

### 4. Send Messages
1. Click "Upload Contacts"
2. Preview your message
3. Click "SEND TO ALL CONTACTS"
4. Keep Chrome window visible (don't minimize)

---

## ⚠️ Best Practices

### Avoid Getting Blocked
- Start with small batches (10-20 contacts)
- Use 5-10 second delays between messages
- Personalize messages with {name}, {clinic_name}, etc.
- Don't send identical messages repeatedly
- Space out campaigns over multiple days

### Rate Limits
WhatsApp may temporarily block sending if you:
- Send too many messages too fast
- Send to invalid numbers repeatedly
- Get reported as spam

---

## 🔧 Troubleshooting

### "Chrome already in use" Error
- Close all Chrome windows
- Delete lock files: `chrome_profile/SingletonLock`
- Restart the app

### QR Code Not Loading
- Ensure you have stable internet
- Clear `chrome_profile` folder and restart
- Wait longer (up to 30 seconds)

### Messages Not Sending
- Verify phone number format
- Check that WhatsApp is still logged in
- Ensure Chrome window is not minimized

### "Invalid number" Error
- Ensure number has correct country code
- Remove spaces, dashes, or special characters
- Use 10+ digits

---

## 📁 Project Files

```
├── desktop_app.py      # Desktop GUI application (USE THIS)
├── app.py              # Streamlit app (for local testing only)
├── whatsapp_sender.py  # WhatsApp automation logic
├── utils.py            # Helper functions
├── config.json         # Saved settings
├── chrome_profile/     # Persistent Chrome session (keeps you logged in)
├── sample_contacts.csv # Sample contact file
└── requirements.txt    # Python dependencies
```

---

## 🔄 Alternative: WhatsApp Business API

For high-volume, reliable messaging without browser automation:
- Use official **WhatsApp Business API** via providers like:
  - Twilio
  - MessageBird
  - Gupshup
  - Meta Business Suite

These cost money but work reliably at scale without risk of being blocked.
