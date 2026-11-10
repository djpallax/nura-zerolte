# Publish the zerolte sources

Review the kernel and integration repositories separately. The kernel fork owns
the drivers and defconfig. The Nura repository owns the source lock, fallback
patch, BOOT tools and installation guides.

1. Review and publish the kernel changes to the fork first. From the kernel
   checkout, get the commit and tree with `git rev-parse HEAD HEAD^{tree}`.
2. In Nura, record that commit as `kernel.fork_commit` in `sources.lock.json`.
   The tree must match `kernel.source_tree`. If the source changed during
   review, regenerate and verify the fallback patch against the pinned base
   before publishing the lock.
3. Review the staged integration changes, regenerate the source checksums and
   verify them before committing and pushing Nura.

After staging the reviewed source files in Nura, refresh the manifest and
run the checks from the repository root:

```sh
git status --short
git diff --check
git diff --cached --check
git ls-files -z | grep -zvxF SOURCE-SHA256SUMS |
  xargs -0 sha256sum > SOURCE-SHA256SUMS
git add SOURCE-SHA256SUMS
python3 scripts/check-public-tree.py
sha256sum -c SOURCE-SHA256SUMS
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Review provenance and licensing before publication. The source audit does not
replace that review. Keep BOOT receipts, firmware, personal device data and
experimental binaries under the ignored `private/`, `build/` or `dist/` paths.
