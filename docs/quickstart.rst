Quickstart
==========

Prerequisites
-------------

The only dependency for ``Thorlabs-Elliptec-Motorized-Stages`` is the Python serial library (``pyserial``), which should be installed automatically if using ``pip`` or similar. If you obtain the code by other means, ensure ``pyserial`` is installed and can be found on your Python path.

Installing the Software
-------------------------

Use a virtual environment (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each custom project that uses ``Thorlabs-Elliptec-Motorized-Stages``, create and activate a dedicated Python virtual environment first, then install the package inside that environment. This keeps all required dependencies isolated to that project and avoids conflicts with system-level or other project packages.

Download using pip
~~~~~~~~~~~~~~~~~~

The package installer for Python (``pip``) is the typical method for installation:

.. code-block:: bash

   pip install Thorlabs-Elliptec-Motorized-Stages

Clone from Git
~~~~~~~~~~~~~~

Alternatively, the latest version can be downloaded from the Git repository:

.. code-block:: bash

   git clone https://github.com/few-cycle/Thorlabs-Elliptec-Motorized-Stages.git

and optionally installed to your system using ``pip``:

.. code-block:: bash

   pip install Thorlabs-Elliptec-Motorized-Stages

Minimal example
---------------

.. code-block:: python

   from ElliptecBus.elliptec_bus import ElliptecBus
   from ElliptecRotaryStages.ELL16 import Ell16

   with ElliptecBus("COM18") as bus:
       stage = Ell16(bus, address="0")
       print(stage.get_info())
       print(stage.get_status())
       print(stage.get_position_degrees())

Bench test script
-----------------

The repository includes ``ell16_bench_test.py`` for manual validation.

.. code-block:: bash

   python ell16_bench_test.py COM18 --home --move 90
