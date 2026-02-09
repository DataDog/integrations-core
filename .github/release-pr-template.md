## TUF Targets Release

This PR adds TUF target files (wheel manifests) for Agent integration releases.

**Note:** This branch is continuously updated by release workflows. Each workflow run will add a comment below with details about the integrations it released.

---

## Validation Steps

Before merging this PR, please verify:

1. **Target File Structure**
   - Verify all target files follow the naming convention: `targets/datadog-{integration}/{version}.yaml`
   - Check that integration names and versions are correct

2. **Target File Contents**
   - Each target file should contain: `digest`, `length`, `version`, `repository`, `wheel_path`, `attestation_path`
   - Verify digest format is a valid SHA256 hash (64 hex characters)
   - Verify length is a positive integer
   - Verify paths are absolute (start with `/`)

3. **Attestations**
   - Verify SLSA provenance attestations were generated for all wheels
   - Check attestation links in workflow comments below

4. **Conflicts**
   - Ensure there are no duplicate versions for the same integration
   - Verify no files were accidentally deleted

---

## Next Steps

After validation and approval:

1. Merge this PR to add targets to the staging area
2. The TUF metadata will be signed and published in a subsequent workflow
