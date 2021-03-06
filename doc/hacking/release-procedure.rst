=========================================
Checklist for releasing a new NAV version
=========================================

.. highlight:: sh

.. warning:: This checklist is currently under review, as NAV has moved from
             Mercurial/Launchpad to Git/GitHub.

CI status check
---------------

* Verify that the Jenkins jobs (at https://ci.nav.uninett.no/) related to the
  current stable branch are all green.
* If any tests are failing, these must be resolved before moving forward.


Review milestone for next release in Launchpad
----------------------------------------------

* Check the list of bugs targeted to the upcoming milestone at
  https://launchpad.net/nav .
* Do all the targeted bugs have a status of `Fix Committed`?
* Unless any unfixed bugs are showstoppers, untarget them from this milestone
  to remove clutter.

Getting the code
----------------

* Start by cloning the latest stable branch (or use `hg pull` to update your
  existing clone), e.g. 4.5.x::

    hg clone -b 4.5.x https://nav.uninett.no/hg/default nav
    cd nav


Updating changelog and release notes
------------------------------------

* Generate a list of referenced bugfixes from the changelog since the last
  release::

    hg log -v -r <LASTRELEASE>:tip | ./tools/buglog.py

* Add a new entry to the CHANGES file for for the new release and paste the
  list produced by the above command.

* Verify that all the bugs in this list are in the list of bugs targeted to
  the Launchpad milestone, and vice versa.  Any differences need to be
  resolved manually.

* Once the CHANGES file has been properly updated, commit it, tag the new
  release and push changes back to the official repository::

    hg commit -m 'Update changelog for the upcoming X.Y.Z release'
    hg tag X.Y.Z
    hg push


Rolling and uploading a new distribution tarball
------------------------------------------------

* Update to the newly created tag and create a distribution tarball::

    hg up X.Y.Z
    ./dist.sh -r X.Y.Z

* Create a detached PGP signature of the created tarball::

    gpg --armor --detach-sign nav-X.Y.X.tar.gz

* Browse the Launchpad milestone page and create a new release from the
  milestone.
* Upload the tarball and the detached signature to the release page.
* Set the ``Fix Released`` status on all bug reports targeted to the new
  release.

Announcing the release
----------------------

* Add a new release entry in the homepage admin panel
* Change the topic of the #nav freenode IRC channel to reference the new
  release + Launchpad URL.
* Send email announcement to nav-users. Use previous release announcements as
  your template.
