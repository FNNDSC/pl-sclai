# pl-sclai

[![Version](https://img.shields.io/docker/v/fnndsc/pl-sclai?sort=semver)](https://hub.docker.com/r/fnndsc/pl-sclai)
[![MIT License](https://img.shields.io/github/license/fnndsc/pl-sclai)](https://github.com/FNNDSC/pl-sclai/blob/main/LICENSE)
[![ci](https://github.com/FNNDSC/pl-sclai/actions/workflows/ci.yml/badge.svg)](https://github.com/FNNDSC/pl-sclai/actions/workflows/ci.yml)

`pl-sclai` is an _incidental_ [_ChRIS_](https://chrisproject.org/) _ds_ plugin that offers an interactive terminal based session with various LLMs.

## Abstract

The standard web-based interfaces to various (typically commercial) LLMs are convenient for simple interactions, but lack many more "power user" features. As the context of the "chat" becomes more and more complex (for instance multiple source files in a coding project) LLMs have been shown to suffer from several undesirable behaviors. For instance, "prompt directive decay" (where the LLM gradually ignores or "forgets" specific guidelines) and "consistency drift" (the LLM offers numerous slightly different versions of the same source file as the interaction continues).

For example, a prompt directive of "always use docstrings" will result in the next several code suggestions to adhere to this, but within a few iterations the model will revert (or "forget") to a default behavior. If a source file has been uploaded as a reference, the LLM will invariably suggest specific edits but will often when asked for the whole file, "forget" or "omit" large parts of simply refactor.

This application is an attempt to mitigate this: `pl-sclai` offers a text-based interface that easily allows the user to "re-inject" (reinforce) specific directives with each interaction (using convenient text markup shortcuts) and simplify the refreshing of source files with a base reference. Simply stated it is an attempt to keep the context as current as possible with minimal disruption to the end user.

## Installation

While `pl-sclai` is developed as _[ChRIS](https://chrisproject.org/) plugin_ this is mostly incidental. The plugin framework was used more as a means to simply setup a python (dockerizable) project than to create an application to use in _ChRIS_. In fact, given that `pl-sclai` is a strongly interactive application, it is not really suitable to run in _ChRIS_ (where plugins are typically and strongly non-interactive).

The two vectors for use are either as a PyPI application installed into a virtual environment or run from a container.

## Local Usage

### On the metal with PyPI

To run _on the metal_ directly on your system, use/create a virtual python env (say with `uv`):

```shell
cd ~/some/dir
uv init
```

### Containerized version

To get started with local command-line usage, use [Apptainer](https://apptainer.org/) (a.k.a. Singularity) to run `pl-sclai` as a container:

```shell
apptainer exec docker://fnndsc/pl-sclai sclai [--args values...] input/ output/
```

To print its available options, run:

```shell
apptainer exec docker://fnndsc/pl-sclai sclai --help
```

## Examples

`sclai` requires two positional arguments as artifacts of the application framework factory. These are not needed or used right now and can simply be set to `/tmp`.

```shell
apptainer exec docker://fnndsc/pl-sclai:latest sclai [--args] /tmp /tmp
```

## Development

Instructions for developers.

### Building

Build a local container image:

```shell
docker build -t localhost/fnndsc/pl-sclai .
```

### Running

Mount the source code `sclai.py` into a container to try out changes without rebuild.

```shell
docker run --rm -it --userns=host -u $(id -u):$(id -g) \
    -v $PWD/sclai.py:/usr/local/lib/python3.13/site-packages/sclai.py:ro \
    -v $PWD/in:/incoming:ro -v $PWD/out:/outgoing:rw -w /outgoing \
    localhost/fnndsc/pl-sclai sclai /incoming /outgoing
```

### Testing

Run unit tests using `pytest`.
It's recommended to rebuild the image to ensure that sources are up-to-date.
Use the option `--build-arg extras_require=dev` to install extra dependencies for testing.

```shell
docker build -t localhost/fnndsc/pl-sclai:dev --build-arg extras_require=dev .
docker run --rm -it localhost/fnndsc/pl-sclai:dev pytest
```

## Release

Steps for release can be automated by [Github Actions](.github/workflows/ci.yml).
This section is about how to do those steps manually.

### Increase Version Number

Increase the version number in `setup.py` and commit this file.

### Push Container Image

Build and push an image tagged by the version. For example, for version `1.2.3`:

```
docker build -t docker.io/fnndsc/pl-sclai:1.2.3 .
docker push docker.io/fnndsc/pl-sclai:1.2.3
```

### Get JSON Representation

Run [`chris_plugin_info`](https://github.com/FNNDSC/chris_plugin#usage)
to produce a JSON description of this plugin, which can be uploaded to _ChRIS_.

```shell
docker run --rm docker.io/fnndsc/pl-sclai:1.2.3 chris_plugin_info -d docker.io/fnndsc/pl-sclai:1.2.3 > chris_plugin_info.json
```

Intructions on how to upload the plugin to _ChRIS_ can be found here:
https://chrisproject.org/docs/tutorials/upload_plugin
