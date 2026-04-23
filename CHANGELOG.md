# Changelog

## [0.3.2](https://github.com/kushpvo/scriptflow/compare/scriptflow-v0.3.1...scriptflow-v0.3.2) (2026-04-23)


### Bug Fixes

* trigger Docker version tags via release event instead of tag push ([#7](https://github.com/kushpvo/scriptflow/issues/7)) ([93d70c8](https://github.com/kushpvo/scriptflow/commit/93d70c8ecf5619ba6f7b254fdd1551a29f91332b))
* use stored token when re-cloning existing repo via wizard ([#9](https://github.com/kushpvo/scriptflow/issues/9)) ([217f510](https://github.com/kushpvo/scriptflow/commit/217f510686588f90894587638586564c05e65def))

## [0.3.1](https://github.com/kushpvo/scriptflow/compare/scriptflow-v0.3.0...scriptflow-v0.3.1) (2026-04-23)


### Bug Fixes

* use x-access-token format for GitHub token injection ([#5](https://github.com/kushpvo/scriptflow/issues/5)) ([98b1187](https://github.com/kushpvo/scriptflow/commit/98b11871a603c76351187b5b6b87bd076dfd7c64))

## [0.3.0](https://github.com/kushpvo/scriptflow/compare/scriptflow-v0.2.0...scriptflow-v0.3.0) (2026-04-23)


### Features

* use uv for Python version management, add Python 3.14 support ([#3](https://github.com/kushpvo/scriptflow/issues/3)) ([117bcad](https://github.com/kushpvo/scriptflow/commit/117bcad9c935d27c7777499ae65aac4db0139652))

## [0.2.0](https://github.com/kushpvo/scriptflow/compare/scriptflow-v0.1.0...scriptflow-v0.2.0) (2026-04-23)


### Features

* initial ScriptFlow implementation ([495f30b](https://github.com/kushpvo/scriptflow/commit/495f30ba0b9bdcb35baef51ccb0e0dbf017374ca))


### Bug Fixes

* correct bare repo HEAD in github tests, wizard test assertion, and stale page title ([38decdc](https://github.com/kushpvo/scriptflow/commit/38decdcd7d141bf6da58a4aff4645f2451679efc))
* remove unraid-template.xml from Dockerfile ([ab4e52b](https://github.com/kushpvo/scriptflow/commit/ab4e52b46fdeb7417cad1d80935c05c273b53385))
* update uv.lock with scriptflow package name ([e41faa8](https://github.com/kushpvo/scriptflow/commit/e41faa8fb268494b43d394d5023dc652d0fb6086))
* use -inf default in stderr rate limiter to handle fresh process start ([fb42520](https://github.com/kushpvo/scriptflow/commit/fb42520a1d9d2f8101a1dd60aa3599672f8fbdd9))


### Reverts

* remove test commit from branch protection check ([#2](https://github.com/kushpvo/scriptflow/issues/2)) ([1008f7d](https://github.com/kushpvo/scriptflow/commit/1008f7d6fcf75d6d62710f685875c52551469b5c))


### Documentation

* add CI/CD section to CLAUDE.md ([4bd90f1](https://github.com/kushpvo/scriptflow/commit/4bd90f1ce2c72136b59a731785b73c0f312c4412))
