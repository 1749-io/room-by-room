# Third-party software and example assets

The toolkit's MIT licence applies to its original work. The illustrated examples are listed with their origin, rights notes and reviewed file hashes in the [asset inventory](examples/asset-inventory.json). Site drawings, listing photographs and homeowner material need their own redistribution rights.

The furnished Alder library uses original procedural geometry, materials, book covers and wall art. Its concept photograph was generated from the reviewed Blender camera. The furnished house ZIP embeds those images in its room review and homeowner presentation. The [camera and photograph comparison](examples/furnished-room/reference/review.json) identifies both source files.

## PDF tools

We distribute the toolkit source and the fictional recipient documents. The combined PDF tools use Artifex's open-source AGPLv3 option for PyMuPDF and its MuPDF engine. The original toolkit source retains its MIT copyright and permission notice. A checkout installs the upstream PDF dependency from [requirements-packs.txt](requirements-packs.txt). The release contains no dependency wheels, native libraries, executable installers or container images.

| Component | Version used by the PDF tools | Source |
| --- | --- | --- |
| PyMuPDF | 2.1 | [Upstream source distribution](https://pypi.org/project/PyMuPDF/2.1/#files), SHA-256 `9ac95f98016e83eafb8f1d786396f9c60e400d559590596e5b2df9eb6384948b` |
| MuPDF | 1.28.6 | [Source archive used by the PyMuPDF build](https://mupdf.com/downloads/archive/mupdf-1.28.6-source.tar.gz) and [tagged source tree](https://github.com/ArtifexSoftware/mupdf/tree/1.28.6) |

Keep the applicable copyright and licence notices with redistributed copies. If you distribute a build containing the PDF engine, provide the corresponding source by a method allowed under section 6. Section 13 covers the source offer to remote users of a modified version. The full terms and the publisher's explanation are available here. [AGPLv3](LICENSES/AGPL-3.0.txt) · [Artifex licensing](https://artifex.com/licensing)

The fictional audience PDFs use standard PDF fonts. The [asset inventory](examples/asset-inventory.json) identifies the provenance of the sample content.

## Editable presentations

The editable sample decks use the default Office package in python-pptx 1.0.2. Their opening-slide preview is rendered from the example itself. The package licence follows.

```text
The MIT License (MIT)
Copyright (c) 2013 Steve Canny, https://github.com/scanny

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## Editable workbooks

The toolkit generates the editable schedules with XlsxWriter 3.3.4, copyright 2013–2026 John McNamara, distributed under the BSD 2-Clause licence. The source distribution has SHA-256 `3512f4210622d4040e0f2882e2caf7263a3fd8be876704304314f0e275377fea`. [Upstream source distribution](https://pypi.org/project/XlsxWriter/3.3.4/#files) · [Copyright and licence](https://github.com/jmcnamara/XlsxWriter/blob/RELEASE_3.3.4/LICENSE.txt)
