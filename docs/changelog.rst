**Changelog**

1.5.1
^^^^^
Tuesday Sep 20 2022

* Fixing wrong reference (#235)

1.5.0
^^^^^
Tuesday Nov 30 2021

* Support app level relation data on Endpoint (#232)

1.4.1
^^^^^
Friday Feb 19 2021

* Add set_flag and other aliases to RelationBase (#233)

1.4.0
^^^^^
Tuesday Jan 5 2021

* Switch to GitHub Workflows for PR tests (#229)
* Fix config.default.foo automatic flag doc (#223)
* Up-port get_unset_flags from lp:1836063 (#228)
* Add relation factory discovery and trigger callbacks (#227)

1.3.2
^^^^^
Friday July 17 2020

* Drop blacklist in favor of shebang and binary check (#225)

1.3.1
^^^^^
Thursday July 16 2020

* Exclude .pyc and __pycache__ files from discovery (#224)
* Fix typo and update link to action params definition (#220)
* Fix link to charm-helpers in layer-basic docs (#219)
* Reverse diagram to match text (#216)

1.3.0
^^^^^
Monday Aug 26 2019

* Add pattern for request / response Endpoints (#215)
* Update link to the juju docs on debugging (#214)
* Separate layer-options sidenote from the main text (#211)

1.2.1
^^^^^
Wednesday Apr 3 2019

* Fix errant str.format handling of flags in expand_name (#210)
* Remove departed flag when joined (#209)

1.2.0
^^^^^
Wednesday Feb 6 2019

* Add ability to trigger on flag being cleared (#205)
* Add documentation for python_packages layer option (#204)
* Fix docs on upgrade series for final syntax (#203)
* Add OS Series Upgrades to main index (#202)
* Turn on flag and handler log tracing for all charms (#200)
* Update docs around hook.template and call out removing apt package (#199)

1.1.2
^^^^^
Thursday Oct 4 2018

* Adjust imports to work with Python 3.4 (#194)
* Adjust tests to work with older Ubuntu 14.04 (trusty) packages
* Update CI for charm-tools snap confinement change.

1.1.1
^^^^^
Friday Sep 28 2018

* Add is_data_changed to export list (#193)

1.1.0
^^^^^
Friday Sep 28 2018

* Flag and handler trace logging (#191)
* Add non-destructive version of data_changed (#188)

1.0.0
^^^^^
Wednesday Aug 8 2018

* Preliminary support for operating system series upgrades (#183)
* Hotfix for Python 3.4 incompatibility (#181)
* Hotfix adding missed backwards compatibility alias (#176)
* Documentation updates, including merging in core layer docs (#186)
* Acknowledgment by version number that this is mature software
  (and has been for quite some time).

0.6.3
^^^^^
Tuesday Apr 24 2018

* Export endpoint_from_name as well (#174)
* Rename Endpoint.joined to Endpoint.is_joined (#168)
* Only pass one copy of self to Endpoint method handlers (#172)
* Make Endpoint.from_flag return None for unset flags (#173)
* Fix hard-coded version in docs config (#167)
* Fix documentation of unit_name and application_name on RelatedUnit (#165)
* Fix setdefault on Endpoint data collections (#163)

0.6.2
^^^^^
Friday Feb 23 2018

* Hotfix for issue #161 (#162)
* Add diagram showing endpoint workflow and all_departed_units example to docs (#157)
* Fix doc builds on RTD (#156)

0.6.1
^^^^^

* Separate departed units from joined in Endpoint (#153)
* Add deprecated placeholder for RelationBase.from_state (#148)

0.6.0
^^^^^

* Endpoint base for easier interface layers (#123)
* Public API is now only documented via the top level charms.reactive namespace.
  The internal organization of the library is not part of the public API.
* Added layer-basic docs (#144)
* Fix test error from juju-wait snap (#143)
* More doc fixes (#140)
* Update help output in charms.reactive.sh (#136)
* Multiple docs fixes (#134)
* Fix import in triggers.rst (#133)
* Update README (#132)
* Fixed test, order doesn't matter (#131)
* Added FAQ section to docs (#129)
* Deprecations:

  * relation_from_name (renamed to endpoint_from_name)
  * relation_from_flag (renamed to endpoint_from_flag)
  * RelationBase.from_state (use endpoint_from_flag instead)

0.5.0
^^^^^

* Add flag triggers (#121)
* Add integration test to Travis to build and deploy a reactive charm (#120)
* Only execute matching hooks in restricted context. (#119)
* Rename "state" to "flag" and deprecate "state" name (#112)
* Allow pluggable alternatives to RelationBase (#111)
* Deprecations:

  * State
  * StateList
  * set_state (renamed to set_flag)
  * remove_state (renamed to clear_flag)
  * toggle_state (renamed to toggle_flag)
  * is_state (renamed to is_flag_set)
  * all_states (renamed to all_flags)
  * any_states (renamed to any_flags)
  * get_states (renamed to get_flags)
  * get_state
  * only_once
  * relation_from_state (renamed to relation_from_flag)

0.4.7
^^^^^

* Move docs to ReadTheDocs because PythonHosted is deprecated
* Fix cold loading of relation instances (#106)

0.4.6
^^^^^

* Correct use of templating.render (fixes #93)
* Add comments to bash reactive wrappers
* Use the standard import mechanism with module discovery
