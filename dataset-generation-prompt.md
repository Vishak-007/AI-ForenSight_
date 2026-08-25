Generate a synthetic UFDR (Universal Forensic Data Extraction Report) test case as a ZIP file, matching this exact format:

**Structure (at the zip root):**
```
report.xml
media/
  img_001.jpg
  aud_001.wav          (or a real, valid .mp4/.m4a/.mp3 audio file)
  doc_001.pdf
  vid_001.mp4
  ...
```

`report.xml` and `media/` must sit directly at the top level of the zip (not nested inside another folder). Every filename referenced in `report.xml` must be a real file that actually exists under `media/` with that exact name — do not invent placeholder filenames that don't correspond to real files in the archive.

**`report.xml` schema** (root element must be `<ufdr_report>`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ufdr_report>
  <device_info>
    <device_id>DEV003</device_id>
    <imei>359268100009999</imei>
    <extraction_date>2026-08-25T09:00:00</extraction_date>
  </device_info>

  <messages>
    <message>
      <id>M001</id>
      <sender>+91XXXXXXXXXX</sender>
      <receiver>+91XXXXXXXXXX</receiver>
      <timestamp>2026-08-20T10:14:00</timestamp>
      <text>Message body text here</text>
    </message>
    <!-- more <message> entries -->
  </messages>

  <calls>
    <call>
      <id>C001</id>
      <caller>+91XXXXXXXXXX</caller>
      <callee>+91XXXXXXXXXX</callee>
      <timestamp>2026-08-20T21:00:00</timestamp>
      <duration_seconds>184</duration_seconds>
      <type>outgoing</type>  <!-- or "incoming" -->
    </call>
    <!-- more <call> entries -->
  </calls>

  <contacts>
    <contact>
      <id>CT001</id>
      <name>Full Name</name>
      <phone>+91XXXXXXXXXX</phone>
    </contact>
    <!-- more <contact> entries -->
  </contacts>

  <media>
    <media_item>
      <id>MED001</id>
      <type>image</type>  <!-- one of: image, audio, document, video -->
      <timestamp>2026-08-20T10:20:00</timestamp>
      <filename>img_001.jpg</filename>  <!-- relative to media/, must match a real file -->
      <associated_message_id>M001</associated_message_id>  <!-- or empty/omit -->
      <associated_call_id></associated_call_id>  <!-- or empty/omit -->
    </media_item>
    <!-- one <media_item> per file actually placed in media/ -->
  </media>
</ufdr_report>
```

**Requirements for the actual media files:**
- Images: real, valid JPEG or PNG files (any innocuous content/placeholder image is fine, just needs to be a real decodable image).
- Audio: a genuinely valid, decodable audio file. `.wav` (PCM) is ideal since it gets full duration/channel/sample-rate metadata; `.mp4`/`.m4a`/`.mp3` also work (they just skip that extra metadata) as long as they're real playable audio, not a renamed/fake file.
- Documents: real PDF or PNG/JPEG files.
- Video: a real `.mp4` is fine — it will be recorded as "seen" but its content isn't processed (video analysis isn't implemented yet), so any valid mp4 works.

Every `media_item.id` must be unique, and every `associated_message_id`/`associated_call_id` (when set) must reference a real `<message>`/`<call>` `<id>` that actually exists in the same file.

Keep the case narrative internally consistent (phone numbers reused across messages/calls/contacts, timestamps in a sensible order) but the specific content is up to you.
