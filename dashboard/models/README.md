# Tutor character model

`tutor.vrm` is the 3D character shown beside the tutor chat (drawn by `../avatar.js`).

**To change the character**, replace `tutor.vrm` with any VRM 1.0 or 0.x model (for example one made in the free
[VRoid Studio](https://vroid.com/en/studio)) whose license allows redistribution, keep the file name, and reload the page.
The lip sync and expressions use the standard VRM expressions (`aa ih ou ee oh`, `happy sad surprised relaxed`, `blink`),
which every VRM model has.

The file is stored with Git LFS (see `.gitattributes`). If the page says the model "wasn't downloaded", run
`git lfs install` and then `git lfs pull` in the project folder.

## Credits

Current model: **VRM1_Constraint_Twist_Sample** v1.0.1, (c) 2022 pixiv Inc., from the
[VRM specification samples](https://github.com/vrm-c/vrm-specification/tree/94e82dd346fa6cf0337c4421728640e5252dd38e/samples/VRM1_Constraint_Twist_Sample).
License: [VRM Public License 1.0](https://vrm.dev/licenses/1.0/), as recorded in the model itself: use by everyone,
commercial use allowed, redistribution and modification allowed, credit not required.
