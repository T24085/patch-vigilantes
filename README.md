# The Patch Vigilantes

**No project left for dead.**

Digital archaeology, with fixes people can actually use. We want useful software to feel less disposable: keep what made it interesting, repair a concrete path, and show the evidence.

<img src="site/assets/patch-vigilantes-banner.png" alt="The Patch Vigilantes repair workshop" style="width:100%;height:auto">
<img src="site/assets/patch-vigilantes-avatar.png" alt="CRT mechanic mascot" width="160" style="height:auto">

## On the Workbench

| Project | Actual Status | Evidence and Gaps |
| --- | --- | --- |
| Light Table revival | Experimental partial revival; private staging | Original editor opens, edits and saves proof files. Electron 44.5.1 / Chromium 152.0.7977.130 runs with sandboxing on and Node access off. Synchronous JavaScript plus promises and bounded one-shot timers pass verified checks. Private runtime worker reports 44 policy, 23 UI, 15 language and 31 async/resource checks passed. Native menus, legacy plugins and broader compatibility remain incomplete. 192 MiB memory monitoring is reactive, not a hard OS quota; execution has a 1.5-second watchdog and no autorun. No public download or release. |

## How We Restore

Preserve upstream history, licenses and credit. Reproduce a failure before claiming a fix. Keep tests and instructions reviewable. Label experimental work honestly. Where practical, prepare useful upstream contributions; none has been submitted for this proof. A working demonstration is not a production release.

One workshop home, one repository per repaired program. Light Table is the first project; no other projects are presented as completed.

## Website

Open `site/index.html` locally. Static HTML/CSS; no paid services, external fonts, package installation or server required. The site uses Agency OS and its Creative Direction, Web Color System, Typography Mastery and QA Polish guidance. Live site: https://t24085.github.io/patch-vigilantes/ . Taylor approved this workshop repository becoming public; GitHub Pages serves the clean site-only gh-pages branch. Light Table remains private. The retro page view counter uses the verified HTTPS counter.novatec.casa endpoint, with a persistent aggregate on Taylor's Jetson and a dedicated Cloudflare tunnel. Counter and connector boot services are enabled. Rapid same-tab reloads normally count once for 30 seconds; this measures page views, not unique people. See COUNTER.md and deploy/ACTIVATION.md.

[Original Light Table](https://github.com/LightTable/LightTable) · [Original MIT license](https://github.com/LightTable/LightTable/blob/develop/LICENSE.md)
