# Third-party libraries (local copies)

Copied unchanged from the official npm packages (checksums verified against the npm registry), so the web app needs
no build step, no npm and no internet. Each folder keeps its MIT license.

| Folder | Package | Version | Files |
|---|---|---|---|
| `three/` | [three](https://threejs.org) | 0.180.0 | `build/three.module.min.js`, `build/three.core.min.js`, `examples/jsm/loaders/GLTFLoader.js`, `examples/jsm/utils/BufferGeometryUtils.js` |
| `three-vrm/` | [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) | 3.5.5 | `lib/three-vrm.module.min.js` |

three-vrm 3.5.5 is built and tested against three 0.180, so upgrade the two together.
They are loaded through the import map in `../index.html`.
