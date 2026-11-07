PWA icons are resized, aspect-ratio-preserving copies of `../images/brand-mark.png`:

- `icon-192.png`: standard install icon
- `icon-512.png`: large and maskable install icon
- `apple-touch-icon.png`: iOS home-screen icon


Beamers Farm ivory monogram assets:
- `beamers-farm-ivory.svg`: vector favicon and manifest icon (`#FDF9ED`).
- `notification-icon-192.png`: transparent PNG fallback for Web Push notification icons.
- `notification-badge-96.png`: transparent compact PNG for notification badges.

SVG is used directly for favicon and supported manifest contexts. Transparent PNG notification assets are intentionally retained for browser/OS compatibility because push notification icon support for SVG is inconsistent.
