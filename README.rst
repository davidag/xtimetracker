tt is here to help you manage your time. You want to know how
much time you are spending on your projects? You want to generate a nice
report for your client? tt is here for you.

Quick start
-----------

Installation
~~~~~~~~~~~~

TODO

Usage
~~~~~

Start tracking your activity via:

.. code:: bash

  $ tt start world-domination +cats

With this command, you have started a new **frame** for the *world-domination* project with the *cats* tag. That's it.

Now stop tracking you world domination plan via:

.. code:: bash

  $ tt stop
  Project world-domination [cats] started 8 minutes ago (2016.01.27 13:00:28+0100)

You can log your latest working sessions (aka **frames**) thanks to the ``log`` command:

.. code:: bash

  $ tt log
  Tuesday 26 January 2016 (8m 32s)
        ffb2a4c  13:00 to 13:08      08m 32s   world-domination  [cats]

Please note that, as the report command, the `log` command comes with projects, tags and dates filtering.

To list all available commands use:

.. code:: bash

  $ tt help

License
-------

tt is released under the MIT License. See the bundled LICENSE file for
details.

