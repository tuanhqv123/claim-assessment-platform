-- Broaden the accepted image types for uploaded claim documents.
update storage.buckets
set allowed_mime_types = array[
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'image/bmp',
  'image/tiff',
  'application/pdf'
]
where id = 'claim-documents';
