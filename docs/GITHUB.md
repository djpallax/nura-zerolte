# Create the integration repository

The local preparation is a separate Git repository on branch main. Reviewed
sources are staged; no commit or GitHub repository was created automatically.

```sh
git status
python3 scripts/check-public-tree.py
sha256sum -c SOURCE-SHA256SUMS
git diff --cached --stat
git commit -m "Initial zerolte integration sources and build documentation"
```

After source/licensing review, create the GitHub repository and push:

```sh
gh repo create djpallax/nura-zerolte --public --source=. --remote=origin --push
```

Use --private instead if keeping this preparation private initially. If the
repository already exists, inspect it first; do not overwrite its history.

Kernel source stays in djpallax/linux-zerolte. After its commit/push, record the
exact commit in sources.lock.json and verify the tree matches the recorded
snapshot. No phone data is needed to create either repository.
