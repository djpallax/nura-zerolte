# Publication and contribution route

Checked 2026-10-28 against primary project documentation:

- https://nura.eco/contribute/
- https://docs.nura.eco/policies-and-processes/development/project-maintainers.html
- https://docs.nura.eco/pmaports/main/packaging.html
- https://docs.nura.eco/pmaports/main/merge-requests/commitstyle.html
- https://docs.nura.eco/pmaports/main/packaging/device-packages/deviceinfo-reference.html
- https://docs.nura.eco/pmaports/main/packaging/device-categorization.html
- https://docs.nura.eco/policies-and-processes/development/ai-policy.html

Nura uses pmaports for package recipes and pmbootstrap for builds/installations.
Package names follow manufacturer/codename, not the independent GitHub repo name.
Before choosing device-samsung-zerolte versus an existing zeroltexx device or a
variant, inspect the current pmaports tree and coordinate the device identity.
Do not silently replace an existing device port or assume other models work.

The eventual integration needs a device package (deviceinfo, services, input and
display configuration), kernel package, firmware handling, and loader/boot-deploy
integration. The deviceinfo documentation explicitly warns against repartitioning
Android devices. Our installation must preserve the existing partition table.

Nura's AI policy says: “Submitting contributions fully or in part created by
generative AI tools to Nura” is not allowed. This project has substantial AI
assistance. It must remain transparent about that origin; human review alone
does not make the present contribution eligible under that policy. This export
does not submit an MR or contact maintainers, and does not suggest concealing
provenance. It is an independent experiment, not an accepted Nura port.

The uniLoader checkout separately forbids LLM agents from reading, generating
or modifying its project code. Its code was not copied into this export. Plan
loader integration around an exact upstream revision, its license and existing
build interface, with no claims of an upstream contribution from this work.
