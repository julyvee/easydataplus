gcloud functions deploy versusvirus-text-extraction --runtime python37 --trigger-resource versusvirus-output --trigger-event google.storage.object.finalize