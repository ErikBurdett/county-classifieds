# ADR 0009: WhiteNoise for Static Assets, S3 for User Media

- Status: Accepted
- Date: 2026-07-22

## Context

Static application assets are immutable and small, while user listing photos are large, untrusted, mutable, and must outlive containers. Sending both through one storage path would either complicate deployment or weaken upload controls.

## Decision

Collect versioned static assets into the image and serve them with WhiteNoise initially. Upload user media directly to a private S3 staging prefix, process/re-encode it, and deliver approved derivatives through a controlled S3/CloudFront path.

## Consequences

- Simple application deploys and cacheable static assets.
- Containers never own persistent user media.
- Media requires explicit upload, processing, lifecycle, and delivery controls.
- Static assets may move to CloudFront later if measured needs justify it.
