#!/usr/bin/env bash
# Copies the fixture and builds a small git history over the last week.
set -euo pipefail
cp -R "$(dirname "$0")/fixture/." .
git init -q -b main .
git config user.email "owner@example.com"
git config user.name "Sam"
c() { mkdir -p "$(dirname "$2")"; echo "$3" >> "$2"; git add -A; GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q -m "$4"; }
c "$(date -d '12 days ago' -R)" shop/photos.md "photos" "Add new product photos"
c "$(date -d '5 days ago' -R)" shop/checkout.js "mobile fix" "Fix gift-card form on mobile Safari"
c "$(date -d '4 days ago' -R)" shop/checkout.js "gift cards" "Ship gift-card checkout"
c "$(date -d '3 days ago' -R)" shop/invoice.js "vat" "Fix VAT rounding on invoices"
c "$(date -d '2 days ago' -R)" shop/shipping.js "min" "Free shipping only on orders of 30 or more"
c "$(date -d '1 day ago' -R)" shop/courier.js "stub" "WIP courier integration (needs live API key)"
