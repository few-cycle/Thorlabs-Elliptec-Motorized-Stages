Quickstart
==========

Install dependencies
--------------------

.. code-block:: bash

   pip install pyserial

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
