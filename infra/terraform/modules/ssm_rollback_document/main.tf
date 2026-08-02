# Custom staging-only SSM Command document for rollback (Sprint 25b.5).
# Bounded parameters only — no free-form commands, no secrets.
# Invokes the fixed host rollback entrypoint; no image rebuild, no Terraform.

locals {
  document_content = {
    schemaVersion = "2.2"
    description   = "DealBrain staging digest rollback. Bounded parameters; host-side secrets only."
    parameters = {
      ReleaseId = {
        type           = "String"
        description    = "Target release ID from the validated build manifest."
        allowedPattern = "^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$"
      }
      GitSha = {
        type           = "String"
        description    = "Full 40-character git SHA of the target image source."
        allowedPattern = "^[0-9a-f]{40}$"
      }
      ImageRepository = {
        type           = "String"
        description    = "Canonical GHCR repository without tag or digest."
        allowedPattern = "^ghcr\\.io/[a-z0-9._/-]+$"
      }
      ImageDigest = {
        type           = "String"
        description    = "Immutable target image digest."
        allowedPattern = "^sha256:[0-9a-f]{64}$"
      }
      BundleChecksum = {
        type           = "String"
        description    = "SHA-256 hex digest of the target release bundle.tar.gz."
        allowedPattern = "^[0-9a-f]{64}$"
      }
      DeployRunId = {
        type           = "String"
        description    = "GitHub Actions rollback workflow run ID."
        allowedPattern = "^[0-9]+$"
      }
      BundleBucket = {
        type           = "String"
        description    = "Staging release-artifacts S3 bucket name."
        allowedPattern = "^dealbrain-staging-release-artifacts-[0-9]{12}$"
      }
      BundleKey = {
        type           = "String"
        description    = "S3 object key for the target release bundle tarball."
        allowedPattern = "^releases/rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}/bundle\\.tar\\.gz$"
      }
      SourceManifestSha256 = {
        type           = "String"
        description    = "Checksum of the authoritative target release-manifest."
        allowedPattern = "^[0-9a-f]{64}$"
      }
    }
    mainSteps = [
      {
        action = "aws:runShellScript"
        name   = "DealBrainStagingRollback"
        inputs = {
          workingDirectory = "/opt/dealbrain"
          timeoutSeconds   = tostring(var.timeout_seconds)
          runCommand = [
            "#!/bin/bash",
            "set -euo pipefail",
            "# Fixed rollback entrypoint only — parameters exported as env, never eval'd.",
            "export DEALBRAIN_RELEASE_ID='{{ReleaseId}}'",
            "export DEALBRAIN_GIT_SHA='{{GitSha}}'",
            "export DEALBRAIN_IMAGE_REPOSITORY='{{ImageRepository}}'",
            "export DEALBRAIN_IMAGE_DIGEST='{{ImageDigest}}'",
            "export DEALBRAIN_BUNDLE_CHECKSUM='{{BundleChecksum}}'",
            "export DEALBRAIN_DEPLOY_RUN_ID='{{DeployRunId}}'",
            "export DEALBRAIN_BUNDLE_BUCKET='{{BundleBucket}}'",
            "export DEALBRAIN_BUNDLE_KEY='{{BundleKey}}'",
            "export DEALBRAIN_SOURCE_MANIFEST_SHA256='{{SourceManifestSha256}}'",
            "export DEALBRAIN_ENVIRONMENT='staging'",
            "export DEALBRAIN_OPERATION='rollback'",
            "exec /opt/dealbrain/bin/dealbrain-staging-rollback.sh",
          ]
        }
      },
    ]
  }
}

resource "aws_ssm_document" "staging_rollback" {
  name            = var.document_name
  document_type   = "Command"
  document_format = "JSON"
  content         = jsonencode(local.document_content)

  tags = merge(var.tags, {
    Name        = var.document_name
    Environment = var.environment
    Role        = "ssm-rollback-document"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
    Sprint      = "25b.5"
  })
}
