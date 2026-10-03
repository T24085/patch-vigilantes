# Deployed Visual Update — 2026-10-03

Live URL: https://t24085.github.io/patch-vigilantes/

GitHub Pages reported `built` with no error for exact deployment commit `726800fa02cf99842b65efdc8af7e99265f98c28`, created 2026-10-03T02:55:51Z and completed 02:56:12Z. Main implementation commits: `93ffd6c` (design/art) and `1f86d0c` (latest verified private runtime status).

## External Verification

The public URL was rendered after the completed build at desktop 1440×1000, tablet 768×1024, phone 390×844, small phone 320×740. All four have no horizontal overflow, broken images, invalid section anchors, browser page errors or axe WCAG 2/2.1 A/AA violations. The actual project-navigation click reaches #workbench at all four sizes. Reduced-motion emulation yields auto scrolling and zero running animations. Desktop, tablet and phone compositions were visually inspected. Automated accessibility checks are useful evidence, not a claim of full human accessibility certification.

Every production HTML/CSS/JS file and loaded image returns HTTP 200 and matches the reviewed checkout (text comparison normalizes CRLF). All eight loaded image files together total 1,020,732 bytes versus the earlier 4,974,058 bytes, a 79.5% reduction. Existing original PNG artwork stays in the repo as source material. The existing proof PNG is unchanged; public SHA-256 `f0073b7cf6ea164c18fdc4cf9ddeeec1dee93ad39ce1858a60da0447c66f156b`. The upstream repository and original license links return HTTP 200.

## Scope and Limits

Only the public workshop/site assets and documentation were changed. E: isolated clone `E:\Patch-Vigilantes-Visual-20261003`; Pages worktree `E:\Patch-Vigilantes-Pages-20261003`. The Light Table runtime checkout was read only during initial inventory and never edited. No new project, fake restoration, public runtime download, paid service, domain change, server or network route was added.

The genuine project collection currently contains one experimental active project and zero completed restorations. The verified private runtime worker supplied the updated Electron 44.5.1 and bounded async facts. The original public screenshot remains the synchronous proof and is explicitly labeled accordingly. The Retro Visits counter still displays unavailable; its backend remains a separately approved task.

Before/after visual comparison saved as native Library image `Patch-Vigilantes-Before-After.png`. Browser QA reports and screenshots remain in the private task workspace rather than the public repository.
