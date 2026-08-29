Flutter Web notes:

- `just_audio` plays the generated WAV over HTTP.
- The API server must send CORS headers.
- Chrome/Edge/Safari may apply their normal autoplay rules. This demo starts
  playback after the user's Generate button click, which satisfies the usual
  browser gesture requirement.
- For production, serve both Flutter and the API over HTTPS.
