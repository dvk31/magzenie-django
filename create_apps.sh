#!/bin/bash

# List of app names
apps=(
  "core"
  "influencer"
  "kiosk"
  "kiosk_vendor"
  "platform_vendor"
  "store"
  "user"
)

# Create apps using manage.py startapp
for app in "${apps[@]}"
do
  python manage.py startapp "$app"
done

# Run app_setup.py for each app
for app in "${apps[@]}"
do
  echo "Setting up app: $app"
  python app_setup.py <<< "$app"
done