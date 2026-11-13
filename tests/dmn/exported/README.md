# DMN files exported by other tools

Copies of DMN files written by other modelling tools, for `tests/test_dmn_exported.py`: each is refused, naming why, or
loads and answers. The content is unchanged; git stores the TCK files' line endings as LF, and one file is renamed.

| Folder | Source | Licence | Commit |
|---|---|---|---|
| `tck/` | [DMN TCK](https://github.com/dmn-tck/tck), `TestCases/compliance-level-2/` (models and `-test-01.xml` expected results) | Apache 2.0, stated in its `LICENSE-ASL-2.0.txt` | `5cd912f281831bc535e710aba435e16de198028a` |
| `camunda/dinnerDecisions.dmn` | [camunda-bpm-examples](https://github.com/camunda/camunda-bpm-examples), `dmn-engine/dmn-engine-drg/` | Apache 2.0 | `6c7f4c4adb4beb9a2f5d4c5e49fc1ddfc6dab3fc` |
| `camunda/` (the others) | [camunda-bpm-platform](https://github.com/camunda/camunda-bpm-platform), `engine-dmn/engine/src/test/resources/org/camunda/bpm/dmn/engine/` (`api/`, `el/`) | Apache 2.0 | `ee4826e5e76c2348a1510ef46a2f4ccd3b080e48` |
| `kogito/` | [Apache KIE Kogito examples](https://github.com/apache/incubator-kie-kogito-examples), `kogito-quarkus-examples/` and `kogito-java-examples/` | Apache 2.0, stated in its `licensesheader.txt` | `72d795324427a4fc42a1d465e993d1756570cc20` |

`kogito/traffic_violation.dmn` is `Traffic Violation.dmn` from `dmn-listener-quarkus`, renamed without the space.

The Camunda files carry this notice from their repositories' NOTICE files: "Camunda. Copyright 2013-2025 Camunda
Services GmbH."
