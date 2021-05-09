# Usage: ./deploy.sh $BUILD_ARTEFACT $BUCKET_NAME $CDN_DISTRIBUTION_ID

set -eux
aws s3 sync $1 s3://$2 --delete
aws cloudfront create-invalidation --distribution-id $3 --paths /\*