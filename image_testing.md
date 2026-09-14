# NutriMitra image integration testing rules

- Use base64-encoded images for all image requests and tests.
- Accepted formats: JPEG, PNG, WEBP only.
- Do not use blank, solid-color, or uniform-variance images.
- Every test image must contain real visual features such as objects, edges, textures, or shadows.
- Transcode unsupported inputs to PNG or JPEG before upload and re-detect the MIME type.
- For animated images, test only the first frame.
- Resize large images to reasonable bounds before sending.