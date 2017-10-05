**Changelog**

0.5.0
^^^^^

* Add flag triggers (#121)
* Add integration test to Travis to build and deploy a reactive charm (#120)
* Only execute matching hooks in restricted context. (#119)
* Rename "state" to "flag" and deprecate "state" name (#112)
* Allow pluggable alternatives to RelationBase (#111)

0.4.7
^^^^^

* Move docs to ReadTheDocs because PythonHosted is deprecated
* Fix cold loading of relation instances (#106)

0.4.6
^^^^^

* Correct use of templating.render (fixes #93)
* Add comments to bash reactive wrappers
* Use the standard import mechanism with module discovery
